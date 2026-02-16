import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import tempfile
import os
import shutil
from backend.core.data_feed import DataFeedManager
from backend.core.store import MetadataStore
from backend.database import db

class TestDataFeed(unittest.TestCase):
    def setUp(self):
        self.test_db_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_db_dir, "test_data.db")
        db.db_path = self.test_db_path
        db._init_schema()

        self.store = MetadataStore()
        self.manager = DataFeedManager()
        self.manager.data_manager.data_dir = self.test_db_dir # Save parquet here

    def tearDown(self):
        shutil.rmtree(self.test_db_dir)

    @patch('yfinance.Ticker')
    def test_download_market_data(self, mock_ticker):
        # Mock YF Response
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        df = pd.DataFrame({
            "Open": [100.0]*50, "High": [105.0]*50, "Low": [95.0]*50, "Close": [100.0]*50, "Volume": [1000]*50
        }, index=dates)
        df.index.name = "Date"

        # yfinance.history returns DataFrame with Datetime index usually
        # Mock instance
        instance = mock_ticker.return_value
        instance.history.return_value = df

        result = self.manager.download_market_data("AAPL", "1d")

        self.assertEqual(result['status'], 'success')
        self.assertIn('dataset_id', result)

        # Verify it's in store
        datasets = self.store.list_datasets()
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0]['symbol'], 'AAPL')
        self.assertEqual(datasets[0]['row_count'], 50)

if __name__ == '__main__':
    unittest.main()
