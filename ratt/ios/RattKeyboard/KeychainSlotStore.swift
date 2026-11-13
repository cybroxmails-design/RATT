// KeychainSlotStore.swift — AES-256-GCM Hardware-Backed Slot Storage (Apple CryptoKit)
// Encrypts and decrypts RATT's 10 slots inside the shared App Group (group.com.cybrox.ratt)
// using a 256-bit symmetric key stored in the iOS Hardware Keychain with
// `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` (`IOS-01`).

import Foundation
import CryptoKit
import Security
import Darwin

public final class KeychainSlotStore {
    public static let shared = KeychainSlotStore()

    private let suiteName = "group.com.cybrox.ratt"
    private let keychainAccount = "com.cybrox.ratt.masterkey.v2"
    private let keychainService = "com.cybrox.ratt.keychain"
    private lazy var defaults = UserDefaults(suiteName: suiteName)

    private static let documentAndMediaExtensions: Set<String> = [
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf",
        ".txt", ".csv", ".rtf", ".odt", ".ods", ".odp",
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
        ".mp4", ".mkv", ".mov", ".avi", ".webm",
        ".zip", ".rar", ".7z", ".tar", ".gz"
    ]

    public init() {}

    // MARK: - Entitlement Check (RATT Commercial & PC Subscription Rules)
    // 1. Basic: Max 10 slots for text, links, images, and vector diagrams (SVG).
    // 2. Android <-> iOS and macOS sync: Limited to Premium & Enterprise.
    // 3. Documents & Media files (.docx, .xls, .pdf, .mp4, etc.): Limited to Premium & Enterprise.
    // 4. 9-Language Translation: Limited to Premium & Enterprise.
    // 5. Share (across accounts) & Mirror: Limited to Premium & Enterprise.
    // 6. Enterprise: 50 base slots (expandable up to 50,000) + up to 3,000 worker accounts.

    public func getUserTier() -> String {
        return defaults?.string(forKey: "ratt_user_tier") ?? "basic"
    }

    public func hasPaidEntitlement() -> Bool {
        let tierRaw = getUserTier()
        return tierRaw == "premium" || tierRaw == "enterprise"
    }

    public func isEnterprise() -> Bool {
        return getUserTier() == "enterprise"
    }

    public func setUserTier(_ tier: String) {
        let normalized = tier.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        let valid = (normalized == "premium" || normalized == "enterprise") ? normalized : "basic"
        defaults?.set(valid, forKey: "ratt_user_tier")
    }

    public func maxSlots() -> Int {
        switch getUserTier() {
        case "enterprise":
            return 50
        case "premium":
            return 50_000
        default:
            return 10
        }
    }

    public func maxEnterpriseWorkers() -> Int {
        return isEnterprise() ? 3_000 : 1
    }

    public func canAccessSlot(_ slot: Int) -> Bool {
        return (1...maxSlots()).contains(slot)
    }

    public func canSyncWithMac() -> Bool {
        return hasPaidEntitlement()
    }

    public func canSyncWithWindows() -> Bool {
        return hasPaidEntitlement()
    }

    public func canSyncWithAndroid() -> Bool {
        return hasPaidEntitlement()
    }

    public func canCopyDocumentAndMediaFiles() -> Bool {
        return hasPaidEntitlement()
    }

    public func canTranslate() -> Bool {
        return hasPaidEntitlement()
    }

    public func canShareAndMirror() -> Bool {
        return hasPaidEntitlement()
    }

    public func isAllowedPayloadForTier(_ payloadText: String) -> Bool {
        if hasPaidEntitlement() { return true }
        let trimmed = payloadText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        for ext in Self.documentAndMediaExtensions {
            if trimmed.hasSuffix(ext) && (trimmed.hasPrefix("file://") || trimmed.contains("/") || trimmed.contains("\\")) {
                return false
            }
        }
        return true
    }

    // MARK: - Encrypted Slot Operations (AES-256-GCM)

    @discardableResult
    public func encryptAndStore(slot: Int, text: String) -> Bool {
        guard (1...10).contains(slot), isAllowedPayloadForTier(text) else { return false }
        let (isSafe, cleanText) = RattSecurityGuard.sanitizeText(text)
        guard isSafe,
              var data = cleanText.data(using: .utf8),
              let key = getOrCreateMasterKey() else {
            return false
        }
        defer {
            data.withUnsafeMutableBytes { ptr in
                if let base = ptr.baseAddress, ptr.count > 0 {
                    _ = memset_s(base, ptr.count, 0, ptr.count)
                }
            }
        }
        guard let sealed = try? AES.GCM.seal(data, using: key),
              let combined = sealed.combined else {
            return false
        }
        defaults?.set(combined, forKey: "slot_\(slot)")
        defaults?.set(Date().timeIntervalSince1970, forKey: "slot_ts_\(slot)")
        return true
    }

    public func decryptSlot(_ slot: Int) -> String? {
        guard (1...10).contains(slot),
              let data = defaults?.data(forKey: "slot_\(slot)"),
              let key = getOrCreateMasterKey(),
              let box = try? AES.GCM.SealedBox(combined: data),
              var decrypted = try? AES.GCM.open(box, using: key) else {
            return nil
        }
        defer {
            decrypted.withUnsafeMutableBytes { ptr in
                if let base = ptr.baseAddress, ptr.count > 0 {
                    _ = memset_s(base, ptr.count, 0, ptr.count)
                }
            }
        }
        guard let rawText = String(data: decrypted, encoding: .utf8) else {
            return nil
        }
        let (isSafe, cleanText) = RattSecurityGuard.sanitizeText(rawText)
        return isSafe ? cleanText : nil
    }

    public func clearSlot(_ slot: Int) {
        if var existing = defaults?.data(forKey: "slot_\(slot)") {
            existing.withUnsafeMutableBytes { ptr in
                if let base = ptr.baseAddress, ptr.count > 0 {
                    _ = memset_s(base, ptr.count, 0, ptr.count)
                }
            }
        }
        defaults?.removeObject(forKey: "slot_\(slot)")
        defaults?.removeObject(forKey: "slot_ts_\(slot)")
        let name = CFNotificationName("com.cybrox.ratt.slotCleared" as CFString)
        CFNotificationCenterPostNotification(CFNotificationCenterGetDarwinNotifyCenter(), name, nil, nil, true)
    }

    public func clearAllSlots() {
        for slot in 1...10 {
            clearSlot(slot)
        }
    }

    /// Requirement 5: Empty and zero all slots in Keychain/App Group when the user exits the app.
    public func exitAndWipeAllSlots() {
        clearAllSlots()
        defaults?.synchronize()
    }

    // MARK: - iOS Keychain Master Key Management (`kSecAttrAccessibleWhenUnlockedThisDeviceOnly`)

    private func getOrCreateMasterKey() -> SymmetricKey? {
        var query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: keychainAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecSuccess, var keyData = item as? Data, keyData.count == 32 {
            let symKey = SymmetricKey(data: keyData)
            keyData.withUnsafeMutableBytes { ptr in
                if let base = ptr.baseAddress, ptr.count > 0 {
                    _ = memset_s(base, ptr.count, 0, ptr.count)
                }
            }
            return symKey
        }

        let newKey = SymmetricKey(size: .bits256)
        var keyData = newKey.withUnsafeBytes { Data($0) }
        defer {
            keyData.withUnsafeMutableBytes { ptr in
                if let base = ptr.baseAddress, ptr.count > 0 {
                    _ = memset_s(base, ptr.count, 0, ptr.count)
                }
            }
        }

        query.removeValue(forKey: kSecReturnData as String)
        query.removeValue(forKey: kSecMatchLimit as String)
        query[kSecValueData as String] = keyData
        query[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly

        SecItemDelete(query as CFDictionary)
        let addStatus = SecItemAdd(query as CFDictionary, nil)
        return addStatus == errSecSuccess ? newKey : nil
    }
}
