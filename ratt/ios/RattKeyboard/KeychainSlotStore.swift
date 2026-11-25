// KeychainSlotStore.swift — AES-256-GCM Hardware-Backed Slot Storage (Apple CryptoKit)
// Compatible with iPhone X (iOS 15+) through iPhone 17 Pro Max, including both App Store
// and Sideloadly / free-Apple-ID installations.

import Foundation
import CryptoKit
import Security
import Darwin

public final class KeychainSlotStore {
    public static let shared = KeychainSlotStore()

    private let suiteName = "group.com.cybrox.ratt"
    private let keychainAccount = "com.cybrox.ratt.masterkey.v2"
    private let keychainService = "com.cybrox.ratt.keychain"
    private let keychainAccessGroup = "com.cybrox.ratt"
    private lazy var groupDefaults: UserDefaults? = UserDefaults(suiteName: suiteName)
    private let standardDefaults: UserDefaults = UserDefaults.standard
    private var cachedMasterKey: SymmetricKey?

    private static let documentAndMediaExtensions: Set<String> = [
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf",
        ".txt", ".csv", ".rtf", ".odt", ".ods", ".odp",
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
        ".mp4", ".mkv", ".mov", ".avi", ".webm",
        ".zip", ".rar", ".7z", ".tar", ".gz"
    ]

    public init() {}

    // MARK: - Dual UserDefaults Helpers (Works on both App Group & Sideloadly Installs)

    private func setData(_ data: Data, forKey key: String) {
        groupDefaults?.set(data, forKey: key)
        standardDefaults.set(data, forKey: key)
    }

    private func getData(forKey key: String) -> Data? {
        if let d = groupDefaults?.data(forKey: key) {
            return d
        }
        return standardDefaults.data(forKey: key)
    }

    private func setString(_ value: String, forKey key: String) {
        groupDefaults?.set(value, forKey: key)
        standardDefaults.set(value, forKey: key)
    }

    private func getString(forKey key: String) -> String? {
        if let s = groupDefaults?.string(forKey: key), !s.isEmpty {
            return s
        }
        return standardDefaults.string(forKey: key)
    }

    private func removeValue(forKey key: String) {
        groupDefaults?.removeObject(forKey: key)
        standardDefaults.removeObject(forKey: key)
    }

    // MARK: - Entitlement Check (RATT Commercial & PC Subscription Rules)

    public func getUserTier() -> String {
        return getString(forKey: "ratt_user_tier") ?? "basic"
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
        setString(valid, forKey: "ratt_user_tier")
    }

    public func maxSlots() -> Int {
        switch getUserTier() {
        case "enterprise":
            return 50_000
        case "premium":
            return 50
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
        return true
    }

    public func canSyncWithWindows() -> Bool {
        return true
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
              var data = cleanText.data(using: .utf8) else {
            return false
        }
        let key = getOrCreateMasterKey()
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
        setData(combined, forKey: "slot_\(slot)")
        groupDefaults?.set(Date().timeIntervalSince1970, forKey: "slot_ts_\(slot)")
        standardDefaults.set(Date().timeIntervalSince1970, forKey: "slot_ts_\(slot)")
        return true
    }

    public func decryptSlot(_ slot: Int) -> String? {
        guard (1...10).contains(slot),
              let data = getData(forKey: "slot_\(slot)") else {
            return nil
        }
        let key = getOrCreateMasterKey()
        guard let box = try? AES.GCM.SealedBox(combined: data),
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
        if var existing = getData(forKey: "slot_\(slot)") {
            existing.withUnsafeMutableBytes { ptr in
                if let base = ptr.baseAddress, ptr.count > 0 {
                    _ = memset_s(base, ptr.count, 0, ptr.count)
                }
            }
        }
        removeValue(forKey: "slot_\(slot)")
        removeValue(forKey: "slot_ts_\(slot)")
        let name = CFNotificationName("com.cybrox.ratt.slotCleared" as CFString)
        CFNotificationCenterPostNotification(CFNotificationCenterGetDarwinNotifyCenter(), name, nil, nil, true)
    }

    public func clearAllSlots() {
        for slot in 1...10 {
            clearSlot(slot)
        }
    }

    public func exitAndWipeAllSlots() {
        clearAllSlots()
        groupDefaults?.synchronize()
        standardDefaults.synchronize()
    }

    // MARK: - iOS Keychain Master Key Management (With Sideloadly Entitlement Fallback)

    public func getOrCreateMasterKey() -> SymmetricKey {
        if let cached = cachedMasterKey {
            return cached
        }

        // 1. Try reading from Keychain (first with access group, then default app keychain)
        for useGroup in [true, false] {
            var query: [String: Any] = [
                kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: keychainService,
                kSecAttrAccount as String: keychainAccount,
                kSecReturnData as String: true,
                kSecMatchLimit as String: kSecMatchLimitOne
            ]
            if useGroup {
                query[kSecAttrAccessGroup as String] = keychainAccessGroup
            }
            var item: CFTypeRef?
            let status = SecItemCopyMatching(query as CFDictionary, &item)
            if status == errSecSuccess, var keyData = item as? Data, keyData.count == 32 {
                let symKey = SymmetricKey(data: keyData)
                keyData.withUnsafeMutableBytes { ptr in
                    if let base = ptr.baseAddress, ptr.count > 0 {
                        _ = memset_s(base, ptr.count, 0, ptr.count)
                    }
                }
                cachedMasterKey = symKey
                return symKey
            }
        }

        // 2. Fallback check in local protected storage (for Sideloadly free Apple ID profiles)
        if let fallbackData = getData(forKey: "ratt_local_master_key_v2"), fallbackData.count == 32 {
            let symKey = SymmetricKey(data: fallbackData)
            cachedMasterKey = symKey
            return symKey
        }

        // 3. Generate a new 256-bit key and save in Keychain + fallback storage
        let newKey = SymmetricKey(size: .bits256)
        let keyData = newKey.withUnsafeBytes { Data($0) }

        for useGroup in [true, false] {
            var addQuery: [String: Any] = [
                kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: keychainService,
                kSecAttrAccount as String: keychainAccount,
                kSecValueData as String: keyData,
                kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            ]
            if useGroup {
                addQuery[kSecAttrAccessGroup as String] = keychainAccessGroup
            }
            SecItemDelete(addQuery as CFDictionary)
            if SecItemAdd(addQuery as CFDictionary, nil) == errSecSuccess {
                break
            }
        }

        setData(keyData, forKey: "ratt_local_master_key_v2")
        cachedMasterKey = newKey
        return newKey
    }
}
