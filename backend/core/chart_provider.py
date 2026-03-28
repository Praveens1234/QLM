"""
QLM Chart Data Provider
Handles server-side data extraction, timeframe resampling, and cursor-based pagination
for large Parquet datasets to serve the frontend charting library.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import pyarrow.parquet as pq
import logging
import math
from datetime import datetime, timezone

logger = logging.getLogger("QLM.ChartProvider")

class ChartDataProvider:
    
    # Standard timeframes supported for chart viewing
    STANDARD_TFS = [
        {"label": "1s",  "sec": 1},
        {"label": "5s",  "sec": 5},
        {"label": "15s", "sec": 15},
        {"label": "30s", "sec": 30},
        {"label": "1m",  "sec": 60},
        {"label": "2m",  "sec": 120},
        {"label": "3m",  "sec": 180},
        {"label": "5m",  "sec": 300},
        {"label": "10m", "sec": 600},
        {"label": "15m", "sec": 900},
        {"label": "30m", "sec": 1800},
        {"label": "1H",  "sec": 3600},
        {"label": "2H",  "sec": 7200},
        {"label": "4H",  "sec": 14400},
        {"label": "1D",  "sec": 86400},
        {"label": "1W",  "sec": 604800},
        {"label": "1MO", "sec": 2592000}
    ]

    @staticmethod
    def get_valid_timeframes(base_tf_sec: int) -> List[Dict[str, Any]]:
        """
        Returns a list of timeframes that are >= base_tf_sec and are integer multiples.
        If base_tf_sec is 0 (unknown), assume tick/1s and return all.
        """
        if base_tf_sec <= 0:
            return ChartDataProvider.STANDARD_TFS
            
        valid = []
        for tf in ChartDataProvider.STANDARD_TFS:
            # Must be greater than or equal to base timeframe
            if tf["sec"] >= base_tf_sec:
                # Must be an integer multiple (e.g. can't make 3m from 2m)
                if tf["sec"] % base_tf_sec == 0:
                    valid.append(tf)
                    
        # Always ensure the base itself is included, even if non-standard
        if not any(t["sec"] == base_tf_sec for t in valid):
            custom = {"label": f"{base_tf_sec}s_base", "sec": base_tf_sec}
            valid.insert(0, custom)
            
        return valid

    @staticmethod
    def get_chart_window(file_path: str, target_tf_sec: int, end_cursor: Optional[int] = None, limit: int = 2000) -> Dict[str, Any]:
        """
        Reads from parquet, filters by end_cursor (timestamp), takes the LAST `limit` rows (BEFORE resampling),
        resamples to `target_tf_sec`, and returns the OHLCV array.
        """
        try:
            # 1. Read the necessary columns from Parquet
            df = pq.read_table(
                file_path, 
                columns=['dtv', 'open', 'high', 'low', 'close', 'volume']
            ).to_pandas()
            
            if df.empty:
                return {"bars": [], "has_more": False, "next_cursor": None}

            # 1.5 Detect variable timestamp precision and normalize `dtv` to seconds
            sample_dtv = int(df['dtv'].iloc[0])
            if sample_dtv > 1e16: # Nanoseconds
                df['dtv'] = df['dtv'] // 10**9
            elif sample_dtv > 1e13: # Microseconds
                df['dtv'] = df['dtv'] // 10**6
            elif sample_dtv > 1e10: # Milliseconds
                df['dtv'] = df['dtv'] // 10**3

            # 2. Sort by time ascending
            df = df.sort_values(by='dtv').reset_index(drop=True)

            # 3. Apply cursor filter (end_cursor is exclusive)
            # end_cursor is the Unix timestamp of the oldest visible bar we have so far
            if end_cursor is not None:
                df = df[df['dtv'] < end_cursor]

            if df.empty:
                return {"bars": [], "has_more": False, "next_cursor": None}

            # 4. We need `limit` rows AFTER resampling. 
            # To be safe, if we resample from 1M to 1H (ratio 60), we need 60 * limit rows.
            # But what if the data has gaps? We should fetch more. 
            # Safest is to just resample the LAST chunk of data that covers enough time.
            
            # Find base timeframe (median time difference)
            time_diffs = df['dtv'].diff().dropna()
            base_tf_sec = int(time_diffs.median()) if not time_diffs.empty else 1
            if base_tf_sec <= 0: base_tf_sec = 1
            
            # Calculate how many raw rows we need to get `limit` resampled rows
            ratio = max(1, target_tf_sec // base_tf_sec)
            
            # Multiply by ratio, add a buffer for weekends/gaps (e.g., 3x buffer)
            rows_needed = limit * ratio * 3
            
            # Take the last N rows before the cursor
            chunk = df.tail(rows_needed).copy()
            
            # 5. Determine if there is more data before this chunk
            has_more = len(df) > len(chunk)
            next_cursor = int(chunk['dtv'].iloc[0]) if has_more else None
            
            df_len_before_tail = len(chunk)

            # 6. Set datetime index for resampling
            chunk['datetime'] = pd.to_datetime(chunk['dtv'], unit='s', utc=True)
            chunk.set_index('datetime', inplace=True)
            
            # 7. Resample if needed
            if target_tf_sec > base_tf_sec:
                # Create pandas offset string (e.g. '300s' for 5m)
                freq_str = f"{target_tf_sec}s"
                
                # OHLCV aggregation rules
                # Use closed='left', label='left' to match standard crypto/forex charting
                resampled = chunk.resample(freq_str, closed='left', label='left').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna(subset=['close']) # Drop NA rows (gaps)
                
                chunk = resampled
                # Re-add timestamp 
                chunk['dtv'] = chunk.index.astype('int64') // 10**9

            # 8. Limit to exactly `limit` rows (take the tail)
            final_df = chunk.tail(limit).reset_index(drop=True)
            
            # If after taking the tail we still skipped some rows in our RESAMPLED chunk, 
            # Or if we skipped rows in our RAW chunk (has_more is True)
            if target_tf_sec > base_tf_sec and len(chunk) > limit:
                oldest_resampled_time = int(final_df['dtv'].iloc[0])
                next_cursor = oldest_resampled_time
                has_more = True
            elif target_tf_sec <= base_tf_sec:
                # Need to check if there are any rows in `df` before the start of `final_df`
                oldest_returned_time = float(final_df['dtv'].iloc[0]) if not final_df.empty else None
                if oldest_returned_time is not None:
                    # Are there any rows in df strictly before this time?
                    has_more = not df[df['dtv'] < oldest_returned_time].empty
                    next_cursor = int(oldest_returned_time) if has_more else None
                else:
                    has_more = False
                    next_cursor = None

            # 9. Format for Lightweight Charts (requires {time: unix_timestamp, open, high, low, close, value?})
            bars = []
            for _, row in final_df.iterrows():
                try:
                    bars.append({
                        "time": int(row['dtv']),
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "value": float(row['volume']) # For volume pane
                    })
                except (ValueError, TypeError):
                    continue

            return {
                "bars": bars,
                "has_more": has_more,
                "next_cursor": next_cursor
            }

        except Exception as e:
            logger.error(f"Chart data provider error: {e}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Failed to generate chart data: {str(e)}")
