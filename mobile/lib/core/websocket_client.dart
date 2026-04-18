import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

/// WebSocket client for receiving real-time backtest progress updates.
class WSClient {
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  String _serverUrl = '';
  bool _connected = false;

  // Callbacks
  void Function(Map<String, dynamic>)? onProgress;
  void Function(Map<String, dynamic>)? onResult;
  void Function(Map<String, dynamic>)? onError;
  void Function()? onConnected;
  void Function()? onDisconnected;

  bool get isConnected => _connected;

  void setServerUrl(String url) {
    _serverUrl = url
        .replaceFirst('https://', 'wss://')
        .replaceFirst('http://', 'ws://');
    if (_serverUrl.endsWith('/')) {
      _serverUrl = _serverUrl.substring(0, _serverUrl.length - 1);
    }
  }

  Future<void> connect() async {
    if (_connected) return;

    try {
      final wsUrl = '$_serverUrl/api/ws';
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));

      _subscription = _channel!.stream.listen(
        (message) {
          try {
            final data = jsonDecode(message as String) as Map<String, dynamic>;
            final type = data['type'] as String?;

            switch (type) {
              case 'progress':
                onProgress?.call(data);
                break;
              case 'finished':
                onResult?.call(data);
                break;
              case 'error':
                onError?.call(data);
                break;
            }
          } catch (e) {
            // Ignore malformed messages
          }
        },
        onDone: () {
          _connected = false;
          onDisconnected?.call();
        },
        onError: (error) {
          _connected = false;
          onDisconnected?.call();
        },
      );

      _connected = true;
      onConnected?.call();
    } catch (e) {
      _connected = false;
    }
  }

  Future<void> disconnect() async {
    await _subscription?.cancel();
    await _channel?.sink.close();
    _channel = null;
    _connected = false;
  }

  void dispose() {
    disconnect();
  }
}

/// Global singleton
final wsClient = WSClient();
