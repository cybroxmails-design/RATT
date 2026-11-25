// ContentView.swift — RATT v2 for iOS Container App (iPhone X through iPhone 17 Pro Max)
// Full Feature Parity with RATT Android & PC:
// 1. Compatible with iPhone X (iOS 15/16) and all newer iPhones up to iPhone 17 Pro Max
// 2. Choose Any Slot (1–10) to Paste:
//    - Dedicated "CHOOSE SLOT TO PASTE (1–10)" Picker & 10-Slot Quick-Paste Grid
//    - Tap any slot (or its "Paste This" button) to load THAT chosen slot into the iPhone Clipboard
//    - Active Paste Slot badge ("✓ ACTIVE") clearly shows which slot is currently ready to paste
// 3. Touch anywhere outside text fields to minimize keyboard + dedicated Hide Keyboard button
// 4. Direct Wi-Fi Pairing & Two-Way Sync with RATT PC (ports 49211 / 49210)

import SwiftUI
import UIKit

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3:
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

public struct ContentView: View {
    private let PC_SLOT_COLORS: [Color] = [
        Color(hex: "#00BFFF"), // Slot 1: Deep Cyan
        Color(hex: "#10B981"), // Slot 2: Emerald Green
        Color(hex: "#F59E0B"), // Slot 3: Amber / Orange
        Color(hex: "#8B5CF6"), // Slot 4: Purple
        Color(hex: "#EC4899"), // Slot 5: Pink
        Color(hex: "#3B82F6"), // Slot 6: Royal Blue
        Color(hex: "#14B8A6"), // Slot 7: Teal
        Color(hex: "#EF4444"), // Slot 8: Coral Red
        Color(hex: "#EAB308"), // Slot 9: Yellow Gold
        Color(hex: "#06B6D4")  // Slot 10: Neon Cyan
    ]

    @State private var userTier: RattUserTier = .basic
    @State private var slotPreviews: [Int: String] = [:]
    @State private var activePasteSlot: Int = 0
    @State private var lastSavedTexts: Set<String> = []
    @State private var directInputText: String = ""
    @State private var statusMessage: String = "RATT v2 Ready • Choose any slot (1–10) below to paste"
    @State private var statusIsSuccess: Bool = true
    @State private var showUpgradeAlert: Bool = false
    @State private var upgradeReason: String = ""
    @State private var showPairDialog: Bool = false
    @State private var pairIpDraft: String = ""
    @State private var showSaveSlotSheet: Bool = false
    @State private var showPasteSlotSheet: Bool = false
    @State private var showCrossSyncAlert: Bool = false
    @State private var crossSyncTarget: String = ""
    @State private var pcIpAddress: String = ""
    @State private var iphoneIpAddress: String = ""

    private let store = KeychainSlotStore.shared
    private let dataManager = AppGroupDataManager.shared

    public init() {}

    /// Dismiss the iOS on-screen keyboard from anywhere in the app.
    private func dismissKeyboard() {
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }

    public var body: some View {
        NavigationView {
            ZStack {
                Color(hex: "#0A0D12")
                    .ignoresSafeArea()
                    .contentShape(Rectangle())
                    .onTapGesture {
                        dismissKeyboard()
                    }

                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        // ================= 1. HEADER ROW =================
                        HStack(alignment: .center) {
                            HStack(spacing: 10) {
                                Image(systemName: "r.square.fill")
                                    .resizable()
                                    .frame(width: 34, height: 34)
                                    .foregroundColor(Color(hex: "#00BFFF"))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("RATT v2")
                                        .font(.title3)
                                        .fontWeight(.heavy)
                                        .foregroundColor(Color(hex: "#00BFFF"))
                                    Text("iPhone X – iPhone 17 Pro Max • Cybrox")
                                        .font(.caption2)
                                        .foregroundColor(Color(hex: "#8B949E"))
                                }
                            }

                            Spacer()

                            Button(action: {
                                dismissKeyboard()
                                upgradeReason = "Manage your RATT Commercial Subscription"
                                showUpgradeAlert = true
                            }) {
                                Text(userTier.rawValue.uppercased())
                                    .font(.system(size: 11, weight: .bold))
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 4)
                                    .background(userTier.isPaidEntitlement ? Color(hex: "#10B981").opacity(0.2) : Color(hex: "#21262D"))
                                    .foregroundColor(userTier.isPaidEntitlement ? Color(hex: "#39FF14") : Color(hex: "#8B949E"))
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 6)
                                            .stroke(userTier.isPaidEntitlement ? Color(hex: "#10B981") : Color(hex: "#30363D"), lineWidth: 1)
                                    )
                                    .cornerRadius(6)
                            }
                        }
                        .padding(.horizontal)
                        .padding(.top, 8)
                        .contentShape(Rectangle())
                        .onTapGesture {
                            dismissKeyboard()
                        }

                        // ================= LIVE STATUS & ACTIVE PASTE SLOT BANNER =================
                        VStack(alignment: .leading, spacing: 4) {
                            HStack(spacing: 8) {
                                Image(systemName: statusIsSuccess ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                                    .foregroundColor(statusIsSuccess ? Color(hex: "#39FF14") : Color(hex: "#F59E0B"))
                                    .font(.system(size: 13))
                                Text(statusMessage)
                                    .font(.system(size: 11.5, weight: .semibold))
                                    .foregroundColor(.white)
                                    .lineLimit(2)
                                Spacer()
                            }
                            if activePasteSlot > 0, let activeTxt = slotPreviews[activePasteSlot], !activeTxt.isEmpty {
                                Text("📌 Ready to Paste: Slot #\(activePasteSlot) (\"\(activeTxt)\")")
                                    .font(.system(size: 10.5, weight: .bold))
                                    .foregroundColor(Color(hex: "#39FF14"))
                                    .lineLimit(1)
                            }
                        }
                        .padding(10)
                        .background(Color(hex: "#10241B"))
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(statusIsSuccess ? Color(hex: "#10B981") : Color(hex: "#F59E0B"), lineWidth: 1)
                        )
                        .cornerRadius(8)
                        .padding(.horizontal)
                        .onTapGesture {
                            dismissKeyboard()
                        }

                        // ================= 2. CHOOSE SLOT TO PASTE (1-10) =================
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("1️⃣ CHOOSE WHICH SLOT TO PASTE (1–10)")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(Color(hex: "#39FF14"))
                                Spacer()
                                if activePasteSlot > 0 {
                                    Text("Active: Slot #\(activePasteSlot)")
                                        .font(.system(size: 10.5, weight: .bold))
                                        .foregroundColor(Color(hex: "#39FF14"))
                                }
                            }

                            // Big Slot Picker Button to Choose from Slots 1-10 for Pasting
                            Button(action: {
                                dismissKeyboard()
                                showPasteSlotSheet = true
                            }) {
                                HStack {
                                    Image(systemName: "doc.on.clipboard.fill")
                                    Text(activePasteSlot > 0 ? "📤 Choose Slot to Paste (Currently Slot #\(activePasteSlot))..." : "📤 Choose Slot to Paste (Slots 1–10)...")
                                }
                                .font(.system(size: 13, weight: .bold))
                                .foregroundColor(.black)
                                .frame(maxWidth: .infinity)
                                .frame(height: 40)
                                .background(Color(hex: "#39FF14"))
                                .cornerRadius(6)
                            }

                            Text("Or tap any filled slot button below to select it as your active Paste slot:")
                                .font(.system(size: 10))
                                .foregroundColor(Color(hex: "#8B949E"))

                            // 10 Quick "Select to Paste" Buttons
                            VStack(spacing: 6) {
                                HStack(spacing: 5) {
                                    ForEach(1...5, id: \.self) { slotId in
                                        quickPasteSlotButton(slotId: slotId)
                                    }
                                }
                                HStack(spacing: 5) {
                                    ForEach(6...10, id: \.self) { slotId in
                                        quickPasteSlotButton(slotId: slotId)
                                    }
                                }
                            }
                        }
                        .padding(14)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(hex: "#10B981"), lineWidth: 1.5))
                        .cornerRadius(10)
                        .padding(.horizontal)

                        // ================= 3. SAVE NEW TEXT OR CLIPBOARD TO A SLOT =================
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("2️⃣ SAVE TEXT OR CLIPBOARD INTO A SLOT")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(Color(hex: "#00BFFF"))
                                Spacer()
                                Button("Hide Keyboard ⌨️↓") {
                                    dismissKeyboard()
                                }
                                .font(.system(size: 10.5, weight: .bold))
                                .foregroundColor(Color(hex: "#00BFFF"))
                            }

                            HStack(spacing: 6) {
                                TextField("Type or paste new text here to save into a slot...", text: $directInputText)
                                    .font(.system(size: 13))
                                    .foregroundColor(.white)
                                    .padding(10)
                                    .background(Color(hex: "#0D1117"))
                                    .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#30363D"), lineWidth: 1))
                                    .cornerRadius(6)

                                if !directInputText.isEmpty {
                                    Button(action: {
                                        directInputText = ""
                                        dismissKeyboard()
                                    }) {
                                        Image(systemName: "xmark.circle.fill")
                                            .foregroundColor(Color(hex: "#8B949E"))
                                            .font(.system(size: 18))
                                    }
                                }
                            }

                            Button(action: {
                                dismissKeyboard()
                                showSaveSlotSheet = true
                            }) {
                                HStack {
                                    Image(systemName: "square.and.arrow.down.fill")
                                    Text(directInputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                                         ? "📥 Save Copied iPhone Clipboard to Slot (Choose 1–10)..."
                                         : "📥 Save Typed Text Above to Slot (Choose 1–10)...")
                                }
                                .font(.system(size: 12.5, weight: .bold))
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .frame(height: 38)
                                .background(Color(hex: "#00BFFF"))
                                .cornerRadius(6)
                            }
                        }
                        .padding(14)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(hex: "#30363D"), lineWidth: 1))
                        .cornerRadius(10)
                        .padding(.horizontal)

                        // ================= 4. LIVE 10-SLOT PREVIEW (TAP 'PASTE THIS' ON ANY SLOT) =================
                        VStack(alignment: .leading, spacing: 6) {
                            Text("LIVE 10-SLOT PREVIEW (TAP 'PASTE THIS' TO CHOOSE SLOT FOR PASTING)")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(Color(hex: "#8B949E"))
                                .padding(.horizontal)

                            VStack(spacing: 6) {
                                ForEach(1...10, id: \.self) { slotId in
                                    slotRowCard(slotId: slotId)
                                }
                            }
                            .padding(.horizontal)

                            Button(action: {
                                dismissKeyboard()
                                clearAllSlots()
                            }) {
                                HStack {
                                    Image(systemName: "trash")
                                    Text("🗑️ Clear All Slots")
                                }
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(Color(hex: "#EF4444"))
                                .frame(maxWidth: .infinity)
                                .frame(height: 38)
                                .background(Color(hex: "#161B22"))
                                .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#EF4444"), lineWidth: 1))
                                .cornerRadius(6)
                            }
                            .padding(.horizontal)
                            .padding(.top, 4)
                        }

                        // ================= 5. IP / WI-FI SYNC CARD =================
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("THIS IPHONE IP ADDRESS:")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(Color(hex: "#8B949E"))

                                    Text(iphoneIpAddress)
                                        .font(.system(size: 20, weight: .bold, design: .monospaced))
                                        .foregroundColor(Color(hex: "#39FF14"))
                                }
                                Spacer()
                                Button(action: {
                                    dismissKeyboard()
                                    UIPasteboard.general.string = iphoneIpAddress
                                    setStatus("📋 Copied iPhone IP (\(iphoneIpAddress)) to Clipboard", ok: true)
                                }) {
                                    HStack(spacing: 4) {
                                        Image(systemName: "doc.on.doc")
                                        Text("Copy IP")
                                    }
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(Color(hex: "#00BFFF"))
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 6)
                                    .background(Color(hex: "#0D1117"))
                                    .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#00BFFF"), lineWidth: 1))
                                    .cornerRadius(6)
                                }
                            }

                            HStack {
                                Text("Connected PC IP: \(pcIpAddress.isEmpty ? "Not Paired Yet" : pcIpAddress)")
                                    .font(.system(size: 12, weight: .semibold, design: .monospaced))
                                    .foregroundColor(Color(hex: "#00BFFF"))
                                Spacer()
                                Text("(Tap to pair)")
                                    .font(.system(size: 10))
                                    .foregroundColor(Color(hex: "#8B949E"))
                            }
                            .contentShape(Rectangle())
                            .onTapGesture {
                                dismissKeyboard()
                                pairIpDraft = pcIpAddress
                                showPairDialog = true
                            }

                            if showPairDialog {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Enter the PC IP shown on your RATT PC toolbar (e.g. 10.191.126.253):")
                                        .font(.system(size: 11, weight: .semibold))
                                        .foregroundColor(Color(hex: "#E6EDF3"))

                                    HStack(spacing: 8) {
                                        TextField("PC IP Address", text: $pairIpDraft)
                                            .keyboardType(.numbersAndPunctuation)
                                            .autocapitalization(.none)
                                            .disableAutocorrection(true)
                                            .font(.system(size: 14, weight: .bold, design: .monospaced))
                                            .foregroundColor(.white)
                                            .padding(10)
                                            .background(Color(hex: "#0D1117"))
                                            .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#00BFFF"), lineWidth: 1))
                                            .cornerRadius(6)

                                        Button("Hide ⌨️") {
                                            dismissKeyboard()
                                        }
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(Color(hex: "#C9D1D9"))
                                        .padding(.horizontal, 10)
                                        .frame(height: 38)
                                        .background(Color(hex: "#21262D"))
                                        .cornerRadius(6)
                                    }

                                    HStack(spacing: 8) {
                                        Button(action: {
                                            dismissKeyboard()
                                            let cleanIp = pairIpDraft.trimmingCharacters(in: .whitespacesAndNewlines)
                                            guard !cleanIp.isEmpty else {
                                                setStatus("Please enter the PC IP address shown in RATT PC.", ok: false)
                                                return
                                            }
                                            pcIpAddress = cleanIp
                                            UserDefaults.standard.set(cleanIp, forKey: "paired_pc_ip")
                                            showPairDialog = false
                                            pairAndSyncWithPc(cleanIp)
                                        }) {
                                            Text("Save & Pair Now")
                                                .font(.system(size: 12.5, weight: .bold))
                                                .foregroundColor(.white)
                                                .frame(maxWidth: .infinity)
                                                .frame(height: 36)
                                                .background(Color(hex: "#10B981"))
                                                .cornerRadius(6)
                                        }

                                        Button(action: {
                                            dismissKeyboard()
                                            showPairDialog = false
                                        }) {
                                            Text("Cancel")
                                                .font(.system(size: 12.5, weight: .bold))
                                                .foregroundColor(Color(hex: "#C9D1D9"))
                                                .frame(width: 80, height: 36)
                                                .background(Color(hex: "#21262D"))
                                                .cornerRadius(6)
                                        }
                                    }
                                }
                                .padding(10)
                                .background(Color(hex: "#0D1117"))
                                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color(hex: "#00BFFF"), lineWidth: 1))
                                .cornerRadius(8)
                            } else {
                                Button(action: {
                                    dismissKeyboard()
                                    pairIpDraft = pcIpAddress
                                    showPairDialog = true
                                }) {
                                    HStack {
                                        Image(systemName: "link")
                                        Text(pcIpAddress.isEmpty ? "Pair with PC (Enter PC IP)" : "Pair / Change PC (\(pcIpAddress))")
                                    }
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 38)
                                    .background(Color(hex: "#00BFFF"))
                                    .cornerRadius(6)
                                }
                            }

                            HStack(spacing: 8) {
                                Button(action: {
                                    dismissKeyboard()
                                    pushAllSlotsToPc()
                                }) {
                                    HStack {
                                        Image(systemName: "arrow.up.circle.fill")
                                        Text("Push Slots to PC")
                                    }
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(Color(hex: "#39FF14"))
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 36)
                                    .background(Color(hex: "#161B22"))
                                    .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#10B981"), lineWidth: 1))
                                    .cornerRadius(6)
                                }

                                Button(action: {
                                    dismissKeyboard()
                                    pullAllSlotsFromPc()
                                }) {
                                    HStack {
                                        Image(systemName: "arrow.down.circle.fill")
                                        Text("Pull Slots from PC")
                                    }
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(Color(hex: "#00BFFF"))
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 36)
                                    .background(Color(hex: "#161B22"))
                                    .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#00BFFF"), lineWidth: 1))
                                    .cornerRadius(6)
                                }
                            }
                        }
                        .padding(14)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(hex: "#30363D"), lineWidth: 1))
                        .cornerRadius(10)
                        .padding(.horizontal)

                        // ================= 6. KEYBOARD SETUP & PERMISSION DIAGNOSTICS =================
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                HStack(spacing: 6) {
                                    Circle()
                                        .fill(Color(hex: "#39FF14"))
                                        .frame(width: 8, height: 8)
                                    Text("RATT KEYBOARD (CHOOSE SLOTS INSIDE ANY APP)")
                                        .font(.system(size: 10.5, weight: .bold))
                                        .foregroundColor(Color(hex: "#39FF14"))
                                }
                                Spacer()
                                Button(action: {
                                    dismissKeyboard()
                                    if let url = URL(string: UIApplication.openSettingsURLString) {
                                        UIApplication.shared.open(url)
                                    }
                                }) {
                                    HStack(spacing: 4) {
                                        Image(systemName: "gearshape.fill")
                                        Text("Open Settings")
                                    }
                                    .font(.system(size: 10.5, weight: .bold))
                                    .foregroundColor(.white)
                                    .padding(.horizontal, 9)
                                    .padding(.vertical, 5)
                                    .background(Color(hex: "#238636"))
                                    .cornerRadius(6)
                                }
                            }

                            Text("Settings → General → Keyboard → Keyboards → Add 'RATT v2' → Enable 'Allow Full Access'")
                                .font(.system(size: 10))
                                .foregroundColor(Color(hex: "#8B949E"))
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color(hex: "#30363D"), lineWidth: 1))
                        .cornerRadius(8)
                        .padding(.horizontal)
                        .onTapGesture {
                            dismissKeyboard()
                        }

                        // ================= 7. CROSS-PLATFORM SYNC =================
                        VStack(alignment: .leading, spacing: 6) {
                            Text("CROSS-PLATFORM SYNC (PREMIUM & ENTERPRISE)")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(Color(hex: "#8B949E"))

                            HStack(spacing: 8) {
                                Button(action: {
                                    dismissKeyboard()
                                    handleCrossSync(target: "macOS")
                                }) {
                                    HStack {
                                        Image(systemName: "laptopcomputer")
                                        Text("💻 Sync with macOS")
                                    }
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 38)
                                    .background(Color(hex: "#7C3AED"))
                                    .cornerRadius(6)
                                }

                                Button(action: {
                                    dismissKeyboard()
                                    handleCrossSync(target: "Android")
                                }) {
                                    HStack {
                                        Image(systemName: "phone.fill")
                                        Text("📱 Sync with Android")
                                    }
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 38)
                                    .background(Color(hex: "#2563EB"))
                                    .cornerRadius(6)
                                }
                            }
                        }
                        .padding(.horizontal)
                        .padding(.top, 6)

                        // ================= 8. SHARE, MIRROR & TRANSLATE =================
                        VStack(alignment: .leading, spacing: 6) {
                            Text("SHARE, MIRROR & 9-LANGUAGE TRANSLATION (PREMIUM & ENTERPRISE)")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(Color(hex: "#8B949E"))

                            HStack(spacing: 8) {
                                Button(action: {
                                    dismissKeyboard()
                                    handleShare()
                                }) {
                                    HStack {
                                        Image(systemName: "person.2.fill")
                                        Text("Share with Account")
                                    }
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 38)
                                    .background(Color(hex: "#059669"))
                                    .cornerRadius(6)
                                }

                                Button(action: {
                                    dismissKeyboard()
                                    handleMirror()
                                }) {
                                    HStack {
                                        Image(systemName: "rectangle.2.swap")
                                        Text("Mirror Devices")
                                    }
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 38)
                                    .background(Color(hex: "#D97706"))
                                    .cornerRadius(6)
                                }
                            }

                            Button(action: {
                                dismissKeyboard()
                                handleTranslate()
                            }) {
                                HStack {
                                    Image(systemName: "globe")
                                    Text("🌐 Translate Slot Text (9 Languages)")
                                }
                                .font(.system(size: 11.5, weight: .bold))
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .frame(height: 36)
                                .background(Color(hex: "#0284C7"))
                                .cornerRadius(6)
                            }
                        }
                        .padding(.horizontal)
                        .padding(.top, 4)

                        // ================= 9. EXIT & WIPE SLOTS =================
                        Button(action: {
                            dismissKeyboard()
                            emptySlotsAndExit()
                        }) {
                            HStack {
                                Image(systemName: "door.right.hand.open")
                                Text("🚪 Exit RATT (Wipe All Slots on Exit)")
                            }
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(Color(hex: "#9CA3AF"))
                            .frame(maxWidth: .infinity)
                            .frame(height: 38)
                            .background(Color(hex: "#161B22"))
                            .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#30363D"), lineWidth: 1))
                            .cornerRadius(6)
                        }
                        .padding(.horizontal)
                        .padding(.bottom, 24)
                    }
                }
            }
            .navigationBarHidden(true)
            .onAppear {
                _ = SecurityHardening.enforceRuntimeDefense()
                dataManager.startSyncListener(port: 49211)
                loadPreferences()
                refreshSlots()
            }
            .onReceive(NotificationCenter.default.publisher(for: .slotUpdated)) { _ in
                loadPreferences()
                refreshSlots()
            }
            .onReceive(NotificationCenter.default.publisher(for: .slotCleared)) { _ in
                refreshSlots()
            }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.willTerminateNotification)) { _ in
                emptySlotsOnExit()
            }
            .alert("⭐ RATT Subscription & Licensing", isPresented: $showUpgradeAlert) {
                Button("Basic (Free) - 10 Slots (Text/Links/Images/SVG)") {
                    userTier = .basic
                    store.setUserTier("basic")
                    refreshSlots()
                }
                Button("Upgrade to Premium ($0.99/mo)") {
                    userTier = .premium
                    store.setUserTier("premium")
                    refreshSlots()
                }
                Button("Upgrade to Enterprise ($2.99/mo)") {
                    userTier = .enterprise
                    store.setUserTier("enterprise")
                    refreshSlots()
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text(upgradeReason.isEmpty ? "Current Plan: \(userTier.rawValue.uppercased())\n\nBasic includes 10 slots for text, links, images & SVG diagrams. Cross-platform sync (Android/iOS/macOS), Documents & Media files, 9-Language Translation, and Share & Mirror require Premium or Enterprise." : upgradeReason)
            }
            .alert("Sync with \(crossSyncTarget)", isPresented: $showCrossSyncAlert) {
                Button("Sync with Paired IP (\(pcIpAddress.isEmpty ? "Set IP First" : pcIpAddress))") {
                    if !pcIpAddress.isEmpty {
                        performCrossSync(target: crossSyncTarget, targetIp: pcIpAddress)
                    } else {
                        showPairDialog = true
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Sync all 10 slots with your \(crossSyncTarget) device running RATT.")
            }
            // Background modifier container for the two separate ActionSheets (Paste Picker vs Save Picker)
            .background(
                HStack {
                    Color.clear
                        .actionSheet(isPresented: $showPasteSlotSheet) {
                            var buttons: [ActionSheet.Button] = []
                            for s in 1...10 {
                                let preview = slotPreviews[s] ?? ""
                                let label = preview.isEmpty
                                    ? "Slot #\(s) — [Empty]"
                                    : "Slot #\(s): \(preview.count > 36 ? String(preview.prefix(36)) + "..." : preview)"
                                buttons.append(.default(Text(label)) {
                                    copySlotToIphoneClipboard(slotId: s)
                                })
                            }
                            buttons.append(.cancel())
                            return ActionSheet(
                                title: Text("Choose Which Slot (1–10) to Paste"),
                                message: Text("Select a slot below to load it into your iPhone Clipboard for pasting:"),
                                buttons: buttons
                            )
                        }
                    Color.clear
                        .actionSheet(isPresented: $showSaveSlotSheet) {
                            var buttons: [ActionSheet.Button] = []
                            for s in 1...10 {
                                let preview = slotPreviews[s] ?? ""
                                let label = preview.isEmpty
                                    ? "Save into Slot #\(s) [Empty]"
                                    : "Overwrite Slot #\(s) (\(preview.count > 24 ? String(preview.prefix(24)) + "..." : preview))"
                                buttons.append(.default(Text(label)) {
                                    saveClipboardToSlot(slotId: s)
                                })
                            }
                            buttons.append(.cancel())
                            return ActionSheet(
                                title: Text("Save into Which Slot (1–10)?"),
                                message: Text("Choose the slot number where you want to store this item:"),
                                buttons: buttons
                            )
                        }
                }
            )
        }
        .navigationViewStyle(StackNavigationViewStyle())
    }

    // ================= SUB-VIEWS =================

    /// Quick button in the "1️⃣ CHOOSE WHICH SLOT TO PASTE" grid — ALWAYS selects that slot for pasting!
    @ViewBuilder
    private func quickPasteSlotButton(slotId: Int) -> some View {
        let content = slotPreviews[slotId]
        let hasData = content != nil && !content!.isEmpty
        let isSelectedForPaste = (activePasteSlot == slotId) && hasData
        let slotColor = PC_SLOT_COLORS[slotId - 1]

        Button(action: {
            dismissKeyboard()
            if hasData {
                copySlotToIphoneClipboard(slotId: slotId)
            } else {
                setStatus("Slot #\(slotId) is empty. Save text into Slot #\(slotId) first.", ok: false)
            }
        }) {
            Text(isSelectedForPaste ? "✓ #\(slotId)" : (hasData ? "Paste #\(slotId)" : "Slot \(slotId)"))
                .font(.system(size: 10.5, weight: hasData ? .bold : .regular))
                .foregroundColor(isSelectedForPaste ? .black : (hasData ? .white : Color(hex: "#6E7681")))
                .frame(maxWidth: .infinity)
                .frame(height: 36)
                .background(isSelectedForPaste ? Color(hex: "#39FF14") : (hasData ? Color(hex: "#133024") : Color(hex: "#161B22")))
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(isSelectedForPaste ? Color.white : (hasData ? slotColor : Color(hex: "#30363D")), lineWidth: isSelectedForPaste ? 2 : 1)
                )
                .cornerRadius(6)
        }
    }

    @ViewBuilder
    private func slotRowCard(slotId: Int) -> some View {
        let content = slotPreviews[slotId]
        let hasData = content != nil && !content!.isEmpty
        let isSelectedForPaste = (activePasteSlot == slotId) && hasData
        let slotColor = PC_SLOT_COLORS[slotId - 1]

        HStack(spacing: 6) {
            RoundedRectangle(cornerRadius: 2)
                .fill(hasData ? slotColor : Color(hex: "#21262D"))
                .frame(width: 4, height: 28)

            Text("#\(slotId)")
                .font(.system(size: 11.5, weight: .bold))
                .foregroundColor(hasData ? .white : slotColor)
                .frame(width: 30, height: 24)
                .background(hasData ? slotColor : Color(hex: "#161B22"))
                .overlay(
                    RoundedRectangle(cornerRadius: 4)
                        .stroke(slotColor, lineWidth: 1)
                )
                .cornerRadius(4)

            if hasData {
                Text(content!)
                    .font(.system(size: 12.5, weight: .bold))
                    .foregroundColor(.white)
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        dismissKeyboard()
                        copySlotToIphoneClipboard(slotId: slotId)
                    }
            } else {
                Text("Slot \(slotId): [Empty]")
                    .font(.system(size: 12.5))
                    .foregroundColor(Color(hex: "#6E7681"))
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            if hasData {
                // Choose This Slot to Paste Button
                Button(action: {
                    dismissKeyboard()
                    copySlotToIphoneClipboard(slotId: slotId)
                }) {
                    Text(isSelectedForPaste ? "✓ Ready" : "Paste This")
                        .font(.system(size: 10.5, weight: .bold))
                        .foregroundColor(isSelectedForPaste ? .black : .white)
                        .padding(.horizontal, 8)
                        .frame(height: 28)
                        .background(isSelectedForPaste ? Color(hex: "#39FF14") : Color(hex: "#00BFFF"))
                        .cornerRadius(4)
                }
            }

            // Save Button -> Saves typed text or external clipboard into this Slot
            Button(action: {
                dismissKeyboard()
                saveClipboardToSlot(slotId: slotId)
            }) {
                Text("Save")
                    .font(.system(size: 10.5, weight: .semibold))
                    .foregroundColor(Color(hex: "#C9D1D9"))
                    .padding(.horizontal, 8)
                    .frame(height: 28)
                    .background(Color(hex: "#21262D"))
                    .cornerRadius(4)
            }

            Button(action: {
                dismissKeyboard()
                clearSlot(slotId: slotId)
            }) {
                Text("X")
                    .font(.system(size: 10.5, weight: .bold))
                    .foregroundColor(Color(hex: "#EF4444"))
                    .padding(.horizontal, 7)
                    .frame(height: 28)
                    .background(Color(hex: "#21262D"))
                    .cornerRadius(4)
            }
        }
        .padding(8)
        .background(isSelectedForPaste ? Color(hex: "#143828") : (hasData ? Color(hex: "#10241B") : Color(hex: "#12161C")))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(isSelectedForPaste ? Color(hex: "#39FF14") : (hasData ? slotColor : Color(hex: "#21262D")), lineWidth: (isSelectedForPaste || hasData) ? 2 : 1)
        )
        .cornerRadius(8)
    }

    // ================= ACTIONS =================

    private func setStatus(_ msg: String, ok: Bool) {
        statusMessage = msg
        statusIsSuccess = ok
    }

    private func loadPreferences() {
        let savedPc = UserDefaults.standard.string(forKey: "paired_pc_ip") ?? ""
        self.pcIpAddress = savedPc
        self.iphoneIpAddress = dataManager.getDeviceIpAddress()
        self.userTier = RattUserTier(rawValue: store.getUserTier()) ?? .basic
        self.activePasteSlot = UserDefaults.standard.integer(forKey: "ratt_active_paste_slot")
    }

    private func refreshSlots() {
        var loaded: [Int: String] = [:]
        for s in 1...10 {
            if let txt = store.decryptSlot(s), !txt.isEmpty {
                loaded[s] = txt
            } else if let groupTxt = dataManager.loadSlot(id: s)?.content, !groupTxt.isEmpty {
                loaded[s] = groupTxt
            }
        }
        slotPreviews = loaded
        if activePasteSlot > 0 && loaded[activePasteSlot] == nil {
            activePasteSlot = 0
        }
    }

    /// Saves text into `slotId` WITHOUT overwriting the user's chosen paste slot or other slots.
    private func saveTextToSlot(slotId: Int, text: String) {
        if !store.isAllowedPayloadForTier(text) {
            upgradeReason = "UPGRADE REQUIRED: Copying Document & Media files (.docx, .xls, .pdf, .mp4, etc.) is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
        }
        let okStore = store.encryptAndStore(slot: slotId, text: text)
        let okGroup = dataManager.saveSlot(id: slotId, content: text)
        lastSavedTexts.insert(text)
        UINotificationFeedbackGenerator().notificationOccurred(.success)
        sendSlotToPc(slotId: slotId, text: text)
        refreshSlots()
        if okStore || okGroup {
            // If no active paste slot was selected yet, or if saving into the active paste slot, load it for paste
            if activePasteSlot == 0 || activePasteSlot == slotId {
                activePasteSlot = slotId
                UserDefaults.standard.set(slotId, forKey: "ratt_active_paste_slot")
                UIPasteboard.general.string = text
            }
            setStatus("✅ Saved to Slot #\(slotId)! Tap any slot in Section 1️⃣ to choose which slot to paste.", ok: true)
        } else {
            setStatus("⚠️ Security Guard blocked unsafe link or script in Slot #\(slotId).", ok: false)
        }
    }

    /// Explicitly chooses `slotId` (1–10) as the Active Paste Slot and loads it into `UIPasteboard.general`.
    private func copySlotToIphoneClipboard(slotId: Int) {
        if let slotObj = dataManager.loadSlot(id: slotId) {
            if slotObj.kind == "image", let b64 = slotObj.dataBase64, let imgData = Data(base64Encoded: b64), let img = UIImage(data: imgData) {
                UIPasteboard.general.image = img
                activePasteSlot = slotId
                UserDefaults.standard.set(slotId, forKey: "ratt_active_paste_slot")
                UINotificationFeedbackGenerator().notificationOccurred(.success)
                setStatus("📋 Selected Slot #\(slotId) (Image) for Paste!", ok: true)
                return
            }
            if !slotObj.content.isEmpty {
                UIPasteboard.general.string = slotObj.content
                activePasteSlot = slotId
                UserDefaults.standard.set(slotId, forKey: "ratt_active_paste_slot")
                UINotificationFeedbackGenerator().notificationOccurred(.success)
                setStatus("📋 Slot #\(slotId) is now Active for Paste! Go to any app and tap Paste.", ok: true)
                return
            }
        }
        if let txt = slotPreviews[slotId] ?? store.decryptSlot(slotId), !txt.isEmpty {
            UIPasteboard.general.string = txt
            activePasteSlot = slotId
            UserDefaults.standard.set(slotId, forKey: "ratt_active_paste_slot")
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            setStatus("📋 Slot #\(slotId) is now Active for Paste! Go to any app and tap Paste.", ok: true)
        } else {
            setStatus("Slot #\(slotId) is empty. Save text into Slot #\(slotId) first.", ok: false)
        }
    }

    /// Saves typed text (or a new external item from the iPhone Clipboard) into `slotId`.
    private func saveClipboardToSlot(slotId: Int) {
        let typed = directInputText.trimmingCharacters(in: .whitespacesAndNewlines)
        if !typed.isEmpty {
            saveTextToSlot(slotId: slotId, text: typed)
            directInputText = ""
            return
        }
        if let clip = UIPasteboard.general.string, !clip.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            saveTextToSlot(slotId: slotId, text: clip)
        } else if let img = UIPasteboard.general.image, let pngData = img.pngData() {
            let b64 = pngData.base64EncodedString()
            let desc = "Image [\(Int(img.size.width))x\(Int(img.size.height))]"
            _ = store.encryptAndStore(slot: slotId, text: desc)
            _ = dataManager.saveSlot(id: slotId, content: desc, kind: "image", dataBase64: b64, mimeType: "image/png", byteSize: pngData.count)
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            refreshSlots()
            setStatus("✅ Saved iPhone Clipboard Image to Slot #\(slotId)!", ok: true)
        } else {
            setStatus("Type text in the box above or copy text in another app first, then tap Save.", ok: false)
        }
    }

    private func clearSlot(slotId: Int) {
        dataManager.clearSlot(id: slotId)
        store.clearSlot(slotId)
        if activePasteSlot == slotId {
            activePasteSlot = 0
            UserDefaults.standard.set(0, forKey: "ratt_active_paste_slot")
        }
        sendClearSlotToPc(slotId: slotId)
        refreshSlots()
        setStatus("🗑️ Cleared Slot #\(slotId)", ok: true)
    }

    private func clearAllSlots() {
        dataManager.clearAllSlots()
        store.clearAllSlots()
        activePasteSlot = 0
        UserDefaults.standard.set(0, forKey: "ratt_active_paste_slot")
        sendClearAllToPc()
        refreshSlots()
        setStatus("🗑️ Cleared all 10 slots", ok: true)
    }

    private func emptySlotsOnExit() {
        dataManager.exitAndWipeAllSlots()
        store.exitAndWipeAllSlots()
        activePasteSlot = 0
        slotPreviews.removeAll()
    }

    private func emptySlotsAndExit() {
        sendClearAllToPc()
        emptySlotsOnExit()
        setStatus("🔒 All 10 slots securely wiped.", ok: true)
    }

    private func handleCrossSync(target: String) {
        if target == "Android" && !store.canSyncWithAndroid() {
            upgradeReason = "UPGRADE REQUIRED: Cross-platform sync between iOS and Android is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
        }
        crossSyncTarget = target
        showCrossSyncAlert = true
    }

    private func handleTranslate() {
        if !store.canTranslate() {
            upgradeReason = "UPGRADE REQUIRED: 9-Language Translation is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
        }
        setStatus("🌐 9-Language Translation Ready", ok: true)
    }

    private func handleShare() {
        if !store.canShareAndMirror() {
            upgradeReason = "UPGRADE REQUIRED: Account Sharing (copy/cut/paste across different RATT accounts) is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
        }
    }

    private func handleMirror() {
        if !store.canShareAndMirror() {
            upgradeReason = "UPGRADE REQUIRED: Device Mirroring across RATT devices is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
        }
    }

    private func pairAndSyncWithPc(_ targetIp: String) {
        setStatus("🔗 Pairing with PC (\(targetIp))...", ok: true)
        let myIp = dataManager.getDeviceIpAddress()
        let myToken = dataManager.getOrCreateSyncToken()

        for port in [49211, 49210] {
            guard let url = URL(string: "http://\(targetIp):\(port)/pair") else { continue }
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.timeoutInterval = 3.0
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.setValue(myToken, forHTTPHeaderField: "X-RATT-Token")
            let payload: [String: Any] = [
                "action": "PAIR",
                "device": "iOS",
                "phone_ip": myIp,
                "sync_token": myToken,
                "timestamp": Date().timeIntervalSince1970,
                "nonce": UUID().uuidString
            ]
            req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
            URLSession.shared.dataTask(with: req) { data, _, _ in
                if let data = data,
                   let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let pcTok = json["sync_token"] as? String, !pcTok.isEmpty {
                    self.dataManager.setSyncToken(pcTok)
                    DispatchQueue.main.async {
                        self.setStatus("✅ Paired with PC (\(targetIp))! Syncing slots...", ok: true)
                        self.pushAllSlotsToPc()
                        self.pullAllSlotsFromPc()
                    }
                }
            }.resume()
        }
    }

    private func pullAllSlotsFromPc() {
        guard !pcIpAddress.isEmpty else {
            showPairDialog = true
            setStatus("Please enter your PC IP address to pair first.", ok: false)
            return
        }
        let token = dataManager.getOrCreateSyncToken()
        for port in [49211, 49210] {
            guard let url = URL(string: "http://\(pcIpAddress):\(port)/get_all_slots") else { continue }
            var req = URLRequest(url: url)
            req.httpMethod = "GET"
            req.timeoutInterval = 3.0
            req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
            URLSession.shared.dataTask(with: req) { data, _, _ in
                guard let data = data,
                      let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let slots = json["slots"] as? [String: String] else {
                    return
                }
                var pulled = 0
                for (k, v) in slots {
                    if let sId = Int(k), (1...10).contains(sId), !v.isEmpty {
                        _ = self.store.encryptAndStore(slot: sId, text: v)
                        _ = self.dataManager.saveSlot(id: sId, content: v)
                        pulled += 1
                    }
                }
                DispatchQueue.main.async {
                    self.refreshSlots()
                    self.setStatus("✅ Pulled \(pulled) slot(s) from PC! Tap any slot in Section 1️⃣ to choose which slot to paste.", ok: true)
                }
            }.resume()
        }
    }

    private func performCrossSync(target: String, targetIp: String) {
        guard !targetIp.isEmpty else { return }
        let port = target == "Android" ? 49210 : 49211
        let token = dataManager.getOrCreateSyncToken()
        for s in 1...10 {
            let text = store.decryptSlot(s) ?? ""
            guard let url = URL(string: "http://\(targetIp):\(port)/sync_slot") else { continue }
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.timeoutInterval = 2.5
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
            let payload: [String: Any] = [
                "action": text.isEmpty ? "CLEAR_SLOT" : "SYNC_FROM_IOS",
                "slot_id": s,
                "content": text,
                "ts": Date().timeIntervalSince1970,
                "nonce": UUID().uuidString
            ]
            req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
            URLSession.shared.dataTask(with: req).resume()
        }
        setStatus("🔄 Synced slots with \(target) (\(targetIp))", ok: true)
    }

    private func sendSlotToPc(slotId: Int, text: String) {
        guard !pcIpAddress.isEmpty else { return }
        let token = dataManager.getOrCreateSyncToken()
        for port in [49211, 49210] {
            guard let url = URL(string: "http://\(pcIpAddress):\(port)/sync_from_phone") else { continue }
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.timeoutInterval = 2.5
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
            let payload: [String: Any] = [
                "action": text.isEmpty ? "CLEAR_SLOT" : "SYNC_FROM_PHONE",
                "slot_id": slotId,
                "content": text,
                "ts": Date().timeIntervalSince1970,
                "nonce": UUID().uuidString
            ]
            req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
            URLSession.shared.dataTask(with: req).resume()
        }
    }

    private func sendClearSlotToPc(slotId: Int) {
        guard !pcIpAddress.isEmpty else { return }
        let token = dataManager.getOrCreateSyncToken()
        for port in [49211, 49210] {
            guard let url = URL(string: "http://\(pcIpAddress):\(port)/sync_from_phone") else { continue }
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.timeoutInterval = 2.0
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
            let payload: [String: Any] = [
                "action": "CLEAR_SLOT",
                "slot_id": slotId,
                "content": "",
                "ts": Date().timeIntervalSince1970,
                "nonce": UUID().uuidString
            ]
            req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
            URLSession.shared.dataTask(with: req).resume()
        }
    }

    private func sendClearAllToPc() {
        guard !pcIpAddress.isEmpty else { return }
        let token = dataManager.getOrCreateSyncToken()
        for port in [49211, 49210] {
            guard let url = URL(string: "http://\(pcIpAddress):\(port)/sync_from_phone") else { continue }
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.timeoutInterval = 2.0
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
            let payload: [String: Any] = [
                "action": "CLEAR_ALL",
                "content": "",
                "ts": Date().timeIntervalSince1970,
                "nonce": UUID().uuidString
            ]
            req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
            URLSession.shared.dataTask(with: req).resume()
        }
    }

    private func pushAllSlotsToPc() {
        guard !pcIpAddress.isEmpty else {
            showPairDialog = true
            setStatus("Please enter your PC IP address to pair first.", ok: false)
            return
        }
        var pushed = 0
        for s in 1...10 {
            if let text = store.decryptSlot(s), !text.isEmpty {
                sendSlotToPc(slotId: s, text: text)
                pushed += 1
            } else {
                sendClearSlotToPc(slotId: s)
            }
        }
        setStatus("🔄 Pushed \(pushed) slot(s) to PC (\(pcIpAddress))", ok: true)
    }
}
