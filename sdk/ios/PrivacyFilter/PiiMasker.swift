import Foundation
import os.log

// MARK: - PII Pattern Definition

/// A single PII detection pattern backed by regex.
public struct PiiPattern {
    public let type: String
    public let regex: NSRegularExpression
    public let placeholderFormat: String

    public init(type: String, pattern: String, placeholderFormat: String) throws {
        self.type = type
        self.regex = try NSRegularExpression(pattern: pattern, options: [.caseInsensitive])
        self.placeholderFormat = placeholderFormat
    }
}

// MARK: - Local PII Masking Engine

/// Synchronous PII masking engine that applies regex patterns locally.
///
/// Design decisions:
/// - Fully synchronous — never makes network calls, safe to call from
///   within `handleOutboundData` on the NE serial queue.
/// - Counter-per-type — each pattern family (phone, email, …) uses its
///   own monotonically increasing counter so placeholders stay readable.
/// - Thread-safe via internal lock.
public class PiiMasker {
    private let logger = Logger(subsystem: "com.privacygw.filter", category: "PiiMasker")
    private let patterns: [PiiPattern]
    private var counters: [String: Int] = [:]
    private let lock = NSLock()
    // MARK: - Initialisation

    public init() {
        self.patterns = Self.defaultPatterns()
        logger.info("PiiMasker initialised with \(self.patterns.count) patterns")
    }

    /// Load patterns from an array (used when syncing from gateway).
    public init(patterns: [PiiPattern]) {
        self.patterns = patterns
        logger.info("PiiMasker initialised with \(patterns.count) custom patterns")
    }

    // MARK: - Public API

    /// Mask all recognised PII in `text`.
    /// - Returns: The masked text and the total number of replacements made.
    public func mask(_ text: String) -> (masked: String, count: Int) {
        lock.lock()
        defer { lock.unlock() }

        var masked = text
        var totalReplacements = 0

        for pattern in patterns {
            let nsRange = NSRange(masked.startIndex..<masked.endIndex, in: masked)
            guard nsRange.length > 0 else { continue }

            // Collect all matches (we apply from last-to-first so that
            // earlier ranges stay valid after earlier (later-in-string)
            // replacements).
            var matches: [(NSRange, String)] = []

            pattern.regex.enumerateMatches(in: masked, options: [], range: nsRange) { match, _, _ in
                guard let m = match, m.range.location != NSNotFound else { return }
                let typeCount = (self.counters[pattern.type] ?? 0) + 1
                self.counters[pattern.type] = typeCount
                let placeholder = String(format: pattern.placeholderFormat, typeCount)
                matches.append((m.range, placeholder))
            }

            for (range, placeholder) in matches.sorted(by: { $0.0.location > $1.0.location }) {
                guard let swiftRange = Range(range, in: masked) else { continue }
                masked.replaceSubrange(swiftRange, with: placeholder)
                totalReplacements += 1
            }
        }

        return (masked, totalReplacements)
    }

    /// Mask only JSON string *values* (more precise than raw text masking).
    /// Walks a JSON body, finds every string value, masks PII within it.
    /// - Returns: The full JSON `Data` with masked string values, and the
    ///   total count of replacements made across the entire JSON tree.
    public func maskJSONBody(_ data: Data) -> (masked: Data, count: Int)? {
        lock.lock()
        defer { lock.unlock() }

        // Snapshot counters before the walk so we can compute the delta.
        let beforeCounts = counters

        guard let json = try? JSONSerialization.jsonObject(with: data),
              let masked = walkJSON(json) as? [String: Any],
              let result = try? JSONSerialization.data(withJSONObject: masked, options: []) else {
            return nil
        }

        let totalNew = counters.values.reduce(0, +) - beforeCounts.values.reduce(0, +)
        return (result, totalNew)
    }

    /// Reset all counters (e.g. at filter start).
    public func resetCounters() {
        lock.lock()
        counters.removeAll()
        lock.unlock()
    }

    /// Sum of all pattern counters.
    public var totalMasked: Int {
        lock.lock()
        defer { lock.unlock() }
        return counters.values.reduce(0, +)
    }

    /// Per-pattern-type counters.
    public func countersByType() -> [String: Int] {
        lock.lock()
        defer { lock.unlock() }
        return counters
    }

    // MARK: - Private helpers

    /// Recursively walk a decoded JSON tree and mask every string value.
    ///
    /// Caller MUST already hold `lock`.
    private func walkJSON(_ value: Any) -> Any {
        if let string = value as? String {
            return applyPatterns(string)
        } else if let dict = value as? [String: Any] {
            var masked = dict
            for (k, v) in dict {
                masked[k] = walkJSON(v)
            }
            return masked
        } else if let array = value as? [Any] {
            return array.map { walkJSON($0) }
        }
        // Numbers, booleans, null — pass through unchanged
        return value
    }

    /// Apply all patterns to a single string value.
    ///
    /// Caller MUST already hold `lock`.
    private func applyPatterns(_ text: String) -> String {
        var masked = text
        for pattern in patterns {
            let nsRange = NSRange(masked.startIndex..<masked.endIndex, in: masked)
            guard nsRange.length > 0 else { continue }

            var matches: [(NSRange, String)] = []

            pattern.regex.enumerateMatches(in: masked, options: [], range: nsRange) { match, _, _ in
                guard let m = match, m.range.location != NSNotFound else { return }
                let typeCount = (self.counters[pattern.type] ?? 0) + 1
                self.counters[pattern.type] = typeCount
                let placeholder = String(format: pattern.placeholderFormat, typeCount)
                matches.append((m.range, placeholder))
            }

            for (range, placeholder) in matches.sorted(by: { $0.0.location > $1.0.location }) {
                guard let swiftRange = Range(range, in: masked) else { continue }
                masked.replaceSubrange(swiftRange, with: placeholder)
            }
        }
        return masked
    }

    // MARK: - Default patterns

    private static func defaultPatterns() -> [PiiPattern] {
        var ps: [PiiPattern] = []

        // ── Chinese mobile: 1[3-9]XXXXXXXXX ──
        // Lookbehind/lookahead ensure we don't match part of a longer digit sequence.
        tryAdd(&ps, type: "PHONE",    pattern: "(?<!\\d)1[3-9]\\d{9}(?!\\d)",                          fmt: "[PHONE_%04d]")

        // ── Email ──
        tryAdd(&ps, type: "EMAIL",    pattern: "[\\w._%+-]+@[\\w.-]+\\.[a-zA-Z]{2,}",                  fmt: "[EMAIL_%04d]")

        // ── Chinese ID card (18-digit, second-generation) ──
        tryAdd(&ps, type: "IDCARD",   pattern: "[1-9]\\d{5}(?:19|20)\\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx](?!\\d)", fmt: "[IDCARD_%04d]")

        // ── Bank card (16-19 digits, not part of a longer number) ──
        tryAdd(&ps, type: "BANKCARD", pattern: "(?<!\\d)\\d{16,19}(?!\\d)",                            fmt: "[BANKCARD_%04d]")

        // ── OpenAI / DeepSeek / generic sk- API keys ──
        tryAdd(&ps, type: "APIKEY",   pattern: "sk-[A-Za-z0-9]{20,}(?![A-Za-z0-9])",                  fmt: "[APIKEY_%04d]")

        // ── Anthropic API keys ──
        tryAdd(&ps, type: "APIKEY",   pattern: "sk-ant-[A-Za-z0-9]{20,}(?![A-Za-z0-9])",              fmt: "[APIKEY_%04d]")

        // ── Generic bearer tokens in JSON bodies ──
        tryAdd(&ps, type: "TOKEN",    pattern: "(?i)\"bearer\\s+[A-Za-z0-9._-]{8,}\"",                fmt: "\"[TOKEN_%04d]\"")

        // ── IPv4 address ──
        tryAdd(&ps, type: "IP",       pattern: "(?<!\\d)\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}(?!\\d)", fmt: "[IP_%04d]")

        // ── Chinese / Taiwan phone numbers with area code ──
        tryAdd(&ps, type: "PHONE",    pattern: "(?<!\\d)0\\d{2,3}-?\\d{7,8}(?!\\d)",                  fmt: "[PHONE_%04d]")

        return ps
    }

    private static func tryAdd(_ ps: inout [PiiPattern], type: String, pattern: String, fmt: String) {
        guard let p = try? PiiPattern(type: type, pattern: pattern, placeholderFormat: fmt) else {
            return
        }
        ps.append(p)
    }
}
