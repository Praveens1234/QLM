import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../themes/app_theme.dart';

class BacktestRunnerScreen extends StatefulWidget {
  const BacktestRunnerScreen({super.key});

  @override
  State<BacktestRunnerScreen> createState() => _BacktestRunnerScreenState();
}

class _BacktestRunnerScreenState extends State<BacktestRunnerScreen> {
  bool _isRunning = false;
  double _progress = 0.0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Backtest Runner'),
        actions: [
          IconButton(
            icon: const Icon(Icons.play_arrow_rounded),
            onPressed: _isRunning ? null : _startBacktest,
            tooltip: 'Start Backtest',
          ),
          IconButton(
            icon: const Icon(Icons.save_rounded),
            onPressed: () => _saveResults(context),
            tooltip: 'Save Results',
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _buildConfigurationCard(context),
                const SizedBox(height: 16),
                _buildProgressCard(context),
                const SizedBox(height: 16),
                _buildResultsCard(context),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConfigurationCard(BuildContext context) {
    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Configuration',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            _buildConfigRow(
              context,
              'Strategy',
              'Moving Average Crossover',
              Icons.extension_rounded,
            ),
            const SizedBox(height: 12),
            _buildConfigRow(
              context,
              'Dataset',
              'NASDAQ 2020-2024',
              Icons.storage_rounded,
            ),
            const SizedBox(height: 12),
            _buildConfigRow(
              context,
              'Initial Capital',
              '\$10,000.00',
              Icons.account_balance_rounded,
            ),
            const SizedBox(height: 12),
            _buildConfigRow(
              context,
              'Time Period',
              'Jan 2020 - Dec 2024',
              Icons.calendar_today_rounded,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                ElevatedButton.icon(
                  onPressed: () => _configureBacktest(context),
                  icon: const Icon(Icons.settings_rounded),
                  label: const Text('Configure'),
                ),
                const Spacer(),
                if (_isRunning)
                  ElevatedButton.icon(
                    onPressed: _stopBacktest,
                    icon: const Icon(Icons.stop_rounded),
                    label: const Text('Stop'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                    ),
                  )
                else
                  ElevatedButton.icon(
                    onPressed: _startBacktest,
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: const Text('Run Backtest'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressCard(BuildContext context) {
    if (!_isRunning) return const SizedBox.shrink();

    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Backtest Progress',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            LinearProgressIndicator(
              value: _progress,
              minHeight: 20,
              borderRadius: BorderRadius.circular(10),
              backgroundColor: Theme.of(context).colorScheme.surfaceVariant,
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${(_progress * 100).toStringAsFixed(1)}%',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                Text(
                  'Processing...',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Theme.of(context).colorScheme.primary,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              children: [
                Chip(
                  avatar: const Icon(Icons.calendar_today, size: 18),
                  label: Text('Day 145 of 1825'),
                ),
                Chip(
                  avatar: const Icon(Icons.trending_up, size: 18),
                  label: Text('Trades: 847'),
                ),
                Chip(
                  avatar: const Icon(Icons.timer, size: 18),
                  label: Text('ETA: 5m 23s'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultsCard(BuildContext context) {
    if (_isRunning) return const SizedBox.shrink();

    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Results',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
              childAspectRatio: 1.5,
              children: const [
                _ResultTile(
                  title: 'Total Return',
                  value: '+24.8%',
                  icon: Icons.trending_up,
                  color: Colors.green,
                ),
                _ResultTile(
                  title: 'Sharpe Ratio',
                  value: '1.42',
                  icon: Icons.analytics,
                  color: Colors.blue,
                ),
                _ResultTile(
                  title: 'Max Drawdown',
                  value: '-12.3%',
                  icon: Icons.trending_down,
                  color: Colors.red,
                ),
                _ResultTile(
                  title: 'Win Rate',
                  value: '58.2%',
                  icon: Icons.pie_chart,
                  color: Colors.orange,
                ),
              ],
            ),
            const SizedBox(height: 16),
            _buildEquityCurve(context),
            const SizedBox(height: 16),
            _buildTradeList(context),
          ],
        ),
      ),
    );
  }

  Widget _buildEquityCurve(BuildContext context) {
    return Container(
      height: 200,
      child: CustomPaint(
        size: Size.infinite,
        painter: EquityCurvePainter(
          data: _generateEquityData(),
        ),
      ),
    );
  }

  Widget _buildTradeList(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Recent Trades',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            TextButton(
              onPressed: () => _viewAllTrades(context),
              child: const Text('View All'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Card(
          elevation: 0,
          child: ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: 5,
            itemBuilder: (context, index) {
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: index % 2 == 0 ? Colors.green : Colors.red,
                  child: Icon(
                    index % 2 == 0 ? Icons.arrow_upward : Icons.arrow_downward,
                    color: Colors.white,
                    size: 18,
                  ),
                ),
                title: Text(
                  index % 2 == 0 ? 'BUY AAPL' : 'SELL AAPL',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                subtitle: Text('2024-01-${15 + index}'),
                trailing: Text(
                  '${index % 2 == 0 ? '+' : '-'}\$${(index * 45).toStringAsFixed(2)}',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: index % 2 == 0 ? Colors.green : Colors.red,
                        fontWeight: FontWeight.bold,
                      ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildConfigRow(BuildContext context, String label, String value, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              Text(
                value,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  List<double> _generateEquityData() {
    return List.generate(100, (i) => 10000 + (i * 50) + (i % 3 == 0 ? -200 : 100));
  }

  void _startBacktest() {
    setState(() {
      _isRunning = true;
      _progress = 0.0;
    });

    // Simulate progress
    Future.delayed(const Duration(milliseconds: 500), () {
      _updateProgress();
    });
  }

  void _updateProgress() {
    if (!_isRunning) return;

    setState(() {
      _progress += 0.01;
      if (_progress >= 1.0) {
        _progress = 1.0;
        _isRunning = false;
        _onBacktestComplete();
      }
    });

    if (_progress < 1.0) {
      Future.delayed(const Duration(milliseconds: 200), () {
        _updateProgress();
      });
    }
  }

  void _stopBacktest() {
    setState(() {
      _isRunning = false;
    });
  }

  void _onBacktestComplete() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Backtest completed successfully!'),
        backgroundColor: Colors.green,
      ),
    );
  }

  void _configureBacktest(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Configure Backtest'),
        content: const Text('Backtest configuration coming soon'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _saveResults(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Results saved')),
    );
  }

  void _viewAllTrades(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('All Trades'),
        content: const Text('Full trade history coming soon'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
}

class _ResultTile extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;

  const _ResultTile({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: color.withOpacity(0.1),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 24, color: color),
            const SizedBox(height: 12),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
            ),
            Text(
              title,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: color,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class EquityCurvePainter extends CustomPainter {
  final List<double> data;

  EquityCurvePainter({required this.data});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.blue
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    if (data.isEmpty) return;

    final maxValue = data.reduce((a, b) => a > b ? a : b);
    final minValue = data.reduce((a, b) => a < b ? a : b);
    final valueRange = maxValue - minValue;

    final points = data.asMap().entries.map((entry) {
      final x = entry.key * size.width / (data.length - 1);
      final y = size.height - ((entry.value - minValue) / valueRange) * size.height;
      return Offset(x, y);
    }).toList();

    for (int i = 0; i < points.length - 1; i++) {
      canvas.drawLine(points[i], points[i + 1], paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) {
    return true;
  }
}