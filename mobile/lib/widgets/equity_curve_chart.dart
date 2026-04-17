import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';

import '../core/constants.dart';

class EquityCurveChart extends StatelessWidget {
  final List<Map<String, dynamic>> data;

  const EquityCurveChart({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) {
      return const Center(child: Text('No equity data available'));
    }

    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AspectRatio(
      aspectRatio: 1.5,
      child: CustomPaint(
        size: Size.infinite,
        painter: _EquityPainter(data: data, isDark: isDark),
      ),
    );
  }
}

class _EquityPainter extends CustomPainter {
  final List<Map<String, dynamic>> data;
  final bool isDark;

  _EquityPainter({required this.data, required this.isDark});

  @override
  void paint(Canvas canvas, Size size) {
    final width = size.width - 60; // Leave 60px for scale
    const ddHeight = 60.0;
    final eqHeight = size.height - ddHeight;

    double minEq = double.infinity;
    double maxEq = -double.infinity;
    double minDd = 0; // Drawdown is negative or 0

    for (final pt in data) {
      final eq = (pt['equity'] as num).toDouble();
      final dd = (pt['drawdown'] as num?)?.toDouble() ?? 0.0;
      minEq = math.min(minEq, eq);
      maxEq = math.max(maxEq, eq);
      minDd = math.min(minDd, dd);
    }

    final eqRange = math.max(1.0, maxEq - minEq);

    // Padding for equity scale
    minEq -= eqRange * 0.05;
    maxEq += eqRange * 0.05;

    final eqPaint = Paint()
      ..color = AppConstants.chartGreen
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final ddPaint = Paint()
      ..color = AppConstants.chartRed.withOpacity(0.5)
      ..style = PaintingStyle.fill;

    final eqPath = Path();
    final ddPath = Path();
    final eqFillPath = Path();

    final step = width / math.max(1, data.length - 1);

    for (int i = 0; i < data.length; i++) {
      final pt = data[i];
      final eq = (pt['equity'] as num).toDouble();
      final dd = (pt['drawdown'] as num?)?.toDouble() ?? 0.0;

      final x = i * step;
      final yEq = eqHeight - ((eq - minEq) / (maxEq - minEq)) * eqHeight;
      // Drawdown starts from the top of the DD pane (0) and goes down
      // Actually, dd is negative, so minDd is the bottom.
      final yDd = size.height - ddHeight + (-dd / minDd.abs()) * ddHeight;

      if (i == 0) {
        eqPath.moveTo(x, yEq);
        eqFillPath.moveTo(x, eqHeight);
        eqFillPath.lineTo(x, yEq);
        ddPath.moveTo(x, size.height - ddHeight);
        ddPath.lineTo(x, yDd);
      } else {
        eqPath.lineTo(x, yEq);
        eqFillPath.lineTo(x, yEq);
        ddPath.lineTo(x, yDd);
      }
      
      if (i == data.length - 1) {
        eqFillPath.lineTo(x, eqHeight);
        eqFillPath.close();
        
        ddPath.lineTo(x, size.height - ddHeight);
        ddPath.close();
      }
    }

    // Draw Equity Fill
    canvas.drawPath(
      eqFillPath,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            AppConstants.chartGreen.withOpacity(0.3),
            AppConstants.chartGreen.withOpacity(0.0),
          ],
        ).createShader(Rect.fromLTWH(0, 0, width, eqHeight)),
    );

    // Draw lines
    canvas.drawPath(eqPath, eqPaint);
    canvas.drawPath(ddPath, ddPaint);

    // Draw separator
    canvas.drawLine(
      Offset(0, eqHeight),
      Offset(width, eqHeight),
      Paint()..color = isDark ? Colors.white24 : Colors.black12,
    );

    // Draw Price Scales
    final textStyle = TextStyle(
      fontSize: 10,
      color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
    );

    // Max/Min Equity
    _drawText(canvas, maxEq.toStringAsFixed(0), Offset(width + 4, 0), textStyle);
    _drawText(canvas, minEq.toStringAsFixed(0), Offset(width + 4, eqHeight - 12), textStyle);

    // Max Drawdown
    _drawText(canvas, '\$${minDd.toStringAsFixed(0)}', Offset(width + 4, size.height - 12), 
        textStyle.copyWith(color: AppConstants.chartRed));
  }

  void _drawText(Canvas canvas, String text, Offset offset, TextStyle style) {
    final tp = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: ui.TextDirection.ltr,
    );
    tp.layout();
    tp.paint(canvas, offset);
  }

  @override
  bool shouldRepaint(covariant _EquityPainter oldDelegate) => true;
}
