
from backend.core.strategy import Strategy
import pandas as pd
class BrokenStrategy(Strategy):
    def define_variables(self, df): return {}
    def entry_long(self, df, vars): return pd.Series([False]*len(df))
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): raise ValueError("Boom")
    def risk_model(self, df, vars): return {}
