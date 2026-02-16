from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger("QLM.Execution")

class ExecutionHandler(ABC):
    @abstractmethod
    def place_order(self, symbol: str, side: str, quantity: float, order_type: str = "MARKET", price: float = None, sl: float = None, tp: float = None) -> Dict:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass

    @abstractmethod
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Dict:
        pass

    @abstractmethod
    def get_balance(self) -> Dict:
        pass

class PaperTradingAdapter(ExecutionHandler):
    """
    Simulates a broker execution environment.
    """
    def __init__(self, initial_balance: float = 100000.0):
        self.balance = initial_balance
        self.positions = {} # {symbol: {quantity, avg_price}}
        self.orders = [] # List of active orders
        self.fill_history = []

    def place_order(self, symbol: str, side: str, quantity: float, order_type: str = "MARKET", price: float = None, sl: float = None, tp: float = None) -> Dict:
        order_id = str(uuid.uuid4())
        order = {
            "id": order_id,
            "symbol": symbol,
            "side": side.lower(),
            "quantity": quantity,
            "type": order_type.upper(),
            "price": price,
            "sl": sl,
            "tp": tp,
            "status": "OPEN",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        self.orders.append(order)
        logger.info(f"Paper Order Placed: {order}")
        return order

    def cancel_order(self, order_id: str) -> bool:
        for o in self.orders:
            if o['id'] == order_id:
                o['status'] = 'CANCELLED'
                self.orders.remove(o)
                return True
        return False

    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        if symbol:
            return [o for o in self.orders if o['symbol'] == symbol]
        return self.orders

    def get_position(self, symbol: str) -> Dict:
        return self.positions.get(symbol, {"quantity": 0, "avg_price": 0.0})

    def get_balance(self) -> Dict:
        return {"available": self.balance, "currency": "USD"}

    def on_tick(self, symbol: str, current_price: float):
        """
        Process orders based on new market data.
        This would be called by the Live Runner loop.
        """
        filled_orders = []

        for order in self.orders:
            if order['symbol'] != symbol: continue

            should_fill = False
            fill_price = current_price

            if order['type'] == 'MARKET':
                should_fill = True
                fill_price = current_price
            elif order['type'] == 'LIMIT':
                if order['side'] == 'long' and current_price <= order['price']:
                    should_fill = True
                    fill_price = order['price']
                elif order['side'] == 'short' and current_price >= order['price']:
                    should_fill = True
                    fill_price = order['price']

            if should_fill:
                self._execute_fill(order, fill_price)
                filled_orders.append(order)

        for o in filled_orders:
            if o in self.orders:
                self.orders.remove(o)

    def _execute_fill(self, order, price):
        qty = order['quantity']
        side = order['side']

        # Update Position
        pos = self.positions.get(order['symbol'], {"quantity": 0.0, "avg_price": 0.0})
        curr_qty = pos['quantity']

        if side == 'long':
            new_qty = curr_qty + qty
            # Update Avg Price (simple weighted avg)
            if new_qty > 0:
                total_cost = (curr_qty * pos['avg_price']) + (qty * price)
                pos['avg_price'] = total_cost / new_qty
            else:
                pos['avg_price'] = 0.0
        else: # short
            new_qty = curr_qty - qty
            # Short average price logic is same if we consider negative quantity?
            # Keeping it simple for prototype.
            if new_qty != 0:
                 if curr_qty < 0: # Adding to short
                      total_val = (abs(curr_qty) * pos['avg_price']) + (qty * price)
                      pos['avg_price'] = total_val / abs(new_qty)
                 elif curr_qty > 0: # Closing long
                      pass # Closing doesn't change avg price of remaining

        pos['quantity'] = new_qty
        self.positions[order['symbol']] = pos

        order['status'] = 'FILLED'
        order['fill_price'] = price
        order['filled_at'] = datetime.now(timezone.utc).isoformat()
        self.fill_history.append(order)
        logger.info(f"Order Filled: {order['symbol']} {side} {qty} @ {price}")
