import 'package:flutter_test/flutter_test.dart';
import 'package:privacy_gateway_sdk/models.dart';

void main() {
  group('MaskResult', () {
    test('fromJson parses correctly', () {
      final json = {
        'masked_text': 'Hello [PHONE_0001]',
        'entities': [
          {
            'type': 'PII_PHONE',
            'value': '13812345678',
            'placeholder': '[PHONE_0001]',
            'position': 6
          }
        ],
        'stats': {'phone': 1}
      };

      final result = MaskResult.fromJson(json);

      expect(result.maskedText, 'Hello [PHONE_0001]');
      expect(result.entities.length, 1);
      expect(result.entities[0].type, 'PII_PHONE');
      expect(result.entities[0].value, '13812345678');
      expect(result.stats.phone, 1);
    });
  });

  group('Entity', () {
    test('fromJson parses correctly', () {
      final json = {
        'type': 'PII_EMAIL',
        'value': 'test@example.com',
        'placeholder': '[EMAIL_0001]',
        'position': 0
      };

      final entity = Entity.fromJson(json);

      expect(entity.type, 'PII_EMAIL');
      expect(entity.value, 'test@example.com');
      expect(entity.placeholder, '[EMAIL_0001]');
      expect(entity.position, 0);
    });
  });

  group('RestoreResult', () {
    test('fromJson parses correctly', () {
      final json = {'original_text': 'Hello World'};
      final result = RestoreResult.fromJson(json);
      expect(result.originalText, 'Hello World');
    });
  });

  group('BatchMaskResponse', () {
    test('fromJson parses correctly', () {
      final json = {
        'results': [
          {
            'original': 'test',
            'masked': 'masked',
            'entities': [],
            'stats': {}
          }
        ],
        'total_count': 1
      };

      final response = BatchMaskResponse.fromJson(json);

      expect(response.results.length, 1);
      expect(response.totalCount, 1);
      expect(response.results[0].original, 'test');
      expect(response.results[0].masked, 'masked');
    });
  });

  group('EntitiesResponse', () {
    test('fromJson parses correctly', () {
      final json = {
        'entities': [
          {
            'type': 'PII_PHONE',
            'name': '手机号',
            'description': '中国大陆手机号',
            'enabled': true
          }
        ],
        'total': 1,
        'version': 'Lite'
      };

      final response = EntitiesResponse.fromJson(json);

      expect(response.entities.length, 1);
      expect(response.total, 1);
      expect(response.version, 'Lite');
      expect(response.entities[0].type, 'PII_PHONE');
      expect(response.entities[0].enabled, true);
    });
  });

  group('GatewayConfig', () {
    test('buildHeaders adds API key header when set', () {
      final config = GatewayConfig(
        baseUrl: 'http://localhost:9999',
        apiKey: 'test-key',
      );

      final headers = config.buildHeaders();

      expect(headers['X-API-Key'], 'test-key');
      expect(headers.length, 1);
    });

    test('buildHeaders does not add API key when null', () {
      final config = GatewayConfig(baseUrl: 'http://localhost:9999');

      final headers = config.buildHeaders();

      expect(headers.containsKey('X-API-Key'), false);
    });

    test('buildHeaders merges custom headers', () {
      final config = GatewayConfig(
        baseUrl: 'http://localhost:9999',
        headers: {'X-Custom': 'value'},
      );

      final headers = config.buildHeaders();

      expect(headers['X-Custom'], 'value');
    });
  });

  group('PrivacyGatewayException', () {
    test('toString includes status code when set', () {
      final e = PrivacyGatewayException('Not found', 404);
      expect(e.toString(), 'Not found (HTTP 404)');
    });

    test('toString without status code', () {
      final e = PrivacyGatewayException('Error');
      expect(e.toString(), 'Error');
    });
  });
}
