import numpy as np
from numba import jit

@jit(nopython=True, cache=True, nogil=True)
def run_numba_backtest(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    times: np.ndarray,
    entry_long: np.ndarray,
    entry_short: np.ndarray,
    exit_long: np.ndarray,
    exit_short: np.ndarray,
    sl_arr: np.ndarray,
    tp_arr: np.ndarray,
    size_arr: np.ndarray
):
    """
    High-performance Numba-compiled backtest loop.
    Returns: (entry_times, exit_times, entry_prices, exit_prices, pnls, reasons, directions, maes, mfes)
    """
    n = len(closes)

    # Output arrays
    out_entry_times = np.zeros(n, dtype=np.int64)
    out_exit_times = np.zeros(n, dtype=np.int64)
    out_entry_prices = np.zeros(n, dtype=np.float64)
    out_exit_prices = np.zeros(n, dtype=np.float64)
    out_pnls = np.zeros(n, dtype=np.float64)
    out_reasons = np.zeros(n, dtype=np.int8)
    out_directions = np.zeros(n, dtype=np.int8)
    out_maes = np.zeros(n, dtype=np.float64)
    out_mfes = np.zeros(n, dtype=np.float64)

    trade_count = 0

    active_idx = -1
    entry_price = 0.0
    direction = 0
    curr_sl = 0.0
    curr_tp = 0.0
    curr_size = 0.0
    entry_time = 0

    # Track intra-trade extremes
    curr_mae = 0.0
    curr_mfe = 0.0

    for i in range(n):
        c_time = times[i]
        o = opens[i]
        h = highs[i]
        l = lows[i]
        c = closes[i]

        # Check Exit
        if active_idx != -1:
            exit_price = 0.0
            reason = 0

            # Update MAE/MFE for current bar (before exit check to include current bar's wicks)
            if direction == 1: # Long
                # MFE: High - Entry
                bar_mfe = h - entry_price
                if bar_mfe > curr_mfe: curr_mfe = bar_mfe

                # MAE: Entry - Low (max loss excursion)
                bar_mae = entry_price - l
                if bar_mae > curr_mae: curr_mae = bar_mae

                # SL/TP Checks
                if not np.isnan(curr_sl) and l <= curr_sl:
                    exit_price = curr_sl
                    reason = 1 # SL
                    # Adjust MAE if SL hit on wick
                    if (entry_price - curr_sl) > curr_mae: curr_mae = entry_price - curr_sl

                elif not np.isnan(curr_tp) and h >= curr_tp:
                    exit_price = curr_tp
                    reason = 2 # TP
                    # Adjust MFE if TP hit on wick
                    if (curr_tp - entry_price) > curr_mfe: curr_mfe = curr_tp - entry_price

                elif exit_long[i]:
                    exit_price = c
                    reason = 3 # Signal

            elif direction == -1: # Short
                # MFE: Entry - Low
                bar_mfe = entry_price - l
                if bar_mfe > curr_mfe: curr_mfe = bar_mfe

                # MAE: High - Entry
                bar_mae = h - entry_price
                if bar_mae > curr_mae: curr_mae = bar_mae

                # SL/TP Checks
                if not np.isnan(curr_sl) and h >= curr_sl:
                    exit_price = curr_sl
                    reason = 1 # SL
                    if (curr_sl - entry_price) > curr_mae: curr_mae = curr_sl - entry_price

                elif not np.isnan(curr_tp) and l <= curr_tp:
                    exit_price = curr_tp
                    reason = 2 # TP
                    if (entry_price - curr_tp) > curr_mfe: curr_mfe = entry_price - curr_tp

                elif exit_short[i]:
                    exit_price = c
                    reason = 3 # Signal

            if reason > 0:
                # Record Trade
                out_entry_times[trade_count] = entry_time
                out_exit_times[trade_count] = c_time
                out_entry_prices[trade_count] = entry_price
                out_exit_prices[trade_count] = exit_price
                out_directions[trade_count] = direction
                out_reasons[trade_count] = reason
                out_maes[trade_count] = curr_mae
                out_mfes[trade_count] = curr_mfe

                # PnL
                if direction == 1:
                    pnl = (exit_price - entry_price) * curr_size
                else:
                    pnl = (entry_price - exit_price) * curr_size
                out_pnls[trade_count] = pnl

                trade_count += 1
                active_idx = -1
                continue

        # Check Entry
        if active_idx == -1:
            if entry_long[i]:
                active_idx = i
                entry_price = c
                direction = 1
                curr_sl = sl_arr[i]
                curr_tp = tp_arr[i]
                curr_size = size_arr[i]
                entry_time = c_time
                curr_mae = 0.0 # Reset
                curr_mfe = 0.0 # Reset

            elif entry_short[i]:
                active_idx = i
                entry_price = c
                direction = -1
                curr_sl = sl_arr[i]
                curr_tp = tp_arr[i]
                curr_size = size_arr[i]
                entry_time = c_time
                curr_mae = 0.0
                curr_mfe = 0.0

    return (
        out_entry_times[:trade_count],
        out_exit_times[:trade_count],
        out_entry_prices[:trade_count],
        out_exit_prices[:trade_count],
        out_pnls[:trade_count],
        out_reasons[:trade_count],
        out_directions[:trade_count],
        out_maes[:trade_count],
        out_mfes[:trade_count]
    )
