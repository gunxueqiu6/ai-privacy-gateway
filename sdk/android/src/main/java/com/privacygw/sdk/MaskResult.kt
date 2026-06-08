package com.privacygw.sdk

import com.google.gson.annotations.SerializedName

data class MaskResult(
    @SerializedName("masked_text") val maskedText: String,
    @SerializedName("entities") val entities: List<Entity>,
    @SerializedName("stats") val stats: Stats
)

data class Entity(
    @SerializedName("type") val type: String,
    @SerializedName("value") val value: String,
    @SerializedName("placeholder") val placeholder: String,
    @SerializedName("position") val position: Int
)

data class Stats(
    @SerializedName("phone") val phone: Int = 0,
    @SerializedName("email") val email: Int = 0,
    @SerializedName("idcard") val idcard: Int = 0,
    @SerializedName("bankcard") val bank: Int = 0,
    @SerializedName("person") val person: Int = 0,
    @SerializedName("location") val location: Int = 0,
    @SerializedName("organization") val organization: Int = 0,
    @SerializedName("plate") val plate: Int = 0,
    @SerializedName("ip") val ip: Int = 0,
    @SerializedName("url") val url: Int = 0,
    @SerializedName("date") val date: Int = 0,
    @SerializedName("amount") val amount: Int = 0,
    @SerializedName("postcode") val postcode: Int = 0,
    @SerializedName("custom") val custom: Int = 0
)

data class RestoreResult(
    @SerializedName("original_text") val originalText: String
)

data class BatchMaskResponse(
    @SerializedName("results") val results: List<BatchResult>,
    @SerializedName("total_count") val totalCount: Int
)

data class BatchResult(
    @SerializedName("original") val original: String,
    @SerializedName("masked") val masked: String,
    @SerializedName("entities") val entities: List<Entity>,
    @SerializedName("stats") val stats: Stats
)

data class EntitiesResponse(
    @SerializedName("entities") val entities: List<EntityInfo>,
    @SerializedName("total") val total: Int,
    @SerializedName("version") val version: String
)

data class EntityInfo(
    @SerializedName("type") val type: String,
    @SerializedName("name") val name: String,
    @SerializedName("description") val description: String,
    @SerializedName("enabled") val enabled: Boolean
)