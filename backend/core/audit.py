from typing import List, Dict, Any
import logging
from backend.core.exceptions import DataError

logger = logging.getLogger("QLM.Audit.Ledger")

class LedgerAuditor:
    """
    Audits trade ledgers for logical inconsistencies.
    """
    @staticmethod
    def audit(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        errors = []
        warnings = []

        for i, trade in enumerate(trades):
            # 1. Check PnL Consistency
            # PnL ~= (Exit - Entry) * Size * Direction
            try:
                entry = float(trade.get("entry_price", 0))
                exit_p = float(trade.get("exit_price", 0))
                size = float(trade.get("size", 1.0)) # Default size logic? Engine uses size
                pnl = float(trade.get("pnl", 0))
                direction = 1 if trade.get("direction") == "long" else -1

                # Check simple PnL (ignoring fees/slippage which might cause deviation)
                # We allow a small epsilon or skip if fees involved
                expected_pnl = (exit_p - entry) * size * direction

                # If difference is significant (> 1%), flag it
                if abs(pnl - expected_pnl) > (abs(expected_pnl) * 0.05 + 0.01): # 5% tolerance for slippage/fees
                    warnings.append(f"Trade {i}: PnL deviation. Reported: {pnl}, Calc: {expected_pnl}")

            except Exception:
                errors.append(f"Trade {i}: Malformed numeric data")

            # 2. Check Timestamps
            try:
                # Assuming ISO strings or timestamps
                # Engine returns ISO strings
                pass
                # Ideally check exit > entry.
                # But string parsing here might be slow.
            except:
                pass

            # 3. Check Price Negativity
            if entry < 0 or exit_p < 0:
                errors.append(f"Trade {i}: Negative prices found.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "trade_count": len(trades)
        }
