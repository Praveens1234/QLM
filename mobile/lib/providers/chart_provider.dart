import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../models/chart_data.dart';

class ChartProvider extends ChangeNotifier {
  ChartMeta? _meta;
  List<ChartBar> _bars = [];
  int _currentTfSec = 60;
  int? _oldestCursor;
  bool _hasMore = true;
  bool _loading = false;
  String? _error;

  // Indicator toggles
  bool showSma50 = false;
  bool showEma20 = false;
  bool showEma50 = false;
  bool showEma200 = false;
  bool showBb = false;
  bool showRsi = false;

  ChartMeta? get meta => _meta;
  List<ChartBar> get bars => _bars;
  int get currentTfSec => _currentTfSec;
  bool get hasMore => _hasMore;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> loadDataset(String datasetId) async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      final res = await apiClient.get('/chart/$datasetId/meta');
      _meta = ChartMeta.fromJson(Map<String, dynamic>.from(res as Map));

      // Set default timeframe
      final tf1m = _meta!.validTimeframes.where((t) => t.sec == 60);
      _currentTfSec = tf1m.isNotEmpty ? 60 : (_meta!.validTimeframes.isNotEmpty ? _meta!.validTimeframes.first.sec : 60);

      // Reset and load bars
      _bars = [];
      _oldestCursor = null;
      _hasMore = true;

      await fetchBars(datasetId);
    } catch (e) {
      _error = e.toString();
    }

    _loading = false;
    notifyListeners();
  }

  Future<void> fetchBars(String datasetId) async {
    if (!_hasMore || _loading) return;

    _loading = true;
    notifyListeners();

    try {
      String url = '/chart/$datasetId/bars?tf=$_currentTfSec&limit=2000';
      if (_oldestCursor != null) {
        url += '&end=$_oldestCursor';
      }

      final res = await apiClient.get(url);
      final data = res['data'] as Map<String, dynamic>;
      final barList = (data['bars'] as List<dynamic>?)
              ?.map((e) => ChartBar.fromJson(Map<String, dynamic>.from(e as Map)))
              .toList() ??
          [];

      if (barList.isNotEmpty) {
        _bars = [...barList, ..._bars];
      }

      _hasMore = data['has_more'] == true;
      _oldestCursor = data['next_cursor'] as int?;
    } catch (e) {
      _error = e.toString();
    }

    _loading = false;
    notifyListeners();
  }

  Future<void> switchTimeframe(String datasetId, int tfSec) async {
    _currentTfSec = tfSec;
    _bars = [];
    _oldestCursor = null;
    _hasMore = true;
    notifyListeners();

    await fetchBars(datasetId);
  }

  void toggleIndicator(String name) {
    switch (name) {
      case 'sma50':
        showSma50 = !showSma50;
        break;
      case 'ema20':
        showEma20 = !showEma20;
        break;
      case 'ema50':
        showEma50 = !showEma50;
        break;
      case 'ema200':
        showEma200 = !showEma200;
        break;
      case 'bb':
        showBb = !showBb;
        break;
      case 'rsi':
        showRsi = !showRsi;
        break;
    }
    notifyListeners();
  }

  // ─── Indicator Calculations ─────────────────────────
  List<double?> calculateSMA(int period) {
    if (_bars.isEmpty) return [];
    final closes = _bars.map((b) => b.close).toList();
    final result = List<double?>.filled(closes.length, null);

    for (int i = period - 1; i < closes.length; i++) {
      double sum = 0;
      for (int j = i - period + 1; j <= i; j++) {
        sum += closes[j];
      }
      result[i] = sum / period;
    }
    return result;
  }

  List<double?> calculateEMA(int period) {
    if (_bars.isEmpty) return [];
    final closes = _bars.map((b) => b.close).toList();
    final result = List<double?>.filled(closes.length, null);
    final multiplier = 2.0 / (period + 1);

    // Start with SMA for the first value
    double sum = 0;
    for (int i = 0; i < period && i < closes.length; i++) {
      sum += closes[i];
    }
    if (period <= closes.length) {
      result[period - 1] = sum / period;

      for (int i = period; i < closes.length; i++) {
        result[i] = (closes[i] - result[i - 1]!) * multiplier + result[i - 1]!;
      }
    }
    return result;
  }

  Map<String, List<double?>> calculateBollingerBands({int period = 20, double stdDev = 2.0}) {
    final sma = calculateSMA(period);
    final closes = _bars.map((b) => b.close).toList();
    final upper = List<double?>.filled(closes.length, null);
    final lower = List<double?>.filled(closes.length, null);

    for (int i = period - 1; i < closes.length; i++) {
      if (sma[i] == null) continue;
      double sumSq = 0;
      for (int j = i - period + 1; j <= i; j++) {
        sumSq += (closes[j] - sma[i]!) * (closes[j] - sma[i]!);
      }
      final sd = _sqrt(sumSq / period);
      upper[i] = sma[i]! + stdDev * sd;
      lower[i] = sma[i]! - stdDev * sd;
    }

    return {'upper': upper, 'middle': sma, 'lower': lower};
  }

  List<double?> calculateRSI({int period = 14}) {
    if (_bars.length < period + 1) return List.filled(_bars.length, null);

    final closes = _bars.map((b) => b.close).toList();
    final result = List<double?>.filled(closes.length, null);

    List<double> gains = [];
    List<double> losses = [];

    for (int i = 1; i <= period; i++) {
      final change = closes[i] - closes[i - 1];
      gains.add(change > 0 ? change : 0);
      losses.add(change < 0 ? -change : 0);
    }

    double avgGain = gains.reduce((a, b) => a + b) / period;
    double avgLoss = losses.reduce((a, b) => a + b) / period;

    result[period] = avgLoss == 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss));

    for (int i = period + 1; i < closes.length; i++) {
      final change = closes[i] - closes[i - 1];
      final gain = change > 0 ? change : 0.0;
      final loss = change < 0 ? -change : 0.0;

      avgGain = (avgGain * (period - 1) + gain) / period;
      avgLoss = (avgLoss * (period - 1) + loss) / period;

      result[i] = avgLoss == 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss));
    }

    return result;
  }

  double _sqrt(double value) {
    if (value <= 0) return 0;
    double x = value;
    double y = (x + 1) / 2;
    while (y < x) {
      x = y;
      y = (x + value / x) / 2;
    }
    return x;
  }
}
