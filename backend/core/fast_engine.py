import numpy as np
import numba
from numba import float64, int64, boolean

@numba.jit(nopython=True, cache=True)
def fast_backtest_core(
    times,      # int64[:]
    opens,      # float64[:]
    highs,      # float64[:]
    lows,       # float64[:]
    closes,     # float64[:]
    long_entries,  # boolean[:]
    short_entries, # boolean[:]
    long_exits,    # boolean[:]
    short_exits,   # boolean[:]
    sl_arr,     # float64[:] (NaN if no SL)
    tp_arr,     # float64[:] (NaN if no TP)
    size_arr    # float64[:]
):
    n = len(closes)

    # Pre-allocate generic result arrays (max possible trades = n)
    # 0: entry_time (int64)
    # 1: exit_time (int64)
    # 2: entry_price (float64)
    # 3: exit_price (float64)
    # 4: pnl (float64)
    # 5: direction (1 for long, -1 for short)
    # 6: exit_reason (1: SL, 2: TP, 3: Signal, 4: End)
    # 7: size (float64)

    trades = np.zeros((n, 8), dtype=np.float64)
    trade_count = 0

    # State
    in_position = False
    direction = 0 # 1 long, -1 short
    entry_price = 0.0
    entry_idx = 0
    curr_sl = np.nan
    curr_tp = np.nan
    curr_size = 1.0

    for i in range(n):
        current_time = times[i]
        open_p = opens[i]
        high_p = highs[i]
        low_p = lows[i]
        close_p = closes[i]

        # Check Exit if in position
        if in_position:
            exit_price = 0.0
            exit_reason = 0

            # 1. Check SL/TP
            if direction == 1: # Long
                # Check SL
                if not np.isnan(curr_sl) and low_p <= curr_sl:
                    exit_price = curr_sl
                    exit_reason = 1 # SL
                # Check TP
                elif not np.isnan(curr_tp) and high_p >= curr_tp:
                    exit_price = curr_tp
                    exit_reason = 2 # TP
                # Check Signal
                elif long_exits[i]:
                    exit_price = close_p
                    exit_reason = 3 # Signal

            elif direction == -1: # Short
                # Check SL
                if not np.isnan(curr_sl) and high_p >= curr_sl:
                    exit_price = curr_sl
                    exit_reason = 1 # SL
                # Check TP
                elif not np.isnan(curr_tp) and low_p <= curr_tp:
                    exit_price = curr_tp
                    exit_reason = 2 # TP
                # Check Signal
                elif short_exits[i]:
                    exit_price = close_p
                    exit_reason = 3 # Signal

            # Exec Exit
            if exit_reason > 0:
                pnl = 0.0
                if direction == 1:
                    pnl = (exit_price - entry_price) * curr_size
                else:
                    pnl = (entry_price - exit_price) * curr_size

                # Record Trade
                trades[trade_count, 0] = float(times[entry_idx])
                trades[trade_count, 1] = float(current_time)
                trades[trade_count, 2] = entry_price
                trades[trade_count, 3] = exit_price
                trades[trade_count, 4] = pnl
                trades[trade_count, 5] = float(direction)
                trades[trade_count, 6] = float(exit_reason)
                trades[trade_count, 7] = curr_size

                trade_count += 1
                in_position = False
                direction = 0

        # Check Entry (if not in position)
        if not in_position:
            if long_entries[i]:
                in_position = True
                direction = 1
                entry_price = close_p
                entry_idx = i
                curr_sl = sl_arr[i]
                curr_tp = tp_arr[i]
                curr_size = size_arr[i]

            elif short_entries[i]:
                in_position = True
                direction = -1
                entry_price = close_p
                entry_idx = i
                curr_sl = sl_arr[i]
                curr_tp = tp_arr[i]
                curr_size = size_arr[i]

    return trades[:trade_count]
