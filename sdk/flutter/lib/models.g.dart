// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

GatewayConfig _$GatewayConfigFromJson(Map<String, dynamic> json) =>
    GatewayConfig(
      baseUrl: json['baseUrl'] as String,
      apiKey: json['apiKey'] as String?,
      timeout: (json['timeout'] as num?)?.toInt() ?? 10000,
      headers: (json['headers'] as Map<String, dynamic>?)?.map(
            (k, e) => MapEntry(k, e as String),
          ) ??
          const {},
    );

Map<String, dynamic> _$GatewayConfigToJson(GatewayConfig instance) =>
    <String, dynamic>{
      'baseUrl': instance.baseUrl,
      'apiKey': instance.apiKey,
      'timeout': instance.timeout,
      'headers': instance.headers,
    };

MaskResult _$MaskResultFromJson(Map<String, dynamic> json) => MaskResult(
      maskedText: json['masked_text'] as String,
      entities: (json['entities'] as List<dynamic>)
          .map((e) => Entity.fromJson(e as Map<String, dynamic>))
          .toList(),
      stats: Stats.fromJson(json['stats'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$MaskResultToJson(MaskResult instance) =>
    <String, dynamic>{
      'masked_text': instance.maskedText,
      'entities': instance.entities,
      'stats': instance.stats,
    };

Entity _$EntityFromJson(Map<String, dynamic> json) => Entity(
      type: json['type'] as String,
      value: json['value'] as String,
      placeholder: json['placeholder'] as String,
      position: (json['position'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$EntityToJson(Entity instance) => <String, dynamic>{
      'type': instance.type,
      'value': instance.value,
      'placeholder': instance.placeholder,
      'position': instance.position,
    };

Stats _$StatsFromJson(Map<String, dynamic> json) => Stats(
      phone: (json['phone'] as num?)?.toInt() ?? 0,
      email: (json['email'] as num?)?.toInt() ?? 0,
      idCard: (json['idcard'] as num?)?.toInt() ?? 0,
      bank: (json['bank'] as num?)?.toInt() ?? 0,
      person: (json['person'] as num?)?.toInt() ?? 0,
      location: (json['location'] as num?)?.toInt() ?? 0,
      organization: (json['organization'] as num?)?.toInt() ?? 0,
      plate: (json['plate'] as num?)?.toInt() ?? 0,
      ip: (json['ip'] as num?)?.toInt() ?? 0,
      url: (json['url'] as num?)?.toInt() ?? 0,
      date: (json['date'] as num?)?.toInt() ?? 0,
      amount: (json['amount'] as num?)?.toInt() ?? 0,
      postcode: (json['postcode'] as num?)?.toInt() ?? 0,
      custom: (json['custom'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$StatsToJson(Stats instance) => <String, dynamic>{
      'phone': instance.phone,
      'email': instance.email,
      'idcard': instance.idCard,
      'bank': instance.bank,
      'person': instance.person,
      'location': instance.location,
      'organization': instance.organization,
      'plate': instance.plate,
      'ip': instance.ip,
      'url': instance.url,
      'date': instance.date,
      'amount': instance.amount,
      'postcode': instance.postcode,
      'custom': instance.custom,
    };

RestoreResult _$RestoreResultFromJson(Map<String, dynamic> json) =>
    RestoreResult(
      originalText: json['original_text'] as String,
    );

Map<String, dynamic> _$RestoreResultToJson(RestoreResult instance) =>
    <String, dynamic>{
      'original_text': instance.originalText,
    };

BatchMaskResponse _$BatchMaskResponseFromJson(Map<String, dynamic> json) =>
    BatchMaskResponse(
      results: (json['results'] as List<dynamic>)
          .map((e) => BatchResult.fromJson(e as Map<String, dynamic>))
          .toList(),
      totalCount: (json['total_count'] as num).toInt(),
    );

Map<String, dynamic> _$BatchMaskResponseToJson(BatchMaskResponse instance) =>
    <String, dynamic>{
      'results': instance.results,
      'total_count': instance.totalCount,
    };

BatchResult _$BatchResultFromJson(Map<String, dynamic> json) => BatchResult(
      original: json['original'] as String,
      masked: json['masked'] as String,
      entities: (json['entities'] as List<dynamic>)
          .map((e) => Entity.fromJson(e as Map<String, dynamic>))
          .toList(),
      stats: Stats.fromJson(json['stats'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$BatchResultToJson(BatchResult instance) =>
    <String, dynamic>{
      'original': instance.original,
      'masked': instance.masked,
      'entities': instance.entities,
      'stats': instance.stats,
    };

EntitiesResponse _$EntitiesResponseFromJson(Map<String, dynamic> json) =>
    EntitiesResponse(
      entities: (json['entities'] as List<dynamic>)
          .map((e) => EntityInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      version: json['version'] as String,
    );

Map<String, dynamic> _$EntitiesResponseToJson(EntitiesResponse instance) =>
    <String, dynamic>{
      'entities': instance.entities,
      'total': instance.total,
      'version': instance.version,
    };

EntityInfo _$EntityInfoFromJson(Map<String, dynamic> json) => EntityInfo(
      type: json['type'] as String,
      name: json['name'] as String,
      description: json['description'] as String,
      enabled: json['enabled'] as bool,
    );

Map<String, dynamic> _$EntityInfoToJson(EntityInfo instance) =>
    <String, dynamic>{
      'type': instance.type,
      'name': instance.name,
      'description': instance.description,
      'enabled': instance.enabled,
    };
