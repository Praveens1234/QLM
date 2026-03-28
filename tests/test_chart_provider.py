import pytest
import pandas as pd
import numpy as np
import os
import pyarrow as pa
import pyarrow.parquet as pq
from backend.core.chart_provider import ChartDataProvider

@pytest.fixture
def mock_dataset_file(tmp_path):
    """Creates a small Parquet dataset for testing."""
    file_path = tmp_path / "test_data.parquet"
    
    # Create 1-minute data (base tf = 60s)
    # Let's create exactly 60 bars (1 hour of data)
    # Start at a nice round hour to avoid pandas resampling offset issues
    now = 1704067200 # Jan 1, 2024 00:00:00 UTC
    times = [now + i * 60 for i in range(60)]
    
    df = pd.DataFrame({
        'dtv': times,
        'open': np.linspace(100, 160, 60),
        'high': np.linspace(101, 161, 60),
        'low': np.linspace(99, 159, 60),
        'close': np.linspace(100.5, 160.5, 60),
        'volume': np.ones(60) * 10
    })
    
    table = pa.Table.from_pandas(df)
    pq.write_table(table, file_path)
    
    return str(file_path), df

def test_valid_timeframes():
    # Base 60s
    tfs = ChartDataProvider.get_valid_timeframes(60)
    # Check that 1m is there, but 1s, 5s, 30s are NOT
    secs = [t['sec'] for t in tfs]
    assert 60 in secs
    assert 300 in secs # 5m
    assert 3600 in secs # 1H
    assert 1 not in secs
    assert 30 not in secs
    
    # Base 3m (180s)
    tfs = ChartDataProvider.get_valid_timeframes(180)
    secs = [t['sec'] for t in tfs]
    assert 180 in secs
    assert 3600 in secs # 3m fits into 1H (3600 / 180 = 20)
    assert 300 not in secs # 5m is not a multiple of 3m (300 / 180 = 1.66)

def test_chart_window_no_resample(mock_dataset_file):
    file_path, df = mock_dataset_file
    
    # Ask for 1m data (base=60, target=60)
    res = ChartDataProvider.get_chart_window(file_path, 60, limit=30)
    
    bars = res['bars']
    assert len(bars) == 30
    assert res['has_more'] is True
    
    # The last 30 bars should be returned
    assert bars[-1]['time'] == df['dtv'].iloc[-1]
    assert bars[-1]['close'] == float(df['close'].iloc[-1])

def test_chart_window_resampling(mock_dataset_file):
    file_path, df = mock_dataset_file
    
    # Ask for 5m data (target=300)
    # Our data is 60 bars of 1m = Exactly twelve 5m bars
    res = ChartDataProvider.get_chart_window(file_path, 300, limit=12)
    
    bars = res['bars']
    assert len(bars) == 12
    
    # Verify OHLC logic on the first resampled bar
    # A 5m resampled bar is made of the first 5 1m bars
    first_5m_bar = bars[0]
    first_5_raw_bars = df.iloc[0:5]
    
    assert first_5m_bar['open'] == float(first_5_raw_bars['open'].iloc[0])
    assert first_5m_bar['high'] == float(first_5_raw_bars['high'].max())
    assert first_5m_bar['low'] == float(first_5_raw_bars['low'].min())
    assert first_5m_bar['close'] == float(first_5_raw_bars['close'].iloc[-1])
    assert first_5m_bar['value'] == float(first_5_raw_bars['volume'].sum()) # Volume sum

def test_chart_cursor_pagination(mock_dataset_file):
    file_path, df = mock_dataset_file
    
    # Limit to 10 bars
    res1 = ChartDataProvider.get_chart_window(file_path, 60, limit=10)
    bars1 = res1['bars']
    assert len(bars1) == 10
    assert res1['has_more'] is True
    
    # Use cursor to fetch the next (older) batch
    next_cursor = res1['next_cursor']
    assert next_cursor == bars1[0]['time']
    
    res2 = ChartDataProvider.get_chart_window(file_path, 60, end_cursor=next_cursor, limit=10)
    bars2 = res2['bars']
    assert len(bars2) == 10
    
    # Ensure they are disjoint and contiguous
    assert bars2[-1]['time'] < bars1[0]['time']
