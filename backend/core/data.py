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
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List, Optional
from backend.core.exceptions import DataError

logger = logging.getLogger("QLM.Data")

# ─── Shared Parquet Schema ───────────────────────────────────────────────────
# Single source of truth for dataset schema — used everywhere data is written.
PARQUET_SCHEMA = pa.schema([
    ('datetime', pa.timestamp('ns', tz='UTC')),
    ('open', pa.float64()),
    ('high', pa.float64()),
    ('low', pa.float64()),
    ('close', pa.float64()),
    ('volume', pa.float64()),
    ('dtv', pa.int64()),
])


# ─── Market Calendar ────────────────────────────────────────────────────────
class MarketCalendar:
    """
    Forex market calendar.  Forex trades Sun 17:00 ET → Fri 17:00 ET continuously.
    ET = UTC-5 (EST) or UTC-4 (EDT).  We use a simplified UTC model:
      - Market CLOSED: Saturday 00:00 UTC → Sunday 22:00 UTC (approximation)
      - Market OPEN:  Sunday 22:00 UTC → Friday 22:00 UTC

    This is a practical approximation.  Holiday closures (Christmas, New Year)
    are NOT modelled — they vary by broker — but the engine will naturally skip
    bars that are absent from the dataset for those periods.
    """

    # UTC weekday boundaries (Mon=0 … Sun=6)
    # Closed window:  Friday 22:00 UTC  →  Sunday 22:00 UTC
    MARKET_CLOSE_WEEKDAY = 4   # Friday
    MARKET_CLOSE_HOUR = 22     # 22:00 UTC
    MARKET_OPEN_WEEKDAY = 6    # Sunday
    MARKET_OPEN_HOUR = 22      # 22:00 UTC

    @classmethod
    def is_market_closed(cls, ts_utc: pd.Timestamp) -> bool:
        """Return True if the given UTC timestamp falls in the weekend closure."""
        wd = ts_utc.weekday()
        hour = ts_utc.hour

        # Saturday: always closed
        if wd == 5:
            return True
        # Sunday before 22:00 UTC: closed
        if wd == 6 and hour < cls.MARKET_OPEN_HOUR:
            return True
        # Friday at or after 22:00 UTC: closed
        if wd == 4 and hour >= cls.MARKET_CLOSE_HOUR:
            return True
        return False

    @classmethod
    def classify_gap(cls, gap_start_ns: int, gap_end_ns: int, tf_sec: int) -> str:
        """
        Classify a time gap between two consecutive bars.

        Returns:
            "MARKET_CLOSURE" — gap spans the weekly weekend closure
            "EXPECTED"       — gap is ≤ 1.5× the timeframe (normal jitter)
            "UNEXPECTED"     — gap is too large but doesn't span the weekend
        """
        gap_sec = (gap_end_ns - gap_start_ns) / 1e9

        # Within normal jitter
        if gap_sec <= tf_sec * 1.5:
            return "EXPECTED"

        ts_start = pd.Timestamp(gap_start_ns, unit='ns', tz='UTC')
        ts_end = pd.Timestamp(gap_end_ns, unit='ns', tz='UTC')

        # Check if the gap spans through the weekend closure
        # Walk from start forward — if we hit the Friday close and the end
        # is on Sunday/Monday, it's a market closure gap.
        if cls._spans_weekend(ts_start, ts_end):
            return "MARKET_CLOSURE"

        return "UNEXPECTED"

    @classmethod
    def _spans_weekend(cls, ts_start: pd.Timestamp, ts_end: pd.Timestamp) -> bool:
        """Check if the gap spans from before Friday 22:00 to after Sunday 22:00."""
        # Find the Friday 22:00 UTC on or after ts_start
        days_to_friday = (4 - ts_start.weekday()) % 7
        if days_to_friday == 0 and ts_start.hour >= cls.MARKET_CLOSE_HOUR:
            # Already past Friday close — look at NEXT Friday
            days_to_friday = 7
        friday_close = ts_start.normalize() + pd.Timedelta(days=days_to_friday, hours=cls.MARKET_CLOSE_HOUR)

        # Find the corresponding Sunday 22:00 UTC
        sunday_open = friday_close + pd.Timedelta(days=2)  # Fri → Sun

        # Gap spans if start is before fri close AND end is after sun open
        return ts_start <= friday_close and ts_end >= sunday_open

    @classmethod
    def build_market_closed_mask(cls, timestamps_ns: np.ndarray) -> np.ndarray:
        """
        Build a boolean array: True for each bar that falls during market closure.
        Uses vectorised weekday/hour computation for performance.
        """
        ts_series = pd.to_datetime(timestamps_ns, unit='ns', utc=True)
        weekdays = ts_series.weekday.values  # 0=Mon … 6=Sun
        hours = ts_series.hour.values

        mask = np.zeros(len(timestamps_ns), dtype=np.bool_)
        mask |= (weekdays == 5)                                       # Saturday
        mask |= (weekdays == 6) & (hours < cls.MARKET_OPEN_HOUR)     # Sunday before 22:00
        mask |= (weekdays == 4) & (hours >= cls.MARKET_CLOSE_HOUR)   # Friday >= 22:00
        return mask


# ─── DataManager ─────────────────────────────────────────────────────────────
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

    # ── Public API ──────────────────────────────────────────────────────────

    def process_url(self, url: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Download dataset from URL (CSV or ZIP containing single CSV), process, and save."""
        temp_dir = tempfile.mkdtemp()
        try:
            local_filename = url.split('/')[-1] or f"download_{uuid.uuid4()}.tmp"
            download_path = os.path.join(temp_dir, local_filename)
            logger.info(f"Downloading from {url} to {download_path}...")

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(download_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            target_csv = download_path
            if download_path.lower().endswith('.zip'):
                target_csv = self._extract_csv_from_zip(download_path, temp_dir)

            return self._process_csv(target_csv, symbol, timeframe)

        except DataError:
            raise
        except Exception as e:
            logger.error(f"Error processing URL import: {e}")
            raise DataError(f"Failed to process URL: {str(e)}")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def process_upload(self, file_path: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Process a local CSV upload."""
        try:
            return self._process_csv(file_path, symbol, timeframe)
        except DataError:
            raise
        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            raise DataError(f"Failed to process upload: {str(e)}")

    def load_dataset(self, file_path: str) -> pd.DataFrame:
        """Load dataset efficiently using PyArrow."""
        if not os.path.exists(file_path):
            raise DataError(f"Dataset file not found: {file_path}")
        try:
            return pd.read_parquet(file_path, engine='pyarrow')
        except Exception as e:
            raise DataError(f"Failed to load Parquet file: {e}")

    # ── Discrepancy Scanner ─────────────────────────────────────────────────

    def scan_discrepancies(self, file_path: str, detected_tf_sec: int) -> List[Dict[str, Any]]:
        """
        Scans a parquet dataset for OHLC anomalies and time gaps.
        Classifies time gaps as MARKET_CLOSURE or UNEXPECTED.
        """
        df = self.load_dataset(file_path)
        discrepancies: List[Dict[str, Any]] = []

        def _add(dtype: str, idx: int, msg: str):
            if len(discrepancies) < 1000:
                discrepancies.append({
                    "type": dtype,
                    "index": int(idx),
                    "timestamp": df['datetime'].iloc[idx].isoformat(),
                    "details": msg,
                })

        # 1. Zero OHLC
        zero_mask = (df['open'] == 0) | (df['high'] == 0) | (df['low'] == 0) | (df['close'] == 0)
        for idx in np.where(zero_mask)[0][:100]:
            _add("ZERO_VALUE", idx, "One or more OHLC values are exactly 0.")

        # 2. Negative Values
        neg_mask = (df['open'] < 0) | (df['high'] < 0) | (df['low'] < 0) | (df['close'] < 0) | (df['volume'] < 0)
        for idx in np.where(neg_mask)[0][:100]:
            _add("NEGATIVE_VALUE", idx, "Negative price or volume detected.")

        # 3. Logic Errors (H < L, C > H, C < L, O > H, O < L)
        logic_mask = (
            (df['high'] < df['low'])
            | (df['close'] > df['high']) | (df['close'] < df['low'])
            | (df['open'] > df['high']) | (df['open'] < df['low'])
        )
        for idx in np.where(logic_mask)[0][:100]:
            _add("LOGIC_ERROR", idx, "OHLC bounds violated.")

        # 4. Massive Price Spikes (>15% intra-bar range vs open)
        with np.errstate(divide='ignore', invalid='ignore'):
            spike_mask = (np.abs(df['high'] - df['low']) / df['open']) > 0.15
        spike_mask = spike_mask & ~zero_mask & ~neg_mask
        for idx in np.where(spike_mask)[0][:100]:
            _add("PRICE_SPIKE", idx, "Massive intra-bar anomaly (>15% range). Suspected bad tick.")

        # 5. Time Gaps — with market-closure classification
        if detected_tf_sec > 0:
            dtvs = df['dtv'].values
            diffs_ns = np.diff(dtvs)
            diffs_sec = diffs_ns / 1e9

            gap_indices = np.where(diffs_sec > detected_tf_sec * 1.5)[0]
            for pos in gap_indices[:100]:
                idx = pos + 1  # index of bar AFTER the gap
                gap_sec = float(diffs_sec[pos])
                expected_missing = int(gap_sec // detected_tf_sec) - 1

                gap_class = MarketCalendar.classify_gap(
                    int(dtvs[pos]), int(dtvs[idx]), detected_tf_sec
                )

                if gap_class == "MARKET_CLOSURE":
                    _add("TIME_GAP_MARKET_CLOSURE", idx,
                         f"Market closure gap of {gap_sec:.0f}s ({expected_missing} bars). Expected — weekend/session break.")
                elif expected_missing > 0:
                    _add("TIME_GAP", idx,
                         f"Unexpected gap of {gap_sec:.0f}s ending here. Approx {expected_missing} bars missing.")

        discrepancies.sort(key=lambda x: x['index'], reverse=True)
        return discrepancies

    # ── Row-Level Editing ───────────────────────────────────────────────────

    def delete_dataset_row(self, file_path: str, index: int) -> None:
        """Deletes a specific row by its global index from the Parquet dataset."""
        df = self.load_dataset(file_path)
        if index < 0 or index >= len(df):
            raise DataError(f"Index {index} out of bounds (0–{len(df)-1}).")
        df = df.drop(index).reset_index(drop=True)
        self._save_parquet(df, file_path)

    def autofix_dataset_row(self, file_path: str, index: int) -> None:
        """Fix Logic Errors: swap H/L if inverted, clamp O/C within [Low, High]."""
        df = self.load_dataset(file_path)
        if index < 0 or index >= len(df):
            raise DataError("Index out of bounds.")

        row = df.iloc[index]
        o, h, l, c = row['open'], row['high'], row['low'], row['close']

        if h < l:
            h, l = l, h
            df.at[index, 'high'] = h
            df.at[index, 'low'] = l

        if o > h: df.at[index, 'open'] = h
        if o < l: df.at[index, 'open'] = l
        if c > h: df.at[index, 'close'] = h
        if c < l: df.at[index, 'close'] = l

        self._save_parquet(df, file_path)

    def interpolate_dataset_gap(self, file_path: str, index_after_gap: int, detected_tf_sec: int) -> int:
        """
        Interpolates missing rows into a TIME_GAP.
        Returns the number of rows inserted.
        """
        df = self.load_dataset(file_path)
        if index_after_gap <= 0 or index_after_gap >= len(df):
            raise DataError("Invalid gap index.")

        row_after = df.iloc[index_after_gap]
        row_before = df.iloc[index_after_gap - 1]

        gap_sec = (row_after['dtv'] - row_before['dtv']) / 1e9
        num_missing = int(gap_sec // detected_tf_sec) - 1

        if num_missing <= 0 or num_missing > 5000:
            raise DataError(
                f"Missing bar count ({num_missing}) is invalid or > 5000. "
                f"Cannot safely auto-interpolate."
            )

        new_dtvs = [row_before['dtv'] + int((i + 1) * detected_tf_sec * 1e9) for i in range(num_missing)]
        new_datetimes = pd.to_datetime(new_dtvs, utc=True)

        c_start, c_end = row_before['close'], row_after['close']
        step = (c_end - c_start) / (num_missing + 1)

        new_rows = []
        for i in range(num_missing):
            sim_close = c_start + (step * (i + 1))
            new_rows.append({
                'datetime': new_datetimes[i],
                'open': sim_close, 'high': sim_close,
                'low': sim_close, 'close': sim_close,
                'volume': 0.0, 'dtv': new_dtvs[i],
            })

        new_df = pd.DataFrame(new_rows)
        final_df = pd.concat([df.iloc[:index_after_gap], new_df, df.iloc[index_after_gap:]]).reset_index(drop=True)
        self._save_parquet(final_df, file_path)
        return num_missing

    def get_dataset_window(self, file_path: str, center_index: int, window: int = 10) -> List[Dict[str, Any]]:
        """Retrieves a window of rows around a specific index for context and inline editing."""
        df = self.load_dataset(file_path)
        start_idx = max(0, center_index - window)
        end_idx = min(len(df), center_index + window + 1)

        records = df.iloc[start_idx:end_idx].copy().to_dict(orient='records')
        for i, row in enumerate(records):
            row['index'] = start_idx + i
            row['datetime'] = row['datetime'].isoformat() if hasattr(row['datetime'], 'isoformat') else str(row['datetime'])
        return records

    def inspect_dataset_row(self, file_path: str, query: str) -> Dict[str, Any]:
        """
        Find a row by integer index or datetime string, return context window.
        """
        df = self.load_dataset(file_path)

        try:
            target_idx = int(query)
            if target_idx < 0 or target_idx >= len(df):
                raise ValueError("Index out of bounds.")
        except ValueError:
            try:
                dt_query = pd.to_datetime(query, utc=True, dayfirst=True)
                diffs = (df['datetime'] - dt_query).abs()
                target_idx = int(diffs.idxmin())
            except Exception:
                raise DataError(f"Could not parse query '{query}' as index or datetime.")

        context = self.get_dataset_window(file_path, target_idx, window=5)
        return {
            "query": query,
            "target_index": target_idx,
            "target_datetime": df.iloc[target_idx]['datetime'].isoformat(),
            "context": context,
        }

    def update_dataset_row(self, file_path: str, index: int, updates: Dict[str, float]) -> None:
        """Save individual row edits back into the Parquet file."""
        df = self.load_dataset(file_path)
        if index < 0 or index >= len(df):
            raise DataError(f"Index {index} out of bounds.")

        allowed_cols = ['open', 'high', 'low', 'close', 'volume']
        for k, v in updates.items():
            if k in allowed_cols:
                df.at[index, k] = float(v)

        self._save_parquet(df, file_path)

    # ── Internal Helpers ────────────────────────────────────────────────────

    def _extract_csv_from_zip(self, zip_path: str, extract_dir: str) -> str:
        """Safely extract a single CSV from a ZIP archive."""
        logger.info("Detected ZIP file. Extracting safely...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            members = zip_ref.namelist()
            abs_target = os.path.abspath(extract_dir)

            safe_members = []
            for member in members:
                abs_dest = os.path.abspath(os.path.join(extract_dir, member))
                if not abs_dest.startswith(abs_target):
                    raise DataError(f"Zip Slip attempt detected: {member}")
                safe_members.append(member)

            zip_ref.extractall(extract_dir, members=safe_members)

        csv_files = [f for f in os.listdir(extract_dir) if f.lower().endswith('.csv') and not f.startswith('__')]
        if len(csv_files) == 0:
            raise DataError("No CSV file found in the ZIP archive.")
        if len(csv_files) > 1:
            raise DataError(f"Multiple CSV files found in ZIP ({len(csv_files)}). Provide a ZIP with exactly one CSV.")

        logger.info(f"Found CSV: {csv_files[0]}")
        return os.path.join(extract_dir, csv_files[0])

    def _process_csv(self, file_path: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Validate, parse, sort, and convert CSV to Parquet.  Returns metadata."""
        try:
            # 1. Load CSV (Robust Separator Detection)
            try:
                df = pd.read_csv(file_path, skipinitialspace=True, engine='c')
            except Exception:
                df = pd.read_csv(file_path, skipinitialspace=True, sep=None, engine='python')

            df.columns = df.columns.str.strip().str.lower()

            # Normalise date column
            date_col_candidates = ['date', 'time', 'timestamp', 'datetime', 'dt', 'ts', 'utc']
            found_date = False
            for col in date_col_candidates:
                if col in df.columns:
                    df.rename(columns={col: 'datetime'}, inplace=True)
                    found_date = True
                    break
            if not found_date:
                raise DataError(f"Missing datetime column. Expected one of: {date_col_candidates}")

            missing = [c for c in self.REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                raise DataError(f"Missing required columns: {missing}")

            # 2. Parse Datetime
            original_len = len(df)
            try:
                df['datetime'] = pd.to_datetime(df['datetime'], utc=True, dayfirst=True, format='mixed', errors='coerce')
            except Exception:
                try:
                    df['datetime'] = pd.to_datetime(df['datetime'], utc=True, errors='coerce')
                except Exception:
                    pass

            if df['datetime'].isna().any():
                n_dropped = int(df['datetime'].isna().sum())
                drop_ratio = n_dropped / original_len
                if drop_ratio > 0.01:
                    raise DataError(
                        f"Fatal: {n_dropped} rows ({drop_ratio*100:.1f}%) have unparseable dates. "
                        f"Check CSV format (expected YYYY-MM-DD or DD.MM.YYYY)."
                    )
                logger.warning(f"Dropping {n_dropped} rows with invalid datetime.")
                df = df.dropna(subset=['datetime'])

            if df.empty:
                raise DataError("Dataset is completely empty after date parsing.")

            # 3. Numeric Conversion
            for col in self.REQUIRED_COLUMNS:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
            if df.empty:
                raise DataError("Dataset is empty after removing NaNs.")

            # 4. Sort & Deduplicate
            df.sort_values('datetime', inplace=True)
            df.drop_duplicates(subset=['datetime'], keep='first', inplace=True)

            # 5. Create 'dtv' (int64 nanoseconds)
            df['dtv'] = df['datetime'].astype('int64')

            # 6. Detect Timeframe (in seconds)
            diffs = df['dtv'].diff().dropna() / 1e9
            mode_diff = diffs.mode()
            detected_tf = int(mode_diff.iloc[0]) if not mode_diff.empty else 0

            # 7. Convert to PyArrow & Save
            table = pa.Table.from_pandas(df, schema=PARQUET_SCHEMA, preserve_index=False)

            dataset_id = str(uuid.uuid4())
            parquet_path = os.path.join(self.data_dir, f"{dataset_id}.parquet")
            pq.write_table(table, parquet_path)

            return {
                "id": dataset_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "detected_tf_sec": detected_tf,
                "start_date": df['datetime'].iloc[0].isoformat(),
                "end_date": df['datetime'].iloc[-1].isoformat(),
                "row_count": len(df),
                "file_path": parquet_path,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        except DataError:
            raise
        except Exception as e:
            raise DataError(f"Processing failed: {str(e)}")

    def _save_parquet(self, df: pd.DataFrame, file_path: str) -> None:
        """Write DataFrame to Parquet using the shared schema."""
        table = pa.Table.from_pandas(df, schema=PARQUET_SCHEMA, preserve_index=False)
        pq.write_table(table, file_path)
