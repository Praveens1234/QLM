import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;

class ServerProvider extends ChangeNotifier {
  final SharedPreferences _prefs;

  String _serverUrl = '';
  bool _isConnected = false;
  bool _isConnecting = false;
  String? _errorMessage;

  ServerProvider(this._prefs, String savedUrl, bool isConnected) {
    if (savedUrl.isNotEmpty && isConnected) {
      _serverUrl = savedUrl;
      _isConnected = isConnected;
    }
  }

  String get serverUrl => _serverUrl;
  bool get isConnected => _isConnected;
  bool get isConnecting => _isConnecting;
  String? get errorMessage => _errorMessage;
  bool get hasError => _errorMessage != null;

  Future<bool> connect(String url) async {
    _isConnecting = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final sanitizedUrl = _sanitizeUrl(url);
      final isValid = _isValidUrl(sanitizedUrl);

      if (!isValid) {
        throw Exception('Invalid URL format. Please enter a valid URL like http://localhost:3000');
      }

      final response = await http
          .get(
            Uri.parse('$sanitizedUrl/health'),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200 || response.statusCode == 201) {
        await _saveConnection(sanitizedUrl);
        return true;
      } else {
        throw Exception('Server responded with status ${response.statusCode}');
      }
    } catch (e) {
      String message;

      if (e.toString().contains('SocketException')) {
        message = 'Cannot connect to server. Check if the server is running and the URL is correct';
      } else if (e.toString().contains('TimeoutException')) {
        message = 'Connection timed out. Please check your network and server';
      } else {
        message = e.toString().replaceAll('Exception: ', '');
      }

      _errorMessage = message;
      _isConnected = false;
      await _clearConnection();
      return false;
    } finally {
      _isConnecting = false;
      notifyListeners();
    }
  }

  String _sanitizeUrl(String url) {
    String sanitized = url.trim();

    if (!sanitized.startsWith('http://') && !sanitized.startsWith('https://')) {
      sanitized = 'http://$sanitized';
    }

    if (sanitized.endsWith('/')) {
      sanitized = sanitized.substring(0, sanitized.length - 1);
    }

    return sanitized;
  }

  bool _isValidUrl(String url) {
    final regex = RegExp(
      r'^(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)'
      r'(([a-zA-Z0-9_-])+\.){1,}'
      r'([a-zA-Z]{2,63})'
      r'(:[0-9]{1,5})?'
      r'(\/.*)?$',
      caseSensitive: false,
    );
    return regex.hasMatch(url) || url.startsWith('http://localhost') || url.startsWith('http://127.0.0.1') || url.startsWith('https://localhost') || url.startsWith('https://127.0.0.1');
  }

  Future<void> _saveConnection(String url) async {
    _serverUrl = url;
    _isConnected = true;
    _errorMessage = null;
    await _prefs.setString('serverUrl', url);
    await _prefs.setBool('isConnected', true);
  }

  Future<void> _clearConnection() async {
    _serverUrl = '';
    _isConnected = false;
    await _prefs.remove('serverUrl');
    await _prefs.setBool('isConnected', false);
  }

  Future<void> disconnect() async {
    await _clearConnection();
    notifyListeners();
  }

  Future<void> reconnect() async {
    if (_serverUrl.isNotEmpty) {
      await connect(_serverUrl);
    }
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  Map<String, String> get authHeaders {
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  String get apiUrl => _serverUrl.isNotEmpty ? '$_serverUrl/api' : '';
  String get websocketUrl => _serverUrl.isNotEmpty ? _serverUrl.replaceFirst('http', 'ws') : '';
}