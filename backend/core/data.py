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
from typing import Dict, Any, Tuple

# Logger
logger = logging.getLogger("QLM.Data")

class DataManager:
    """
    Handles CSV ingestion, validation, and Parquet conversion.
    Supports local upload and remote URL download (CSV/ZIP).
    """
    
    # We allow 'datetime' or 'utc' for timestamp
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

            # Use requests with a user agent to avoid basic blocks
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            with requests.get(url, headers=headers, stream=True) as r:
                r.raise_for_status()
                with open(download_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # 2. Extract if ZIP
            target_csv = download_path

            if download_path.lower().endswith('.zip'):
                logger.info("Detected ZIP file. Extracting...")

                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    # Security Check: Zip Slip
                    # Validate all members before extraction
                    members = zip_ref.namelist()
                    safe_members = []

                    for member in members:
                        # Normalize path
                        member_path = os.path.normpath(member)
                        # Check for traversal
                        if member_path.startswith("..") or os.path.isabs(member_path):
                             logger.warning(f"Skipping unsafe file in zip: {member}")
                             continue

                        # We only care about CSVs in the root or direct folders for now,
                        # but let's extract safe files.
                        # Actually, we extract everything safe to temp_dir
                        safe_members.append(member)

                    if not safe_members:
                        raise ValueError("No safe files found in ZIP archive.")

                    zip_ref.extractall(temp_dir, members=safe_members)

                # Find CSV
                csv_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                         if file.lower().endswith('.csv') and not file.startswith('__'):
                             csv_files.append(os.path.join(root, file))

                if len(csv_files) == 0:
                    raise ValueError("No CSV file found in the ZIP archive.")
                if len(csv_files) > 1:
                     # Strict rule: only 1 CSV allowed to avoid ambiguity
                    raise ValueError(f"Multiple CSV files found in ZIP ({len(csv_files)}). Please provide a ZIP with exactly one CSV.")

                target_csv = csv_files[0]
                logger.info(f"Found CSV: {target_csv}")

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

    def _process_csv(self, file_path: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Internal: Validate, parse, sort, and convert CSV to Parquet.
        Returns metadata for the dataset.
        """
        try:
            # 1. Load CSV
            # Format: dd.mm.yyyy hh:mm:ss
            df = pd.read_csv(file_path, skipinitialspace=True)
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower()
            
            # 2. Validate Structure & Normalization
            # Rename 'utc' or 'date' or 'time' to 'datetime' if present
            for col in ['utc', 'date', 'time', 'timestamp']:
                if col in df.columns:
                    df.rename(columns={col: 'datetime'}, inplace=True)
                    break

            self._validate_columns(df)
            
            # 3. Parse Datetime to UTC Epoch
            # Ensure strings are stripped of whitespace
            df['datetime'] = df['datetime'].astype(str).str.strip()

            # Clean common garbage like " UTC" suffix in values
            df['datetime'] = df['datetime'].str.replace(' UTC', '', regex=False).str.replace(' GMT', '', regex=False)
                
            try:
                # Try ISO first (common)
                df['datetime'] = pd.to_datetime(df['datetime'], errors='raise', utc=True)
            except (ValueError, TypeError):
                # Fallback to specific format d.m.y h:m:s
                try:
                    df['datetime'] = pd.to_datetime(df['datetime'], format='%d.%m.%Y %H:%M:%S', errors='raise')
                    df['datetime'] = df['datetime'].dt.tz_localize('UTC', ambiguous='raise', nonexistent='raise')
                except Exception:
                    # Fallback to d.m.y h:m:s.f
                    try:
                        df['datetime'] = pd.to_datetime(df['datetime'], format='%d.%m.%Y %H:%M:%S.%f', errors='raise')
                        df['datetime'] = df['datetime'].dt.tz_localize('UTC', ambiguous='raise', nonexistent='raise')
                    except Exception:
                        # Final attempt: mixed format
                        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce', utc=True)
                        if df['datetime'].isna().any():
                            # Try parsing with dayfirst=True for DD.MM.YYYY
                            try:
                                 df['datetime'] = pd.to_datetime(df['datetime'], dayfirst=True, errors='coerce', utc=True)
                            except:
                                 pass

                        if df['datetime'].isna().any():
                             raise ValueError("Could not parse datetime column. Ensure standard ISO or 'dd.mm.yyyy HH:MM:SS' format.")
            
            # Convert to int64 nanoseconds (Unix epoch)
            # stored as int64 in parquet for efficiency
            try:
                df['datetime'] = df['datetime'].dt.as_unit('ns')
            except Exception:
                # Fallback for older pandas or if as_unit fails
                df['datetime'] = df['datetime'].astype('datetime64[ns, UTC]')
                
            df['dtv'] = df['datetime'].astype('int64') # nanoseconds since epoch
            
            # 4. Sort and Validate Continuity
            df = df.sort_values(by='dtv').reset_index(drop=True)
            
            if df['dtv'].is_unique is False:
                raise ValueError("Duplicate timestamps found in dataset.")
            
            # 5. Detect Timeframe (Simple Check)
            detected_tf_sec = self._detect_timeframe(df)
            
            # 6. Save as Parquet
            dataset_id = str(uuid.uuid4())
            parquet_filename = f"{dataset_id}.parquet"
            parquet_path = os.path.join(self.data_dir, parquet_filename)
            
            # Standardize logic: datetime, dtv, open, high, low, close, volume (all float64 except dtv/datetime)
            final_df = df[['datetime', 'dtv', 'open', 'high', 'low', 'close', 'volume']].copy()
            for col in ['open', 'high', 'low', 'close', 'volume']:
                final_df[col] = final_df[col].astype('float64')
                
            final_df.to_parquet(parquet_path, engine='pyarrow', index=False)
            
            # 7. Generate Metadata
            metadata = {
                "id": dataset_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "detected_tf_sec": detected_tf_sec,
                "start_date": df['datetime'].iloc[0].isoformat(),
                "end_date": df['datetime'].iloc[-1].isoformat(),
                "row_count": len(final_df),
                "file_path": parquet_path,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return metadata

        except Exception as e:
            logger.error(f"Error processing csv: {e}")
            raise e

    def _validate_columns(self, df: pd.DataFrame):
        # We need datetime (or alias) plus OHLCV
        if 'datetime' not in df.columns:
             raise ValueError("Missing required column: datetime (or date/time/utc/timestamp)")

        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def _detect_timeframe(self, df: pd.DataFrame) -> int:
        if len(df) < 2:
            return 0
        
        # Calculate diff in seconds
        # dtv is in nanoseconds, so / 1e9
        diffs = df['dtv'].diff().dropna() / 1e9
        mode_val = diffs.mode()
        if not mode_val.empty:
            return int(mode_val.iloc[0])
        return 0

    def load_dataset(self, file_path: str) -> pd.DataFrame:
        return pd.read_parquet(file_path)
