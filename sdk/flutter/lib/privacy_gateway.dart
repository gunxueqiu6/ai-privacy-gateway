import 'dart:convert';
import 'dart:developer' as dev;

import 'package:http/http.dart' as http;

import 'models.dart';

class PrivacyGateway {
  final String _baseUrl;
  final int _timeout;
  final Map<String, String> _headers;

  PrivacyGateway._(
    this._baseUrl,
    this._timeout,
    this._headers,
  );

  static PrivacyGateway? _instance;

  static void initialize(GatewayConfig config) {
    final url = config.baseUrl.endsWith('/')
        ? config.baseUrl.substring(0, config.baseUrl.length - 1)
        : config.baseUrl;
    _instance = PrivacyGateway._(url, config.timeout, config.buildHeaders());
  }

  static PrivacyGateway get instance {
    if (_instance == null) {
      throw PrivacyGatewayException('PrivacyGateway not initialized. Call initialize() first.');
    }
    return _instance!;
  }

  Future<MaskResult> mask(String text) async {
    if (text.isEmpty) {
      throw PrivacyGatewayException('text must be a non-empty string');
    }

    final response = await _post('/api/mask', {'text': text});
    return MaskResult.fromJson(response);
  }

  Future<RestoreResult> restore(String maskedText, Map<String, String> mappings) async {
    if (maskedText.isEmpty) {
      throw PrivacyGatewayException('maskedText must be a non-empty string');
    }

    final response = await _post('/api/restore', {
      'text': maskedText,
      'mappings': mappings,
    });
    return RestoreResult.fromJson(response);
  }

  Future<BatchMaskResponse> maskBatch(List<String> texts) async {
    if (texts.isEmpty) {
      throw PrivacyGatewayException('texts must be a non-empty list');
    }

    if (texts.length > 50) {
      throw PrivacyGatewayException('Maximum 50 texts per batch');
    }

    final response = await _post('/api/mask/batch', {'texts': texts});
    return BatchMaskResponse.fromJson(response);
  }

  Future<EntitiesResponse> getEntities() async {
    final response = await _get('/api/entities');
    return EntitiesResponse.fromJson(response);
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final url = Uri.parse('$_baseUrl$path');
    _validateUrlScheme(url);
    final request = http.Request('GET', url);
    _headers.forEach((key, value) => request.headers[key] = value);

    final streamedResponse = await request.send().timeout(Duration(milliseconds: _timeout));
    final response = await http.Response.fromStream(streamedResponse);
    return _parseResponse(response);
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body) async {
    final url = Uri.parse('$_baseUrl$path');
    _validateUrlScheme(url);
    final headers = {'Content-Type': 'application/json', ..._headers};

    final response = await http.post(
      url,
      headers: headers,
      body: jsonEncode(body),
    ).timeout(Duration(milliseconds: _timeout));

    return _parseResponse(response);
  }

  /// Validates that the URL uses HTTPS unless targeting localhost/127.0.0.1.
  void _validateUrlScheme(Uri url) {
    if (url.host == 'localhost' || url.host == '127.0.0.1') {
      return; // localhost is allowed for development
    }
    if (url.scheme != 'https') {
      throw PrivacyGatewayException(
        'Insecure URL: "$url". HTTPS is required for non-localhost endpoints.',
      );
    }
  }

  Map<String, dynamic> _parseResponse(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      // Log the full body for debugging, but only expose a generic message.
      _logError('Request failed with status ${response.statusCode}: ${response.body}');
      throw PrivacyGatewayException(
        'Request failed with status ${response.statusCode}',
        response.statusCode,
      );
    }

    try {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw PrivacyGatewayException('Failed to parse response: $e');
    }
  }

  /// Logs an error message to the developer console.
  /// Response bodies are logged here for debugging and never exposed to callers.
  static void _logError(String message) {
    dev.log(message, name: 'PrivacyGateway');
  }

  static Future<MaskResult> maskText(String text) => instance.mask(text);

  static Future<RestoreResult> restoreText(String maskedText, Map<String, String> mappings) =>
      instance.restore(maskedText, mappings);

  static Future<BatchMaskResponse> maskTextBatch(List<String> texts) =>
      instance.maskBatch(texts);

  static Future<EntitiesResponse> getEntityList() => instance.getEntities();
}