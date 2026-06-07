import Foundation

public struct GatewayConfig {
    public let baseUrl: String
    public let apiKey: String?
    public let timeout: TimeInterval
    public let headers: [String: String]
    
    public init(baseUrl: String, apiKey: String? = nil, timeout: TimeInterval = 10.0, headers: [String: String] = [:]) {
        self.baseUrl = baseUrl
        self.apiKey = apiKey
        self.timeout = timeout
        self.headers = headers
    }
}