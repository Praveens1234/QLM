import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional
from backend.core.data import DataManager
from backend.core.store import MetadataStore
import logging

logger = logging.getLogger("QLM.DataFeed")

class DataFeedManager:
    """
    Manages data ingestion from external providers (e.g. Yahoo Finance).
    """
    def __init__(self):
        self.data_manager = DataManager()
        self.store = MetadataStore()

    def download_market_data(self, symbol: str, timeframe: str = "1d", start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Download market data from Yahoo Finance and save it to the system.

        Args:
            symbol (str): Ticker symbol (e.g. AAPL, BTC-USD)
            timeframe (str): Timeframe (1d, 1h, 15m, 5m, 1m). Default '1d'.
            start_date (str): YYYY-MM-DD
            end_date (str): YYYY-MM-DD
        """
        try:
            logger.info(f"Downloading {symbol} ({timeframe})...")

            # Map common timeframe aliases
            interval = timeframe.lower()
            if interval == 'h1': interval = '1h'
            if interval == 'd1': interval = '1d'
            if interval == 'm1': interval = '1m'
            if interval == 'm5': interval = '5m'
            if interval == 'm15': interval = '15m'

            ticker = yf.Ticker(symbol)

            kwargs = {"interval": interval, "auto_adjust": True}
            if start_date: kwargs["start"] = start_date
            if end_date: kwargs["end"] = end_date
            if not start_date and not end_date:
                kwargs["period"] = "max"
                if interval in ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h']:
                    kwargs["period"] = "60d" # YF limit for intraday

            df = ticker.history(**kwargs)

            if df.empty:
                raise ValueError(f"No data found for {symbol} on Yahoo Finance.")

            # Reset index to get Date/Datetime as column
            df.reset_index(inplace=True)

            # Rename columns to match QLM expected format
            rename_map = {
                "Date": "datetime",
                "Datetime": "datetime",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            }
            df.rename(columns=rename_map, inplace=True)

            # Keep only required columns
            req_cols = ["datetime", "open", "high", "low", "close", "volume"]
            df = df[[c for c in req_cols if c in df.columns]]

            # Save
            metadata = self.data_manager.save_dataframe(df, symbol, timeframe)
            self.store.add_dataset(metadata)

            return {
                "status": "success",
                "message": f"Downloaded {metadata['row_count']} rows for {symbol}.",
                "dataset_id": metadata['id']
            }

        except Exception as e:
            logger.error(f"Data download failed: {e}")
            return {"status": "error", "error": str(e)}
