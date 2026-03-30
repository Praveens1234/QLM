import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:provider/provider.dart';
import '../widgets/metric_card.dart';
import '../widgets/performance_chart.dart';
import '../providers/server_provider.dart';
import '../themes/app_theme.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _buildAppBar(context),
      body: RefreshIndicator(
        onRefresh: _refreshData,
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(16),
              sliver: SliverToBoxAdapter(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildWelcomeSection(context),
                    const SizedBox(height: 24),
                    _buildMetricsGrid(context),
                    const SizedBox(height: 24),
                    _buildChartsSection(context),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  AppBar _buildAppBar(BuildContext context) {
    return AppBar(
      title: const Text('Dashboard'),
      actions: [
        IconButton(
          icon: const Icon(Icons.notifications_rounded),
          onPressed: () {},
          tooltip: 'Notifications',
        ),
        IconButton(
          icon: const Icon(Icons.refresh_rounded),
          onPressed: _refreshData,
          tooltip: 'Refresh',
        ),
      ],
    );
  }

  Widget _buildWelcomeSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Welcome Back',
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 8),
        Text(
          'Your trading systems are running smoothly',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
        ),
        const SizedBox(height: 16),
        _buildConnectionStatus(context),
      ],
    );
  }

  Widget _buildConnectionStatus(BuildContext context) {
    final serverUrl = 'http://localhost:3000'; // placeholder
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.success50,
        border: Border.all(color: AppTheme.success500),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(
            Icons.check_circle_rounded,
            color: AppTheme.success600,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Connected to Server',
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: AppTheme.success600,
                      ),
                ),
                Text(
                  serverUrl,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppTheme.success600,
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricsGrid(BuildContext context) {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      crossAxisSpacing: 16,
      mainAxisSpacing: 16,
      childAspectRatio: 1.3,
      children: const [
        MetricCard(
          title: 'Active Strategies',
          value: '12',
          icon: Icons.extension,
          change: '+2',
          changeType: ChangeType.positive,
        ),
        MetricCard(
          title: 'Total Return',
          value: '+24.8%',
          icon: Icons.trending_up,
          change: '+3.2%',
          changeType: ChangeType.positive,
        ),
        MetricCard(
          title: 'Data Sets',
          value: '47',
          icon: Icons.storage,
          change: '+5',
          changeType: ChangeType.positive,
        ),
        MetricCard(
          title: 'Active Trades',
          value: '8',
          icon: Icons.show_chart,
          change: '-2',
          changeType: ChangeType.negative,
        ),
      ],
    );
  }

  Widget _buildChartsSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Performance Overview',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            TextButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.arrow_forward_rounded, size: 18),
              label: const Text('View Details'),
            ),
          ],
        ),
        const SizedBox(height: 16),
        _buildPerformanceChart(context),
        const SizedBox(height: 24),
        _buildRecentActivity(context),
      ],
    );
  }

  Widget _buildPerformanceChart(BuildContext context) {
    return Card(
      elevation: 0,
      color: Theme.of(context).colorScheme.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Portfolio Value',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                Row(
                  children: [
                    _buildTimeFilter(context, '1D', false),
                    const SizedBox(width: 8),
                    _buildTimeFilter(context, '1W', false),
                    const SizedBox(width: 8),
                    _buildTimeFilter(context, '1M', true),
                    const SizedBox(width: 8),
                    _buildTimeFilter(context, '1Y', false),
                  ],
                ),
              ],
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
                    horizontalInterval: 2000,
                    getDrawingVerticalLine: (value) => FlLine(
                      color: Theme.of(context).dividerColor,
                      strokeWidth: .5,
                    ),
                    getDrawingHorizontalLine: (value) => FlLine(
                      color: Theme.of(context).dividerColor,
                      strokeWidth: .5,
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

  Widget _buildTimeFilter(BuildContext context, String label, bool isActive) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: isActive ? Theme.of(context).colorScheme.primaryContainer : null,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isActive
              ? Theme.of(context).colorScheme.primary
              : Theme.of(context).dividerColor,
        ),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              fontWeight: FontWeight.w600,
              color: isActive
                  ? Theme.of(context).colorScheme.primary
                  : Theme.of(context).colorScheme.onSurfaceVariant,
            ),
      ),
    );
  }

  Widget _buildRecentActivity(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Recent Activity',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 16),
        Card(
          elevation: 0,
          child: Column(
            children: List.generate(5, (index) {
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                  child: Icon(
                    Icons.auto_graph_rounded,
                    color: Theme.of(context).colorScheme.primary,
                    size: 20,
                  ),
                ),
                title: Text(
                  'Strategy ${index + 1} executed',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                subtitle: Text('2 min ago'),
                trailing: Icon(Icons.arrow_forward),
              );
            }),
          ),
        ),
      ],
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

  Future<void> _refreshData() async {
    await Future.delayed(const Duration(seconds: 1));
  }
}