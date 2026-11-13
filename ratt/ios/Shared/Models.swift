// Models.swift — Shared Data Models for RATT v2 iOS (App Group: group.com.cybrox.ratt)
// Shared between RattApp (Container App) and RattKeyboard (UIInputViewController Extension).

import Foundation

public enum RattSlotKind: String, Codable {
    case text = "text"
    case link = "link"
    case image = "image"
    case diagram = "diagram"
    case files = "files"
}

public enum RattSlotAction: String, Codable {
    case copy = "copy"
    case cut = "cut"
}

public enum RattUserTier: String, Codable {
    case basic = "basic"
    case premium = "premium"
    case enterprise = "enterprise"

    public var isPaidEntitlement: Bool {
        return self == .premium || self == .enterprise
    }
}

public struct RattSlotPayload: Codable, Identifiable {
    public var id: Int { slotNumber }
    public let slotNumber: Int
    public let kind: RattSlotKind
    public let action: RattSlotAction
    public let text: String
    public let dataBase64: String?
    public let fileName: String?
    public let mimeType: String?
    public let byteSize: Int?
    public let dimensions: [Int]?
    public let timestamp: TimeInterval

    public init(
        slotNumber: Int,
        kind: RattSlotKind = .text,
        action: RattSlotAction = .copy,
        text: String,
        dataBase64: String? = nil,
        fileName: String? = nil,
        mimeType: String? = nil,
        byteSize: Int? = nil,
        dimensions: [Int]? = nil,
        timestamp: TimeInterval = Date().timeIntervalSince1970
    ) {
        self.slotNumber = slotNumber
        self.kind = kind
        self.action = action
        self.text = text
        self.dataBase64 = dataBase64
        self.fileName = fileName
        self.mimeType = mimeType
        self.byteSize = byteSize
        self.dimensions = dimensions
        self.timestamp = timestamp
    }
}

public struct RattSyncPacket: Codable {
    public let slot: Int
    public let kind: String
    public let action: String
    public let text: String
    public let tier: String
    public let dataBase64: String?
    public let fileName: String?
    public let mimeType: String?
    public let byteSize: Int?
    public let dimensions: [Int]?

    public init(
        slot: Int,
        kind: String = "text",
        action: String = "copy",
        text: String,
        tier: String = "premium",
        dataBase64: String? = nil,
        fileName: String? = nil,
        mimeType: String? = nil,
        byteSize: Int? = nil,
        dimensions: [Int]? = nil
    ) {
        self.slot = slot
        self.kind = kind
        self.action = action
        self.text = text
        self.tier = tier
        self.dataBase64 = dataBase64
        self.fileName = fileName
        self.mimeType = mimeType
        self.byteSize = byteSize
        self.dimensions = dimensions
    }
}
