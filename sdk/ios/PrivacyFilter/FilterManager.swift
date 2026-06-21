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
        let defaults = UserDefaults(suiteName: appGroup)
        gatewayUrl = defaults?.string(forKey: "gateway_url") ?? gatewayUrl
        gatewayApiKey = KeychainHelper.read(key: "api_key") ?? gatewayApiKey
        maskedCount = defaults?.integer(forKey: "masked_count") ?? 0
        totalRequests = defaults?.integer(forKey: "total_requests") ?? 0

        logger.info("Configuration loaded")
    }

    /**
     * 保存配置
     */
    func saveConfiguration() {
        let defaults = UserDefaults(suiteName: appGroup)
        defaults?.set(gatewayUrl, forKey: "gateway_url")
        KeychainHelper.save(key: "api_key", value: gatewayApiKey)

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
        let filterManager = NEFilterManager.shared()
        filterManager.localizedDescription = "AI Privacy Gateway"
        try await filterManager.saveToPreferences()

        isEnabled = true
        logger.info("Filter enabled successfully")
    }

    /**
     * 禁用过滤器
     */
    func disableFilter() async throws {
        logger.info("Disabling filter")

        let filterManager = NEFilterManager.shared()
        filterManager.isEnabled = false

        try await filterManager.saveToPreferences()

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