package com.privacygw.sdk

data class MaskResult(
    val maskedText: String,
    val entities: List<Entity>,
    val stats: Stats
)

data class Entity(
    val type: String,
    val value: String,
    val placeholder: String,
    val position: Int
)

data class Stats(
    val phone: Int = 0,
    val email: Int = 0,
    val idcard: Int = 0,
    val bank: Int = 0,
    val person: Int = 0,
    val location: Int = 0,
    val organization: Int = 0,
    val plate: Int = 0,
    val ip: Int = 0,
    val url: Int = 0,
    val date: Int = 0,
    val amount: Int = 0,
    val postcode: Int = 0,
    val custom: Int = 0
)

data class RestoreResult(
    val originalText: String
)

data class BatchMaskResponse(
    val results: List<BatchResult>,
    val totalCount: Int
)

data class BatchResult(
    val original: String,
    val masked: String,
    val entities: List<Entity>,
    val stats: Stats
)

data class EntitiesResponse(
    val entities: List<EntityInfo>,
    val total: Int,
    val version: String
)

data class EntityInfo(
    val type: String,
    val name: String,
    val description: String,
    val enabled: Boolean
)