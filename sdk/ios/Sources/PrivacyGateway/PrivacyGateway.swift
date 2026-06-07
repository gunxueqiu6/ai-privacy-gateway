import Foundation

public class PrivacyGateway {
    
    private let baseUrl: String
    private let timeout: TimeInterval
    private let headers: [String: String]
    
    private var urlSession: URLSession {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = timeout
        configuration.timeoutIntervalForResource = timeout
        return URLSession(configuration: configuration)
    }
    
    private init(baseUrl: String, timeout: TimeInterval, headers: [String: String]) {
        self.baseUrl = baseUrl.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        self.timeout = timeout
        self.headers = headers
    }
    
    public func mask(text: String) async throws -> MaskResult {
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw PrivacyGatewayError.invalidInput("text must be a non-empty string")
        }
        
        let request = try buildRequest(path: "/api/mask", method: "POST", body: ["text": text])
        return try await executeRequest(request: request, type: MaskResult.self)
    }
    
    public func restore(maskedText: String, mappings: [String: String]) async throws -> RestoreResult {
        guard !maskedText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw PrivacyGatewayError.invalidInput("maskedText must be a non-empty string")
        }
        
        let request = try buildRequest(path: "/api/restore", method: "POST", body: ["text": maskedText, "mappings": mappings])
        return try await executeRequest(request: request, type: RestoreResult.self)
    }
    
    public func maskBatch(texts: [String]) async throws -> BatchMaskResponse {
        guard !texts.isEmpty else {
            throw PrivacyGatewayError.invalidInput("texts must be a non-empty array")
        }
        
        guard texts.count <= 50 else {
            throw PrivacyGatewayError.invalidInput("Maximum 50 texts per batch")
        }
        
        let request = try buildRequest(path: "/api/mask/batch", method: "POST", body: ["texts": texts])
        return try await executeRequest(request: request, type: BatchMaskResponse.self)
    }
    
    public func getEntities() async throws -> EntitiesResponse {
        let request = try buildRequest(path: "/api/entities", method: "GET", body: nil)
        return try await executeRequest(request: request, type: EntitiesResponse.self)
    }
    
    private func buildRequest(path: String, method: String, body: [String: Any]?) throws -> URLRequest {
        guard let url = URL(string: "\(baseUrl)\(path)") else {
            throw PrivacyGatewayError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        headers.forEach { key, value in
            request.setValue(value, forHTTPHeaderField: key)
        }
        
        if let body = body {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        
        return request
    }
    
    private func executeRequest<T: Decodable>(request: URLRequest, type: T.Type) async throws -> T {
        let (data, response) = try await urlSession.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw PrivacyGatewayError.networkError
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw PrivacyGatewayError.serverError(httpResponse.statusCode)
        }
        
        do {
            return try JSONDecoder().decode(type, from: data)
        } catch {
            throw PrivacyGatewayError.decodingError(error)
        }
    }
    
    // MARK: - Shared Instance
    
    private static var shared: PrivacyGateway?
    
    public static func initialize(config: GatewayConfig) {
        let headers = buildHeaders(config: config)
        shared = PrivacyGateway(baseUrl: config.baseUrl, timeout: config.timeout, headers: headers)
    }
    
    public static func getInstance() throws -> PrivacyGateway {
        guard let instance = shared else {
            throw PrivacyGatewayError.notInitialized
        }
        return instance
    }
    
    private static func buildHeaders(config: GatewayConfig) -> [String: String] {
        var headers = config.headers
        if let apiKey = config.apiKey {
            headers["X-API-Key"] = apiKey
        }
        return headers
    }
    
    // MARK: - Static Convenience Methods
    
    public static func mask(text: String) async throws -> MaskResult {
        let instance = try getInstance()
        return try await instance.mask(text: text)
    }
    
    public static func restore(maskedText: String, mappings: [String: String]) async throws -> RestoreResult {
        let instance = try getInstance()
        return try await instance.restore(maskedText: maskedText, mappings: mappings)
    }
    
    public static func maskBatch(texts: [String]) async throws -> BatchMaskResponse {
        let instance = try getInstance()
        return try await instance.maskBatch(texts: texts)
    }
    
    public static func getEntities() async throws -> EntitiesResponse {
        let instance = try getInstance()
        return try await instance.getEntities()
    }
}

// MARK: - Errors

public enum PrivacyGatewayError: Error, LocalizedError {
    case notInitialized
    case invalidURL
    case invalidInput(String)
    case networkError
    case serverError(Int)
    case decodingError(Error)
    
    public var errorDescription: String? {
        switch self {
        case .notInitialized:
            return "PrivacyGateway not initialized. Call initialize(config:) first."
        case .invalidURL:
            return "Invalid URL"
        case .invalidInput(let message):
            return message
        case .networkError:
            return "Network error occurred"
        case .serverError(let code):
            return "Server returned error code \(code)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        }
    }
}