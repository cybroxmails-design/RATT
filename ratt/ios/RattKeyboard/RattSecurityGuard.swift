// RattSecurityGuard.swift — Cybrox RATT Non-Execution & Anti-Malware Protocol (iOS)
// Native Swift port of ratt/security_guard.py for iPhone & iPadOS (iOS 16+).
// Guarantees zero payload execution, strips HTML/RTF styling, removes Unicode BiDi/RTLO
// spoofing characters, and blocks hazardous URI schemes (javascript:, shortcuts:, file:, etc.).

import Foundation

public struct RattSecurityGuard {
    public static let blockedSchemes: [String] = [
        "javascript:",
        "vbscript:",
        "data:",
        "file:",
        "intent:",
        "content:",
        "shortcuts:",
        "workflow:",
        "powershell:",
        "shell:",
        "cmd:",
        "ms-msdt:",
        "ms-officecmd:",
        "ms-word:",
        "ms-excel:",
        "ms-powerpoint:",
        "ms-settings:",
        "search-ms:",
        "itms-services:",
        "apple-magnifier:"
    ]

    public static let blockedExtensions: Set<String> = [
        ".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jse", ".wsf",
        ".hta", ".scr", ".pif", ".com", ".msi", ".msp", ".lnk", ".url", ".scf",
        ".iso", ".img", ".vhd", ".vhdx", ".chm", ".docm", ".xlsm", ".pptm",
        ".sh", ".command", ".pkg", ".dmg", ".app", ".ipa", ".mobileconfig"
    ]

    /// Sanitize copied or synced text/links into clean, unformatted, non-executable text.
    public static func sanitizeText(_ raw: String) -> (isSafe: Bool, clean: String) {
        if raw.isEmpty {
            return (false, "")
        }

        // 1. Strip HTML tags and embedded formatting
        var text = raw.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)

        // 2. Remove Unicode zero-width and BiDi / RTLO spoofing characters + NUL bytes
        if let spoofRegex = try? NSRegularExpression(
            pattern: "[\\u{200B}-\\u{200F}\\u{202A}-\\u{202E}\\u{2060}-\\u{2069}\\u{FEFF}\\0]",
            options: []
        ) {
            let range = NSRange(location: 0, length: text.utf16.count)
            text = spoofRegex.stringByReplacingMatches(in: text, options: [], range: range, withTemplate: "")
        }

        let trimmedLower = text.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if trimmedLower.isEmpty {
            return (false, "")
        }

        // 3. Block hazardous executable URI schemes
        for scheme in blockedSchemes {
            if trimmedLower.hasPrefix(scheme) ||
               trimmedLower.contains(" " + scheme) ||
               trimmedLower.contains("\n" + scheme) ||
               trimmedLower.contains("\t" + scheme) {
                return (false, "")
            }
        }

        // 4. If single-line URL, strip control characters to prevent paste-jacking
        if isLikelyURL(trimmedLower) {
            let cleanURL = text.trimmingCharacters(in: .whitespacesAndNewlines)
                .replacingOccurrences(of: "[\\r\\n\\t\\u{0000}-\\u{001F}\\u{007F}]", with: "", options: .regularExpression)
            return (true, cleanURL)
        }

        return (true, text)
    }

    /// Validate that a file name does not carry blocked executable/script extensions or RTLO spoofing.
    public static func isSafeFileName(_ filename: String) -> Bool {
        let trimmed = filename.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            return false
        }
        if trimmed.unicodeScalars.contains(where: { (0x202A...0x202E).contains($0.value) || (0x2066...0x2069).contains($0.value) }) {
            return false
        }
        let parts = trimmed.lowercased().split(separator: ".")
        guard parts.count > 1 else { return true }
        for part in parts.dropFirst() {
            if blockedExtensions.contains("." + part) {
                return false
            }
        }
        return true
    }

    private static func isLikelyURL(_ candidate: String) -> Bool {
        return candidate.hasPrefix("https://") ||
               candidate.hasPrefix("http://") ||
               candidate.hasPrefix("mailto:") ||
               candidate.hasPrefix("www.")
    }
}
