import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../models/dataset.dart';

class InspectorProvider extends ChangeNotifier {
  List<DatasetRow> _results = [];
  int? _targetIndex;
  bool _loading = false;
  String? _error;

  List<DatasetRow> get results => _results;
  int? get targetIndex => _targetIndex;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> inspect(String datasetId, String query) async {
    _loading = true;
    _error = null;
    _results = [];
    _targetIndex = null;
    notifyListeners();

    try {
      // Get the target index
      final inspectRes = await apiClient.get('/data/$datasetId/inspect?query=$query');
      final targetIdx = (inspectRes['target_index'] as num?)?.toInt();

      if (targetIdx != null) {
        _targetIndex = targetIdx;

        // Get surrounding window
        final windowRes = await apiClient.get('/data/$datasetId/window/$targetIdx');
        final list = (windowRes['data'] as List<dynamic>?) ?? [];
        _results = list
            .map((e) => DatasetRow.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList();
      }
    } catch (e) {
      _error = e.toString();
    }

    _loading = false;
    notifyListeners();
  }

  void clear() {
    _results = [];
    _targetIndex = null;
    _error = null;
    notifyListeners();
  }
}
