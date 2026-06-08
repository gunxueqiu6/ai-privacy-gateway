import NetworkExtension
import Foundation
import os.log

/**
 * AI Privacy Gateway Filter Data Provider
 *
 * 系统级网络过滤器，拦截所有出站HTTP流量，对AI服务请求进行脱敏处理。
 *
 * 工作原理：
 * 1. 实现 NEFilterDataProvider，拦截所有HTTP/HTTPS请求
 * 2. 检查目标域名是否为AI服务
 * 3. AI服务请求 → 代理到网关脱敏 → 返回脱敏数据
 * 4. 其他请求 → 直通
 */
class FilterDataProvider: NEFilterDataProvider {

    private let logger = Logger(subsystem: "com.privacygw.filter", category: "DataProvider")

    // AI服务域名白名单
    private let aiServiceDomains: Set<String> = [
        "openai.com",
        "api.openai.com",
        "chat.openai.com",
        "api.anthropic.com",
        "anthropic.com",
        "api.deepseek.com",
        "deepseek.com",
        "chat.deepseek.com",
        "api.moonshot.cn",
        "moonshot.cn",
        "kimi.moonshot.cn",
        "api.x.ai",
        "x.ai",
        "grok.x.ai",
        "api.doubao.com",
        "doubao.com",
        "api.yuanbao.com",
        "yuanbao.com",
        "api.coze.cn",
        "coze.cn",
        "api.coze.com",
        "coze.com"
    ]

    // 网关配置
    private var gatewayUrl: String = "http://localhost:9999"
    private var gatewayApiKey: String = ""

    // 统计
    private var maskedCount: Int = 0
    private var totalRequests: Int = 0

    override func startFilter(completionHandler: @escaping (Error?) -> Void) {
        logger.info("Filter started")

        // 加载配置
        loadConfiguration()

        // 启动成功
        completionHandler(nil)
    }

    override func stopFilter(with reason: NEProviderStopReason, completionHandler: @escaping () -> Void) {
        logger.info("Filter stopped with reason: \(reason.rawValue)")
        completionHandler()
    }

    /**
     * 处理新的网络流
     *
     * 这是核心过滤逻辑入口
     */
    override func handleNewFlow(_ flow: NEFilterFlow) -> NEFilterNewFlowVerdict {
        guard let socketFlow = flow as? NEFilterSocketFlow else {
            logger.warning("Unknown flow type, passing through")
            return .pass()
        }

        // 获取目标地址
        let remoteEndpoint = socketFlow.remoteEndpoint

        guard let hostEndpoint = remoteEndpoint as? NWHostEndpoint else {
            logger.warning("Unknown endpoint type, passing through")
            return .pass()
        }

        let hostname = hostEndpoint.hostname
        let port = Int(hostEndpoint.port) ?? 0

        logger.debug("New flow to: \(hostname):\(port)")

        totalRequests += 1

        // 检查是否为AI服务域名
        if isAiServiceDomain(hostname) {
            logger.info("AI service detected: \(hostname), will filter")

            // 需要过滤的流量
            // 返回需要处理的判决
            return .filterData(
                needInbound: true,
                needOutbound: true,
                peekInbound: 4096,
                peekOutbound: 4096
            )
        }

        // 非AI服务，直接放行
        return .pass()
    }

    /**
     * 处理入站数据
     */
    override func handleInboundData(from flow: NEFilterFlow, readDataStart offset: Int, readDataLength length: Int) -> NEFilterDataVerdict {
        // 读取数据
        let data = flow.readData(offset: offset, length: length)

        guard let dataBytes = data else {
            return .pass()
        }

        logger.debug("Inbound data: \(dataBytes.count) bytes")

        // 响应数据通常不需要处理，直接放行
        return .pass()
    }

    /**
     * 处理出站数据（请求）
     */
    override func handleOutboundData(from flow: NEFilterFlow, readDataStart offset: Int, readDataLength length: Int) -> NEFilterDataVerdict {
        // 读取数据
        let data = flow.readData(offset: offset, length: length)

        guard let dataBytes = data else {
            return .pass()
        }

        logger.debug("Outbound data: \(dataBytes.count) bytes")

        // 解析HTTP请求
        if let httpRequest = parseHttpRequest(dataBytes) {
            logger.info("HTTP request detected: \(httpRequest.method) \(httpRequest.path)")

            // 调用网关脱敏
            if let maskedBody = maskRequestBody(httpRequest.body) {
                maskedCount += 1

                // 重新组装请求
                let maskedRequest = rebuildHttpRequest(httpRequest, maskedBody: maskedBody)

                logger.info("Request masked successfully")

                // 返回修改后的数据
                return .replaceData(maskedRequest)
            }
        }

        // 无法处理，放行
        return .pass()
    }

    /**
     * 检查是否为AI服务域名
     */
    private func isAiServiceDomain(_ hostname: String) -> Bool {
        // 直接匹配
        if aiServiceDomains.contains(hostname) {
            return true
        }

        // 子域名匹配
        for domain in aiServiceDomains {
            if hostname.hasSuffix(domain) {
                return true
            }
        }

        return false
    }

    /**
     * 加载配置
     */
    private func loadConfiguration() {
        // TODO: Migrate to Keychain for secure storage (C-10).
        // UserDefaults stores data in plaintext on disk — API keys and tokens
        // must be stored in the Keychain instead.
        // Use a Keychain wrapper (e.g. SwiftKeychainWrapper or SecItem API):
        //   let keychain = KeychainWrapper.standard
        //   gatewayApiKey = keychain.string(forKey: "api_key") ?? gatewayApiKey
        let defaults = UserDefaults(suiteName: "group.com.privacygw.filter")
        gatewayUrl = defaults?.string(forKey: "gateway_url") ?? gatewayUrl
        gatewayApiKey = defaults?.string(forKey: "api_key") ?? gatewayApiKey

        logger.info("Configuration loaded: gateway=\(gatewayUrl)")
    }

    /**
     * 解析HTTP请求
     */
    private func parseHttpRequest(_ data: Data) -> HttpRequest? {
        guard let requestString = String(data: data, encoding: .utf8) else {
            return nil
        }

        // 简化的HTTP解析
        let lines = requestString.split(separator: "\r\n")

        guard let firstLine = lines.first else {
            return nil
        }

        let parts = firstLine.split(separator: " ")
        guard parts.count >= 2 else {
            return nil
        }

        let method = String(parts[0])
        let path = String(parts[1])

        // 查找body
        var headers: [String: String] = [:]
        var bodyStartIndex = 0

        for (index, line) in lines.enumerated() {
            if line.isEmpty {
                bodyStartIndex = index + 1
                break
            }

            let headerParts = line.split(separator: ":")
            if headerParts.count >= 2 {
                let key = String(headerParts[0]).trimmingCharacters(in: .whitespaces)
                let value = String(headerParts[1]).trimmingCharacters(in: .whitespaces)
                headers[key] = value
            }
        }

        // 提取body
        let bodyLines = lines.dropFirst(bodyStartIndex)
        let body = bodyLines.joined(separator: "\r\n")

        return HttpRequest(
            method: method,
            path: path,
            headers: headers,
            body: body
        )
    }

    /**
     * 调用网关脱敏请求体
     */
    private func maskRequestBody(_ body: String) -> String? {
        guard !body.isEmpty else {
            return nil
        }

        // 构建请求
        guard let url = URL(string: "\(gatewayUrl)/api/mask") else {
            logger.error("Invalid gateway URL: \(gatewayUrl)")
            return nil
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if !gatewayApiKey.isEmpty {
            request.setValue("Bearer \(gatewayApiKey)", forHTTPHeaderField: "Authorization")
        }

        let payload = ["text": body]
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)

        // 发送请求（同步，因为Network Extension不支持异步）
        // 注意：实际实现需要使用更复杂的异步处理
        // TODO: 重新设计异步架构，消除 DispatchSemaphore 阻塞。
        // 当前使用同步模式会阻塞线程，影响吞吐量。
        // 可考虑使用 NEFilterFlow 的异步回调链或 OperationQueue 管理。
        let semaphore = DispatchSemaphore(value: 0)
        var result: String?

        URLSession.shared.dataTask(with: request) { data, response, error in
            if let data = data {
                if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    result = json["masked_text"] as? String
                }
            }
            semaphore.signal()
        }.resume()

        _ = semaphore.wait(timeout: .now() + 30)

        return result
    }

    /**
     * 重新组装HTTP请求
     */
    private func rebuildHttpRequest(_ original: HttpRequest, maskedBody: String) -> Data {
        var request = "\(original.method) \(original.path) HTTP/1.1\r\n"

        // 添加headers
        for (key, value) in original.headers {
            // 更新Content-Length
            if key.lowercased() == "content-length" {
                request += "\(key): \(maskedBody.count)\r\n"
            } else {
                request += "\(key): \(value)\r\n"
            }
        }

        request += "\r\n"
        request += maskedBody

        return Data(request.utf8)
    }
}

/**
 * HTTP请求结构
 */
struct HttpRequest {
    let method: String
    let path: String
    let headers: [String: String]
    let body: String
}