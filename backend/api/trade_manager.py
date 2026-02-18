from backend.core.trading_engine import TradingEngine

# Global Singleton Instance
# Initialize in PAPER mode by default for safety
trading_engine = TradingEngine(mode="PAPER")
