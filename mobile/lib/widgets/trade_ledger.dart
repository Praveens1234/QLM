import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Trade ledger list for backtest results — optimized for mobile.
class TradeLedger extends StatelessWidget {
  final List<Map<String, dynamic>> trades;

  const TradeLedger({super.key, required this.trades});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (trades.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
            'No trades',
            style: GoogleFonts.inter(
              fontSize: 13,
              color: isDark ? const Color(0xFF475569) : const Color(0xFF94A3B8),
            ),
          ),
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: trades.length,
      itemBuilder: (context, index) {
        final t = trades[index];
        return _TradeRow(trade: t, isDark: isDark, index: index);
      },
    );
  }
}

class _TradeRow extends StatelessWidget {
  final Map<String, dynamic> trade;
  final bool isDark;
  final int index;

  const _TradeRow({
    required this.trade,
    required this.isDark,
    required this.index,
  });

  @override
  Widget build(BuildContext context) {
    final pnl = (trade['pnl'] as num?)?.toDouble() ?? 0;
    final isWin = pnl > 0;
    final direction = trade['direction']?.toString() ?? '';
    final isLong = direction == 'long';
    final entryTime = trade['entry_time']?.toString() ?? '';
    final exitReason = trade['exit_reason']?.toString() ?? '';
    final rMultiple = (trade['r_multiple'] as num?)?.toDouble() ?? 0;
    final entryPrice = (trade['entry_price'] as num?)?.toDouble() ?? 0;
    final exitPrice = (trade['exit_price'] as num?)?.toDouble() ?? 0;
    final duration = (trade['duration'] as num?)?.toDouble() ?? 0;

    return Container(
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: isDark ? const Color(0xFF1E293B) : const Color(0xFFE2E8F0),
            width: 0.5,
          ),
        ),
      ),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 12),
        childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
        leading: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: isLong
                ? const Color(0xFF10B981).withOpacity(0.1)
                : const Color(0xFFF43F5E).withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            isLong ? Icons.trending_up : Icons.trending_down,
            size: 16,
            color: isLong ? const Color(0xFF10B981) : const Color(0xFFF43F5E),
          ),
        ),
        title: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    entryTime.split(' ').first,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: isDark ? Colors.white : Colors.black87,
                    ),
                  ),
                  Text(
                    entryTime.split(' ').length > 1 ? entryTime.split(' ')[1] : '',
                    style: GoogleFonts.inter(
                      fontSize: 10,
                      color: const Color(0xFF64748B),
                    ),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${isWin ? '+' : ''}\$${pnl.toStringAsFixed(2)}',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: isWin ? const Color(0xFF10B981) : const Color(0xFFF43F5E),
                  ),
                ),
                Text(
                  '${rMultiple.toStringAsFixed(2)}R',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    color: const Color(0xFF64748B),
                  ),
                ),
              ],
            ),
          ],
        ),
        children: [
          _detailRow('Entry Price', entryPrice.toStringAsFixed(2), isDark),
          _detailRow('Exit Price', exitPrice.toStringAsFixed(2), isDark),
          _detailRow('Duration', '${duration.toStringAsFixed(0)} min', isDark),
          _detailRow('Exit Reason', exitReason, isDark),
          if (trade['sl'] != null)
            _detailRow('Stop Loss', (trade['sl'] as num).toDouble().toStringAsFixed(2), isDark),
          if (trade['tp'] != null)
            _detailRow('Take Profit', (trade['tp'] as num).toDouble().toStringAsFixed(2), isDark),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 11,
              color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
            ),
          ),
          Text(
            value,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: isDark ? const Color(0xFFCBD5E1) : const Color(0xFF475569),
            ),
          ),
        ],
      ),
    );
  }
}
