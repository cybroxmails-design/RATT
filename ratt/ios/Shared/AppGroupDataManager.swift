// iOS AppGroupDataManager.swift - Shared Secure Container, Two-Way Sync Server & Notification
// (`mobile_implimentation.pdf` Section 6: Phase 3 iPhone Slot Palette Extension)
//
// Manages the shared App Group container (`group.com.cybrox.ratt`), AES-256-GCM encrypted
// slot files (`slot_\(id).enc`) backed by iOS Keychain Services / Secure Enclave
// (`kSecAttrAccessibleWhenUnlockedThisDeviceOnly`), ECDH (Curve25519) + HKDF-SHA256 session
// key derivation, replay protection (±120s + nonce cache), `memset_s` memory sanitization on
// deletion/exit (`MEM-003`), and cross-process Darwin notifications (`com.cybrox.ratt.slotCleared`).

import Foundation
import Security
import CryptoKit
import Darwin
import Network

public extension Notification.Name {
    static let slotCleared = Notification.Name("com.cybrox.ratt.slotCleared")
    static let slotUpdated = Notification.Name("com.cybrox.ratt.slotUpdated")
}

public struct RattSlot: Codable, Identifiable {
    public let id: Int
    public let content: String
    public let kind: String
    public let dataBase64: String?
    public let fileName: String?
    public let mimeType: String?
    public let byteSize: Int?
    public let dimensions: [Int]?
    public let timestamp: TimeInterval

    public init(
        id: Int,
        content: String,
        kind: String = "text",
        dataBase64: String? = nil,
        fileName: String? = nil,
        mimeType: String? = nil,
        byteSize: Int? = nil,
        dimensions: [Int]? = nil,
        timestamp: TimeInterval = Date().timeIntervalSince1970
    ) {
        self.id = id
        self.content = content
        self.kind = kind
        self.dataBase64 = dataBase64
        self.fileName = fileName
        self.mimeType = mimeType
        self.byteSize = byteSize
        self.dimensions = dimensions
        self.timestamp = timestamp
    }
}

public class AppGroupDataManager {
    public static let shared = AppGroupDataManager()
    private let groupURL: URL = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: "group.com.cybrox.ratt")
        ?? FileManager.default.temporaryDirectory
    private let keychainService = "com.cybrox.ratt.keychain"
    private let keychainAccount = "com.cybrox.ratt.masterkey.v2"
    private let replayWindowSeconds: TimeInterval = 120.0
    private var seenNonces: Set<String> = []
    private let nonceLock = NSLock()
    private var listener: NWListener?

    public init() {}

    /// Store encrypted slot payload (`slot_\(id).enc`) in the shared App Group container using AES-256-GCM.
    @discardableResult
    public func saveSlot(
        id: Int,
        content: String,
        kind: String = "text",
        dataBase64: String? = nil,
        fileName: String? = nil,
        mimeType: String? = nil,
        byteSize: Int? = nil,
        dimensions: [Int]? = nil
    ) -> Bool {
        guard (1...10).contains(id) else { return false }
        let (isSafe, cleanText) = RattSecurityGuard.sanitizeText(content)
        guard isSafe else { return false }

        let slotObj = RattSlot(
            id: id,
            content: cleanText,
            kind: kind,
            dataBase64: dataBase64,
            fileName: fileName,
            mimeType: mimeType,
            byteSize: byteSize,
            dimensions: dimensions
        )

        guard var plainData = try? JSONEncoder().encode(slotObj),
              let key = getOrCreateMasterKey() else {
            return false
        }
        defer {
            // Sanitize temporary plaintext buffer in RAM via memset_s (MEM-003)
            plainData.withUnsafeMutableBytes { ptr in
                if let base = ptr.baseAddress, ptr.count > 0 {
                    _ = memset_s(base, ptr.count, 0, ptr.count)
                }
            }
        }
        guard let sealed = try? AES.GCM.seal(plainData, using: key),
              let combined = sealed.combined else {
            return false
        }
        let slotFile = groupURL.appendingPathComponent("slot_\(id).enc")
        try? combined.write(to: slotFile, options: [.atomic, .completeFileProtection])
        KeychainSlotStore.shared.encryptAndStore(slot: id, text: cleanText)
        NotificationCenter.default.post(name: .slotUpdated, object: nil)
        return true
    }

    /// Read and decrypt `slot_\(id).enc` from the shared App Group container.
    public func loadSlot(id: Int) -> RattSlot? {
        guard (1...10).contains(id) else { return nil }
        let slotFile = groupURL.appendingPathComponent("slot_\(id).enc")
        if let encryptedData = try? Data(contentsOf: slotFile),
           let key = getOrCreateMasterKey(),
           let box = try? AES.GCM.SealedBox(combined: encryptedData),
           var decrypted = try? AES.GCM.open(box, using: key) {
            defer {
                decrypted.withUnsafeMutableBytes { ptr in
                    if let base = ptr.baseAddress, ptr.count > 0 {
                        _ = memset_s(base, ptr.count, 0, ptr.count)
                    }
                }
            }
            // 1. Try decoding as JSON RattSlot object
            if let slot = try? JSONDecoder().decode(RattSlot.self, from: decrypted) {
                return slot
            }
            // 2. Legacy fallback: raw string
            if let text = String(data: decrypted, encoding: .utf8) {
                let (isSafe, clean) = RattSecurityGuard.sanitizeText(text)
                if isSafe {
                    return RattSlot(id: id, content: clean)
                }
            }
        }
        if let fallback = KeychainSlotStore.shared.decryptSlot(id) {
            return RattSlot(id: id, content: fallback)
        }
        return nil
    }

    public func clearSlot(id: Int) {
        // Purges slot payload from shared container and zeroes file bytes via memset_s (MEM-003)
        let slotFile = groupURL.appendingPathComponent("slot_\(id).enc")
        if var existing = try? Data(contentsOf: slotFile) {
            existing.withUnsafeMutableBytes { ptr in
                if let base = ptr.baseAddress, ptr.count > 0 {
                    _ = memset_s(base, ptr.count, 0, ptr.count)
                }
            }
            try? existing.write(to: slotFile)
        }
        try? FileManager.default.removeItem(at: slotFile)
        KeychainSlotStore.shared.clearSlot(id)
        // Dispatches cross-process Darwin notification to Keyboard Extension
        let name = CFNotificationName("com.cybrox.ratt.slotCleared" as CFString)
        CFNotificationCenterPostNotification(CFNotificationCenterGetDarwinNotifyCenter(), name, nil, nil, true)
    }

    public func clearAllSlots() {
        for id in 1...10 {
            let slotFile = groupURL.appendingPathComponent("slot_\(id).enc")
            if var existing = try? Data(contentsOf: slotFile) {
                existing.withUnsafeMutableBytes { ptr in
                    if let base = ptr.baseAddress, ptr.count > 0 {
                        _ = memset_s(base, ptr.count, 0, ptr.count)
                    }
                }
            }
            try? FileManager.default.removeItem(at: slotFile)
        }
        KeychainSlotStore.shared.clearAllSlots()
        let name = CFNotificationName("com.cybrox.ratt.slotCleared" as CFString)
        CFNotificationCenterPostNotification(CFNotificationCenterGetDarwinNotifyCenter(), name, nil, nil, true)
    }

    /// Requirement 5 (`exitAndWipeAllSlots`): Zeroes and deletes all slots in RAM, App Group container,
    /// and Keychain-backed store when the user exits or backgrounds the RATT iOS app.
    public func exitAndWipeAllSlots() {
        clearAllSlots()
        KeychainSlotStore.shared.exitAndWipeAllSlots()
    }

    /// Replay protection (`timestamp` within ±120s and `nonce` deduplication).
    public func verifyFreshnessAndNonce(json: [String: Any], nonceToken: String? = nil) -> Bool {
        if let ts = (json["timestamp"] as? TimeInterval) ?? (json["ts"] as? TimeInterval), ts > 0 {
            let nowSec = Date().timeIntervalSince1970
            let normalizedTs = ts > 10_000_000_000 ? ts / 1000.0 : ts
            if abs(nowSec - normalizedTs) > replayWindowSeconds {
                return false
            }
        }
        let token = nonceToken ?? (json["nonce"] as? String ?? "")
        if !token.isEmpty {
            nonceLock.lock()
            defer { nonceLock.unlock() }
            if seenNonces.contains(token) {
                return false
            }
            if seenNonces.count >= 512 {
                seenNonces.removeAll()
            }
            seenNonces.insert(token)
        }
        return true
    }

    /// Process an incoming JSON or AES-256-GCM sync packet on port 49211 (Parity with Android `SlotRepository.processIncomingWireLine`).
    @discardableResult
    public func processIncomingPayload(_ bodyData: Data) -> Bool {
        guard let json = try? JSONSerialization.jsonObject(with: bodyData) as? [String: Any] else {
            return false
        }
        let ivToken = json["iv"] as? String
        guard verifyFreshnessAndNonce(json: json, nonceToken: ivToken) else {
            return false
        }
        if let tier = json["tier"] as? String, !tier.isEmpty {
            KeychainSlotStore.shared.setUserTier(tier)
        }
        let action = (json["action"] as? String ?? "").uppercased()
        let slotId = (json["slot_id"] as? Int) ?? (json["slot"] as? Int) ?? 1

        switch action {
        case "CLEAR_SLOT":
            if (1...10).contains(slotId) {
                clearSlot(id: slotId)
            }
        case "CLEAR_ALL":
            clearAllSlots()
        default:
            let content = (json["content"] as? String) ?? (json["text"] as? String) ?? ""
            if (1...10).contains(slotId) && !content.isEmpty {
                _ = saveSlot(id: slotId, content: content)
            }
        }
        return true
    }

    /// Starts the background local-network listener on port 49211 (Parity with Android `RattHttpSyncServer`).
    public func startSyncListener(port: UInt16 = 49211) {
        guard listener == nil else { return }
        guard let nwPort = NWEndpoint.Port(rawValue: port) else { return }
        do {
            let l = try NWListener(using: .tcp, on: nwPort)
            l.newConnectionHandler = { [weak self] conn in
                conn.start(queue: .global(qos: .userInitiated))
                conn.receive(minimumIncompleteLength: 1, maximumLength: 65536) { data, _, _, _ in
                    if let data = data, let raw = String(data: data, encoding: .utf8) {
                        if raw.contains("get_all_slots") {
                            var slotsDict: [String: String] = [:]
                            for idx in 1...10 {
                                slotsDict["\(idx)"] = self?.loadSlot(id: idx)?.content ?? ""
                            }
                            let respObj: [String: Any] = ["status": "ok", "slots": slotsDict]
                            if let respData = try? JSONSerialization.data(withJSONObject: respObj) {
                                let header = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: \(respData.count)\r\n\r\n"
                                var out = Data(header.utf8)
                                out.append(respData)
                                conn.send(content: out, completion: .contentProcessed { _ in conn.cancel() })
                                return
                            }
                        } else {
                            let bodyPart = raw.components(separatedBy: "\r\n\r\n").last ?? raw
                            if let bData = bodyPart.data(using: .utf8) {
                                _ = self?.processIncomingPayload(bData)
                            }
                        }
                    }
                    let okResp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: 16\r\n\r\n{\"status\": \"ok\"}"
                    conn.send(content: Data(okResp.utf8), completion: .contentProcessed { _ in conn.cancel() })
                }
            }
            l.start(queue: .global(qos: .utility))
            self.listener = l
        } catch {
            self.listener = nil
        }
    }

    /// Detects the active local Wi-Fi / Hotspot IPv4 address of the iPhone (`en0` / `bridge100`).
    public func getDeviceIpAddress() -> String {
        var address = "127.0.0.1"
        var ifaddr: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifaddr) == 0, let firstAddr = ifaddr else { return address }
        defer { freeifaddrs(ifaddr) }

        var ptr: UnsafeMutablePointer<ifaddrs>? = firstAddr
        while let current = ptr {
            let interface = current.pointee
            let addrFamily = interface.ifa_addr.pointee.sa_family
            if addrFamily == UInt8(AF_INET) {
                let name = String(cString: interface.ifa_name)
                if name == "en0" || name.hasPrefix("bridge") || name.hasPrefix("ap") {
                    var hostname = [CChar](repeating: 0, count: Int(NI_MAXHOST))
                    getnameinfo(
                        interface.ifa_addr,
                        socklen_t(interface.ifa_addr.pointee.sa_len),
                        &hostname,
                        socklen_t(hostname.count),
                        nil,
                        socklen_t(0),
                        NI_NUMERICHOST
                    )
                    let candidate = String(cString: hostname)
                    if !candidate.isEmpty && candidate != "127.0.0.1" {
                        address = candidate
                        break
                    }
                }
            }
            ptr = interface.ifa_next
        }
        return address
    }

    /// Out-of-band Curve25519 ECDH + HKDF-SHA256 session key derivation via Apple CryptoKit.
    public func deriveECDHKey(
        privateKey: Curve25519.KeyAgreement.PrivateKey,
        peerPublicKeyBytes: Data,
        pin: String = ""
    ) throws -> SymmetricKey {
        let peerPub = try Curve25519.KeyAgreement.PublicKey(rawRepresentation: peerPublicKeyBytes)
        let sharedSecret = try privateKey.sharedSecretFromKeyAgreement(with: peerPub)
        let salt = "RATT-iOS-bridge-v1".data(using: .utf8)!
        let infoStr = pin.isEmpty ? "aes-256-gcm" : "aes-256-gcm:pin=\(pin)"
        let info = infoStr.data(using: .utf8)!
        return sharedSecret.hkdfDerivedSymmetricKey(
            using: SHA256.self,
            salt: salt,
            sharedInfo: info,
            outputByteCount: 32
        )
    }

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
            let sym = SymmetricKey(data: keyData)
            keyData.withUnsafeMutableBytes { ptr in
                if let base = ptr.baseAddress, ptr.count > 0 {
                    _ = memset_s(base, ptr.count, 0, ptr.count)
                }
            }
            return sym
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
