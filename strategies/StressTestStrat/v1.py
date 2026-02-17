from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class StressTestStrat(Strategy):
    def define_variables(self, df: pd.DataFrame):
        return {
            "sma": df['close'].rolling(50).mean()
        }

    def entry_long(self, df: pd.DataFrame, vars):
        return df['close'] > vars['sma']

    def entry_short(self, df: pd.DataFrame, vars):
        return df['close'] < vars['sma']

    def exit_long_signal(self, df, vars):
        return df['close'] < vars['sma']

    def exit_short_signal(self, df, vars):
        return df['close'] > vars['sma']

    def exit(self, df, vars, trade):
        return False

    def risk_model(self, df, vars):
        return {}
