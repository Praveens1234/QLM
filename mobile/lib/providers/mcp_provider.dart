import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../models/mcp.dart';

class McpProvider extends ChangeNotifier {
  McpStatus? _status;
  bool _loading = false;
  String? _error;

  McpStatus? get status => _status;
  bool get loading => _loading;
  String? get error => _error;
  bool get isActive => _status?.isActive ?? false;

  Future<void> loadStatus() async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      final res = await apiClient.get('/mcp/status');
      _status = McpStatus.fromJson(Map<String, dynamic>.from(res as Map));
    } catch (e) {
      _error = e.toString();
    }

    _loading = false;
    notifyListeners();
  }

  Future<bool> toggle(bool active) async {
    try {
      await apiClient.post('/mcp/toggle', body: {'active': active});
      await loadStatus();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }
}
