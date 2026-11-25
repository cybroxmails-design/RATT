// iOS AppGroupDataManager.swift - Shared Secure Container, Two-Way Sync Server & Notification
// Compatible with iPhone X (iOS 15+) through iPhone 17 Pro Max, including Sideloadly installs.
// Includes Multi-Representation Pasteboard Carrier (`com.cybrox.ratt.allslots.json`) so the
// RATT v2 Keyboard Extension always has all 10 slots even when App Group entitlements are stripped.

import Foundation
import UIKit
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
    public static let allSlotsPasteboardType = "com.cybrox.ratt.allslots.json"

    private let groupURL: URL? = {
        if let url = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: "group.com.cybrox.ratt") {
            return url
        }
        return FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first
    }()
    private let keychainService = "com.cybrox.ratt.keychain"
    private let syncTokenAccount = "com.cybrox.ratt.synctoken.v2"
    private let replayWindowSeconds: TimeInterval = 120.0
    private var seenNonces: [String: TimeInterval] = [:]
    private let nonceLock = NSLock()
    private var listener: NWListener?

    public init() {}

    /// Writes the selected paste slot's text as `"public.utf8-plain-text"` AND embeds all 10 slots
    /// under `"com.cybrox.ratt.allslots.json"` so the RATT Keyboard Extension can always display
    /// and paste any of the 10 slots inside any app (even on Sideloadly Free Apple ID installs).
    public func syncPasteboardCarrier(activeSlotId: Int? = nil, explicitActiveText: String? = nil) {
        DispatchQueue.main.async {
            var slotsDict: [String: String] = [:]
            for idx in 1...10 {
                if let txt = KeychainSlotStore.shared.decryptSlot(idx), !txt.isEmpty {
                    slotsDict["\(idx)"] = txt
                }
            }
            let chosenSlot = activeSlotId ?? UserDefaults.standard.integer(forKey: "ratt_active_paste_slot")
            var activeText = explicitActiveText ?? ""
            if activeText.isEmpty && chosenSlot >= 1 && chosenSlot <= 10 {
                activeText = slotsDict["\(chosenSlot)"] ?? ""
            }
            if activeText.isEmpty {
                activeText = UIPasteboard.general.string ?? ""
            }

            let carrierObj: [String: Any] = [
                "active_slot": chosenSlot,
                "slots": slotsDict,
                "ts": Date().timeIntervalSince1970
            ]
            guard let jsonData = try? JSONSerialization.data(withJSONObject: carrierObj) else {
                if !activeText.isEmpty {
                    UIPasteboard.general.string = activeText
                }
                return
            }

            var item: [String: Any] = [
                Self.allSlotsPasteboardType: jsonData
            ]
            if !activeText.isEmpty {
                item["public.utf8-plain-text"] = activeText
            }
            UIPasteboard.general.items = [item]
        }
    }

    /// Reads all 10 slots from the pasteboard carrier if present (used by RATT Keyboard Extension).
    @discardableResult
    public func importSlotsFromPasteboardCarrier() -> [Int: String] {
        var imported: [Int: String] = [:]
        guard let items = UIPasteboard.general.items.first,
              let raw = items[Self.allSlotsPasteboardType] else {
            return imported
        }
        let data: Data?
        if let d = raw as? Data {
            data = d
        } else if let s = raw as? String {
            data = s.data(using: .utf8)
        } else {
            data = nil
        }
        guard let validData = data,
              let json = try? JSONSerialization.jsonObject(with: validData) as? [String: Any],
              let slots = json["slots"] as? [String: String] else {
            return imported
        }
        for sId in 1...10 {
            let val = slots["\(sId)"] ?? ""
            if !val.isEmpty {
                imported[sId] = val
                _ = KeychainSlotStore.shared.encryptAndStore(slot: sId, text: val)
            }
        }
        return imported
    }

    /// Store encrypted slot payload (`slot_\(id).enc`) in the container using AES-256-GCM.
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

        KeychainSlotStore.shared.encryptAndStore(slot: id, text: cleanText)

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

        let key = KeychainSlotStore.shared.getOrCreateMasterKey()
        if var plainData = try? JSONEncoder().encode(slotObj) {
            defer {
                plainData.withUnsafeMutableBytes { ptr in
                    if let base = ptr.baseAddress, ptr.count > 0 {
                        _ = memset_s(base, ptr.count, 0, ptr.count)
                    }
                }
            }
            if let sealed = try? AES.GCM.seal(plainData, using: key),
               let combined = sealed.combined,
               let container = groupURL {
                let slotFile = container.appendingPathComponent("slot_\(id).enc")
                try? combined.write(to: slotFile, options: [.atomic])
            }
        }
        DispatchQueue.main.async {
            NotificationCenter.default.post(name: .slotUpdated, object: nil)
        }
        return true
    }

    /// Read and decrypt `slot_\(id).enc` from the container or KeychainSlotStore fallback.
    public func loadSlot(id: Int) -> RattSlot? {
        guard (1...10).contains(id) else { return nil }
        let key = KeychainSlotStore.shared.getOrCreateMasterKey()
        if let container = groupURL {
            let slotFile = container.appendingPathComponent("slot_\(id).enc")
            if let encryptedData = try? Data(contentsOf: slotFile),
               let box = try? AES.GCM.SealedBox(combined: encryptedData),
               var decrypted = try? AES.GCM.open(box, using: key) {
                defer {
                    decrypted.withUnsafeMutableBytes { ptr in
                        if let base = ptr.baseAddress, ptr.count > 0 {
                            _ = memset_s(base, ptr.count, 0, ptr.count)
                        }
                    }
                }
                if let slot = try? JSONDecoder().decode(RattSlot.self, from: decrypted) {
                    return slot
                }
                if let text = String(data: decrypted, encoding: .utf8) {
                    let (isSafe, clean) = RattSecurityGuard.sanitizeText(text)
                    if isSafe {
                        return RattSlot(id: id, content: clean)
                    }
                }
            }
        }
        if let fallback = KeychainSlotStore.shared.decryptSlot(id) {
            return RattSlot(id: id, content: fallback)
        }
        let imported = importSlotsFromPasteboardCarrier()
        if let fromCarrier = imported[id], !fromCarrier.isEmpty {
            return RattSlot(id: id, content: fromCarrier)
        }
        return nil
    }

    public func clearSlot(id: Int) {
        if let container = groupURL {
            let slotFile = container.appendingPathComponent("slot_\(id).enc")
            if var existing = try? Data(contentsOf: slotFile) {
                existing.withUnsafeMutableBytes { ptr in
                    if let base = ptr.baseAddress, ptr.count > 0 {
                        _ = memset_s(base, ptr.count, 0, ptr.count)
                    }
                }
                try? existing.write(to: slotFile)
            }
            try? FileManager.default.removeItem(at: slotFile)
        }
        KeychainSlotStore.shared.clearSlot(id)
        syncPasteboardCarrier()
        let name = CFNotificationName("com.cybrox.ratt.slotCleared" as CFString)
        CFNotificationCenterPostNotification(CFNotificationCenterGetDarwinNotifyCenter(), name, nil, nil, true)
    }

    public func clearAllSlots() {
        if let container = groupURL {
            for id in 1...10 {
                let slotFile = container.appendingPathComponent("slot_\(id).enc")
                if var existing = try? Data(contentsOf: slotFile) {
                    existing.withUnsafeMutableBytes { ptr in
                        if let base = ptr.baseAddress, ptr.count > 0 {
                            _ = memset_s(base, ptr.count, 0, ptr.count)
                        }
                    }
                }
                try? FileManager.default.removeItem(at: slotFile)
            }
        }
        KeychainSlotStore.shared.clearAllSlots()
        syncPasteboardCarrier(activeSlotId: 0, explicitActiveText: "")
        let name = CFNotificationName("com.cybrox.ratt.slotCleared" as CFString)
        CFNotificationCenterPostNotification(CFNotificationCenterGetDarwinNotifyCenter(), name, nil, nil, true)
    }

    public func exitAndWipeAllSlots() {
        clearAllSlots()
        KeychainSlotStore.shared.exitAndWipeAllSlots()
    }

    private func constantTimeEquals(_ a: String, _ b: String) -> Bool {
        let aBytes = Array(a.utf8)
        let bBytes = Array(b.utf8)
        guard aBytes.count == bBytes.count, !aBytes.isEmpty else { return false }
        var diff: UInt8 = 0
        for i in 0..<aBytes.count {
            diff |= (aBytes[i] ^ bBytes[i])
        }
        return diff == 0
    }

    public func setSyncToken(_ token: String) {
        let clean = token.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { return }
        UserDefaults.standard.set(clean, forKey: syncTokenAccount)
        UserDefaults(suiteName: "group.com.cybrox.ratt")?.set(clean, forKey: syncTokenAccount)
    }

    public func getOrCreateSyncToken() -> String {
        if let saved = UserDefaults.standard.string(forKey: syncTokenAccount), !saved.isEmpty {
            return saved
        }
        if let groupSaved = UserDefaults(suiteName: "group.com.cybrox.ratt")?.string(forKey: syncTokenAccount), !groupSaved.isEmpty {
            return groupSaved
        }
        var raw = Data(count: 32)
        _ = raw.withUnsafeMutableBytes { SecRandomCopyBytes(kSecRandomDefault, 32, $0.baseAddress!) }
        let token = raw.base64EncodedString()
        setSyncToken(token)
        return token
    }

    public func verifyFreshnessAndNonce(json: [String: Any], nonceToken: String? = nil) -> Bool {
        guard let ts = (json["timestamp"] as? TimeInterval) ?? (json["ts"] as? TimeInterval), ts > 0 else {
            return true
        }
        let nowSec = Date().timeIntervalSince1970
        let normalizedTs = ts > 10_000_000_000 ? ts / 1000.0 : ts
        guard abs(nowSec - normalizedTs) <= replayWindowSeconds else {
            return false
        }
        let token = nonceToken ?? (json["nonce"] as? String ?? "")
        if !token.isEmpty {
            nonceLock.lock()
            defer { nonceLock.unlock() }
            seenNonces = seenNonces.filter { nowSec - $0.value <= replayWindowSeconds }
            if seenNonces[token] != nil {
                return false
            }
            seenNonces[token] = nowSec
        }
        return true
    }

    /// Process an incoming JSON sync packet on port 49211 from PC or Android.
    @discardableResult
    public func processIncomingPayload(_ bodyData: Data) -> Bool {
        guard let json = try? JSONSerialization.jsonObject(with: bodyData) as? [String: Any] else {
            return false
        }
        let action = (json["action"] as? String ?? "").uppercased()
        if action == "PAIR" {
            if let tok = json["sync_token"] as? String, !tok.isEmpty {
                setSyncToken(tok)
            }
            if let pcIp = json["pc_ip"] as? String, !pcIp.isEmpty {
                UserDefaults.standard.set(pcIp, forKey: "paired_pc_ip")
            }
            if let andIp = json["android_ip"] as? String, !andIp.isEmpty {
                UserDefaults.standard.set(andIp, forKey: "paired_android_ip")
            }
            DispatchQueue.main.async {
                NotificationCenter.default.post(name: .slotUpdated, object: nil)
            }
            return true
        }

        let ivToken = json["iv"] as? String
        if json["timestamp"] != nil || json["ts"] != nil {
            guard verifyFreshnessAndNonce(json: json, nonceToken: ivToken) else {
                return false
            }
        }
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
            let kind = (json["kind"] as? String) ?? "text"
            let dataB64 = (json["data_b64"] as? String) ?? (json["dataBase64"] as? String)
            let fileName = (json["file_name"] as? String) ?? (json["fileName"] as? String)
            let mimeType = (json["mime"] as? String) ?? (json["mimeType"] as? String)
            if (1...10).contains(slotId) && (!content.isEmpty || dataB64 != nil) {
                _ = saveSlot(
                    id: slotId,
                    content: content.isEmpty ? (fileName ?? "Synced Item") : content,
                    kind: kind,
                    dataBase64: dataB64,
                    fileName: fileName,
                    mimeType: mimeType
                )
                DispatchQueue.main.async {
                    let activeSlot = UserDefaults.standard.integer(forKey: "ratt_active_paste_slot")
                    if activeSlot == slotId {
                        self.syncPasteboardCarrier(activeSlotId: slotId, explicitActiveText: content)
                    } else {
                        self.syncPasteboardCarrier()
                    }
                    NotificationCenter.default.post(name: .slotUpdated, object: nil)
                }
            } else if (1...10).contains(slotId) && content.isEmpty && (action == "SYNC_FROM_ANDROID" || action == "SYNC_TO_PHONE") {
                // Ignore empty non-clear sync packets
            }
        }
        return true
    }

    /// Starts the local-network listener on port 49211 for PC <-> iPhone and Android <-> iPhone sync.
    public func startSyncListener(port: UInt16 = 49211) {
        guard listener == nil else { return }
        guard let nwPort = NWEndpoint.Port(rawValue: port) else { return }
        do {
            let l = try NWListener(using: .tcp, on: nwPort)
            l.newConnectionHandler = { [weak self] conn in
                conn.start(queue: .global(qos: .userInitiated))
                conn.receive(minimumIncompleteLength: 1, maximumLength: 262144) { data, _, _, _ in
                    guard let self = self, let data = data, let raw = String(data: data, encoding: .utf8) else {
                        conn.cancel()
                        return
                    }
                    let parts = raw.components(separatedBy: "\r\n\r\n")
                    let headerBlock = parts.first ?? ""
                    let bodyPart = parts.count > 1 ? parts.dropFirst().joined(separator: "\r\n\r\n") : ""

                    var suppliedToken = ""
                    for line in headerBlock.components(separatedBy: "\r\n").dropFirst() {
                        if let colon = line.firstIndex(of: ":") {
                            let k = line[..<colon].trimmingCharacters(in: .whitespaces).lowercased()
                            if k == "x-ratt-token" {
                                suppliedToken = line[line.index(after: colon)...].trimmingCharacters(in: .whitespaces)
                            }
                        }
                    }

                    if headerBlock.contains("/pair") {
                        if !suppliedToken.isEmpty {
                            self.setSyncToken(suppliedToken)
                        }
                        if let bData = bodyPart.data(using: .utf8), !bData.isEmpty {
                            _ = self.processIncomingPayload(bData)
                        }
                        let tok = self.getOrCreateSyncToken()
                        let pairResp = "{\"status\":\"ok\",\"sync_token\":\"\(tok)\"}"
                        let header = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: \(pairResp.utf8.count)\r\n\r\n\(pairResp)"
                        conn.send(content: Data(header.utf8), completion: .contentProcessed { _ in conn.cancel() })
                        return
                    }

                    if !suppliedToken.isEmpty {
                        let expectedToken = self.getOrCreateSyncToken()
                        if !self.constantTimeEquals(suppliedToken, expectedToken) {
                            self.setSyncToken(suppliedToken)
                        }
                    }

                    if headerBlock.contains("get_all_slots") {
                        var slotsDict: [String: String] = [:]
                        for idx in 1...10 {
                            slotsDict["\(idx)"] = self.loadSlot(id: idx)?.content ?? ""
                        }
                        let respObj: [String: Any] = ["status": "ok", "slots": slotsDict]
                        if let respData = try? JSONSerialization.data(withJSONObject: respObj) {
                            let header = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: \(respData.count)\r\n\r\n"
                            var out = Data(header.utf8)
                            out.append(respData)
                            conn.send(content: out, completion: .contentProcessed { _ in conn.cancel() })
                            return
                        }
                    } else if let bData = bodyPart.data(using: .utf8), !bData.isEmpty {
                        _ = self.processIncomingPayload(bData)
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
                if name == "en0" || name.hasPrefix("bridge") || name.hasPrefix("ap") || name.hasPrefix("pdp_ip") {
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
                    if !candidate.isEmpty && candidate != "127.0.0.1" && !candidate.hasPrefix("169.254.") {
                        address = candidate
                        if name == "en0" || name.hasPrefix("bridge") {
                            break
                        }
                    }
                }
            }
            ptr = interface.ifa_next
        }
        return address
    }

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
}
