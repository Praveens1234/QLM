import pytest
from backend.core.audit import LedgerAuditor

def test_ledger_valid():
    trades = [
        {"entry_price": 100, "exit_price": 110, "direction": "long", "size": 1, "pnl": 10},
        {"entry_price": 100, "exit_price": 90, "direction": "long", "size": 1, "pnl": -10},
    ]
    res = LedgerAuditor.audit(trades)
    assert res["valid"]
    assert len(res["errors"]) == 0

def test_ledger_pnl_mismatch():
    trades = [
        {"entry_price": 100, "exit_price": 110, "direction": "long", "size": 1, "pnl": 500} # Wrong
    ]
    res = LedgerAuditor.audit(trades)
    # This might be a warning in my logic, depending on strictness
    assert len(res["warnings"]) > 0

def test_ledger_negative_price():
    trades = [
        {"entry_price": -100, "exit_price": 110, "direction": "long", "size": 1, "pnl": 10}
    ]
    res = LedgerAuditor.audit(trades)
    assert not res["valid"]
    assert "Negative prices" in res["errors"][0]
