import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

logger = logging.getLogger("QLM.Commission")

class CommissionModel:
    """
    Handles commission calculation for trades.
    Supports fixed per-trade, percentage, and per-unit models.
    """
    def __init__(self, type: str = "percent", value: float = 0.0):
        self.type = type
        self.value = value

    def calculate(self, price: float, quantity: float) -> float:
        if self.type == "fixed":
            return self.value
        elif self.type == "percent":
            return (price * quantity) * (self.value / 100.0)
        elif self.type == "per_unit":
            return self.value * quantity
        return 0.0

    @staticmethod
    def apply_to_trade(trade: Dict[str, Any], model: 'CommissionModel') -> float:
        """
        Calculates total commission (Entry + Exit) for a trade.
        """
        size = trade.get("size", 1.0) # Assume 1.0 if missing
        entry_comm = model.calculate(trade["entry_price"], size)
        exit_comm = model.calculate(trade["exit_price"], size)
        return entry_comm + exit_comm
