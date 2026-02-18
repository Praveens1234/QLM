import logging
from typing import Dict, Tuple
from backend.core.execution import Order

logger = logging.getLogger("QLM.RiskManager")

class RiskManager:
    """
    Real-time Pre-Trade Risk Validation.
    Enforces strict limits on:
    - Max Order Quantity
    - Max Order Value (Notional)
    - Max Daily Loss
    - Max Open Positions
    """
    def __init__(self, config: Dict = None):
        self.config = config or {}
        # Defaults
        self.max_order_qty = float(self.config.get("max_order_qty", 10.0))
        self.max_order_value = float(self.config.get("max_order_value", 100000.0)) # $100k
        self.max_daily_loss = float(self.config.get("max_daily_loss", 5000.0)) # $5k
        self.max_positions = int(self.config.get("max_positions", 5))
        self.restricted_symbols = self.config.get("restricted_symbols", [])

    def validate_order(self, order: Order, portfolio_state: Dict) -> Tuple[bool, str]:
        """
        Validates an order against risk rules.
        Returns (is_valid, reason).
        """
        # 1. Symbol Restriction
        if order.symbol in self.restricted_symbols:
            return False, f"Symbol {order.symbol} is restricted."

        # 2. Max Quantity
        if order.quantity > self.max_order_qty:
            return False, f"Order qty {order.quantity} exceeds max {self.max_order_qty}."

        # 3. Max Order Value (requires price)
        # If Market order, we might not know price perfectly, but use current market price if available
        # portfolio_state should contain current price
        price = order.price
        if not price and portfolio_state.get('current_price'):
            price = portfolio_state['current_price']

        if price:
            notional = order.quantity * price
            if notional > self.max_order_value:
                return False, f"Order value {notional:.2f} exceeds max {self.max_order_value}."

        # 4. Max Daily Loss
        # Check realized PnL + Unrealized PnL? Or just Realized?
        # Usually checking Total PnL (Realized + Unrealized) matches "Daily Loss" if reset daily.
        # Here we check total PnL of the session.
        current_pnl = portfolio_state.get('total_pnl', 0.0)
        if current_pnl < -self.max_daily_loss:
            # Only allow reducing positions?
            # If order reduces risk (closes position), maybe allow?
            # For simplicity, block all NEW OPENING orders.
            # We need to know if this order is opening or closing.
            # We assume it's opening if it increases exposure.
            # But checking exposure is complex without full state.
            # Strict mode: Block all.
            return False, f"Max daily loss exceeded ({current_pnl:.2f} < -{self.max_daily_loss}). Trading halted."

        # 5. Max Positions
        current_positions_count = portfolio_state.get('positions_count', 0)
        # If we are opening a NEW position (symbol not in active positions)
        is_new_position = order.symbol not in portfolio_state.get('active_symbols', [])
        if is_new_position and current_positions_count >= self.max_positions:
            return False, f"Max positions limit ({self.max_positions}) reached."

        return True, "OK"
