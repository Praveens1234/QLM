"""
Verification script for capital-based backtesting overhaul.
Tests both capital and RRR modes.
"""
import sys, os
sys.path.insert(0, os.getcwd())

from backend.core.engine import BacktestEngine
from backend.core.store import MetadataStore

store = MetadataStore()
engine = BacktestEngine()

datasets = store.list_datasets()
dataset = datasets[0]
print(f"Dataset: {dataset['symbol']} {dataset['timeframe']} ({dataset.get('row_count')} rows)")

# ======================================================================
# TEST 1: Capital Mode
# ======================================================================
print(f"\n{'='*60}")
print("TEST 1: CAPITAL MODE (USD)")
print(f"{'='*60}")

result = engine.run(
    dataset['id'], "RSI 2",
    mode="capital",
    initial_capital=10000.0,
    leverage=1.0,
    position_sizing="fixed",
    fixed_size=1.0,
)

metrics = result.get('metrics', {})
trades = result.get('trades', [])
print(f"  Status: {result.get('status')}")
print(f"  Mode: {metrics.get('mode')}")
print(f"  Unit: {metrics.get('unit')}")
print(f"  Total Trades: {metrics.get('total_trades')}")
print(f"  Total Long: {metrics.get('total_long')}")
print(f"  Total Short: {metrics.get('total_short')}")
print(f"  Total Wins: {metrics.get('total_wins')}")
print(f"  Total Losses: {metrics.get('total_losses')}")
print(f"  Win Rate: {metrics.get('win_rate')}%")
print(f"  Net Profit: ${metrics.get('net_profit')}")
print(f"  Profit Factor: {metrics.get('profit_factor')}")
print(f"  Max Drawdown: ${metrics.get('max_drawdown')}")
print(f"  Max Runup: ${metrics.get('max_runup')}")
print(f"  Expectancy: ${metrics.get('expectancy')}")
print(f"  Avg RRR: {metrics.get('avg_r_multiple')}")
print(f"  Final Equity: ${metrics.get('final_equity')}")

if trades:
    t = trades[0]
    print(f"\n  First Trade Ledger Entry:")
    print(f"    Entry DT: {t.get('entry_time')}")
    print(f"    DIR: {t.get('direction')}")
    print(f"    Entry Price: {t.get('entry_price')}")
    print(f"    Exit Price: {t.get('exit_price')}")
    print(f"    Exit DT: {t.get('exit_time')}")
    print(f"    PnL: {t.get('pnl')}")
    print(f"    RRR: {t.get('r_multiple')}")
    print(f"    SL: {t.get('sl')}")
    print(f"    TP: {t.get('tp')}")
    print(f"    Max DD: {t.get('mae')}")
    print(f"    Max Runup: {t.get('mfe')}")
    print(f"    Holding Time: {t.get('duration')} min")
    print(f"    Status: {t.get('exit_reason')}")
    
    # Count exit reasons
    reasons = {}
    for tr in trades:
        r = tr.get('exit_reason', 'Unknown')
        reasons[r] = reasons.get(r, 0) + 1
    print(f"\n  Exit Reasons: {reasons}")

# ======================================================================
# TEST 2: RRR Mode
# ======================================================================
print(f"\n{'='*60}")
print("TEST 2: RRR MODE (R-multiples)")
print(f"{'='*60}")

result2 = engine.run(
    dataset['id'], "RSI 2",
    mode="rrr",
    initial_capital=10000.0,
    leverage=1.0,
    position_sizing="fixed",
    fixed_size=1.0,
)

metrics2 = result2.get('metrics', {})
trades2 = result2.get('trades', [])
print(f"  Status: {result2.get('status')}")
print(f"  Mode: {metrics2.get('mode')}")
print(f"  Unit: {metrics2.get('unit')}")
print(f"  Total Trades: {metrics2.get('total_trades')}")
print(f"  Net Profit (R): {metrics2.get('net_profit')}")
print(f"  Avg RRR: {metrics2.get('avg_r_multiple')}")

if trades2:
    t2 = trades2[0]
    print(f"\n  First Trade (RRR mode):")
    print(f"    PnL (R): {t2.get('pnl')}")
    print(f"    RRR: {t2.get('r_multiple')}")
    print(f"    Status: {t2.get('exit_reason')}")

# ======================================================================
# TEST 3: Leverage
# ======================================================================
print(f"\n{'='*60}")
print("TEST 3: LEVERAGE (10x)")
print(f"{'='*60}")

result3 = engine.run(
    dataset['id'], "RSI 2",
    mode="capital",
    initial_capital=10000.0,
    leverage=10.0,
    position_sizing="fixed",
    fixed_size=1.0,
)

metrics3 = result3.get('metrics', {})
print(f"  Net Profit (10x leverage): ${metrics3.get('net_profit')}")
print(f"  Net Profit (1x leverage):  ${metrics.get('net_profit')}")
ratio = abs(metrics3.get('net_profit', 0) / metrics.get('net_profit', 1))
print(f"  Ratio (should be ~10x): {round(ratio, 2)}x")

print(f"\n{'='*60}")
print("VERIFICATION COMPLETE")
print(f"{'='*60}")
