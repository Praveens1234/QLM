import 'dart:convert';

import 'package:http/http.dart' as http;


/// Central HTTP client for all QLM API calls.
/// Base URL is set dynamically after server connection.
class ApiClient {
  String _baseUrl = '';
  final http.Client _client = http.Client();

  String get baseUrl => _baseUrl;

  void setBaseUrl(String url) {
    // Normalize: remove trailing slash
    _baseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
  }

  String _url(String endpoint) => '$_baseUrl$endpoint';

  // ─── GET ───────────────────────────────────────────────
  Future<dynamic> get(String endpoint, {Duration? timeout}) async {
    final response = await _client
        .get(Uri.parse(_url(endpoint)))
        .timeout(timeout ?? const Duration(seconds: 30));
    return _handleResponse(response);
  }

  // ─── POST (JSON) ──────────────────────────────────────
  Future<dynamic> post(String endpoint, {Map<String, dynamic>? body, Duration? timeout}) async {
    final response = await _client
        .post(
          Uri.parse(_url(endpoint)),
          headers: {'Content-Type': 'application/json'},
          body: body != null ? jsonEncode(body) : null,
        )
        .timeout(timeout ?? const Duration(seconds: 30));
    return _handleResponse(response);
  }

  // ─── PUT (JSON) ───────────────────────────────────────
  Future<dynamic> put(String endpoint, {Map<String, dynamic>? body}) async {
    final response = await _client
        .put(
          Uri.parse(_url(endpoint)),
          headers: {'Content-Type': 'application/json'},
          body: body != null ? jsonEncode(body) : null,
        )
        .timeout(const Duration(seconds: 30));
    return _handleResponse(response);
  }

  // ─── DELETE ───────────────────────────────────────────
  Future<dynamic> delete(String endpoint) async {
    final response = await _client
        .delete(Uri.parse(_url(endpoint)))
        .timeout(const Duration(seconds: 30));
    return _handleResponse(response);
  }

  // ─── Multipart Upload ─────────────────────────────────
  Future<dynamic> upload(
    String endpoint, {
    required String filePath,
    required String fileField,
    Map<String, String>? fields,
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse(_url(endpoint)));
    request.files.add(await http.MultipartFile.fromPath(fileField, filePath));
    if (fields != null) {
      request.fields.addAll(fields);
    }
    final streamedResponse = await request.send().timeout(const Duration(seconds: 120));
    final response = await http.Response.fromStream(streamedResponse);
    return _handleResponse(response);
  }

  // ─── Upload from bytes ────────────────────────────────
  Future<dynamic> uploadBytes(
    String endpoint, {
    required List<int> bytes,
    required String fileName,
    required String fileField,
    Map<String, String>? fields,
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse(_url(endpoint)));
    request.files.add(http.MultipartFile.fromBytes(fileField, bytes, filename: fileName));
    if (fields != null) {
      request.fields.addAll(fields);
    }
    final streamedResponse = await request.send().timeout(const Duration(seconds: 120));
    final response = await http.Response.fromStream(streamedResponse);
    return _handleResponse(response);
  }

  // ─── Health Check ─────────────────────────────────────
  Future<bool> healthCheck(String serverUrl) async {
    final url = serverUrl.endsWith('/') ? serverUrl.substring(0, serverUrl.length - 1) : serverUrl;
    final response = await _client
        .get(Uri.parse('$url/health'))
        .timeout(const Duration(seconds: 10));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['status'] == 'ok' && data['system'] == 'QLM';
    }
    return false;
  }

  // ─── Response Handler ─────────────────────────────────
  dynamic _handleResponse(http.Response response) {
    final contentType = response.headers['content-type'] ?? '';
    dynamic data;

    if (contentType.contains('application/json')) {
      data = jsonDecode(response.body);
    } else {
      data = response.body;
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return data;
    }

    // Extract error message
    String errorMsg;
    if (data is Map) {
      errorMsg = data['detail']?.toString() ?? data['error']?.toString() ?? response.reasonPhrase ?? 'Unknown error';
    } else {
      errorMsg = response.reasonPhrase ?? 'Request failed (${response.statusCode})';
    }

    throw ApiException(errorMsg, response.statusCode);
  }

  void dispose() {
    _client.close();
  }
}

class ApiException implements Exception {
  final String message;
  final int statusCode;

  ApiException(this.message, this.statusCode);

  @override
  String toString() => message;
}

/// Global singleton
final apiClient = ApiClient();
