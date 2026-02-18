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

            # 2. Parse Datetime (Strict UTC)
            # Handle various formats
            try:
                # Try fast path (ISO8601)
                df['datetime'] = pd.to_datetime(df['datetime'], utc=True, errors='coerce')
            except Exception:
                pass

            # Drop NaT
            if df['datetime'].isna().any():
                n_dropped = df['datetime'].isna().sum()
                logger.warning(f"Dropping {n_dropped} rows with invalid datetime.")
                df = df.dropna(subset=['datetime'])
            
            if df.empty:
                raise DataError("Dataset is empty after date parsing.")

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
