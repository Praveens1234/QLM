import unittest
from backend.core.execution import PaperTradingAdapter

class TestExecution(unittest.TestCase):
    def test_paper_trading(self):
        adapter = PaperTradingAdapter(initial_balance=10000)

        # Place Order
        order = adapter.place_order("AAPL", "long", 10, "LIMIT", price=150.0)
        self.assertEqual(order['status'], 'OPEN')
        self.assertEqual(len(adapter.orders), 1)

        # Tick - Price above limit (Limit Buy needs price <= limit)
        adapter.on_tick("AAPL", 155.0)
        self.assertEqual(len(adapter.orders), 1) # Should not fill

        # Tick - Price below limit
        adapter.on_tick("AAPL", 149.0)
        self.assertEqual(len(adapter.orders), 0) # Should fill
        self.assertEqual(len(adapter.fill_history), 1)

        filled = adapter.fill_history[0]
        self.assertEqual(filled['status'], 'FILLED')
        # In this implementation, limit buy fills at limit price (conservative)
        self.assertEqual(filled['fill_price'], 150.0)

        # Check Position
        pos = adapter.get_position("AAPL")
        self.assertEqual(pos['quantity'], 10)

if __name__ == '__main__':
    unittest.main()
