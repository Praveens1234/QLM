import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/chart_data.dart';
import '../core/constants.dart';

/// Professional candlestick chart widget built with CustomPainter.
/// Supports OHLCV candles, volume, crosshair, indicators, and gestures.
class CandlestickChart extends StatefulWidget {
  final List<ChartBar> bars;
  final List<double?> sma50;
  final List<double?> ema20;
  final List<double?> ema50;
  final List<double?> ema200;
  final Map<String, List<double?>> bollingerBands;
  final List<double?> rsi;
  final bool showVolume;
  final String symbol;

  const CandlestickChart({
    super.key,
    required this.bars,
    this.sma50 = const [],
    this.ema20 = const [],
    this.ema50 = const [],
    this.ema200 = const [],
    this.bollingerBands = const {},
    this.rsi = const [],
    this.showVolume = true,
    this.symbol = '',
  });

  @override
  State<CandlestickChart> createState() => _CandlestickChartState();
}

class _CandlestickChartState extends State<CandlestickChart> with SingleTickerProviderStateMixin {
  // View state
  double _scrollOffset = 0;
  double _candleWidth = 8.0;
  int? _crosshairIndex;
  Offset? _crosshairPos;

  // Gesture tracking
  double _lastScale = 1.0;
  double _lastFocalX = 0;
  late AnimationController _scrollController;
  Animation<double>? _scrollAnimation;

  static const double _minCandleWidth = 3.0;
  static const double _maxCandleWidth = 24.0;
  static const double _priceScaleWidth = 60.0;
  static const double _timeScaleHeight = 24.0;

  @override
  void initState() {
    super.initState();
    _scrollController = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _scrollController.addListener(() {
      if (_scrollAnimation != null) {
        setState(() {
          _scrollOffset = _scrollAnimation!.value.clamp(0.0, _maxScroll);
        });
      }
    });

    // Scroll to latest data (right side)
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToEnd(animated: false));
  }

  void _scrollToEnd({bool animated = true}) {
    if (widget.bars.isEmpty) return;
    final target = _maxScroll;
    if (animated) {
      _scrollAnimation = Tween<double>(begin: _scrollOffset, end: target).animate(
        CurvedAnimation(parent: _scrollController, curve: Curves.easeOutCubic)
      );
      _scrollController.forward(from: 0);
    } else {
      setState(() => _scrollOffset = target);
    }
  }

  @override
  void didUpdateWidget(CandlestickChart oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.bars.length != widget.bars.length && widget.bars.isNotEmpty) {
      // Auto-pin to new data right edge securely
      WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToEnd(animated: true));
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.bars.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.candlestick_chart, size: 48, color: Colors.white.withOpacity(0.1)),
            const SizedBox(height: 12),
            Text(
              'Select a dataset to view chart',
              style: GoogleFonts.inter(
                fontSize: 13,
                color: Colors.white.withOpacity(0.3),
              ),
            ),
          ],
        ),
      );
    }

    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Stack(
      children: [
        GestureDetector(
          onScaleStart: _onScaleStart,
          onScaleUpdate: _onScaleUpdate,
          onScaleEnd: _onScaleEnd,
          onLongPressStart: _onLongPressStart,
          onLongPressMoveUpdate: _onLongPressMoveUpdate,
          onLongPressEnd: (_) => setState(() {
            _crosshairIndex = null;
            _crosshairPos = null;
          }),
          child: Column(
            children: [
              // OHLCV Legend
              if (_crosshairIndex != null && _crosshairIndex! < widget.bars.length)
                _buildLegend(widget.bars[_crosshairIndex!], isDark),
              // Main Chart
              Expanded(
                flex: widget.rsi.isNotEmpty ? 3 : 1,
                child: ClipRect(
                  child: CustomPaint(
                    size: Size.infinite,
                    painter: _CandlestickPainter(
                      bars: widget.bars,
                      scrollOffset: _scrollOffset,
                      candleWidth: _candleWidth,
                      crosshairIndex: _crosshairIndex,
                      crosshairPos: _crosshairPos,
                      isDark: isDark,
                      showVolume: widget.showVolume,
                      sma50: widget.sma50,
                      ema20: widget.ema20,
                      ema50: widget.ema50,
                      ema200: widget.ema200,
                      bollingerBands: widget.bollingerBands,
                      priceScaleWidth: _priceScaleWidth,
                      timeScaleHeight: _timeScaleHeight,
                    ),
                  ),
                ),
              ),
              // RSI Pane
              if (widget.rsi.isNotEmpty)
                Expanded(
                  flex: 1,
                  child: ClipRect(
                    child: CustomPaint(
                      size: Size.infinite,
                      painter: _RSIPainter(
                        bars: widget.bars,
                        rsi: widget.rsi,
                        scrollOffset: _scrollOffset,
                        candleWidth: _candleWidth,
                        isDark: isDark,
                        priceScaleWidth: _priceScaleWidth,
                        crosshairIndex: _crosshairIndex,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        // Overlay Reset FAB
        if (_scrollOffset < _maxScroll - 50)
          Positioned(
            bottom: widget.rsi.isNotEmpty ? MediaQuery.of(context).size.height / 5 : 24,
            right: _priceScaleWidth + 16,
            child: FloatingActionButton.small(
              backgroundColor: isDark ? const Color(0xFF334155) : Colors.white,
              foregroundColor: isDark ? Colors.white : Colors.black87,
              elevation: 4,
              onPressed: () => _scrollToEnd(animated: true),
              child: const Icon(Icons.arrow_forward_ios, size: 16),
            ),
          ),
      ],
    );
  }

  Widget _buildLegend(ChartBar bar, bool isDark) {
    final isUp = bar.close >= bar.open;
    final color = isUp ? AppConstants.chartGreen : AppConstants.chartRed;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Row(
        children: [
          if (widget.symbol.isNotEmpty)
            Text(
              '${widget.symbol}  ',
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: isDark ? Colors.white : Colors.black87,
              ),
            ),
          _legendItem('O', bar.open, color),
          _legendItem('H', bar.high, color),
          _legendItem('L', bar.low, color),
          _legendItem('C', bar.close, color),
          _legendItem('V', bar.volume, const Color(0xFF94A3B8), isVolume: true),
        ],
      ),
    );
  }

  Widget _legendItem(String label, double value, Color color, {bool isVolume = false}) {
    String text;
    if (isVolume) {
      if (value >= 1e9) {
        text = '${(value / 1e9).toStringAsFixed(1)}B';
      } else if (value >= 1e6) {
        text = '${(value / 1e6).toStringAsFixed(1)}M';
      } else if (value >= 1e3) {
        text = '${(value / 1e3).toStringAsFixed(1)}K';
      } else {
        text = value.toStringAsFixed(0);
      }
    } else {
      text = value.toStringAsFixed(2);
    }

    return Padding(
      padding: const EdgeInsets.only(right: 10),
      child: RichText(
        text: TextSpan(
          children: [
            TextSpan(
              text: '$label ',
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: FontWeight.w500,
                color: const Color(0xFF64748B),
              ),
            ),
            TextSpan(
              text: text,
              style: GoogleFonts.jetBrainsMono(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  double get _maxScroll {
    final renderWidth = (context.size?.width ?? 300) - _priceScaleWidth;
    final totalWidth = widget.bars.length * _candleWidth;
    return math.max(0.0, totalWidth - renderWidth + _candleWidth * 5);
  }

  void _onScaleStart(ScaleStartDetails details) {
    _lastScale = 1.0;
    _lastFocalX = details.localFocalPoint.dx;
    _scrollController.stop(); // Intercept active fling
  }

  void _onScaleUpdate(ScaleUpdateDetails details) {
    setState(() {
      // Precise pinch-to-zoom centered on focal point
      if (details.scale != 1.0) {
        final scaleDelta = details.scale / _lastScale;
        final focalTimeX = details.localFocalPoint.dx + _scrollOffset;
        final focalIdx = focalTimeX / _candleWidth;
        
        _candleWidth = (_candleWidth * scaleDelta).clamp(_minCandleWidth, _maxCandleWidth);
        _lastScale = details.scale;
        
        _scrollOffset = (focalIdx * _candleWidth) - details.localFocalPoint.dx;
      }

      // Smooth Panning
      final dx = details.localFocalPoint.dx - _lastFocalX;
      _lastFocalX = details.localFocalPoint.dx;
      _scrollOffset -= dx;
      _scrollOffset = _scrollOffset.clamp(0, _maxScroll);
    });
  }

  void _onScaleEnd(ScaleEndDetails details) {
    final velocity = details.velocity.pixelsPerSecond.dx;
    if (velocity.abs() > 300) {
      final double distance = velocity * 0.4;
      _scrollAnimation = Tween<double>(
        begin: _scrollOffset,
        end: (_scrollOffset - distance).clamp(0, _maxScroll),
      ).animate(CurvedAnimation(
        parent: _scrollController,
        curve: Curves.easeOutCubic,
      ));
      _scrollController.forward(from: 0);
    }
  }

  void _onLongPressStart(LongPressStartDetails details) {
    _updateCrosshair(details.localPosition);
  }

  void _onLongPressMoveUpdate(LongPressMoveUpdateDetails details) {
    _updateCrosshair(details.localPosition);
  }

  void _updateCrosshair(Offset localPos) {

    final x = localPos.dx + _scrollOffset;
    final idx = (x / _candleWidth).floor();

    setState(() {
      _crosshairIndex = idx.clamp(0, widget.bars.length - 1);
      _crosshairPos = localPos;
    });
  }
}

// ─── Main Candlestick Painter ─────────────────────────
class _CandlestickPainter extends CustomPainter {
  final List<ChartBar> bars;
  final double scrollOffset;
  final double candleWidth;
  final int? crosshairIndex;
  final Offset? crosshairPos;
  final bool isDark;
  final bool showVolume;
  final List<double?> sma50;
  final List<double?> ema20;
  final List<double?> ema50;
  final List<double?> ema200;
  final Map<String, List<double?>> bollingerBands;
  final double priceScaleWidth;
  final double timeScaleHeight;

  _CandlestickPainter({
    required this.bars,
    required this.scrollOffset,
    required this.candleWidth,
    required this.crosshairIndex,
    required this.crosshairPos,
    required this.isDark,
    required this.showVolume,
    required this.sma50,
    required this.ema20,
    required this.ema50,
    required this.ema200,
    required this.bollingerBands,
    required this.priceScaleWidth,
    required this.timeScaleHeight,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (bars.isEmpty) return;

    final chartWidth = size.width - priceScaleWidth;
    final chartHeight = size.height - timeScaleHeight;
    final volumeHeight = showVolume ? chartHeight * 0.15 : 0.0;
    final priceHeight = chartHeight - volumeHeight;

    // Determine visible bar range
    final startIdx = math.max(0, (scrollOffset / candleWidth).floor() - 1);
    final endIdx = math.min(bars.length - 1, ((scrollOffset + chartWidth) / candleWidth).ceil() + 1);

    if (startIdx >= endIdx) return;

    // Find price range in visible area
    double minPrice = double.infinity;
    double maxPrice = -double.infinity;
    double maxVol = 0;

    for (int i = startIdx; i <= endIdx; i++) {
      final bar = bars[i];
      minPrice = math.min(minPrice, bar.low);
      maxPrice = math.max(maxPrice, bar.high);
      maxVol = math.max(maxVol, bar.volume);
    }

    // Add padding to price range
    final priceRange = maxPrice - minPrice;
    final pricePadding = priceRange * 0.05;
    minPrice -= pricePadding;
    maxPrice += pricePadding;

    // Grid
    _drawGrid(canvas, size, chartWidth, priceHeight, minPrice, maxPrice);

    // Price scale
    _drawPriceScale(canvas, size, chartWidth, priceHeight, minPrice, maxPrice);

    // Clip to chart area
    canvas.save();
    canvas.clipRect(Rect.fromLTWH(0, 0, chartWidth, chartHeight));

    // Draw candles and volume
    for (int i = startIdx; i <= endIdx; i++) {
      final bar = bars[i];
      final x = i * candleWidth - scrollOffset;
      final centerX = x + candleWidth / 2;

      // Skip if outside view
      if (centerX < -candleWidth || centerX > chartWidth + candleWidth) continue;

      final isUp = bar.close >= bar.open;
      final color = isUp ? AppConstants.chartGreen : AppConstants.chartRed;

      // Candle body
      final bodyTop = priceHeight - ((math.max(bar.open, bar.close) - minPrice) / (maxPrice - minPrice)) * priceHeight;
      final bodyBottom = priceHeight - ((math.min(bar.open, bar.close) - minPrice) / (maxPrice - minPrice)) * priceHeight;
      final bodyHeight = math.max(1.0, bodyBottom - bodyTop);

      final bodyPaint = Paint()
        ..color = color
        ..style = PaintingStyle.fill;

      canvas.drawRect(
        Rect.fromLTWH(x + 1, bodyTop, candleWidth - 2, bodyHeight),
        bodyPaint,
      );

      // Wicks
      final wickPaint = Paint()
        ..color = color
        ..strokeWidth = 1;

      final highY = priceHeight - ((bar.high - minPrice) / (maxPrice - minPrice)) * priceHeight;
      final lowY = priceHeight - ((bar.low - minPrice) / (maxPrice - minPrice)) * priceHeight;

      canvas.drawLine(Offset(centerX, highY), Offset(centerX, bodyTop), wickPaint);
      canvas.drawLine(Offset(centerX, bodyBottom), Offset(centerX, lowY), wickPaint);

      // Volume bars
      if (showVolume && maxVol > 0) {
        final volHeight = (bar.volume / maxVol) * volumeHeight;
        final volTop = priceHeight + (volumeHeight - volHeight);
        final volColor = isUp
            ? AppConstants.chartGreen.withOpacity(0.25)
            : AppConstants.chartRed.withOpacity(0.25);

        canvas.drawRect(
          Rect.fromLTWH(x + 1, volTop, candleWidth - 2, volHeight),
          Paint()..color = volColor,
        );
      }
    }

    // Draw indicator lines
    _drawIndicatorLine(canvas, sma50, chartWidth, priceHeight, minPrice, maxPrice, AppConstants.sma50Color, 1.0);
    _drawIndicatorLine(canvas, ema20, chartWidth, priceHeight, minPrice, maxPrice, AppConstants.ema20Color, 1.0);
    _drawIndicatorLine(canvas, ema50, chartWidth, priceHeight, minPrice, maxPrice, AppConstants.ema50Color, 1.5);
    _drawIndicatorLine(canvas, ema200, chartWidth, priceHeight, minPrice, maxPrice, AppConstants.ema200Color, 2.0);

    // Bollinger Bands
    final bbUpper = bollingerBands['upper'] ?? [];
    final bbMiddle = bollingerBands['middle'] ?? [];
    final bbLower = bollingerBands['lower'] ?? [];
    _drawIndicatorLine(canvas, bbUpper, chartWidth, priceHeight, minPrice, maxPrice, AppConstants.bbColor, 1.0);
    _drawIndicatorLine(canvas, bbMiddle, chartWidth, priceHeight, minPrice, maxPrice, Colors.white.withOpacity(0.4), 1.0);
    _drawIndicatorLine(canvas, bbLower, chartWidth, priceHeight, minPrice, maxPrice, AppConstants.bbColor, 1.0);

    // Crosshair
    if (crosshairIndex != null && crosshairPos != null) {
      _drawCrosshair(canvas, size, chartWidth, priceHeight, minPrice, maxPrice);
    }

    canvas.restore();
  }

  void _drawGrid(Canvas canvas, Size size, double chartWidth, double priceHeight, double minPrice, double maxPrice) {
    final gridPaint = Paint()
      ..color = isDark ? const Color(0x0AFFFFFF) : const Color(0x0A000000)
      ..strokeWidth = 0.5;

    // Horizontal grid lines
    const gridCount = 5;
    for (int i = 0; i <= gridCount; i++) {
      final y = (i / gridCount) * priceHeight;
      canvas.drawLine(Offset(0, y), Offset(chartWidth, y), gridPaint);
    }

    // Vertical grid lines
    final visibleBars = (chartWidth / candleWidth).ceil();
    final step = math.max(1, visibleBars ~/ 6);
    final startIdx = (scrollOffset / candleWidth).floor();

    for (int i = startIdx; i < startIdx + visibleBars + step; i += step) {
      final x = i * candleWidth - scrollOffset + candleWidth / 2;
      if (x >= 0 && x <= chartWidth) {
        canvas.drawLine(Offset(x, 0), Offset(x, priceHeight), gridPaint);
      }
    }
  }

  void _drawPriceScale(Canvas canvas, Size size, double chartWidth, double priceHeight, double minPrice, double maxPrice) {
    final scaleBg = Paint()
      ..color = isDark ? const Color(0xFF0F172A) : Colors.white;
    canvas.drawRect(Rect.fromLTWH(chartWidth, 0, priceScaleWidth, priceHeight), scaleBg);

    const gridCount = 5;
    for (int i = 0; i <= gridCount; i++) {
      final y = (i / gridCount) * priceHeight;
      final price = maxPrice - (i / gridCount) * (maxPrice - minPrice);

      final textPainter = TextPainter(
        text: TextSpan(
          text: price.toStringAsFixed(2),
          style: TextStyle(
            fontFamily: 'monospace',
            fontSize: 9,
            color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();
      textPainter.paint(canvas, Offset(chartWidth + 4, y - textPainter.height / 2));
    }
  }

  void _drawIndicatorLine(Canvas canvas, List<double?> data, double chartWidth, double priceHeight, double minPrice, double maxPrice, Color color, double width) {
    if (data.isEmpty || data.length != bars.length) return;

    final paint = Paint()
      ..color = color
      ..strokeWidth = width
      ..style = PaintingStyle.stroke;

    final path = Path();
    bool started = false;

    final startIdx = math.max(0, (scrollOffset / candleWidth).floor() - 1);
    final endIdx = math.min(bars.length - 1, ((scrollOffset + chartWidth) / candleWidth).ceil() + 1);

    for (int i = startIdx; i <= endIdx; i++) {
      final value = data[i];
      if (value == null) {
        started = false;
        continue;
      }

      final x = i * candleWidth - scrollOffset + candleWidth / 2;
      final y = priceHeight - ((value - minPrice) / (maxPrice - minPrice)) * priceHeight;

      if (!started) {
        path.moveTo(x, y);
        started = true;
      } else {
        path.lineTo(x, y);
      }
    }

    canvas.drawPath(path, paint);
  }

  void _drawCrosshair(Canvas canvas, Size size, double chartWidth, double priceHeight, double minPrice, double maxPrice) {
    if (crosshairIndex == null || crosshairPos == null) return;

    final idx = crosshairIndex!;
    if (idx < 0 || idx >= bars.length) return;

    final x = idx * candleWidth - scrollOffset + candleWidth / 2;
    final bar = bars[idx];
    final y = priceHeight - ((bar.close - minPrice) / (maxPrice - minPrice)) * priceHeight;

    final crosshairPaint = Paint()
      ..color = AppConstants.chartCrosshair
      ..strokeWidth = 0.5;

    // Vertical line
    canvas.drawLine(Offset(x, 0), Offset(x, priceHeight), crosshairPaint);
    // Horizontal line
    canvas.drawLine(Offset(0, y), Offset(chartWidth, y), crosshairPaint);

    // Price label
    final priceBg = Paint()..color = const Color(0xFF6366F1);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(chartWidth, y - 10, priceScaleWidth, 20),
        const Radius.circular(4),
      ),
      priceBg,
    );

    final priceText = TextPainter(
      text: TextSpan(
        text: bar.close.toStringAsFixed(2),
        style: const TextStyle(fontFamily: 'monospace', fontSize: 9, color: Colors.white),
      ),
      textDirection: TextDirection.ltr,
    );
    priceText.layout();
    priceText.paint(canvas, Offset(chartWidth + 4, y - priceText.height / 2));

    // Dot at crosshair point
    canvas.drawCircle(
      Offset(x, y),
      3,
      Paint()..color = const Color(0xFF6366F1),
    );
  }

  @override
  bool shouldRepaint(covariant _CandlestickPainter oldDelegate) => true;
}

// ─── RSI Sub-pane Painter ────────────────────────────
class _RSIPainter extends CustomPainter {
  final List<ChartBar> bars;
  final List<double?> rsi;
  final double scrollOffset;
  final double candleWidth;
  final bool isDark;
  final double priceScaleWidth;
  final int? crosshairIndex;

  _RSIPainter({
    required this.bars,
    required this.rsi,
    required this.scrollOffset,
    required this.candleWidth,
    required this.isDark,
    required this.priceScaleWidth,
    required this.crosshairIndex,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (rsi.isEmpty || bars.isEmpty) return;

    final chartWidth = size.width - priceScaleWidth;
    final chartHeight = size.height;

    // Background separator
    canvas.drawLine(
      Offset(0, 0),
      Offset(chartWidth, 0),
      Paint()..color = isDark ? const Color(0x1AFFFFFF) : const Color(0x1A000000),
    );

    // Grid lines at 30 and 70
    final gridPaint = Paint()
      ..color = isDark ? const Color(0x0AFFFFFF) : const Color(0x0A000000)
      ..strokeWidth = 0.5;

    final y30 = chartHeight - (30 / 100) * chartHeight;
    final y70 = chartHeight - (70 / 100) * chartHeight;

    // Oversold/overbought zones
    canvas.drawRect(
      Rect.fromLTWH(0, 0, chartWidth, y70),
      Paint()..color = AppConstants.chartRed.withOpacity(0.03),
    );
    canvas.drawRect(
      Rect.fromLTWH(0, y30, chartWidth, chartHeight - y30),
      Paint()..color = AppConstants.chartGreen.withOpacity(0.03),
    );

    canvas.drawLine(Offset(0, y30), Offset(chartWidth, y30), gridPaint);
    canvas.drawLine(Offset(0, y70), Offset(chartWidth, y70), gridPaint);

    // RSI line
    final paint = Paint()
      ..color = AppConstants.rsiColor
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    final path = Path();
    bool started = false;

    final startIdx = math.max(0, (scrollOffset / candleWidth).floor() - 1);
    final endIdx = math.min(bars.length - 1, ((scrollOffset + chartWidth) / candleWidth).ceil() + 1);

    for (int i = startIdx; i <= endIdx; i++) {
      if (i >= rsi.length) break;
      final value = rsi[i];
      if (value == null) {
        started = false;
        continue;
      }

      final x = i * candleWidth - scrollOffset + candleWidth / 2;
      final y = chartHeight - (value / 100) * chartHeight;

      if (!started) {
        path.moveTo(x, y);
        started = true;
      } else {
        path.lineTo(x, y);
      }
    }

    canvas.save();
    canvas.clipRect(Rect.fromLTWH(0, 0, chartWidth, chartHeight));
    canvas.drawPath(path, paint);
    canvas.restore();

    // Scale labels
    final scaleBg = Paint()..color = isDark ? const Color(0xFF0F172A) : Colors.white;
    canvas.drawRect(Rect.fromLTWH(chartWidth, 0, priceScaleWidth, chartHeight), scaleBg);

    for (final val in [0, 30, 50, 70, 100]) {
      final y = chartHeight - (val / 100) * chartHeight;
      final tp = TextPainter(
        text: TextSpan(
          text: val.toString(),
          style: TextStyle(
            fontFamily: 'monospace',
            fontSize: 8,
            color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      tp.layout();
      tp.paint(canvas, Offset(chartWidth + 4, y - tp.height / 2));
    }
  }

  @override
  bool shouldRepaint(covariant _RSIPainter oldDelegate) => true;
}
