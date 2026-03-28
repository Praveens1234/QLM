"""
Tests for the BacktestEngine._sanitize_dataset() data integrity guard.
Ensures the engine handles corrupted datasets safely before backtest execution.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from backend.core.engine import BacktestEngine


def _make_clean_df(n=50) -> pd.DataFrame:
    """Create a clean, valid DataFrame for testing."""
    base_time = datetime(2025, 1, 6, 0, 0, tzinfo=timezone.utc)  # Monday
    rows = []
    price = 2000.0
    for i in range(n):
        dt = base_time + timedelta(hours=i)
        o = price + np.random.uniform(-1, 1)
        h = o + np.random.uniform(0.5, 3)
        l = o - np.random.uniform(0.5, 3)
        c = np.random.uniform(l, h)
        rows.append({
            'datetime': dt,
            'open': round(o, 2),
            'high': round(h, 2),
            'low': round(l, 2),
            'close': round(c, 2),
            'volume': round(np.random.uniform(10, 500), 0),
            'dtv': int(dt.timestamp() * 1e9),
        })
    return pd.DataFrame(rows)


class TestSanitizeDataset:
    """Unit tests for BacktestEngine._sanitize_dataset()"""

    def setup_method(self):
        self.engine = BacktestEngine()

    def test_clean_dataset_unchanged(self):
        """Clean data should pass through with no rows removed."""
        df = _make_clean_df(50)
        result, report = self.engine._sanitize_dataset(df)
        assert report["total_removed"] == 0
        assert report["final_rows"] == 50
        assert len(result) == 50

    def test_zero_price_rows_dropped(self):
        """Rows with any OHLC value == 0 should be dropped."""
        df = _make_clean_df(50)
        # Inject 3 zero-price rows
        df.loc[5, 'open'] = 0
        df.loc[10, 'high'] = 0
        df.loc[15, 'close'] = 0

        result, report = self.engine._sanitize_dataset(df)
        assert report["zero_dropped"] == 3
        assert len(result) == 47

    def test_negative_price_rows_dropped(self):
        """Rows with negative OHLC values should be dropped."""
        df = _make_clean_df(50)
        df.loc[2, 'low'] = -5.0
        df.loc[8, 'open'] = -100.0

        result, report = self.engine._sanitize_dataset(df)
        assert report["negative_dropped"] == 2
        assert len(result) == 48

    def test_nan_rows_dropped(self):
        """Rows with NaN in OHLC should be dropped."""
        df = _make_clean_df(50)
        df.loc[0, 'open'] = np.nan
        df.loc[1, 'high'] = np.nan
        df.loc[2, 'low'] = np.nan

        result, report = self.engine._sanitize_dataset(df)
        assert report["nan_dropped"] == 3
        assert len(result) == 47

    def test_inverted_high_low_fixed(self):
        """Rows where High < Low should be auto-swapped (not dropped)."""
        df = _make_clean_df(30)
        # Create a row where high < low (inverted)
        df.loc[10, 'high'] = 1990.0
        df.loc[10, 'low'] = 2010.0
        df.loc[10, 'open'] = 2000.0
        df.loc[10, 'close'] = 2000.0

        result, report = self.engine._sanitize_dataset(df)
        assert report["logic_fixed"] >= 1
        # Row should still exist (fixed, not dropped)
        assert len(result) == 30
        # High should now be >= Low
        row = result.iloc[10]
        assert row['high'] >= row['low']

    def test_stale_frozen_bars_dropped(self):
        """Rows where O=H=L=C and volume=0 are dead feed bars, should be dropped."""
        df = _make_clean_df(40)
        # Inject 2 stale bars
        for idx in [5, 15]:
            df.loc[idx, 'open'] = 2000.0
            df.loc[idx, 'high'] = 2000.0
            df.loc[idx, 'low'] = 2000.0
            df.loc[idx, 'close'] = 2000.0
            df.loc[idx, 'volume'] = 0.0

        result, report = self.engine._sanitize_dataset(df)
        assert report["stale_dropped"] == 2
        assert len(result) == 38

    def test_duplicate_timestamps_dropped(self):
        """Duplicate timestamps should keep only the first occurrence."""
        df = _make_clean_df(30)
        # Make row 5 have same timestamp as row 4
        df.loc[5, 'datetime'] = df.loc[4, 'datetime']

        result, report = self.engine._sanitize_dataset(df)
        assert report["duplicate_dropped"] == 1
        assert len(result) == 29

    def test_mixed_corruption(self):
        """Test multiple corruption types in a single dataset."""
        df = _make_clean_df(50)
        df.loc[0, 'open'] = 0           # zero
        df.loc[1, 'close'] = np.nan     # nan
        df.loc[2, 'low'] = -10.0        # negative
        # stale bar
        df.loc[3, 'open'] = 1500.0
        df.loc[3, 'high'] = 1500.0
        df.loc[3, 'low'] = 1500.0
        df.loc[3, 'close'] = 1500.0
        df.loc[3, 'volume'] = 0.0

        result, report = self.engine._sanitize_dataset(df)
        # At least 4 rows should be removed
        assert report["total_removed"] >= 4
        assert len(result) <= 46

    def test_critical_corruption_raises(self):
        """If >50% of data is corrupted, sanitization should raise ValueError."""
        df = _make_clean_df(20)
        # Make 11 out of 20 rows have zero prices (>50%)
        for i in range(11):
            df.loc[i, 'open'] = 0

        from backend.core.exceptions import SanitizationError
        with pytest.raises(SanitizationError, match="critically corrupted"):
            self.engine._sanitize_dataset(df)

    def test_open_close_clamped_within_high_low(self):
        """Open and Close should be clamped within [Low, High]."""
        df = _make_clean_df(20)
        # Set a row where Open > High
        df.loc[5, 'high'] = 2010.0
        df.loc[5, 'low'] = 1990.0
        df.loc[5, 'open'] = 2020.0   # Out of bounds (above high)
        df.loc[5, 'close'] = 1980.0  # Out of bounds (below low)

        result, report = self.engine._sanitize_dataset(df)
        row = result.iloc[5]
        assert row['open'] <= row['high']
        assert row['close'] >= row['low']

    def test_flat_bar_with_volume_kept(self):
        """A flat bar (O=H=L=C) WITH non-zero volume is a valid doji, should be kept."""
        df = _make_clean_df(20)
        df.loc[5, 'open'] = 2000.0
        df.loc[5, 'high'] = 2000.0
        df.loc[5, 'low'] = 2000.0
        df.loc[5, 'close'] = 2000.0
        df.loc[5, 'volume'] = 100.0  # Has volume, so it's legitimate

        result, report = self.engine._sanitize_dataset(df)
        assert report["stale_dropped"] == 0 
        assert len(result) == 20  # No rows dropped
