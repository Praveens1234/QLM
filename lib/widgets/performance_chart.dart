import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../themes/app_theme.dart';

class PerformanceChartWidget extends StatelessWidget {
  const PerformanceChartWidget({super.key});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Portfolio Performance',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: true,
                    drawHorizontalLine: true,
                    verticalInterval: 1,
                    horizontalInterval: 5000,
                    getDrawingVerticalLine: (value) => FlLine(
                      color: Theme.of(context).dividerColor,
                      strokeWidth: 0.5,
                    ),
                    getDrawingHorizontalLine: (value) => FlLine(
                      color: Theme.of(context).dividerColor,
                      strokeWidth: 0.5,
                    ),
                  ),
                  borderData: FlBorderData(show: false),
                  lineBarsData: [_createLineChartData()],
                  titlesData: FlTitlesData(show: false),
                  lineTouchData: LineTouchData(
                    enabled: true,
                    touchTooltipData: LineTouchTooltipData(
                      getTooltipColor: (touchedSpot) {
                        return Theme.of(context).colorScheme.surface;
                      },
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  LineChartBarData _createLineChartData() {
    final List<FlSpot> spots = [
      FlSpot(0, 50000),
      FlSpot(1, 52000),
      FlSpot(2, 51000),
      FlSpot(3, 53000),
      FlSpot(4, 55000),
      FlSpot(5, 54000),
      FlSpot(6, 58000),
    ];

    return LineChartBarData(
      spots: spots,
      isCurved: true,
      color: AppTheme.seedColor,
      barWidth: 3,
      isStrokeCapRound: true,
      dotData: FlDotData(show: false),
      belowBarData: BarAreaData(
        show: true,
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            AppTheme.seedColor.withOpacity(0.1),
            Colors.transparent,
          ],
        ),
      ),
    );
  }
}