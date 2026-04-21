import 'package:flutter/material.dart';
import '../core/api_client.dart';

class DashboardProvider extends ChangeNotifier {
  int _datasetCount = 0;
  int _strategyCount = 0;
  int _activeOrders = 0;
  double _totalPnl = 0.0;
  String _liveStatus = 'offline';
  bool _loading = false;
  String? _error;

  int get datasetCount => _datasetCount;
  int get strategyCount => _strategyCount;
  int get activeOrders => _activeOrders;
  double get totalPnl => _totalPnl;
  String get liveStatus => _liveStatus;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> refresh() async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      final results = await Future.wait<dynamic>([
        apiClient.get('/data/'),
        apiClient.get('/strategies/'),
        apiClient.get('/live/status').catchError((_) => <String, dynamic>{
              'active_orders': <dynamic>[],
              'total_pnl': 0.0,
              'status': 'offline',
            }),
      ]);

      // Datasets
      final datasetsRaw = results[0];
      if (datasetsRaw is List) {
        _datasetCount = datasetsRaw.length;
      }

      // Strategies
      final strategiesRaw = results[1];
      if (strategiesRaw is List) {
        _strategyCount = strategiesRaw.length;
      }

      // Live status
      final live = results[2];
      if (live is Map<String, dynamic>) {
        final orders = live['active_orders'];
        _activeOrders = orders is List ? orders.length : 0;
        _totalPnl = (live['total_pnl'] as num?)?.toDouble() ?? 0.0;
        _liveStatus = live['status']?.toString() ?? 'offline';
      }
    } catch (e) {
      _error = e.toString();
    }

    _loading = false;
    notifyListeners();
  }
}
