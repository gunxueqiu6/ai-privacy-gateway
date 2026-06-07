import Foundation

public struct MaskResult: Codable {
    public let maskedText: String
    public let entities: [Entity]
    public let stats: Stats
    
    enum CodingKeys: String, CodingKey {
        case maskedText = "masked_text"
        case entities
        case stats
    }
}

public struct Entity: Codable {
    public let type: String
    public let value: String
    public let placeholder: String
    public let position: Int
}

public struct Stats: Codable {
    public let phone: Int
    public let email: Int
    public let idcard: Int
    public let bank: Int
    public let person: Int
    public let location: Int
    public let organization: Int
    public let plate: Int
    public let ip: Int
    public let url: Int
    public let date: Int
    public let amount: Int
    public let postcode: Int
    public let custom: Int
    
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.phone = try container.decodeIfPresent(Int.self, forKey: .phone) ?? 0
        self.email = try container.decodeIfPresent(Int.self, forKey: .email) ?? 0
        self.idcard = try container.decodeIfPresent(Int.self, forKey: .idcard) ?? 0
        self.bank = try container.decodeIfPresent(Int.self, forKey: .bank) ?? 0
        self.person = try container.decodeIfPresent(Int.self, forKey: .person) ?? 0
        self.location = try container.decodeIfPresent(Int.self, forKey: .location) ?? 0
        self.organization = try container.decodeIfPresent(Int.self, forKey: .organization) ?? 0
        self.plate = try container.decodeIfPresent(Int.self, forKey: .plate) ?? 0
        self.ip = try container.decodeIfPresent(Int.self, forKey: .ip) ?? 0
        self.url = try container.decodeIfPresent(Int.self, forKey: .url) ?? 0
        self.date = try container.decodeIfPresent(Int.self, forKey: .date) ?? 0
        self.amount = try container.decodeIfPresent(Int.self, forKey: .amount) ?? 0
        self.postcode = try container.decodeIfPresent(Int.self, forKey: .postcode) ?? 0
        self.custom = try container.decodeIfPresent(Int.self, forKey: .custom) ?? 0
    }
    
    enum CodingKeys: String, CodingKey {
        case phone, email, idcard, bank, person, location, organization, plate, ip, url, date, amount, postcode, custom
    }
}

public struct RestoreResult: Codable {
    public let originalText: String
    
    enum CodingKeys: String, CodingKey {
        case originalText = "original_text"
    }
}

public struct BatchMaskResponse: Codable {
    public let results: [BatchResult]
    public let totalCount: Int
    
    enum CodingKeys: String, CodingKey {
        case results
        case totalCount = "total_count"
    }
}

public struct BatchResult: Codable {
    public let original: String
    public let masked: String
    public let entities: [Entity]
    public let stats: Stats
}

public struct EntitiesResponse: Codable {
    public let entities: [EntityInfo]
    public let total: Int
    public let version: String
}

public struct EntityInfo: Codable {
    public let type: String
    public let name: String
    public let description: String
    public let enabled: Bool
}