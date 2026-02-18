from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class ParityStrat(Strategy):
    def define_variables(self, df):
        return {}

    def entry_long(self, df, vars):
        # Enter only on first candle
        s = pd.Series(False, index=df.index)
        s.iloc[0] = True
        return s

    def entry_short(self, df, vars):
        return pd.Series(False, index=df.index)

    def risk_model(self, df, vars):
        # Static SL at 100.0
        sl = pd.Series(100.0, index=df.index)
        return {"sl": sl}

    def exit(self, df, vars, trade):
        return False
