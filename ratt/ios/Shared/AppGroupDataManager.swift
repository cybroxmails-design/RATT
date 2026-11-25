// iOS AppGroupDataManager.swift - Shared Secure Container, Two-Way Sync Server & Notification
// Compatible with iPhone X (iOS 15+) through iPhone 17 Pro Max, including Sideloadly installs.
// Features:
// 1. Multi-Packet TCP HTTP Assembler (`Content-Length` byte reader) on BOTH ports 49211 and 49210
//    so Android `HttpURLConnection` and PC `urllib` POST bodies are never dropped.
// 2. Synchronous Pasteboard Carrier (`com.cybrox.ratt.allslots.json`) so clearing a slot with 'X'
//    never resurrects the deleted slot from the pasteboard.

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
    private let syncTokenAccount = "com.cybrox.ratt.synctoken.v2"
    private let replayWindowSeconds: TimeInterval = 86400.0
    private var seenNonces: [String: TimeInterval] = [:]
    private let nonceLock = NSLock()
    private var listeners: [UInt16: NWListener] = [:]

    public init() {}

    /// Synchronously (when on main thread) updates `UIPasteboard.general` with the active paste slot text
    /// AND the JSON dictionary of all filled slots for the RATT Keyboard Extension.
    public func syncPasteboardCarrier(activeSlotId: Int? = nil, explicitActiveText: String? = nil) {
        let work = {
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
            if activeText.isEmpty, let firstFilled = slotsDict.keys.sorted().first {
                activeText = slotsDict[firstFilled] ?? ""
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
            } else {
                item["public.utf8-plain-text"] = ""
            }
            UIPasteboard.general.items = [item]
        }

        if Thread.isMainThread {
            work()
        } else {
            DispatchQueue.main.async(execute: work)
        }
    }

    /// Reads all filled slots from the pasteboard carrier (used ONLY by RATT Keyboard Extension).
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
        // Clear any slot that is empty in the carrier, and store any slot that has data
        for sId in 1...10 {
            let val = slots["\(sId)"] ?? ""
            if !val.isEmpty {
                imported[sId] = val
                _ = KeychainSlotStore.shared.encryptAndStore(slot: sId, text: val)
            } else {
                KeychainSlotStore.shared.clearSlot(sId)
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
        return true
    }

    /// Read and decrypt `slot_\(id).enc` from the container or KeychainSlotStore fallback.
    /// Does NOT re-import from pasteboard carrier so cleared slots never resurrect!
    public func loadSlot(id: Int) -> RattSlot? {
        guard (1...10).contains(id) else { return nil }
        if let fallback = KeychainSlotStore.shared.decryptSlot(id), !fallback.isEmpty {
            return RattSlot(id: id, content: fallback)
        }
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
                if let slot = try? JSONDecoder().decode(RattSlot.self, from: decrypted), !slot.content.isEmpty {
                    return slot
                }
                if let text = String(data: decrypted, encoding: .utf8) {
                    let (isSafe, clean) = RattSecurityGuard.sanitizeText(text)
                    if isSafe && !clean.isEmpty {
                        return RattSlot(id: id, content: clean)
                    }
                }
            }
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

    /// Process an incoming JSON sync packet from PC or Android.
    @discardableResult
    public func processIncomingPayload(_ bodyData: Data, peerIp: String? = nil) -> Bool {
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
            } else if let remoteIp = peerIp, !remoteIp.isEmpty, remoteIp != "127.0.0.1" {
                UserDefaults.standard.set(remoteIp, forKey: "paired_android_ip")
            }
            if let andIp = json["android_ip"] as? String, !andIp.isEmpty {
                UserDefaults.standard.set(andIp, forKey: "paired_android_ip")
            }
            DispatchQueue.main.async {
                NotificationCenter.default.post(name: .slotUpdated, object: nil)
            }
            return true
        }

        if action == "SYNC_FROM_ANDROID", let remoteIp = peerIp, !remoteIp.isEmpty, remoteIp != "127.0.0.1" {
            UserDefaults.standard.set(remoteIp, forKey: "paired_android_ip")
        }

        let slotId = (json["slot_id"] as? Int) ?? (json["slot"] as? Int) ?? 1

        switch action {
        case "CLEAR_SLOT":
            if (1...10).contains(slotId) {
                clearSlot(id: slotId)
                DispatchQueue.main.async {
                    NotificationCenter.default.post(name: .slotCleared, object: nil)
                }
            }
        case "CLEAR_ALL":
            clearAllSlots()
            DispatchQueue.main.async {
                NotificationCenter.default.post(name: .slotCleared, object: nil)
            }
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
                    if activeSlot == slotId || activeSlot == 0 {
                        UserDefaults.standard.set(slotId, forKey: "ratt_active_paste_slot")
                        self.syncPasteboardCarrier(activeSlotId: slotId, explicitActiveText: content)
                    } else {
                        self.syncPasteboardCarrier()
                    }
                    NotificationCenter.default.post(name: .slotUpdated, object: nil)
                }
            }
        }
        return true
    }

    /// Starts the local-network HTTP server on BOTH port 49211 and port 49210 so neither Android nor PC can miss it.
    public func startSyncListener(port: UInt16 = 49211) {
        for p in [UInt16(49211), UInt16(49210)] {
            if listeners[p] != nil { continue }
            guard let nwPort = NWEndpoint.Port(rawValue: p) else { continue }
            do {
                let l = try NWListener(using: .tcp, on: nwPort)
                l.newConnectionHandler = { [weak self] conn in
                    conn.start(queue: .global(qos: .userInitiated))
                    self?.receiveHttpRequest(conn: conn, accumulated: Data())
                }
                l.start(queue: .global(qos: .utility))
                listeners[p] = l
            } catch {
                // Ignore if port already bound
            }
        }
    }

    /// Multi-packet TCP HTTP request assembler that waits until full `Content-Length` body bytes arrive.
    private func receiveHttpRequest(conn: NWConnection, accumulated: Data) {
        conn.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] chunk, _, isComplete, error in
            guard let self = self else {
                conn.cancel()
                return
            }
            var buffer = accumulated
            if let chunk = chunk, !chunk.isEmpty {
                buffer.append(chunk)
            }

            let separator = Data("\r\n\r\n".utf8)
            if let sepRange = buffer.range(of: separator) {
                let headerData = buffer.subdata(in: 0..<sepRange.lowerBound)
                let bodyData = buffer.subdata(in: sepRange.upperBound..<buffer.count)
                let headerStr = String(data: headerData, encoding: .utf8) ?? ""

                var contentLength = 0
                var suppliedToken = ""
                for line in headerStr.components(separatedBy: "\r\n").dropFirst() {
                    if let colon = line.firstIndex(of: ":") {
                        let k = line[..<colon].trimmingCharacters(in: .whitespaces).lowercased()
                        let v = line[line.index(after: colon)...].trimmingCharacters(in: .whitespaces)
                        if k == "content-length", let cl = Int(v) {
                            contentLength = cl
                        } else if k == "x-ratt-token" {
                            suppliedToken = v
                        }
                    }
                }

                // If full HTTP body hasn't arrived yet and connection is still open, keep receiving!
                if bodyData.count < contentLength && !isComplete && error == nil && buffer.count < 524288 {
                    self.receiveHttpRequest(conn: conn, accumulated: buffer)
                    return
                }

                self.handleCompleteHttpRequest(
                    conn: conn,
                    headerBlock: headerStr,
                    bodyData: bodyData,
                    suppliedToken: suppliedToken
                )
                return
            }

            if !isComplete && error == nil && buffer.count < 65536 {
                self.receiveHttpRequest(conn: conn, accumulated: buffer)
            } else {
                conn.cancel()
            }
        }
    }

    private func extractPeerIp(from conn: NWConnection) -> String? {
        if case let .hostPort(host, _) = conn.endpoint {
            let raw = "\(host)"
            return raw.components(separatedBy: "%").first
        }
        return nil
    }

    private func handleCompleteHttpRequest(
        conn: NWConnection,
        headerBlock: String,
        bodyData: Data,
        suppliedToken: String
    ) {
        let peerIp = extractPeerIp(from: conn)
        if !suppliedToken.isEmpty {
            self.setSyncToken(suppliedToken)
        }

        if headerBlock.contains("/pair") {
            if !bodyData.isEmpty {
                _ = self.processIncomingPayload(bodyData, peerIp: peerIp)
            } else if let remoteIp = peerIp, !remoteIp.isEmpty, remoteIp != "127.0.0.1" {
                UserDefaults.standard.set(remoteIp, forKey: "paired_android_ip")
            }
            var slotsDict: [String: String] = [:]
            for idx in 1...10 {
                slotsDict["\(idx)"] = self.loadSlot(id: idx)?.content ?? ""
            }
            let tok = self.getOrCreateSyncToken()
            let respObj: [String: Any] = [
                "status": "ok",
                "sync_token": tok,
                "slots": slotsDict
            ]
            if let respData = try? JSONSerialization.data(withJSONObject: respObj) {
                let header = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: \(respData.count)\r\n\r\n"
                var out = Data(header.utf8)
                out.append(respData)
                conn.send(content: out, completion: .contentProcessed { _ in conn.cancel() })
                return
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
        }

        if !bodyData.isEmpty {
            _ = self.processIncomingPayload(bodyData, peerIp: peerIp)
        }
        let okResp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: 16\r\n\r\n{\"status\": \"ok\"}"
        conn.send(content: Data(okResp.utf8), completion: .contentProcessed { _ in conn.cancel() })
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
