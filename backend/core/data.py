import pandas as pd
import numpy as np
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

# Logger
logger = logging.getLogger("QLM.Data")

class DataManager:
    """
    Handles CSV ingestion, validation, and Parquet conversion.
    """
    
    REQUIRED_COLUMNS = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def process_upload(self, file_path: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Process a raw CSV upload: validate, parse, sort, and convert to Parquet.
        Returns metadata for the dataset.
        """
        try:
            # 1. Load CSV
            # Format: dd.mm.yyyy hh:mm:ss
            df = pd.read_csv(file_path, skipinitialspace=True)
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower()
            
            # 2. Validate Structure
            self._validate_columns(df)
            
            # 3. Parse Datetime to UTC Epoch
            # Ensure strings are stripped of whitespace
            df['datetime'] = df['datetime'].astype(str).str.strip()
                
            try:
                # Try ISO first (common)
                df['datetime'] = pd.to_datetime(df['datetime'], errors='raise', utc=True)
            except (ValueError, TypeError):
                # Fallback to specific format d.m.y h:m:s
                try:
                    df['datetime'] = pd.to_datetime(df['datetime'], format='%d.%m.%Y %H:%M:%S', errors='raise')
                    df['datetime'] = df['datetime'].dt.tz_localize('UTC', ambiguous='raise', nonexistent='raise')
                except Exception:
                    # Final attempt: mixed format
                    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce', utc=True)
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
            
            # Standardize logic: dtv, open, high, low, close, volume (all float64 except dtv)
            final_df = df[['dtv', 'open', 'high', 'low', 'close', 'volume']].copy()
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
            logger.error(f"Error processing upload: {e}")
            raise e

    def _validate_columns(self, df: pd.DataFrame):
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
