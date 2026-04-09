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
    final List<_MetricItem> items = [];
    
    final prioritizedKeys = [
      'net_profit', 'max_drawdown', 'win_rate', 'profit_factor', 
      'total_trades', 'sharpe_ratio', 'sqn', 'expected_payoff' // or expectancy
    ];
    
    void addItem(String key, dynamic value) {
      if (value == null || value is! num) return;
      final val = value.toDouble();
      
      String label = key.replaceAll('_', ' ').toUpperCase();
      String valStr;
      Color? color;

      if (key.contains('profit') || key.contains('loss') || key == 'max_drawdown' || key == 'expected_payoff') {
        valStr = '\$${val.toStringAsFixed(2)}';
        if (val > 0) color = const Color(0xFF10B981);
        if (val < 0) color = const Color(0xFFF43F5E);
      } else if (key.contains('rate') || key.contains('pct') || key.contains('percent')) {
        valStr = '${val.toStringAsFixed(1)}%';
      } else if (key == 'total_trades' || key.contains('cons_')) {
        valStr = val.toInt().toString();
      } else {
        valStr = val.toStringAsFixed(2);
      }
      
      // Override specific colors
      if (key == 'sharpe_ratio') color = const Color(0xFF6366F1);
      if (key == 'sqn') color = const Color(0xFF06B6D4);
      if (key == 'max_drawdown' || key == 'max_dd_pct') color = const Color(0xFFF43F5E);

      items.add(_MetricItem(label, valStr, color: color));
    }

    // Process prioritized
    for (final key in prioritizedKeys) {
      if (metrics.containsKey(key)) addItem(key, metrics[key]);
    }
    
    // Process remaining
    for (final entry in metrics.entries) {
      if (!prioritizedKeys.contains(entry.key) && entry.key != 'equity_curve' && entry.key != 'trades') {
        addItem(entry.key, entry.value);
      }
    }
    
    return items;
  }
}

class _MetricItem {
  final String label;
  final String value;
  final Color? color;

  _MetricItem(this.label, this.value, {this.color});
}
