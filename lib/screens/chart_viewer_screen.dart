import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../themes/app_theme.dart';

class ChartViewerScreen extends StatefulWidget {
  const ChartViewerScreen({super.key});

  @override
  State<ChartViewerScreen> createState() => _ChartViewerScreenState();
}

class _ChartViewerScreenState extends State<ChartViewerScreen> {
  String _selectedTimeframe = '1D';
  final List<String> _timeframes = ['1m', '5m', '15m', '1H', '4H', '1D', '1W', '1M'];
  final List<String> _indicators = ['RSI', 'MACD', 'MA', 'Bollinger', 'Volume'];
  final Set<String> _activeIndicators = {};

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Chart Viewer'),
        actions: [
          _buildIndicatorsButton(context),
          IconButton(
            icon: const Icon(Icons.fullscreen_rounded),
            onPressed: () => _enterFullscreen(context),
            tooltip: 'Fullscreen',
          ),
          IconButton(
            icon: const Icon(Icons.download_rounded),
            onPressed: () => _downloadChart(context),
            tooltip: 'Download Chart',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildTimeframeSelector(context),
          const Divider(height: 1),
          Expanded(
            child: Stack(
              children: [
                _buildCandlestickChart(context),
                if (_activeIndicators.isNotEmpty)
                  _buildIndicatorsPanel(context),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimeframeSelector(BuildContext context) {
    return Container(
      height: 50,
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: Theme.of(context).dividerColor),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              itemCount: _timeframes.length,
              itemBuilder: (context, index) {
                final timeframe = _timeframes[index];
                final isActive = _selectedTimeframe == timeframe;
                return _buildTimeframeButton(context, timeframe, isActive);
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimeframeButton(BuildContext context, String timeframe, bool isActive) {
    return GestureDetector(
      onTap: () => _selectTimeframe(timeframe),
      child: Container(
        width: 60,
        alignment: Alignment.center,
        margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
        decoration: BoxDecoration(
          color: isActive ? Theme.of(context).colorScheme.primary : null,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          timeframe,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
                fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                color: isActive
                    ? Theme.of(context).colorScheme.onPrimary
                    : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
        ),
      ),
    );
  }

  Widget _buildCandlestickChart(BuildContext context) {
    return InteractiveViewer(
      boundaryMargin: EdgeInsets.all(100),
      minScale: 0.5,
      maxScale: 5.0,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Expanded(
              child: Container(
                alignment: Alignment.center,
                child: CustomPaint(
                  size: Size.infinite,
                  painter: CandlestickChartPainter(
                    data: _generateSampleData(),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            _buildVolumeChart(context),
          ],
        ),
      ),
    );
  }

  Widget _buildVolumeChart(BuildContext context) {
    return Container(
      height: 100,
      child: CustomPaint(
        size: Size.infinite,
        painter: VolumeChartPainter(
          data: _generateSampleData(),
        ),
      ),
    );
  }

  Widget _buildIndicatorsButton(BuildContext context) {
    return Stack(
      children: [
        IconButton(
          icon: Icon(Icons.analytics_rounded),
          onPressed: () => _showIndicatorsDialog(context),
          tooltip: 'Indicators',
        ),
        if (_activeIndicators.isNotEmpty)
          Positioned(
            top: 8,
            right: 8,
            child: Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
                shape: BoxShape.circle,
              ),
              child: Text(
                _activeIndicators.length.toString(),
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onPrimary,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildIndicatorsPanel(BuildContext context) {
    return Align(
      alignment: Alignment.topRight,
      child: Container(
        width: 200,
        height: 150,
        margin: const EdgeInsets.all(16),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface.withOpacity(0.9),
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 10,
              offset: Offset(0, 4),
            ),
          ],
        ),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Active Indicators',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              ..._activeIndicators.map((indicator) {
                return Column(
                  children: [
                    _buildIndicatorValue(context, indicator),
                    const SizedBox(height: 8),
                  ],
                );
              }),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildIndicatorValue(BuildContext context, String indicator) {
    String value = '-';
    Color color = Theme.of(context).colorScheme.onSurface;

    switch (indicator) {
      case 'RSI':
        value = '45.2';
        color = Colors.orange;
        break;
      case 'MACD':
        value = '-0.12';
        color = Colors.red;
        break;
      case 'MA':
        value = '298.45';
        color = Colors.green;
        break;
      case 'Volume':
        value = '1.2M';
        color = Theme.of(context).colorScheme.onSurface;
        break;
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          indicator,
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: color,
                fontWeight: FontWeight.bold,
              ),
        ),
      ],
    );
  }

  void _selectTimeframe(String timeframe) {
    setState(() {
      _selectedTimeframe = timeframe;
    });
  }

  void _showIndicatorsDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Technical Indicators'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: _indicators.map((indicator) {
              return CheckboxListTile(
                title: Text(indicator),
                value: _activeIndicators.contains(indicator),
                onChanged: (value) {
                  setState(() {
                    if (value == true) {
                      _activeIndicators.add(indicator);
                    } else {
                      _activeIndicators.remove(indicator);
                    }
                  });
                },
              );
            }).toList(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _enterFullscreen(BuildContext context) {
    // TODO: Implement fullscreen mode
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Fullscreen mode coming soon')),
    );
  }

  void _downloadChart(BuildContext context) {
    // TODO: Implement chart download
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Chart download coming soon')),
    );
  }

  List<CandlestickData> _generateSampleData() {
    return List.generate(50, (index) {
      return CandlestickData(
        open: 290 + (index * 2.5),
        high: 298 + (index * 2.5),
        low: 287 + (index * 2.5),
        close: 295 + (index * 2.5),
        volume: (1000000 + (index * 50000)),
        time:
DateTime.now().subtract(Duration(minutes: 50 - index)),
      );
    });
    }
    }

class CandlestickData {
  final double open;
  final double high;
  final double low;
  final double close;
  final double volume;
  final DateTime time;

  CandlestickData({
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.volume,
    required this.time,
  });
}

class CandlestickChartPainter extends CustomPainter {
  final List<CandlestickData> data;

  CandlestickChartPainter({required this.data});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint();
    final bullishColor = Colors.green;
    final bearishColor = Colors.red;

    final candleWidth = size.width / data.length * 0.6;
    final spacing = size.width / data.length * 0.4;

    for (int i = 0; i < data.length; i++) {
      final candle = data[i];
      final isBullish = candle.close >= candle.open;
      final color = isBullish ? bullishColor : bearishColor;

      final x = i * (candleWidth + spacing) + spacing / 2;

      // Draw wick
      paint.color = color;
      canvas.drawLine(
        Offset(x + candleWidth / 2, candle.low),
        Offset(x + candleWidth / 2, candle.high),
        paint,
      );

      // Draw body
      paint.color = color;
      canvas.drawRect(
        Rect.fromLTRB(
          x,
          isBullish ? candle.close : candle.open,
          x + candleWidth,
          isBullish ? candle.open : candle.close,
        ),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) {
    return true;
  }
}

class VolumeChartPainter extends CustomPainter {
  final List<CandlestickData> data;

  VolumeChartPainter({required this.data});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint();
    final barWidth = size.width / data.length * 0.8;
    final spacing = size.width / data.length * 0.2;

    // Find max volume for scaling
    final maxVolume = data.map((d) => d.volume).reduce((a, b) => a > b ? a : b);

    for (int i = 0; i < data.length; i++) {
      final volume = data[i].volume;
      final height = (volume / maxVolume) * size.height;
      final x = i * (barWidth + spacing);
      final color = data[i].close >= data[i].open
          ? Colors.green.withOpacity(0.6)
          : Colors.red.withOpacity(0.6);

      paint.color = color;
      canvas.drawRect(
        Rect.fromLTRB(x, size.height - height, x + barWidth, size.height),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) {
    return true;
  }
}