from backend.core.strategy import Strategy
import pandas as pd
import numpy as np
from typing import Dict, Any

class StandardStrategy(Strategy):
    '''
    Author: Automated Test
    Description: SMA Crossover for XAUUSD.
    '''
    def __init__(self, parameters: Dict[str, Any] = None):
        super().__init__(parameters)
        self.fast_window = self.parameters.get('fast_window', 10)
        self.slow_window = self.parameters.get('slow_window', 50)

    def define_variables(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        fast_ma = df['close'].rolling(window=self.fast_window).mean()
        slow_ma = df['close'].rolling(window=self.slow_window).mean()
        return {
            "fast_ma": fast_ma,
            "slow_ma": slow_ma
        }

    def entry_long(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        return (vars['fast_ma'] > vars['slow_ma']) & (vars['fast_ma'].shift(1) <= vars['slow_ma'].shift(1))

    def entry_short(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        return (vars['fast_ma'] < vars['slow_ma']) & (vars['fast_ma'].shift(1) >= vars['slow_ma'].shift(1))

    def exit_long_signal(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        return vars['fast_ma'] < vars['slow_ma']

    def exit_short_signal(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        return vars['fast_ma'] > vars['slow_ma']

    def exit(self, df: pd.DataFrame, vars: Dict[str, pd.Series], trade: Dict[str, Any]) -> bool:
        idx = trade['current_idx']
        fast = vars['fast_ma'].iloc[idx]
        slow = vars['slow_ma'].iloc[idx]
        if trade['direction'] == 'long':
            return fast < slow
        else:
            return fast > slow

    def risk_model(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        return {}
