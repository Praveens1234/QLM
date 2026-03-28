"""
QLM High-Performance Numba Backtest Engine.

Realistic Market Simulation Features:
  - Slippage: worsens entry/exit prices
  - Spread: bid-ask applied directionally
  - Next-bar entry: deferred to next bar's open
  - Gap-through SL/TP: exit at open when price gaps beyond levels
  - SL/TP Ambiguity Resolution: worst-case-first when both hit on same bar
  - Market-closure bar skipping
  - Spike bar entry rejection
  - Proper entry-bar MAE/MFE tracking
"""
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
    entry_on_next_bar: bool,
    market_closed: np.ndarray,
    spike_bars: np.ndarray,
):
    """
    High-performance Numba-compiled backtest loop.

    Exit reason codes:
      1 = SL Hit,  2 = TP Hit,  3 = Signal Exit,  4 = End of Data

    SL/TP Ambiguity Resolution:
      When both SL and TP could be hit on the same bar, we use bar topology:
        Long:  if open <= SL → gapped through SL (SL wins)
               elif open >= TP → gapped through TP (TP wins)
               else → check which is "closer" to intra-bar path;
                       conservative: worst-case (SL) wins when ambiguous
        Short: mirror logic

    Market Closure:
      Bars where market_closed[i] == True are skipped:
        - No new entries
        - No SL/TP/Signal exits (trade is frozen)

    Spike Bars:
      Bars where spike_bars[i] == True:
        - No new entries allowed
        - SL/TP exits are still possible (spike may be real)
    """
    n = len(closes)

    # Pre-allocate output arrays (max possible = n trades)
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

    # Active trade state
    active_idx = -1
    entry_price = 0.0
    direction = 0      # 1 = long, -1 = short
    curr_sl = 0.0
    curr_tp = 0.0
    curr_size = 0.0
    entry_time = np.int64(0)
    curr_mae = 0.0
    curr_mfe = 0.0

    # Pending entry state (for next-bar entry mode)
    pending_entry = False
    pending_direction = 0
    pending_signal_idx = -1

    for i in range(n):
        c_time = times[i]
        o = opens[i]
        h = highs[i]
        l = lows[i]
        c = closes[i]
        is_closed = market_closed[i]
        is_spike = spike_bars[i]

        # ─── Handle Pending Entry (next-bar mode) ───────────────────────
        if pending_entry and active_idx == -1:
            # Cancel pending entry if this bar is during market closure or is a spike
            if is_closed or is_spike:
                pending_entry = False
                pending_direction = 0
                pending_signal_idx = -1
                # Fall through — don't enter, don't skip
            else:
                sig_idx = pending_signal_idx
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
                entry_time = c_time
                curr_mae = 0.0
                curr_mfe = 0.0

                # Entry-bar MAE/MFE
                if direction == 1:
                    bar_mfe = h - entry_price
                    bar_mae = entry_price - l
                else:
                    bar_mfe = entry_price - l
                    bar_mae = h - entry_price
                if bar_mfe > 0.0 and bar_mfe > curr_mfe:
                    curr_mfe = bar_mfe
                if bar_mae > 0.0 and bar_mae > curr_mae:
                    curr_mae = bar_mae

                pending_entry = False
                pending_direction = 0
                pending_signal_idx = -1
                continue  # Don't check exit on entry bar

        # ─── Check Exit (if we have an active trade) ────────────────────
        if active_idx != -1:
            # If market is closed, freeze the trade — no exit checking
            if is_closed:
                continue

            exit_price = 0.0
            reason = 0

            if direction == 1:  # ════ LONG ════
                # Update MAE/MFE
                bar_mfe = h - entry_price
                bar_mae = entry_price - l
                if bar_mfe > curr_mfe:
                    curr_mfe = bar_mfe
                if bar_mae > curr_mae:
                    curr_mae = bar_mae

                sl_valid = not np.isnan(curr_sl)
                tp_valid = not np.isnan(curr_tp)
                sl_hit = sl_valid and l <= curr_sl
                tp_hit = tp_valid and h >= curr_tp

                if sl_hit and tp_hit:
                    # ── Ambiguity: both triggered on this bar ──
                    if o <= curr_sl:
                        # Gapped through SL — SL wins
                        exit_price = o
                        reason = 1
                    elif o >= curr_tp:
                        # Gapped through TP — TP wins
                        exit_price = o
                        reason = 2
                    else:
                        # Both could be hit intra-bar — worst-case = SL wins
                        exit_price = curr_sl
                        reason = 1
                elif sl_hit:
                    reason = 1
                    exit_price = o if o < curr_sl else curr_sl
                elif tp_hit:
                    reason = 2
                    exit_price = o if o > curr_tp else curr_tp
                elif exit_long[i]:
                    exit_price = c
                    reason = 3

                # Update MAE/MFE with exit excursion
                if reason == 1:
                    sl_mae = entry_price - exit_price
                    if sl_mae > curr_mae:
                        curr_mae = sl_mae
                elif reason == 2:
                    tp_mfe = exit_price - entry_price
                    if tp_mfe > curr_mfe:
                        curr_mfe = tp_mfe

            elif direction == -1:  # ════ SHORT ════
                bar_mfe = entry_price - l
                bar_mae = h - entry_price
                if bar_mfe > curr_mfe:
                    curr_mfe = bar_mfe
                if bar_mae > curr_mae:
                    curr_mae = bar_mae

                sl_valid = not np.isnan(curr_sl)
                tp_valid = not np.isnan(curr_tp)
                sl_hit = sl_valid and h >= curr_sl
                tp_hit = tp_valid and l <= curr_tp

                if sl_hit and tp_hit:
                    if o >= curr_sl:
                        exit_price = o
                        reason = 1
                    elif o <= curr_tp:
                        exit_price = o
                        reason = 2
                    else:
                        # Worst-case = SL wins
                        exit_price = curr_sl
                        reason = 1
                elif sl_hit:
                    reason = 1
                    exit_price = o if o > curr_sl else curr_sl
                elif tp_hit:
                    reason = 2
                    exit_price = o if o < curr_tp else curr_tp
                elif exit_short[i]:
                    exit_price = c
                    reason = 3

                if reason == 1:
                    sl_mae = exit_price - entry_price
                    if sl_mae > curr_mae:
                        curr_mae = sl_mae
                elif reason == 2:
                    tp_mfe = entry_price - exit_price
                    if tp_mfe > curr_mfe:
                        curr_mfe = tp_mfe

            # ── Record trade if exit triggered ──
            if reason > 0:
                slip = slippage_arr[i]
                half_spread = spread_arr[i] / 2.0

                if reason == 3:  # Signal exit: slippage + spread
                    if direction == 1:
                        exit_price = exit_price - slip - half_spread
                    else:
                        exit_price = exit_price + slip + half_spread
                elif reason == 1:  # SL: slippage worsens further
                    if direction == 1:
                        exit_price = exit_price - slip
                    else:
                        exit_price = exit_price + slip
                # TP (reason 2): no slippage — limit order

                # Compute PnL
                if direction == 1:
                    pnl = (exit_price - entry_price) * curr_size
                else:
                    pnl = (entry_price - exit_price) * curr_size

                out_entry_times[trade_count] = entry_time
                out_exit_times[trade_count] = c_time
                out_entry_prices[trade_count] = entry_price
                out_exit_prices[trade_count] = exit_price
                out_directions[trade_count] = direction
                out_reasons[trade_count] = reason
                out_maes[trade_count] = curr_mae
                out_mfes[trade_count] = curr_mfe
                out_entry_indices[trade_count] = active_idx
                out_pnls[trade_count] = pnl

                trade_count += 1
                active_idx = -1
                continue

        # ─── Check Entry ────────────────────────────────────────────────
        if active_idx == -1 and not pending_entry:
            # Skip entry on closed-market or spike bars
            if is_closed or is_spike:
                continue

            if entry_long[i] or entry_short[i]:
                sig_direction = 1 if entry_long[i] else -1

                if entry_on_next_bar:
                    if i + 1 < n:
                        pending_entry = True
                        pending_direction = sig_direction
                        pending_signal_idx = i
                else:
                    # Classic mode: enter at current bar's close
                    raw_entry = c
                    slip = slippage_arr[i]
                    half_spread = spread_arr[i] / 2.0

                    if sig_direction == 1:
                        entry_price = raw_entry + slip + half_spread
                    else:
                        entry_price = raw_entry - slip - half_spread

                    active_idx = i
                    direction = sig_direction
                    curr_sl = sl_arr[i]
                    curr_tp = tp_arr[i]
                    curr_size = size_arr[i]
                    entry_time = c_time
                    curr_mae = 0.0
                    curr_mfe = 0.0
                    # No entry-bar MAE/MFE for close-entry — trade starts at close

    # ─── Force-close any open trade at end of data ──────────────────────
    if active_idx != -1:
        exit_price = closes[n - 1]
        c_time = times[n - 1]

        slip = slippage_arr[n - 1]
        half_spread = spread_arr[n - 1] / 2.0
        if direction == 1:
            exit_price = exit_price - slip - half_spread
            pnl = (exit_price - entry_price) * curr_size
        else:
            exit_price = exit_price + slip + half_spread
            pnl = (entry_price - exit_price) * curr_size

        out_entry_times[trade_count] = entry_time
        out_exit_times[trade_count] = c_time
        out_entry_prices[trade_count] = entry_price
        out_exit_prices[trade_count] = exit_price
        out_directions[trade_count] = direction
        out_reasons[trade_count] = 4  # End of Data
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
        out_entry_indices[:trade_count],
    )
