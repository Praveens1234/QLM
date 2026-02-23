import pandas as pd
import numpy as np
import os
import uuid
import logging
import zipfile
import requests
import tempfile
import shutil
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional
from backend.core.exceptions import DataError

# Logger
logger = logging.getLogger("QLM.Data")

class DataManager:
    """
    Handles CSV ingestion, validation, and Parquet conversion.
    Supports local upload and remote URL download (CSV/ZIP).
    Enforces strict schema validation using PyArrow.
    """
    
    REQUIRED_COLUMNS = ['open', 'high', 'low', 'close', 'volume']
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def process_url(self, url: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Download dataset from URL (CSV or ZIP containing single CSV), process, and save.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Download
            local_filename = url.split('/')[-1]
            if not local_filename:
                local_filename = f"download_{uuid.uuid4()}.tmp"

            download_path = os.path.join(temp_dir, local_filename)
            logger.info(f"Downloading from {url} to {download_path}...")

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(download_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # 2. Extract if ZIP
            target_csv = download_path

            if download_path.lower().endswith('.zip'):
                logger.info("Detected ZIP file. Extracting safely...")
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    # Zip Slip Protection
                    members = zip_ref.namelist()
                    safe_members = []
                    abs_target = os.path.abspath(temp_dir)

                    for member in members:
                        abs_dest = os.path.abspath(os.path.join(temp_dir, member))
                        if not abs_dest.startswith(abs_target):
                            raise DataError(f"Zip Slip attempt detected: {member}")
                        safe_members.append(member)

                    zip_ref.extractall(temp_dir, members=safe_members)

                # Find CSV
                csv_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.csv') and not f.startswith('__')]

                if len(csv_files) == 0:
                    raise DataError("No CSV file found in the ZIP archive.")
                if len(csv_files) > 1:
                    raise DataError(f"Multiple CSV files found in ZIP ({len(csv_files)}). Please provide a ZIP with exactly one CSV.")

                target_csv = os.path.join(temp_dir, csv_files[0])
                logger.info(f"Found CSV: {csv_files[0]}")

            # 3. Process CSV
            return self._process_csv(target_csv, symbol, timeframe)

        except Exception as e:
            logger.error(f"Error processing URL import: {e}")
            raise DataError(f"Failed to process URL: {str(e)}")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def process_upload(self, file_path: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Process a local CSV upload.
        """
        try:
             return self._process_csv(file_path, symbol, timeframe)
        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            raise DataError(f"Failed to process upload: {str(e)}")

    def _process_csv(self, file_path: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Internal: Validate, parse, sort, and convert CSV to Parquet.
        Returns metadata for the dataset.
        """
        try:
            # 1. Load CSV (Robust Separation Detection)
            try:
                df = pd.read_csv(file_path, skipinitialspace=True, engine='c')
            except Exception:
                # Fallback to python engine with auto separator detection
                df = pd.read_csv(file_path, skipinitialspace=True, sep=None, engine='python')
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower()
            
            # Normalize Date Column
            date_col_candidates = ['date', 'time', 'timestamp', 'datetime', 'dt', 'ts', 'utc']
            found_date = False
            for col in date_col_candidates:
                if col in df.columns:
                    df.rename(columns={col: 'datetime'}, inplace=True)
                    found_date = True
                    break
            
            if not found_date:
                raise DataError(f"Missing datetime column. Expected one of: {date_col_candidates}")

            # Check Required Columns
            missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
            if missing:
                raise DataError(f"Missing required columns: {missing}")

            # 2. Parse Datetime (Strict UTC with European DayFirst support)
            original_len = len(df)
            
            # Robust tiered parsing approach
            try:
                # Attempt 1: Explicit mixed parsing with Day-First bias (fixes DD.MM.YYYY overriding to MM.DD.YYYY)
                df['datetime'] = pd.to_datetime(df['datetime'], utc=True, dayfirst=True, format='mixed', errors='coerce')
            except Exception:
                try:
                    # Attempt 2: Fallback ISO
                    df['datetime'] = pd.to_datetime(df['datetime'], utc=True, errors='coerce')
                except Exception:
                    pass

            # Drop NaT
            if df['datetime'].isna().any():
                n_dropped = df['datetime'].isna().sum()
                drop_ratio = n_dropped / original_len
                
                # Fatal Error if more than 1% of the dataset cannot be parsed into a date (Massive corruption protection)
                if drop_ratio > 0.01:
                    raise DataError(f"Fatal Dataset Corruption: {n_dropped} rows ({drop_ratio*100:.1f}%) have unparseable dates. Check CSV format (expected YYYY-MM-DD or DD.MM.YYYY).")
                    
                logger.warning(f"Dropping {n_dropped} rows with invalid datetime.")
                df = df.dropna(subset=['datetime'])
            
            if df.empty:
                raise DataError("Dataset is completely empty after date parsing.")

            # 3. Numeric Conversion & Cleaning
            cols_to_numeric = ['open', 'high', 'low', 'close', 'volume']
            for col in cols_to_numeric:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Drop rows with NaN in OHLC
            df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
            
            if df.empty:
                raise DataError("Dataset is empty after removing NaNs.")

            # 4. Sort & Deduplicate
            df.sort_values('datetime', inplace=True)
            df.drop_duplicates(subset=['datetime'], keep='first', inplace=True)
            
            # 5. Create 'dtv' (int64 nanoseconds)
            df['dtv'] = df['datetime'].astype('int64')

            # 6. Detect Timeframe (in seconds)
            diffs = df['dtv'].diff().dropna() / 1e9 # seconds
            mode_diff = diffs.mode()
            detected_tf = int(mode_diff.iloc[0]) if not mode_diff.empty else 0

            # 7. Convert to PyArrow Table (Enforce Schema)
            schema = pa.schema([
                ('datetime', pa.timestamp('ns', tz='UTC')),
                ('open', pa.float64()),
                ('high', pa.float64()),
                ('low', pa.float64()),
                ('close', pa.float64()),
                ('volume', pa.float64()),
                ('dtv', pa.int64())
            ])

            table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)

            # 8. Save Parquet
            dataset_id = str(uuid.uuid4())
            parquet_filename = f"{dataset_id}.parquet"
            parquet_path = os.path.join(self.data_dir, parquet_filename)
            
            pq.write_table(table, parquet_path)
            
            # 9. Return Metadata
            return {
                "id": dataset_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "detected_tf_sec": detected_tf,
                "start_date": df['datetime'].iloc[0].isoformat(),
                "end_date": df['datetime'].iloc[-1].isoformat(),
                "row_count": len(df),
                "file_path": parquet_path,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            if isinstance(e, DataError):
                raise e
            raise DataError(f"Processing failed: {str(e)}")

    def load_dataset(self, file_path: str) -> pd.DataFrame:
        """
        Load dataset efficiently using PyArrow.
        """
        if not os.path.exists(file_path):
             raise DataError(f"Dataset file not found: {file_path}")

        try:
            return pd.read_parquet(file_path, engine='pyarrow')
        except Exception as e:
            raise DataError(f"Failed to load Parquet file: {e}")

    def scan_discrepancies(self, file_path: str, detected_tf_sec: int) -> List[Dict[str, Any]]:
        """
        Scans a PyArrow parquet dataset for OHLC zero values, negative prices, logic inversions, massive spikes, and missing time gaps.
        """
        df = self.load_dataset(file_path)
        discrepancies = []
        
        # Helper: add discrepancy safely up to a cap
        def _add_disc(_type, _idx, _msg):
            if len(discrepancies) < 1000:
                discrepancies.append({
                    "type": _type,
                    "index": int(_idx),
                    "timestamp": df['datetime'].iloc[_idx].isoformat(),
                    "details": _msg
                })

        # 1. Zero OHLC
        zero_mask = (df['open'] == 0) | (df['high'] == 0) | (df['low'] == 0) | (df['close'] == 0)
        for idx in np.where(zero_mask)[0][:100]:
            _add_disc("ZERO_VALUE", idx, "One or more OHLC values are exactly 0.")
            
        # 2. Negative Values
        neg_mask = (df['open'] < 0) | (df['high'] < 0) | (df['low'] < 0) | (df['close'] < 0) | (df['volume'] < 0)
        for idx in np.where(neg_mask)[0][:100]:
            _add_disc("NEGATIVE_VALUE", idx, "Negative price or volume detected. Data corruption likely.")
            
        # 3. Logic Errors (High < Low, Close > High, Close < Low, Open > High, Open < Low)
        logic_mask = (df['high'] < df['low']) | (df['close'] > df['high']) | (df['close'] < df['low']) | (df['open'] > df['high']) | (df['open'] < df['low'])
        for idx in np.where(logic_mask)[0][:100]:
            _add_disc("LOGIC_ERROR", idx, "Price bounds inverted (e.g., High is lower than Low, or Close is outside bounds).")
            
        # 4. Massive Price Spikes (>15% intrabar jump relative to open)
        # Using vectorized absolute percentage change based on open price
        with np.errstate(divide='ignore', invalid='ignore'):
            spike_mask = (np.abs(df['high'] - df['low']) / df['open']) > 0.15
        spike_mask = spike_mask & ~zero_mask & ~neg_mask # Only flag if not already flagged as zero/neg
        for idx in np.where(spike_mask)[0][:100]:
            _add_disc("PRICE_SPIKE", idx, "Massive intrabar anomaly (>15% jump). Suspected bad API tick.")

        # 5. Time Gaps (Missing Bars)
        if detected_tf_sec > 0:
            diffs = df['dtv'].diff() / 1e9  # in seconds
            gap_mask = diffs > (detected_tf_sec * 1.5) # Allow 50% jitter
            for idx in np.where(gap_mask)[0][:100]:
                gap_sec = diffs.iloc[idx]
                expected_missing = int(gap_sec // detected_tf_sec) - 1
                if expected_missing > 0:
                    _add_disc("TIME_GAP", idx, f"Gap of {gap_sec}s ending here. Approx {expected_missing} bars missing.")
                
        # Sort by index descending (newest rows first visually)
        discrepancies.sort(key=lambda x: x['index'], reverse=True)
        return discrepancies

    def delete_dataset_row(self, file_path: str, index: int) -> None:
        """
        Deletes a specific row by its global index from the Parquet dataset safely.
        """
        df = self.load_dataset(file_path)
        if index < 0 or index >= len(df):
            raise DataError(f"Index {index} out of bounds.")
            
        df = df.drop(index)
        df.reset_index(drop=True, inplace=True)
        
        schema = pa.schema([
            ('datetime', pa.timestamp('ns', tz='UTC')),
            ('open', pa.float64()),
            ('high', pa.float64()),
            ('low', pa.float64()),
            ('close', pa.float64()),
            ('volume', pa.float64()),
            ('dtv', pa.int64())
        ])
        table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
        pq.write_table(table, file_path)
        
    def autofix_dataset_row(self, file_path: str, index: int) -> None:
        """
        Automatically fixes Logic Errors (High < Low) by swapping them, and bounding Open/Close within High/Low.
        """
        df = self.load_dataset(file_path)
        if index < 0 or index >= len(df):
            raise DataError("Index out of bounds.")
            
        row = df.iloc[index]
        o, h, l, c = row['open'], row['high'], row['low'], row['close']
        
        # 1. Swap high/low if inverted
        if h < l:
            h, l = l, h
            df.at[index, 'high'] = h
            df.at[index, 'low'] = l
            
        # 2. Bound Open and Close
        if o > h: df.at[index, 'open'] = h
        if o < l: df.at[index, 'open'] = l
        if c > h: df.at[index, 'close'] = h
        if c < l: df.at[index, 'close'] = l
        
        schema = pa.schema([
            ('datetime', pa.timestamp('ns', tz='UTC')),
            ('open', pa.float64()),
            ('high', pa.float64()),
            ('low', pa.float64()),
            ('close', pa.float64()),
            ('volume', pa.float64()),
            ('dtv', pa.int64())
        ])
        table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
        pq.write_table(table, file_path)

    def interpolate_dataset_gap(self, file_path: str, index_after_gap: int, detected_tf_sec: int) -> int:
        """
        Interpolates missing rows into a TIME_GAP.
        `index_after_gap` is the index of the row directly following the gap.
        Returns the number of rows inserted.
        """
        df = self.load_dataset(file_path)
        if index_after_gap <= 0 or index_after_gap >= len(df):
            raise DataError("Invalid gap index.")
            
        row_after = df.iloc[index_after_gap]
        row_before = df.iloc[index_after_gap - 1]
        
        gap_sec = (row_after['dtv'] - row_before['dtv']) / 1e9
        num_missing = int(gap_sec // detected_tf_sec) - 1
        
        if num_missing <= 0 or num_missing > 5000: # Safety clamp to prevent memory explosion on massive gaps
            raise DataError(f"Calculated missing bars ({num_missing}) is invalid or dangerously large (>5000). Cannot safely auto-interpolate.")
            
        # Generate new timestamps
        new_dtvs = [row_before['dtv'] + int((i + 1) * detected_tf_sec * 1e9) for i in range(num_missing)]
        new_datetimes = pd.to_datetime(new_dtvs, utc=True)
        
        # Linear Interp for Close prices (Simulate a straight line connecting the gap)
        c_start, c_end = row_before['close'], row_after['close']
        step = (c_end - c_start) / (num_missing + 1)
        
        new_rows = []
        for i in range(num_missing):
            sim_close = c_start + (step * (i + 1))
            new_rows.append({
                'datetime': new_datetimes[i],
                'open': sim_close, # Flat synthetic bars
                'high': sim_close,
                'low': sim_close,
                'close': sim_close,
                'volume': 0.0,
                'dtv': new_dtvs[i]
            })
            
        new_df = pd.DataFrame(new_rows)
        # Split and Insert
        df_top = df.iloc[:index_after_gap]
        df_bottom = df.iloc[index_after_gap:]
        
        final_df = pd.concat([df_top, new_df, df_bottom]).reset_index(drop=True)
        
        schema = pa.schema([
            ('datetime', pa.timestamp('ns', tz='UTC')),
            ('open', pa.float64()),
            ('high', pa.float64()),
            ('low', pa.float64()),
            ('close', pa.float64()),
            ('volume', pa.float64()),
            ('dtv', pa.int64())
        ])
        table = pa.Table.from_pandas(final_df, schema=schema, preserve_index=False)
        pq.write_table(table, file_path)
        return num_missing

    def get_dataset_window(self, file_path: str, center_index: int, window: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves a window of rows around a specific index for context and inline editing.
        """
        df = self.load_dataset(file_path)
        start_idx = max(0, center_index - window)
        end_idx = min(len(df), center_index + window + 1)
        
        sub_df = df.iloc[start_idx:end_idx].copy()
        
        records = sub_df.to_dict(orient='records')
        # Inject global row index references into the dict for deterministic updates
        for i, row in enumerate(records):
            row['index'] = start_idx + i
            row['datetime'] = row['datetime'].isoformat() if hasattr(row['datetime'], 'isoformat') else str(row['datetime'])
            
        return records

    def inspect_dataset_row(self, file_path: str, query: str) -> Dict[str, Any]:
        """
        Takes a string query (either an integer index or a datetime string)
        and finds the corresponding row index, then delegates to get_dataset_window.
        """
        df = self.load_dataset(file_path)
        
        # Try finding by exact Integer Index first
        try:
            target_idx = int(query)
            if target_idx < 0 or target_idx >= len(df):
                raise ValueError("Index out of bounds.")
        except ValueError:
            # Not an integer, try treating it as a Datetime string
            try:
                dt_query = pd.to_datetime(query, utc=True, dayfirst=True)
                
                # We need to find the closest row or exact row
                # df['datetime'] is a timezone aware pandas Series
                diffs = (df['datetime'] - dt_query).abs()
                target_idx = int(diffs.idxmin())
            except Exception:
                raise DataError(f"Could not parse query '{query}' as either an index or a valid Date/Time.")
                
        # Get context window
        context = self.get_dataset_window(file_path, target_idx, window=5)
        
        return {
            "query": query,
            "target_index": target_idx,
            "target_datetime": df.iloc[target_idx]['datetime'].isoformat(),
            "context": context
        }

    def update_dataset_row(self, file_path: str, index: int, updates: Dict[str, float]) -> None:
        """
        Saves individual row edits directly back into the PyArrow Parquet file safely enforcing correct schemas.
        """
        df = self.load_dataset(file_path)
        if index < 0 or index >= len(df):
            raise DataError(f"Index {index} out of bounds.")
            
        # Update strictly mapped allowed cols
        allowed_cols = ['open', 'high', 'low', 'close', 'volume']
        for k, v in updates.items():
            if k in allowed_cols:
                df.at[index, k] = float(v)
                
        # Re-save
        schema = pa.schema([
            ('datetime', pa.timestamp('ns', tz='UTC')),
            ('open', pa.float64()),
            ('high', pa.float64()),
            ('low', pa.float64()),
            ('close', pa.float64()),
            ('volume', pa.float64()),
            ('dtv', pa.int64())
        ])
        table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
        pq.write_table(table, file_path)

