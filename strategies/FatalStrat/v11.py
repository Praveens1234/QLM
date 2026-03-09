
from backend.core.strategy import Strategy
import pandas as pd
class FatalStrategy(Strategy):
    def define_variables(self, df): raise ValueError("Fatal Boom")
    def entry_long(self, df, vars): return pd.Series([False]*len(df))
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): return False
    def risk_model(self, df, vars): return {}
