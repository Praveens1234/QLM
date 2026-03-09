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
    size_arr: np.ndarray,
    slippage_arr: np.ndarray,
    spread_arr: np.ndarray,
    entry_on_next_bar: bool = False
):
    """
    High-performance Numba-compiled backtest loop.
    
    Realistic Market Simulation Features:
    - Slippage: Applied to worsen entry/exit prices
    - Spread: Bid-ask spread applied directionally  
    - Next-bar entry: Enter at next bar's open instead of current close
    - Entry-bar MAE/MFE: Tracks excursion from entry bar's high/low
    - Strict Gap Handling for SL/TP
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
    out_entry_indices = np.zeros(n, dtype=np.int64)

    trade_count = 0

    active_idx = -1
    entry_price = 0.0
    direction = 0
    curr_sl = 0.0
    curr_tp = 0.0
    curr_size = 0.0
    entry_time = 0

    curr_mae = 0.0
    curr_mfe = 0.0

    # Pending entry state for next-bar entry mode
    pending_entry = False
    pending_direction = 0
    pending_signal_idx = -1

    for i in range(n):
        c_time = times[i]
        o = opens[i]
        h = highs[i]
        l = lows[i]
        c = closes[i]

        # ─── Handle Pending Entry (next-bar mode) ───
        if pending_entry and active_idx == -1:
            sig_idx = pending_signal_idx
            # Enter at this bar's open + slippage + spread
            raw_entry = o
            slip = slippage_arr[sig_idx]
            half_spread = spread_arr[sig_idx] / 2.0

            if pending_direction == 1:  # Long: buy at ask (worse = higher)
                entry_price = raw_entry + slip + half_spread
            else:  # Short: sell at bid (worse = lower)
                entry_price = raw_entry - slip - half_spread

            active_idx = sig_idx
            direction = pending_direction
            curr_sl = sl_arr[sig_idx]
            curr_tp = tp_arr[sig_idx]
            curr_size = size_arr[sig_idx]
            entry_time = c_time  # actual entry time is this bar
            curr_mae = 0.0
            curr_mfe = 0.0

            # Entry-bar MAE/MFE: scan from entry price to this bar's high/low
            if direction == 1:  # Long
                bar_mfe = h - entry_price
                if bar_mfe > curr_mfe:
                    curr_mfe = bar_mfe
                bar_mae = entry_price - l
                if bar_mae > curr_mae:
                    curr_mae = bar_mae
            else:  # Short
                bar_mfe = entry_price - l
                if bar_mfe > curr_mfe:
                    curr_mfe = bar_mfe
                bar_mae = h - entry_price
                if bar_mae > curr_mae:
                    curr_mae = bar_mae

            pending_entry = False
            pending_direction = 0
            pending_signal_idx = -1

            # Don't check exit on entry bar — continue to next bar
            continue

        # ─── Check Exit ───
        if active_idx != -1:
            exit_price = 0.0
            reason = 0

            # Update MAE/MFE logic
            if direction == 1: # Long
                bar_mfe = h - entry_price
                if bar_mfe > curr_mfe: curr_mfe = bar_mfe
                bar_mae = entry_price - l
                if bar_mae > curr_mae: curr_mae = bar_mae

                # Check SL (Gap Handling: If open < SL, exit at Open)
                if not np.isnan(curr_sl) and l <= curr_sl:
                    reason = 1 # SL
                    if o < curr_sl:
                        exit_price = o # Gapped down through SL
                    else:
                        exit_price = curr_sl # Hit intrabar

                    if (entry_price - exit_price) > curr_mae: curr_mae = entry_price - exit_price

                # Check TP (Gap Handling: If open > TP, exit at Open)
                elif not np.isnan(curr_tp) and h >= curr_tp:
                    reason = 2 # TP
                    if o > curr_tp:
                        exit_price = o # Gapped up through TP
                    else:
                        exit_price = curr_tp

                    if (exit_price - entry_price) > curr_mfe: curr_mfe = exit_price - entry_price

                elif exit_long[i]:
                    exit_price = c
                    reason = 3 # Signal

            elif direction == -1: # Short
                bar_mfe = entry_price - l
                if bar_mfe > curr_mfe: curr_mfe = bar_mfe
                bar_mae = h - entry_price
                if bar_mae > curr_mae: curr_mae = bar_mae

                # Check SL (Gap Up)
                if not np.isnan(curr_sl) and h >= curr_sl:
                    reason = 1 # SL
                    if o > curr_sl:
                        exit_price = o # Gapped up through SL
                    else:
                        exit_price = curr_sl

                    if (exit_price - entry_price) > curr_mae: curr_mae = exit_price - entry_price

                # Check TP (Gap Down)
                elif not np.isnan(curr_tp) and l <= curr_tp:
                    reason = 2 # TP
                    if o < curr_tp:
                        exit_price = o # Gapped down through TP
                    else:
                        exit_price = curr_tp

                    if (entry_price - exit_price) > curr_mfe: curr_mfe = entry_price - exit_price

                elif exit_short[i]:
                    exit_price = c
                    reason = 3 # Signal

            if reason > 0:
                # Apply slippage + spread to exit price (worsen it)
                slip = slippage_arr[i]
                half_spread = spread_arr[i] / 2.0
                if reason == 3:  # Signal exit: apply slippage + spread
                    if direction == 1:  # Long exit: sell at bid (worse = lower)
                        exit_price = exit_price - slip - half_spread
                    else:  # Short exit: buy at ask (worse = higher)
                        exit_price = exit_price + slip + half_spread
                elif reason == 1:  # SL: slippage worsens further
                    if direction == 1:
                        exit_price = exit_price - slip  # slips below SL
                    else:
                        exit_price = exit_price + slip  # slips above SL
                # TP: no additional slippage (limit order)

                # Record Trade
                out_entry_times[trade_count] = entry_time
                out_exit_times[trade_count] = c_time
                out_entry_prices[trade_count] = entry_price
                out_exit_prices[trade_count] = exit_price
                out_directions[trade_count] = direction
                out_reasons[trade_count] = reason
                out_maes[trade_count] = curr_mae
                out_mfes[trade_count] = curr_mfe
                out_entry_indices[trade_count] = active_idx

                if direction == 1:
                    pnl = (exit_price - entry_price) * curr_size
                else:
                    pnl = (entry_price - exit_price) * curr_size
                out_pnls[trade_count] = pnl

                trade_count += 1
                active_idx = -1
                continue

        # ─── Check Entry ───
        if active_idx == -1 and not pending_entry:
            if entry_long[i] or entry_short[i]:
                sig_direction = 1 if entry_long[i] else -1

                if entry_on_next_bar:
                    # Defer entry to next bar's open
                    if i + 1 < n:  # ensure next bar exists
                        pending_entry = True
                        pending_direction = sig_direction
                        pending_signal_idx = i
                else:
                    # Classic mode: enter at current bar's close
                    raw_entry = c
                    slip = slippage_arr[i]
                    half_spread = spread_arr[i] / 2.0

                    if sig_direction == 1:  # Long: buy at ask (worse = higher)
                        entry_price = raw_entry + slip + half_spread
                    else:  # Short: sell at bid (worse = lower)
                        entry_price = raw_entry - slip - half_spread

                    active_idx = i
                    direction = sig_direction
                    curr_sl = sl_arr[i]
                    curr_tp = tp_arr[i]
                    curr_size = size_arr[i]
                    entry_time = c_time
                    curr_mae = 0.0
                    curr_mfe = 0.0

    # Force-close any open trade at end of data
    if active_idx != -1:
        exit_price = closes[n - 1]
        c_time = times[n - 1]

        # Apply slippage + spread to EOD close
        slip = slippage_arr[n - 1]
        half_spread = spread_arr[n - 1] / 2.0
        if direction == 1:  # Long exit: sell at bid
            exit_price = exit_price - slip - half_spread
            pnl = (exit_price - entry_price) * curr_size
        else:  # Short exit: buy at ask
            exit_price = exit_price + slip + half_spread
            pnl = (entry_price - exit_price) * curr_size

        out_entry_times[trade_count] = entry_time
        out_exit_times[trade_count] = c_time
        out_entry_prices[trade_count] = entry_price
        out_exit_prices[trade_count] = exit_price
        out_directions[trade_count] = direction
        out_reasons[trade_count] = 4  # EOD (End of Data)
        out_maes[trade_count] = curr_mae
        out_mfes[trade_count] = curr_mfe
        out_entry_indices[trade_count] = active_idx
        out_pnls[trade_count] = pnl
        trade_count += 1

    return (
        out_entry_times[:trade_count],
        out_exit_times[:trade_count],
        out_entry_prices[:trade_count],
        out_exit_prices[:trade_count],
        out_pnls[:trade_count],
        out_reasons[:trade_count],
        out_directions[:trade_count],
        out_maes[:trade_count],
        out_mfes[:trade_count],
        out_entry_indices[:trade_count]
    )
