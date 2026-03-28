import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../core/websocket_client.dart';
import '../models/backtest.dart';

enum BacktestStatus { idle, running, completed, failed }

class BacktestProvider extends ChangeNotifier {
  BacktestStatus _status = BacktestStatus.idle;
  double _progress = 0.0;
  String _progressMessage = '';
  BacktestResult? _result;
  String? _error;

  BacktestStatus get status => _status;
  double get progress => _progress;
  String get progressMessage => _progressMessage;
  BacktestResult? get result => _result;
  String? get error => _error;

  BacktestProvider() {
    wsClient.onProgress = _onProgress;
    wsClient.onResult = _onResult;
    wsClient.onError = _onError;
  }

  void _onProgress(Map<String, dynamic> data) {
    _progress = (data['progress'] as num?)?.toDouble() ?? 0.0;
    _progressMessage = data['message']?.toString() ?? '';
    notifyListeners();
  }

  void _onResult(Map<String, dynamic> data) {
    _status = BacktestStatus.completed;
    _progress = 100.0;
    _progressMessage = 'Completed';
    if (data.containsKey('results')) {
      _result = BacktestResult.fromJson(data);
    }
    notifyListeners();
  }

  void _onError(Map<String, dynamic> data) {
    _status = BacktestStatus.failed;
    _error = data['message']?.toString() ?? data['details']?.toString() ?? 'Backtest failed';
    notifyListeners();
  }

  Future<void> runBacktest(BacktestRequest request) async {
    _status = BacktestStatus.running;
    _progress = 0.0;
    _progressMessage = 'Starting...';
    _result = null;
    _error = null;
    notifyListeners();

    try {
      final res = await apiClient.post(
        '/backtest/run',
        body: request.toJson(),
        timeout: const Duration(seconds: 300),
      );

      // If WS didn't deliver result, parse from HTTP response
      if (_status != BacktestStatus.completed) {
        final data = Map<String, dynamic>.from(res as Map);
        if (data['status'] == 'success') {
          _result = BacktestResult.fromJson(data);
          _status = BacktestStatus.completed;
          _progress = 100.0;
          _progressMessage = 'Completed';
        } else {
          _status = BacktestStatus.failed;
          _error = data['error']?.toString() ?? 'Unknown error';
        }
      }
    } catch (e) {
      _status = BacktestStatus.failed;
      _error = e.toString();
    }

    notifyListeners();
  }

  void reset() {
    _status = BacktestStatus.idle;
    _progress = 0.0;
    _progressMessage = '';
    _result = null;
    _error = null;
    notifyListeners();
  }
}
