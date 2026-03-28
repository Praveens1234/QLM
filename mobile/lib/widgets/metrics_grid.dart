import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'glass_card.dart';

/// Grid of performance metrics cards for backtest results.
class MetricsGrid extends StatelessWidget {
  final Map<String, dynamic> metrics;

  const MetricsGrid({super.key, required this.metrics});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final items = _buildItems();

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 1.8,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        return GlassCard(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                item.label,
                style: GoogleFonts.inter(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                item.value,
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: item.color ?? (isDark ? Colors.white : Colors.black87),
                  letterSpacing: -0.5,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  List<_MetricItem> _buildItems() {
    final netProfit = (metrics['net_profit'] as num?)?.toDouble() ?? 0;
    final maxDd = (metrics['max_drawdown'] as num?)?.toDouble() ?? 0;
    final maxDdPct = (metrics['max_drawdown_pct'] as num?)?.toDouble() ?? 0;
    final winRate = (metrics['win_rate'] as num?)?.toDouble() ?? 0;
    final pf = (metrics['profit_factor'] as num?)?.toDouble() ?? 0;
    final totalTrades = (metrics['total_trades'] as num?)?.toInt() ?? 0;
    final sharpe = (metrics['sharpe_ratio'] as num?)?.toDouble() ?? 0;
    final sqn = (metrics['sqn'] as num?)?.toDouble() ?? 0;
    final expectancy = (metrics['expectancy'] as num?)?.toDouble() ?? 0;

    return [
      _MetricItem('NET PROFIT', '\$${netProfit.toStringAsFixed(2)}',
          color: netProfit >= 0 ? const Color(0xFF10B981) : const Color(0xFFF43F5E)),
      _MetricItem('MAX DRAWDOWN', '\$${maxDd.toStringAsFixed(2)}',
          color: const Color(0xFFF43F5E)),
      _MetricItem('WIN RATE', '${winRate.toStringAsFixed(1)}%'),
      _MetricItem('PROFIT FACTOR', pf.toStringAsFixed(2)),
      _MetricItem('TOTAL TRADES', totalTrades.toString()),
      _MetricItem('SHARPE RATIO', sharpe.toStringAsFixed(2),
          color: const Color(0xFF6366F1)),
      _MetricItem('SQN', sqn.toStringAsFixed(2),
          color: const Color(0xFF06B6D4)),
      _MetricItem('EXPECTANCY', '\$${expectancy.toStringAsFixed(2)}',
          color: expectancy >= 0 ? const Color(0xFF10B981) : const Color(0xFFF43F5E)),
    ];
  }
}

class _MetricItem {
  final String label;
  final String value;
  final Color? color;

  _MetricItem(this.label, this.value, {this.color});
}
