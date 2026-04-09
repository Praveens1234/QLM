import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../models/dataset.dart';

class DataProvider extends ChangeNotifier {
  List<Dataset> _datasets = [];
  List<Discrepancy> _discrepancies = [];
  List<DatasetRow> _windowData = [];
  bool _loading = false;
  bool _uploading = false;
  String? _error;

  List<Dataset> get datasets => _datasets;
  List<Discrepancy> get discrepancies => _discrepancies;
  List<DatasetRow> get windowData => _windowData;
  bool get loading => _loading;
  bool get uploading => _uploading;
  String? get error => _error;

  Future<void> loadDatasets() async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      final data = await apiClient.get('/data/');
      _datasets = (data as List<dynamic>)
          .map((e) => Dataset.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    } catch (e) {
      _error = e.toString();
    }

    _loading = false;
    notifyListeners();
  }

  Future<bool> uploadFile({
    required List<int> bytes,
    required String fileName,
    required String symbol,
    required String timeframe,
  }) async {
    _uploading = true;
    notifyListeners();

    try {
      await apiClient.uploadBytes(
        '/data/upload',
        bytes: bytes,
        fileName: fileName,
        fileField: 'file',
        fields: {'symbol': symbol, 'timeframe': timeframe},
      );
      await loadDatasets();
      _uploading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _uploading = false;
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> importUrl({
    required String url,
    required String symbol,
    required String timeframe,
  }) async {
    _uploading = true;
    notifyListeners();

    try {
      await apiClient.post('/data/url', body: {
        'url': url,
        'symbol': symbol,
        'timeframe': timeframe,
      });
      await loadDatasets();
      _uploading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _uploading = false;
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteDataset(String id) async {
    try {
      await apiClient.delete('/data/$id');
      _datasets.removeWhere((d) => d.id == id);
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<void> loadDiscrepancies(String datasetId) async {
    _loading = true;
    notifyListeners();

    try {
      final res = await apiClient.get('/data/$datasetId/discrepancies');
      final list = (res['discrepancies'] as List<dynamic>?) ?? [];
      _discrepancies = list
          .map((e) => Discrepancy.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    } catch (e) {
      _error = e.toString();
      _discrepancies = [];
    }

    _loading = false;
    notifyListeners();
  }

  Future<void> loadWindow(String datasetId, int index) async {
    try {
      final res = await apiClient.get('/data/$datasetId/window/$index');
      final list = (res['data'] as List<dynamic>?) ?? [];
      _windowData = list
          .map((e) => DatasetRow.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _windowData = [];
      notifyListeners();
    }
  }

  Future<bool> updateRow(String datasetId, int index, Map<String, double> updates) async {
    try {
      await apiClient.put('/data/$datasetId/row/$index', body: {
        'open': updates['open'],
        'high': updates['high'],
        'low': updates['low'],
        'close': updates['close'],
        'volume': updates['volume'],
      });
      return true;
    } catch (e) {
      _error = e.toString();
      return false;
    }
  }

  Future<bool> deleteRow(String datasetId, int index) async {
    try {
      await apiClient.delete('/data/$datasetId/row/$index');
      return true;
    } catch (e) {
      _error = e.toString();
      return false;
    }
  }

  Future<bool> interpolateGap(String datasetId, int index) async {
    try {
      await apiClient.post('/data/$datasetId/interpolate/$index');
      return true;
    } catch (e) {
      _error = e.toString();
      return false;
    }
  }

  Future<bool> autofixRow(String datasetId, int index) async {
    try {
      await apiClient.post('/data/$datasetId/autofix/$index');
      return true;
    } catch (e) {
      _error = e.toString();
      return false;
    }
  }

  Future<Map<String, dynamic>?> inspectRow(String datasetId, String query) async {
    try {
      final res = await apiClient.get('/data/$datasetId/inspect?query=$query');
      return Map<String, dynamic>.from(res as Map);
    } catch (e) {
      _error = e.toString();
      return null;
    }
  }
}
