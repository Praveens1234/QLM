import logging
from typing import Dict, Any

logger = logging.getLogger("QLM.Commission")


class CommissionModel:
    """
    Handles commission calculation for trades.
    Supports: fixed per-trade, percentage, per-unit, and per-lot models.
    """

    VALID_TYPES = ("fixed", "percent", "per_unit", "per_lot")

    def __init__(self, type: str = "percent", value: float = 0.0):
        if type not in self.VALID_TYPES:
            raise ValueError(f"Commission type must be one of {self.VALID_TYPES}, got '{type}'")
        if value < 0:
            raise ValueError(f"Commission value must be >= 0, got {value}")
        self.type = type
        self.value = value

    def calculate(self, price: float, quantity: float) -> float:
        """Calculate commission for one side (entry OR exit)."""
        if self.type == "fixed":
            return self.value
        elif self.type == "percent":
            return abs(price * quantity) * (self.value / 100.0)
        elif self.type == "per_unit":
            return self.value * abs(quantity)
        elif self.type == "per_lot":
            # 1 standard lot = 100,000 units.  Commission is per lot.
            lots = abs(quantity)  # In QLM, 'size' is typically in lots
            return self.value * lots
        return 0.0

    @staticmethod
    def apply_to_trade(trade: Dict[str, Any], model: 'CommissionModel') -> float:
        """
        Calculates total commission (Entry + Exit) for a trade.
        """
        size = trade.get("size", 1.0)
        entry_comm = model.calculate(trade["entry_price"], size)
        exit_comm = model.calculate(trade["exit_price"], size)
        return entry_comm + exit_comm
