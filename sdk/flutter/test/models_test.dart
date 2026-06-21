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

    test('toJson round-trips correctly', () {
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
      final output = result.toJson();

      expect(output['masked_text'], json['masked_text']);
      expect(output['stats']['phone'], 1);
    });

    test('equality works', () {
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

      final a = MaskResult.fromJson(json);
      final b = MaskResult.fromJson(json);
      final c = MaskResult.fromJson({
        ...json,
        'masked_text': 'Goodbye [PHONE_0001]',
      });

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
      expect(a, isNot(equals(c)));
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

    test('fromJson handles missing type with default', () {
      final json = {
        'value': 'test@example.com',
        'placeholder': '[EMAIL_0001]',
      };

      final entity = Entity.fromJson(json);

      expect(entity.type, '');
      expect(entity.position, 0);
    });

    test('toJson round-trips correctly', () {
      final json = {
        'type': 'PII_EMAIL',
        'value': 'test@example.com',
        'placeholder': '[EMAIL_0001]',
        'position': 0
      };

      final entity = Entity.fromJson(json);
      final output = entity.toJson();

      expect(output['type'], 'PII_EMAIL');
      expect(output['value'], 'test@example.com');
    });

    test('equality works', () {
      final json = {
        'type': 'PII_EMAIL',
        'value': 'test@example.com',
        'placeholder': '[EMAIL_0001]',
        'position': 0
      };

      final a = Entity.fromJson(json);
      final b = Entity.fromJson(json);
      final c = Entity.fromJson({...json, 'value': 'other@example.com'});

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
      expect(a, isNot(equals(c)));
    });
  });

  group('Stats', () {
    test('fromJson parses bankcard field correctly', () {
      final json = {'bankcard': 3};

      final stats = Stats.fromJson(json);

      expect(stats.bank, 3);
    });

    test('toJson serializes bank as bankcard', () {
      final stats = Stats(bank: 5);
      final output = stats.toJson();

      expect(output['bankcard'], 5);
      expect(output.containsKey('bank'), false);
    });

    test('equality works', () {
      final a = Stats(phone: 1, email: 2);
      final b = Stats(phone: 1, email: 2);
      final c = Stats(phone: 1, email: 3);

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
      expect(a, isNot(equals(c)));
    });
  });

  group('RestoreResult', () {
    test('fromJson parses correctly', () {
      final json = {'original_text': 'Hello World'};
      final result = RestoreResult.fromJson(json);
      expect(result.originalText, 'Hello World');
    });

    test('toJson round-trips correctly', () {
      final json = {'original_text': 'Hello World'};
      final result = RestoreResult.fromJson(json);
      final output = result.toJson();
      expect(output['original_text'], 'Hello World');
    });

    test('equality works', () {
      final a = RestoreResult.fromJson({'original_text': 'Hello'});
      final b = RestoreResult.fromJson({'original_text': 'Hello'});
      final c = RestoreResult.fromJson({'original_text': 'World'});

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
      expect(a, isNot(equals(c)));
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

    test('toJson round-trips correctly', () {
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
      final output = response.toJson();

      expect(output['total_count'], 1);
      expect((output['results'] as List).length, 1);
    });

    test('equality works', () {
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

      final a = BatchMaskResponse.fromJson(json);
      final b = BatchMaskResponse.fromJson(json);
      final c = BatchMaskResponse.fromJson({
        ...json,
        'total_count': 2,
      });

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
      expect(a, isNot(equals(c)));
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
      expect(response.nerAvailable, false);
    });

    test('fromJson parses ner_available when present', () {
      final json = {
        'entities': [],
        'total': 1,
        'version': 'Lite',
        'ner_available': true,
      };

      final response = EntitiesResponse.fromJson(json);

      expect(response.nerAvailable, true);
    });

    test('toJson includes ner_available', () {
      final json = {
        'entities': [],
        'total': 1,
        'version': 'Lite',
        'ner_available': true,
      };

      final response = EntitiesResponse.fromJson(json);
      final output = response.toJson();

      expect(output['ner_available'], true);
    });

    test('equality works', () {
      final json = {
        'entities': [],
        'total': 1,
        'version': 'Lite',
      };

      final a = EntitiesResponse.fromJson(json);
      final b = EntitiesResponse.fromJson(json);
      final c = EntitiesResponse.fromJson({...json, 'version': 'Pro'});

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
      expect(a, isNot(equals(c)));
    });
  });

  group('EntityInfo', () {
    test('fromJson parses engine field correctly', () {
      final json = {
        'type': 'PII_PHONE',
        'name': '手机号',
        'description': '中国大陆手机号',
        'enabled': true,
        'engine': 'regex'
      };

      final info = EntityInfo.fromJson(json);

      expect(info.engine, 'regex');
    });

    test('fromJson defaults engine to empty string when missing', () {
      final json = {
        'type': 'PII_PHONE',
        'name': '手机号',
        'description': '中国大陆手机号',
        'enabled': true,
      };

      final info = EntityInfo.fromJson(json);

      expect(info.engine, '');
    });

    test('toJson includes engine', () {
      final json = {
        'type': 'PII_PHONE',
        'name': '手机号',
        'description': '中国大陆手机号',
        'enabled': true,
        'engine': 'ner',
      };

      final info = EntityInfo.fromJson(json);
      final output = info.toJson();

      expect(output['engine'], 'ner');
    });

    test('equality works', () {
      final json = {
        'type': 'PII_PHONE',
        'name': '手机号',
        'description': '中国大陆手机号',
        'enabled': true,
        'engine': 'regex',
      };

      final a = EntityInfo.fromJson(json);
      final b = EntityInfo.fromJson(json);
      final c = EntityInfo.fromJson({...json, 'name': '座机号'});

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
      expect(a, isNot(equals(c)));
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

    test('toJson round-trips correctly', () {
      final config = GatewayConfig(
        baseUrl: 'http://localhost:9999',
        apiKey: 'test-key',
      );

      final output = config.toJson();

      expect(output['baseUrl'], 'http://localhost:9999');
      expect(output['apiKey'], 'test-key');
    });

    test('equality works', () {
      final a = GatewayConfig(baseUrl: 'http://a.com');
      final b = GatewayConfig(baseUrl: 'http://a.com');
      final c = GatewayConfig(baseUrl: 'http://b.com');

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
      expect(a, isNot(equals(c)));
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
