import NetworkExtension
import Foundation
import os.log

// MARK: - HTTP Request Model

/// Parsed representation of an HTTP/1.1 request.
private struct ParsedHttpRequest {
    let method: String
    let path: String
    let headers: [String: String]
    let bodyRange: Range<Int>       // byte range of the body within the raw data
    let isComplete: Bool
}

/// Result of trying to parse an HTTP request from buffered bytes.
private enum HttpParseResult {
    case notHttp
    case partial                         // valid headers but body not yet complete
    case complete(ParsedHttpRequest)     // fully parsed
}

// MARK: - Per-Flow State

/// Tracks accumulated outbound data for a single flow.
private final class FlowState {
    /// Buffer accumulating all outbound bytes read so far.
    var accumulator = Data()
    /// True once we have returned `.replaceData()` for this flow.
    var didReplace = false
    /// True if this flow matched an AI service domain (from handleNewFlow).
    var isAiService = false
}

// MARK: - AI Privacy Gateway Filter

/**
 * NEFilterDataProvider that intercepts outbound HTTP/HTTPS requests to
 * known AI API endpoints and masks PII (phone numbers, emails, ID cards,
 * bank cards, API keys) in the request body **before** it leaves the device.
 *
 * ── How it works ──
 *
 * 1. `handleNewFlow`  — Checks the flow's remote hostname against a
 *                       domain allowlist. AI-service flows get
 *                       `.filterData(needsOutbound:)` so the system
 *                       delivers decrypted application bytes to us.
 *
 * 2. `handleOutboundData` — The system buffers up to `peekOutbound` bytes
 *    and delivers them in **one** call for typical flows.  We read all
 *    accumulated bytes, parse the HTTP request, apply the local PII
 *    masker synchronously, and return `.replaceData()` with the modified
 *    request bytes.
 *
 *    ⚠️  Large requests (> peekOutbound) arrive in chunks.  The first
 *    chunk is passed through.  This is an acceptable trade-off for
 *    essentially all AI API traffic (typical body < 100 KB).
 *
 * 3. `handleInboundData` — Pass-through.  AI responses are already
 *    masked by the gateway; we do not modify them.
 *
 * ── Watchdog safety ──
 * The PII masker runs locally with regex — no blocking network calls.
 * This avoids the NE watchdog killing the extension process.
 */
final class FilterDataProvider: NEFilterDataProvider {

    // MARK: - Logger

    private let logger = Logger(
        subsystem: "com.privacygw.filter",
        category: "DataProvider"
    )

    // MARK: - AI Service Domain Allowlist

    private let aiServiceDomains: Set<String> = [
        // OpenAI
        "openai.com",
        "api.openai.com",
        "chat.openai.com",

        // Anthropic
        "anthropic.com",
        "api.anthropic.com",

        // DeepSeek
        "deepseek.com",
        "api.deepseek.com",
        "chat.deepseek.com",

        // Moonshot / Kimi
        "moonshot.cn",
        "api.moonshot.cn",
        "kimi.moonshot.cn",

        // xAI / Grok
        "x.ai",
        "api.x.ai",
        "grok.x.ai",

        // Doubao / Volcano Engine
        "doubao.com",
        "api.doubao.com",

        // Yuanbao / Tencent
        "yuanbao.com",
        "api.yuanbao.com",

        // Coze
        "coze.cn",
        "api.coze.cn",
        "coze.com",
        "api.coze.com",

        // Google AI / Vertex
        "generativelanguage.googleapis.com",
        "aiplatform.googleapis.com",

        // Azure OpenAI
        "openai.azure.com",

        // Together AI
        "api.together.xyz",

        // Mistral AI
        "api.mistral.ai",

        // Perplexity
        "api.perplexity.ai",

        // Groq
        "api.groq.com",
    ]

    // MARK: - Components

    private let piiMasker = PiiMasker()
    /// Per-flow state keyed by `ObjectIdentifier(flow)`.
    private var flowStates: [ObjectIdentifier: FlowState] = [:]

    // MARK: - Configuration

    private var gatewayUrl: String = "http://localhost:9999"
    private var gatewayApiKey: String = ""

    // MARK: - Lifecycle

    override func startFilter(completionHandler: @escaping (Error?) -> Void) {
        logger.info("Filter starting…")
        loadConfiguration()
        piiMasker.resetCounters()

        // Background pattern sync from the gateway (informational).
        if !gatewayUrl.isEmpty {
            schedulePatternSync()
        }

        logger.info("Filter started successfully")
        completionHandler(nil)
    }

    override func stopFilter(with reason: NEProviderStopReason, completionHandler: @escaping () -> Void) {
        logger.info("Filter stopped: reason=\(reason.rawValue)")
        persistStats()
        flowStates.removeAll()
        completionHandler()
    }

    // MARK: - Flow Decision

    override func handleNewFlow(_ flow: NEFilterFlow) -> NEFilterNewFlowVerdict {
        let hostname: String

        // ── Extract hostname ───────────────────────────────────────
        // Prefer NEFilterBrowserFlow.url (available on iOS 15+)
        if #available(iOS 15.0, *), let url = flow.url, let host = url.host {
            hostname = host
        } else if let socketFlow = flow as? NEFilterSocketFlow,
                  let endpoint = socketFlow.remoteEndpoint as? NWHostEndpoint {
            hostname = endpoint.hostname
        } else {
            logger.debug("Cannot determine hostname, passing through")
            return .pass()
        }

        logger.debug("New flow: \(hostname)")

        // ── Match against allowlist ────────────────────────────────
        guard isAiServiceDomain(hostname) else {
            // Secondary heuristic: match API path patterns via flow URL
            if #available(iOS 15.0, *), let url = flow.url {
                let path = url.path.lowercased()
                if path.contains("/chat/completions")
                    || path.contains("/v1/completions")
                    || path.contains("/v1/embeddings")
                    || path.contains("/v1/messages")
                    || path.contains("/v1/chat/completions") {
                    logger.info("AI API path detected: \(path) — enabling filter")
                    let state = FlowState()
                    state.isAiService = true
                    flowStates[ObjectIdentifier(flow)] = state
                    return .filterData(
                        needInbound: false,
                        needOutbound: true,
                        peekInbound: 0,
                        peekOutbound: 1_048_576   // 1 MB
                    )
                }
            }
            return .pass()
        }

        logger.info("AI service domain: \(hostname) — enabling filter")

        let state = FlowState()
        state.isAiService = true
        flowStates[ObjectIdentifier(flow)] = state

        return .filterData(
            needInbound: false,
            needOutbound: true,
            peekInbound: 0,
            peekOutbound: 1_048_576   // 1 MB
        )
    }

    // MARK: - Outbound Data

    override func handleOutboundData(
        from flow: NEFilterFlow,
        readDataStart offset: Int,
        readDataLength length: Int
    ) -> NEFilterDataVerdict {
        guard let state = flowStates[ObjectIdentifier(flow)], state.isAiService else {
            return .pass()
        }

        // If we already replaced data for this flow, pass through.
        if state.didReplace {
            return .pass()
        }

        let totalAvailable = offset + length
        guard let chunk = flow.readData(startOffset: 0, length: totalAvailable) else {
            logger.warning("readData returned nil, passing through")
            flowStates.removeValue(forKey: ObjectIdentifier(flow))
            return .pass()
        }

        state.accumulator.append(chunk)
        let accumulated = state.accumulator

        // ── Parse the HTTP request ─────────────────────────────────
        switch parseHttpRequest(accumulated) {
        case .notHttp:
            // Not HTTP — clean up and pass through
            logger.debug("Not HTTP, passing through")
            flowStates.removeValue(forKey: ObjectIdentifier(flow))
            return .pass()

        case .partial:
            // Valid HTTP headers but body not yet complete.
            // The peek buffer still holds the data; the system will
            // call us again as more arrives.  We *must* return a
            // verdict for what we've seen so far.
            //
            // Returning .pass() here will SEND the partial data to
            // the server, which would corrupt the request for anything
            // larger than peekOutbound.  To avoid this, we drop out
            // of filter mode: pass once and the rest of the flow
            // continues unfiltered.
            logger.warning("Request exceeds peek buffer (\(accumulated.count) bytes so far), passing through unfiltered")
            flowStates.removeValue(forKey: ObjectIdentifier(flow))
            return .pass()

        case .complete(let httpReq):
            // ── Full request — apply PII masking ───────────────────
            guard !httpReq.bodyRange.isEmpty else {
                // No body (e.g. GET request)
                state.didReplace = true
                flowStates.removeValue(forKey: ObjectIdentifier(flow))
                return .pass()
            }

            let bodyData = accumulated.subdata(in: httpReq.bodyRange)

            let contentType = httpReq.headers
                .first { $0.key.lowercased() == "content-type" }?
                .value.lowercased() ?? ""

            let maskedResult: Data
            let maskedCount: Int

            if contentType.contains("application/json") {
                if let (maskedData, count) = piiMasker.maskJSONBody(bodyData) {
                    maskedResult = maskedData
                    maskedCount = count
                } else {
                    // Fall back to raw text masking
                    guard let bodyStr = String(data: bodyData, encoding: .utf8) else {
                        logger.warning("Non-UTF8 body, passing through")
                        flowStates.removeValue(forKey: ObjectIdentifier(flow))
                        return .pass()
                    }
                    (maskedResult, maskedCount) = maskRawText(bodyStr)
                }
            } else {
                guard let bodyStr = String(data: bodyData, encoding: .utf8) else {
                    logger.warning("Non-UTF8 body, passing through")
                    flowStates.removeValue(forKey: ObjectIdentifier(flow))
                    return .pass()
                }
                (maskedResult, maskedCount) = maskRawText(bodyStr)
            }

            if maskedCount == 0 {
                logger.debug("No PII found in request body")
                state.didReplace = true
                flowStates.removeValue(forKey: ObjectIdentifier(flow))
                return .pass()
            }

            // ── Rebuild full request with masked body ──────────────
            let newRequestBytes = rebuildHttpRequest(
                original: accumulated,
                httpReq: httpReq,
                newBody: maskedResult
            )

            logger.info("Masked \(maskedCount) PII items in request to \(httpReq.path)")

            let allCounters = piiMasker.countersByType()
            let totalMasked = allCounters.values.reduce(0, +)
            updateStats(maskedTotal: totalMasked, counters: allCounters)

            state.didReplace = true
            flowStates.removeValue(forKey: ObjectIdentifier(flow))
            return .replaceData(newRequestBytes)
        }
    }

    // MARK: - Inbound Data

    override func handleInboundData(
        from flow: NEFilterFlow,
        readDataStart offset: Int,
        readDataLength length: Int
    ) -> NEFilterDataVerdict {
        return .pass()
    }

    // MARK: - Domain Matching

    private func isAiServiceDomain(_ hostname: String) -> Bool {
        let lower = hostname.lowercased()
        if aiServiceDomains.contains(lower) { return true }
        for domain in aiServiceDomains {
            if lower.hasSuffix("." + domain) { return true }
        }
        return false
    }

    // MARK: - Configuration

    private func loadConfiguration() {
        let defaults = UserDefaults(suiteName: "group.com.privacygw.filter")
        if let url = defaults?.string(forKey: "gateway_url"), !url.isEmpty {
            gatewayUrl = url
        }
        if let key = KeychainHelper.read(key: "api_key") {
            gatewayApiKey = key
        }
        logger.info("Config loaded: gateway=\(self.gatewayUrl)")
    }

    // MARK: - Raw Text Masking Helper

    private func maskRawText(_ body: String) -> (Data, Int) {
        let (masked, count) = piiMasker.mask(body)
        return (Data(masked.utf8), count)
    }

    // MARK: - Pattern Sync

    private func schedulePatternSync() {
        let url = gatewayUrl
        let key = gatewayApiKey
        DispatchQueue.global(qos: .background).asyncAfter(deadline: .now() + 5) { [weak self] in
            self?.syncPatterns(gatewayUrl: url, apiKey: key)
        }
    }

    private func syncPatterns(gatewayUrl: String, apiKey: String) {
        guard let url = URL(string: "\(gatewayUrl)/api/entities") else { return }
        var req = URLRequest(url: url)
        req.timeoutInterval = 10
        if !apiKey.isEmpty {
            req.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        }
        URLSession.shared.dataTask(with: req) { [weak self] data, _, error in
            if let error = error {
                self?.logger.warning("Pattern sync failed: \(error.localizedDescription)")
                return
            }
            if let data = data {
                self?.logger.info("Pattern sync completed (\(data.count) bytes)")
            }
        }.resume()
    }

    // MARK: - Stats

    private func persistStats() {
        let counters = piiMasker.countersByType()
        let total = counters.values.reduce(0, +)
        let defaults = UserDefaults(suiteName: "group.com.privacygw.filter")
        defaults?.set(total, forKey: "masked_total")
        defaults?.set(Date(), forKey: "stats_updated_at")
        if let encoded = try? JSONEncoder().encode(counters) {
            defaults?.set(encoded, forKey: "masked_counters")
        }
    }

    private func updateStats(maskedTotal: Int, counters: [String: Int]) {
        let defaults = UserDefaults(suiteName: "group.com.privacygw.filter")
        defaults?.set(maskedTotal, forKey: "masked_total")
        defaults?.set(Date(), forKey: "stats_updated_at")
        if let encoded = try? JSONEncoder().encode(counters) {
            defaults?.set(encoded, forKey: "masked_counters")
        }
    }
}

// MARK: - HTTP/1.1 Request Parser

/**
 * Minimal HTTP/1.1 request parser.
 *
 * Handles:
 * - `Content-Length` based body delimiting
 * - `Transfer-Encoding: chunked` detection
 * - Connections where headers arrive in multiple TCP segments
 *
 * Limitations:
 * - No HTTP/2 support (system maps HTTP/2 to H1 for the filter)
 * - No Content-Encoding decompression
 * - No multi-line header values (extremely rare)
 */
private func parseHttpRequest(_ data: Data) -> HttpParseResult {
    guard data.count >= 16 else { return .partial }

    guard let raw = String(data: data, encoding: .utf8) else { return .notHttp }

    // ── Validate HTTP request-line ────────────────────────────────
    let lines = raw.components(separatedBy: "\r\n")
    guard let requestLine = lines.first else { return .notHttp }

    let requestParts = requestLine.components(separatedBy: " ")
    guard requestParts.count >= 3,
          ["GET", "POST", "PUT", "PATCH", "DELETE"].contains(requestParts[0]),
          requestParts[2].hasPrefix("HTTP/") else {
        return .notHttp
    }

    // ── Locate header / body boundary ─────────────────────────────
    guard let headerEnd = raw.range(of: "\r\n\r\n") else {
        return .partial
    }

    let method        = requestParts[0]
    let path          = requestParts[1]
    let bodyStartByte = headerEnd.upperBound.utf16Offset(in: raw)
    let totalBytes    = data.count

    // ── Parse headers ─────────────────────────────────────────────
    var headers: [String: String] = [:]
    let headerSection = raw[raw.startIndex..<headerEnd.lowerBound]
    for headerLine in headerSection.components(separatedBy: "\r\n").dropFirst() {
        guard let colonIdx = headerLine.firstIndex(of: ":") else { continue }
        let key = headerLine[..<colonIdx].trimmingCharacters(in: .whitespaces)
        let val = headerLine[headerLine.index(after: colonIdx)...]
            .trimmingCharacters(in: .whitespaces)
        headers[key] = val
    }

    // ── Determine body completeness ────────────────────────────────
    let contentLength = headers.first { $0.key.lowercased() == "content-length" }
        .flatMap { Int($0.value) } ?? 0

    let isChunked = headers.first { $0.key.lowercased() == "transfer-encoding" }
        .map { $0.value.lowercased().contains("chunked") } ?? false

    if isChunked {
        // Terminating chunk marker: "0\r\n\r\n"
        if raw.hasSuffix("\r\n0\r\n\r\n") || raw.hasSuffix("\r\n0\r\n") {
            let bodyRange = bodyStartByte..<totalBytes
            return .complete(ParsedHttpRequest(
                method: method,
                path: path,
                headers: headers,
                bodyRange: bodyRange,
                isComplete: true
            ))
        }
        return .partial
    }

    let bodyBytesAvailable = totalBytes - bodyStartByte

    if contentLength > 0 && bodyBytesAvailable < contentLength {
        return .partial
    }

    let bodyRange = bodyStartByte..<totalBytes
    return .complete(ParsedHttpRequest(
        method: method,
        path: path,
        headers: headers,
        bodyRange: bodyRange,
        isComplete: contentLength == 0 || bodyBytesAvailable >= contentLength
    ))
}

// MARK: - Request Re-builder

/**
 * Replaces the body of an HTTP/1.1 request with `newBody` and updates
 * the `Content-Length` header to match.
 */
private func rebuildHttpRequest(
    original: Data,
    httpReq: ParsedHttpRequest,
    newBody: Data
) -> Data {
    // Read header portion as a string
    let headerData = original.subdata(in: 0..<httpReq.bodyRange.lowerBound)
    guard var headerStr = String(data: headerData, encoding: .utf8) else {
        // If we can't decode the header as UTF-8, fall back to just
        // appending the new body.
        var result = headerData
        result.append(newBody)
        return result
    }

    // Replace Content-Length header value
    if let clKey = httpReq.headers.keys.first(where: { $0.lowercased() == "content-length" }),
       let oldVal = httpReq.headers[clKey] {
        let oldLine = "\(clKey): \(oldVal)"
        let newLine = "\(clKey): \(newBody.count)"
        headerStr = headerStr.replacingOccurrences(of: oldLine, with: newLine)
    }

    // Assemble final bytes
    var result = Data()
    result.append(Data(headerStr.utf8))
    result.append(newBody)
    return result
}
