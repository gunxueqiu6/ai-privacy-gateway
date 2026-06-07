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

  Map<String, String> buildHeaders() {
    final Map<String, String> result = Map.from(headers);
    if (apiKey != null) {
      result['X-API-Key'] = apiKey!;
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
}

@JsonSerializable()
class Entity {
  final String type;
  final String value;
  final String placeholder;
  final int position;

  Entity({
    required this.type,
    required this.value,
    required this.placeholder,
    required this.position,
  });

  factory Entity.fromJson(Map<String, dynamic> json) => _$EntityFromJson(json);
}

@JsonSerializable()
class Stats {
  final int phone;
  final int email;
  @JsonKey(name: 'idcard')
  final int idCard;
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
}

@JsonSerializable()
class RestoreResult {
  @JsonKey(name: 'original_text')
  final String originalText;

  RestoreResult({required this.originalText});

  factory RestoreResult.fromJson(Map<String, dynamic> json) =>
      _$RestoreResultFromJson(json);
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
}

@JsonSerializable()
class EntitiesResponse {
  final List<EntityInfo> entities;
  final int total;
  final String version;

  EntitiesResponse({
    required this.entities,
    required this.total,
    required this.version,
  });

  factory EntitiesResponse.fromJson(Map<String, dynamic> json) =>
      _$EntitiesResponseFromJson(json);
}

@JsonSerializable()
class EntityInfo {
  final String type;
  final String name;
  final String description;
  final bool enabled;

  EntityInfo({
    required this.type,
    required this.name,
    required this.description,
    required this.enabled,
  });

  factory EntityInfo.fromJson(Map<String, dynamic> json) =>
      _$EntityInfoFromJson(json);
}

class PrivacyGatewayException implements Exception {
  final String message;
  final int? statusCode;

  PrivacyGatewayException(this.message, [this.statusCode]);

  @override
  String toString() => statusCode != null ? '$message (HTTP $statusCode)' : message;
}