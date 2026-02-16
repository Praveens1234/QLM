import pandas as pd
import numpy as np
import os
import uuid
import logging
import zipfile
import requests
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List

# Logger
logger = logging.getLogger("QLM.Data")

class DataManager:
    """
    Handles CSV ingestion, validation, and Parquet conversion.
    Supports local upload and remote URL download (CSV/ZIP).
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
                local_filename = "downloaded_file"

            download_path = os.path.join(temp_dir, local_filename)
            logger.info(f"Downloading from {url} to {download_path}...")

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

            with requests.get(url, headers=headers, stream=True, timeout=30) as r:
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
                        # Normalize path to prevent traversal
                        abs_dest = os.path.abspath(os.path.join(temp_dir, member))
                        if not abs_dest.startswith(abs_target):
                            raise ValueError(f"Zip Slip attempt detected: {member}")
                        safe_members.append(member)

                    zip_ref.extractall(temp_dir, members=safe_members)

                # Find CSV
                csv_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.csv')]
                csv_files = [f for f in csv_files if not f.startswith('__')]

                if len(csv_files) == 0:
                    raise ValueError("No CSV file found in the ZIP archive.")
                if len(csv_files) > 1:
                    raise ValueError(f"Multiple CSV files found in ZIP ({len(csv_files)}). Please provide a ZIP with exactly one CSV.")

                target_csv = os.path.join(temp_dir, csv_files[0])
                logger.info(f"Found CSV: {csv_files[0]}")

            # 3. Process CSV
            return self._process_csv(target_csv, symbol, timeframe)

        except Exception as e:
            logger.error(f"Error processing URL import: {e}")
            raise e
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def process_upload(self, file_path: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Process a local CSV upload.
        """
        return self._process_csv(file_path, symbol, timeframe)

    def save_dataframe(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Process and save an existing DataFrame (from yfinance or other sources).
        Assumes columns: [open, high, low, close, volume, datetime]
        """
        # Clean column names
        df.columns = df.columns.str.strip().str.lower()

        # Normalize datetime column
        for col in ['utc', 'date', 'time', 'timestamp']:
            if col in df.columns and 'datetime' not in df.columns:
                df.rename(columns={col: 'datetime'}, inplace=True)
                break

        return self._clean_and_save(df, symbol, timeframe)

    def _process_csv(self, file_path: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Internal: Validate, parse, sort, and convert CSV to Parquet.
        Returns metadata for the dataset.
        """
        try:
            # 1. Load CSV (Try to infer separator)
            try:
                df = pd.read_csv(file_path, skipinitialspace=True)
            except Exception:
                 # Fallback to python engine with auto detection
                df = pd.read_csv(file_path, skipinitialspace=True, sep=None, engine='python')
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower()
            
            # 2. Validate Structure & Normalization
            for col in ['utc', 'date', 'time', 'timestamp']:
                if col in df.columns:
                    df.rename(columns={col: 'datetime'}, inplace=True)
                    break

            return self._clean_and_save(df, symbol, timeframe)

        except Exception as e:
            logger.error(f"Error processing csv: {e}")
            raise e

    def _clean_and_save(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        try:
            self._validate_columns(df)
            
            # 3. Parse Datetime
            # Convert column to string first to handle mixed types
            dt_col = df['datetime'].astype(str).str.strip()

            # Remove common suffixes
            dt_col = dt_col.str.replace(' UTC', '', regex=False).str.replace(' GMT', '', regex=False).str.replace('Z', '', regex=False)

            # Try to infer format using pandas to_datetime (which is usually good)
            # We enforce UTC
            try:
                # First attempt: standard ISO or mixed
                df['datetime'] = pd.to_datetime(dt_col, utc=True, errors='raise')
            except Exception:
                # Second attempt: Day first (European)
                try:
                    df['datetime'] = pd.to_datetime(dt_col, utc=True, dayfirst=True, errors='raise')
                except Exception:
                    # Third attempt: manual format string for some common crypto data
                    try:
                        df['datetime'] = pd.to_datetime(dt_col, format='%d.%m.%Y %H:%M:%S', utc=True)
                    except Exception as e:
                         raise ValueError(f"Could not parse datetime column. Ensure standard ISO 8601 or 'dd.mm.yyyy HH:MM:SS' format. Error: {e}")

            # Drop rows with NaT
            if df['datetime'].isna().any():
                logger.warning(f"Dropping {df['datetime'].isna().sum()} rows with invalid dates.")
                df = df.dropna(subset=['datetime'])

            # Convert to int64 nanoseconds (Unix epoch)
            # Ensure we have datetime64[ns, UTC]
            if df['datetime'].dtype != 'datetime64[ns, UTC]':
                df['datetime'] = df['datetime'].dt.tz_convert('UTC')

            df['dtv'] = df['datetime'].astype('int64') # nanoseconds since epoch
            
            # 4. Sort and Validate Continuity
            df = df.sort_values(by='dtv').reset_index(drop=True)
            
            # Check duplicates
            if not df['dtv'].is_unique:
                logger.warning("Duplicate timestamps found. Dropping duplicates (keeping first).")
                df = df.drop_duplicates(subset=['dtv'], keep='first').reset_index(drop=True)
            
            # 5. Detect Timeframe
            detected_tf_sec = self._detect_timeframe(df)
            
            # 6. Save as Parquet
            dataset_id = str(uuid.uuid4())
            parquet_filename = f"{dataset_id}.parquet"
            parquet_path = os.path.join(self.data_dir, parquet_filename)
            
            # Select and cast columns
            final_df = pd.DataFrame()
            final_df['datetime'] = df['datetime']
            final_df['dtv'] = df['dtv']

            for col in ['open', 'high', 'low', 'close', 'volume']:
                # Coerce to numeric, clean bad chars
                final_df[col] = pd.to_numeric(df[col], errors='coerce')

            # Drop rows with NaNs in OHLC
            if final_df[['open', 'high', 'low', 'close']].isna().any().any():
                dropped = final_df[final_df[['open', 'high', 'low', 'close']].isna().any(axis=1)].shape[0]
                logger.warning(f"Dropping {dropped} rows with NaN OHLC data.")
                final_df = final_df.dropna(subset=['open', 'high', 'low', 'close'])
                
            final_df.to_parquet(parquet_path, engine='pyarrow', index=False)
            
            # 7. Generate Metadata
            metadata = {
                "id": dataset_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "detected_tf_sec": int(detected_tf_sec),
                "start_date": final_df['datetime'].iloc[0].isoformat(),
                "end_date": final_df['datetime'].iloc[-1].isoformat(),
                "row_count": len(final_df),
                "file_path": parquet_path,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return metadata
        except Exception as e:
            logger.error(f"Error clean and save: {e}")
            raise e

    def _validate_columns(self, df: pd.DataFrame):
        if 'datetime' not in df.columns:
             raise ValueError("Missing required column: datetime (or date/time/utc/timestamp)")

        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def _detect_timeframe(self, df: pd.DataFrame) -> int:
        if len(df) < 2:
            return 0
        
        # Calculate diff in seconds
        diffs = df['dtv'].diff().dropna() / 1e9
        # Get mode (most frequent interval)
        mode_val = diffs.mode()
        if not mode_val.empty:
            return int(mode_val.iloc[0])
        return 0

    def load_dataset(self, file_path: str) -> pd.DataFrame:
        if not os.path.exists(file_path):
             raise FileNotFoundError(f"Dataset file not found: {file_path}")
        return pd.read_parquet(file_path)
