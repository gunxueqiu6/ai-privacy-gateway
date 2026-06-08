import Foundation
import NetworkExtension

/**
 * Filter配置管理器
 *
 * 管理Network Extension的配置和状态
 */
class FilterManager: ObservableObject {

    static let shared = FilterManager()

    @Published var isEnabled: Bool = false
    @Published var maskedCount: Int = 0
    @Published var totalRequests: Int = 0
    @Published var gatewayUrl: String = "http://localhost:9999"
    @Published var gatewayApiKey: String = ""

    private let logger = Logger(subsystem: "com.privacygw.filter", category: "Manager")
    private let appGroup = "group.com.privacygw.filter"

    /**
     * 加载配置
     */
    func loadConfiguration() {
        // TODO: Migrate to Keychain storage (C-10).
        // API keys must not be stored in UserDefaults (plaintext plist).
        // Use a Keychain wrapper:
        //   let keychain = KeychainWrapper.standard
        //   gatewayApiKey = keychain.string(forKey: "api_key") ?? gatewayApiKey
        let defaults = UserDefaults(suiteName: appGroup)
        gatewayUrl = defaults?.string(forKey: "gateway_url") ?? gatewayUrl
        gatewayApiKey = defaults?.string(forKey: "api_key") ?? gatewayApiKey
        maskedCount = defaults?.integer(forKey: "masked_count") ?? 0
        totalRequests = defaults?.integer(forKey: "total_requests") ?? 0

        logger.info("Configuration loaded")
    }

    /**
     * 保存配置
     */
    func saveConfiguration() {
        // TODO: Migrate to Keychain storage (C-10).
        // See loadConfiguration() for the migration code pattern.
        let defaults = UserDefaults(suiteName: appGroup)
        defaults?.set(gatewayUrl, forKey: "gateway_url")
        defaults?.set(gatewayApiKey, forKey: "api_key")

        logger.info("Configuration saved: gateway=\(gatewayUrl)")
    }

    /**
     * 启用过滤器
     */
    func enableFilter() async throws {
        logger.info("Enabling filter")

        // 保存配置
        saveConfiguration()

        // 加载Network Extension配置
        let providerManager = NEFilterProviderManager()

        // 创建过滤器配置
        let filterConfig = NEFilterRule()
        // 注意：实际实现需要更详细的配置

        // 启用
        try await providerManager.saveToPreferences()

        isEnabled = true
        logger.info("Filter enabled successfully")
    }

    /**
     * 禁用过滤器
     */
    func disableFilter() async throws {
        logger.info("Disabling filter")

        let providerManager = NEFilterProviderManager()
        providerManager.isEnabled = false

        try await providerManager.saveToPreferences()

        isEnabled = false
        logger.info("Filter disabled successfully")
    }

    /**
     * 更新统计
     */
    func updateStats() {
        let defaults = UserDefaults(suiteName: appGroup)
        maskedCount = defaults?.integer(forKey: "masked_count") ?? maskedCount
        totalRequests = defaults?.integer(forKey: "total_requests") ?? totalRequests
    }
}