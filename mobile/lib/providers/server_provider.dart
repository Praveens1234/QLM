import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/api_client.dart';
import '../core/websocket_client.dart';

enum ServerStatus { disconnected, connecting, connected, error }

class ServerProvider extends ChangeNotifier {
  ServerStatus _status = ServerStatus.disconnected;
  String _serverUrl = '';
  String _errorMessage = '';

  ServerStatus get status => _status;
  String get serverUrl => _serverUrl;
  String get errorMessage => _errorMessage;
  bool get isConnected => _status == ServerStatus.connected;

  ServerProvider() {
    _loadSavedUrl();
  }

  Future<void> _loadSavedUrl() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('qlm_server_url');
    if (saved != null && saved.isNotEmpty) {
      _serverUrl = saved;
      notifyListeners();
    }
  }

  Future<bool> connect(String url) async {
    _status = ServerStatus.connecting;
    _errorMessage = '';
    notifyListeners();

    // Normalize URL
    String normalizedUrl = url.trim();
    if (!normalizedUrl.startsWith('http://') && !normalizedUrl.startsWith('https://')) {
      normalizedUrl = 'http://$normalizedUrl';
    }
    if (normalizedUrl.endsWith('/')) {
      normalizedUrl = normalizedUrl.substring(0, normalizedUrl.length - 1);
    }

    try {
      final isValid = await apiClient.healthCheck(normalizedUrl);
      if (isValid) {
        _serverUrl = normalizedUrl;
        _status = ServerStatus.connected;
        apiClient.setBaseUrl('$normalizedUrl/api');
        wsClient.setServerUrl(normalizedUrl);

        // Save for future use
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('qlm_server_url', normalizedUrl);

        // Connect WebSocket
        await wsClient.connect();

        notifyListeners();
        return true;
      } else {
        _status = ServerStatus.error;
        _errorMessage = 'Server responded but is not a valid QLM instance';
        notifyListeners();
        return false;
      }
    } catch (e) {
      _status = ServerStatus.error;
      _errorMessage = 'Connection failed: ${e.toString()}';
      notifyListeners();
      return false;
    }
  }

  Future<void> disconnect() async {
    _status = ServerStatus.disconnected;
    unawaited(wsClient.disconnect());
    notifyListeners();
  }

  Future<void> autoConnect() async {
    if (_serverUrl.isNotEmpty && _status != ServerStatus.connected) {
      await connect(_serverUrl);
    }
  }
}
