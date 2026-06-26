import 'package:json_annotation/json_annotation.dart';

part 'models.g.dart';

@JsonSerializable()
class GatewayConfig {
  final String baseUrl;
  final String? apiKey;
  final int timeout;
  final Map<String, String> headers;

  GatewayConfig({
    required this.baseUrl,
    this.apiKey,
    this.timeout = 10000,
    this.headers = const {},
  });

  factory GatewayConfig.fromJson(Map<String, dynamic> json) =>
      _$GatewayConfigFromJson(json);

  Map<String, dynamic> toJson() => _$GatewayConfigToJson(this);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is GatewayConfig &&
          runtimeType == other.runtimeType &&
          baseUrl == other.baseUrl &&
          apiKey == other.apiKey &&
          timeout == other.timeout &&
          headers == other.headers;

  @override
  int get hashCode => Object.hash(baseUrl, apiKey, timeout, headers);

  Map<String, String> buildHeaders() {
    final Map<String, String> result = Map<String, String>.from(headers);
    final key = apiKey;
    if (key != null) {
      result['Authorization'] = 'Bearer $key';
    }
    return result;
  }
}

@JsonSerializable()
class MaskResult {
  @JsonKey(name: 'masked_text')
  final String maskedText;
  final List<Entity> entities;
  final Stats stats;

  MaskResult({
    required this.maskedText,
    required this.entities,
    required this.stats,
  });

  factory MaskResult.fromJson(Map<String, dynamic> json) =>
      _$MaskResultFromJson(json);

  Map<String, dynamic> toJson() => _$MaskResultToJson(this);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MaskResult &&
          runtimeType == other.runtimeType &&
          maskedText == other.maskedText &&
          entities == other.entities &&
          stats == other.stats;

  @override
  int get hashCode => Object.hash(maskedText, entities, stats);
}

@JsonSerializable()
class Entity {
  @JsonKey(defaultValue: '')
  final String type;
  final String value;
  final String placeholder;
  final int position;

  Entity({
    this.type = '',
    required this.value,
    required this.placeholder,
    this.position = 0,
  });

  factory Entity.fromJson(Map<String, dynamic> json) => _$EntityFromJson(json);

  Map<String, dynamic> toJson() => _$EntityToJson(this);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Entity &&
          runtimeType == other.runtimeType &&
          type == other.type &&
          value == other.value &&
          placeholder == other.placeholder &&
          position == other.position;

  @override
  int get hashCode => Object.hash(type, value, placeholder, position);
}

@JsonSerializable()
class Stats {
  final int phone;
  final int email;
  @JsonKey(name: 'idcard')
  final int idCard;
  @JsonKey(name: 'bankcard')
  final int bank;
  final int person;
  final int location;
  @JsonKey(name: 'organization')
  final int organization;
  final int plate;
  final int ip;
  final int url;
  final int date;
  final int amount;
  final int postcode;
  final int custom;

  Stats({
    this.phone = 0,
    this.email = 0,
    this.idCard = 0,
    this.bank = 0,
    this.person = 0,
    this.location = 0,
    this.organization = 0,
    this.plate = 0,
    this.ip = 0,
    this.url = 0,
    this.date = 0,
    this.amount = 0,
    this.postcode = 0,
    this.custom = 0,
  });

  factory Stats.fromJson(Map<String, dynamic> json) => _$StatsFromJson(json);

  Map<String, dynamic> toJson() => _$StatsToJson(this);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Stats &&
          runtimeType == other.runtimeType &&
          phone == other.phone &&
          email == other.email &&
          idCard == other.idCard &&
          bank == other.bank &&
          person == other.person &&
          location == other.location &&
          organization == other.organization &&
          plate == other.plate &&
          ip == other.ip &&
          url == other.url &&
          date == other.date &&
          amount == other.amount &&
          postcode == other.postcode &&
          custom == other.custom;

  @override
  int get hashCode => Object.hashAll([
        phone,
        email,
        idCard,
        bank,
        person,
        location,
        organization,
        plate,
        ip,
        url,
        date,
        amount,
        postcode,
        custom,
      ]);
}

@JsonSerializable()
class RestoreResult {
  @JsonKey(name: 'original_text')
  final String originalText;

  RestoreResult({required this.originalText});

  factory RestoreResult.fromJson(Map<String, dynamic> json) =>
      _$RestoreResultFromJson(json);

  Map<String, dynamic> toJson() => _$RestoreResultToJson(this);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is RestoreResult &&
          runtimeType == other.runtimeType &&
          originalText == other.originalText;

  @override
  int get hashCode => originalText.hashCode;
}

@JsonSerializable()
class BatchMaskResponse {
  final List<BatchResult> results;
  @JsonKey(name: 'total_count')
  final int totalCount;

  BatchMaskResponse({
    required this.results,
    required this.totalCount,
  });

  factory BatchMaskResponse.fromJson(Map<String, dynamic> json) =>
      _$BatchMaskResponseFromJson(json);

  Map<String, dynamic> toJson() => _$BatchMaskResponseToJson(this);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is BatchMaskResponse &&
          runtimeType == other.runtimeType &&
          results == other.results &&
          totalCount == other.totalCount;

  @override
  int get hashCode => Object.hash(results, totalCount);
}

@JsonSerializable()
class BatchResult {
  final String original;
  final String masked;
  final List<Entity> entities;
  final Stats stats;

  BatchResult({
    required this.original,
    required this.masked,
    required this.entities,
    required this.stats,
  });

  factory BatchResult.fromJson(Map<String, dynamic> json) =>
      _$BatchResultFromJson(json);

  Map<String, dynamic> toJson() => _$BatchResultToJson(this);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is BatchResult &&
          runtimeType == other.runtimeType &&
          original == other.original &&
          masked == other.masked &&
          entities == other.entities &&
          stats == other.stats;

  @override
  int get hashCode => Object.hash(original, masked, entities, stats);
}

@JsonSerializable()
class EntitiesResponse {
  final List<EntityInfo> entities;
  final int total;
  final String version;
  @JsonKey(name: 'ner_available')
  final bool nerAvailable;

  EntitiesResponse({
    required this.entities,
    required this.total,
    required this.version,
    this.nerAvailable = false,
  });

  factory EntitiesResponse.fromJson(Map<String, dynamic> json) =>
      _$EntitiesResponseFromJson(json);

  Map<String, dynamic> toJson() => _$EntitiesResponseToJson(this);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is EntitiesResponse &&
          runtimeType == other.runtimeType &&
          entities == other.entities &&
          total == other.total &&
          version == other.version &&
          nerAvailable == other.nerAvailable;

  @override
  int get hashCode => Object.hash(entities, total, version, nerAvailable);
}

@JsonSerializable()
class EntityInfo {
  final String type;
  final String name;
  final String description;
  final bool enabled;
  @JsonKey(name: 'engine')
  final String engine;

  EntityInfo({
    required this.type,
    required this.name,
    required this.description,
    required this.enabled,
    this.engine = '',
  });

  factory EntityInfo.fromJson(Map<String, dynamic> json) =>
      _$EntityInfoFromJson(json);

  Map<String, dynamic> toJson() => _$EntityInfoToJson(this);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is EntityInfo &&
          runtimeType == other.runtimeType &&
          type == other.type &&
          name == other.name &&
          description == other.description &&
          enabled == other.enabled &&
          engine == other.engine;

  @override
  int get hashCode =>
      Object.hash(type, name, description, enabled, engine);
}

class PrivacyGatewayException implements Exception {
  final String message;
  final int? statusCode;

  PrivacyGatewayException(this.message, [this.statusCode]);

  @override
  String toString() =>
      statusCode != null ? '$message (HTTP $statusCode)' : message;
}
