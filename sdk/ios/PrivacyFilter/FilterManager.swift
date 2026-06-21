import Foundation
import NetworkExtension
import os.log

/**
 * FilterConfigManager
 *
 * Manages the Network Extension configuration, per-type PII masking stats,
 * and periodic pattern syncing from the remote gateway.
 *
 * Thread safety:
 * - UI-facing properties are `@Published` and should be accessed from
 *   the main actor.
 * - Internal book-keeping uses `UserDefaults` in the app group container
 *   shared with the Network Extension process.
 */
final class FilterManager: ObservableObject {

    // MARK: - Singleton

    static let shared = FilterManager()

    // MARK: - Published State

    @Published var isEnabled: Bool = false {
        didSet { persistEnabledState() }
    }

    /// Total number of PII instances masked across all patterns.
    @Published var maskedTotal: Int = 0

    /// Number of requests processed by the filter (since last reset).
    @Published var totalRequests: Int = 0

    /// Per-type counters (e.g. ["PHONE": 42, "EMAIL": 7]).
    @Published var countersByType: [String: Int] = [:]

    /// Gateway URL configured by the user.
    @Published var gatewayUrl: String = "http://localhost:9999"

    /// Optional API key for the gateway.
    @Published var gatewayApiKey: String = ""

    /// When the stats were last updated.
    @Published var statsUpdatedAt: Date?

    // MARK: - Constants

    private let logger = Logger(subsystem: "com.privacygw.filter", category: "Manager")
    private let appGroup = "group.com.privacygw.filter"
    private let syncInterval: TimeInterval = 3600   // 1 hour

    // MARK: - Init

    private init() {
        loadPersistedState()

        // Listen for stats updates from the NE process.
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(statsDidChange),
            name: UserDefaults.didChangeNotification,
            object: UserDefaults(suiteName: appGroup)
        )
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    // MARK: - Persistence

    private func persistEnabledState() {
        let defaults = UserDefaults(suiteName: appGroup)
        defaults?.set(isEnabled, forKey: "filter_enabled")
        logger.info("Filter enabled state persisted: \(self.isEnabled)")
    }

    private func loadPersistedState() {
        let defaults = UserDefaults(suiteName: appGroup)

        isEnabled  = defaults?.bool(forKey: "filter_enabled") ?? false
        gatewayUrl = defaults?.string(forKey: "gateway_url") ?? "http://localhost:9999"

        if let key = KeychainHelper.read(key: "api_key") {
            gatewayApiKey = key
        }

        reloadStats()
    }

    /// Reload stats from the app-group store (written by the NE process).
    private func reloadStats() {
        let defaults = UserDefaults(suiteName: appGroup)

        maskedTotal   = defaults?.integer(forKey: "masked_total") ?? 0
        totalRequests = defaults?.integer(forKey: "total_requests") ?? 0

        if let data = defaults?.data(forKey: "masked_counters"),
           let decoded = try? JSONDecoder().decode([String: Int].self, from: data) {
            countersByType = decoded
        }

        statsUpdatedAt = defaults?.object(forKey: "stats_updated_at") as? Date
    }

    // MARK: - Configuration

    /// Persist current gateway URL & API key to the shared container.
    func saveConfiguration() {
        let defaults = UserDefaults(suiteName: appGroup)
        defaults?.set(gatewayUrl, forKey: "gateway_url")

        if !gatewayApiKey.isEmpty {
            KeychainHelper.save(key: "api_key", value: gatewayApiKey)
        }

        logger.info("Configuration saved: gateway=\(self.gatewayUrl)")
    }

    // MARK: - Filter Lifecycle

    /// Enable the content filter.
    func enableFilter() async throws {
        logger.info("Enabling filter…")

        // Save user config first so the NE process can read it.
        saveConfiguration()

        let mgr = NEFilterManager.shared()
        mgr.localizedDescription = "AI Privacy Gateway"

        let config = NEFilterFilterConfiguration()
        config.filterBrowsers = true
        config.filterSockets  = true
        config.dataProviderDesignatedRequirement = "identifier \"com.privacygw.filter.DataProvider\" and anchor apple generic"
        config.filterDataProviderBundleIdentifier = "com.privacygw.filter.DataProvider"
        mgr.filterConfiguration = config

        mgr.isEnabled = true
        try await mgr.saveToPreferences()

        isEnabled = true

        // Schedule a one-off stats refresh after the filter starts.
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
            self?.reloadStats()
        }

        logger.info("Filter enabled")
    }

    /// Disable the content filter.
    func disableFilter() async throws {
        logger.info("Disabling filter…")

        let mgr = NEFilterManager.shared()
        mgr.isEnabled = false
        try await mgr.saveToPreferences()

        isEnabled = false
        logger.info("Filter disabled")
    }

    // MARK: - Stats

    /// Force a fresh read of the shared stats.
    func refreshStats() {
        reloadStats()
    }

    /// Reset all counters (both local and in the NE process).
    func resetStats() {
        maskedTotal   = 0
        totalRequests = 0
        countersByType = [:]

        let defaults = UserDefaults(suiteName: appGroup)
        defaults?.set(0, forKey: "masked_total")
        defaults?.set(0, forKey: "total_requests")
        defaults?.removeObject(forKey: "masked_counters")

        logger.info("Stats reset")
    }

    // MARK: - Pattern Sync

    /// Trigger an immediate pattern sync with the gateway.
    /// The NE process will pick up new patterns on its next sync cycle.
    func syncPatterns() async {
        guard !gatewayUrl.isEmpty else { return }

        let urlStr = gatewayUrl.hasSuffix("/") ? "\(gatewayUrl)api/entities" : "\(gatewayUrl)/api/entities"
        guard let url = URL(string: urlStr) else { return }

        var req = URLRequest(url: url)
        req.timeoutInterval = 15
        if !gatewayApiKey.isEmpty {
            req.setValue("Bearer \(gatewayApiKey)", forHTTPHeaderField: "Authorization")
        }

        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            logger.info("Pattern sync succeeded (\(data.count) bytes)")
            // Future: parse and update local patterns
        } catch {
            logger.warning("Pattern sync failed: \(error.localizedDescription)")
        }
    }

    // MARK: - Notifications

    @objc private func statsDidChange(_ notification: Notification) {
        DispatchQueue.main.async { [weak self] in
            self?.reloadStats()
        }
    }
}
