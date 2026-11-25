// ContentView.swift — RATT v2 for iOS Container App (iPhone X through iPhone 17 Pro Max)
// Full Feature Parity with RATT Android & PC:
// 1. Compatible with iPhone X (iOS 15/16) and all newer iPhones up to iPhone 17 Pro Max
// 2. Native In-App 10-Slot Chooser Modal for Pasting & Saving:
//    - Tap "📤 Choose Slot to Paste (1–10)" to open a full 10-Slot Popup Chooser
//    - Choose ANY slot (#1 to #10) to load into your iPhone Clipboard or paste directly
//    - Syncs all 10 slots into the RATT Keyboard Pasteboard Carrier so the RATT Keyboard
//      also lets you choose any slot (#1–#10) inside WhatsApp, Notes, Safari, or Messages
// 3. Direct Two-Way Wi-Fi Sync with BOTH RATT Android (Port 49210) and RATT PC (Port 49211)
// 4. Touch anywhere outside text fields to minimize keyboard

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
    @State private var directInputText: String = ""
    @State private var statusMessage: String = "RATT v2 Ready • Tap 'Choose Slot to Paste' to pick any slot (1–10)"
    @State private var statusIsSuccess: Bool = true
    @State private var showUpgradeAlert: Bool = false
    @State private var upgradeReason: String = ""
    @State private var showPairDialog: Bool = false
    @State private var pairIpDraft: String = ""
    @State private var showAndroidSyncBox: Bool = false
    @State private var androidIpDraft: String = ""
    @State private var androidIpAddress: String = ""
    @State private var showPasteSlotModal: Bool = false
    @State private var showSaveSlotModal: Bool = false
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
                                Text("📌 Selected to Paste Now: Slot #\(activePasteSlot) (\"\(activeTxt)\")")
                                    .font(.system(size: 11, weight: .bold))
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

                        // ================= 2. CHOOSE WHICH SLOT TO PASTE (1-10) =================
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

                            // Opens the In-App 10-Slot Chooser Modal (Works reliably on all iOS versions!)
                            Button(action: {
                                dismissKeyboard()
                                refreshSlots()
                                showPasteSlotModal = true
                            }) {
                                HStack {
                                    Image(systemName: "list.number")
                                    Text(activePasteSlot > 0
                                         ? "📤 Choose Slot to Paste (Active: Slot #\(activePasteSlot))..."
                                         : "📤 Choose Slot to Paste (Pick from Slots 1–10)...")
                                }
                                .font(.system(size: 13, weight: .bold))
                                .foregroundColor(.black)
                                .frame(maxWidth: .infinity)
                                .frame(height: 42)
                                .background(Color(hex: "#39FF14"))
                                .cornerRadius(6)
                            }

                            Text("Or tap a slot number below to select which slot (1–10) you want to paste:")
                                .font(.system(size: 10))
                                .foregroundColor(Color(hex: "#8B949E"))

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
                                TextField("Type text here (or tap Paste from Slot below)...", text: $directInputText)
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

                            HStack(spacing: 8) {
                                Button(action: {
                                    dismissKeyboard()
                                    refreshSlots()
                                    showSaveSlotModal = true
                                }) {
                                    HStack(spacing: 4) {
                                        Image(systemName: "square.and.arrow.down.fill")
                                        Text("Save to Slot (1–10)...")
                                    }
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 38)
                                    .background(Color(hex: "#00BFFF"))
                                    .cornerRadius(6)
                                }

                                Button(action: {
                                    dismissKeyboard()
                                    refreshSlots()
                                    showPasteSlotModal = true
                                }) {
                                    HStack(spacing: 4) {
                                        Image(systemName: "doc.on.clipboard.fill")
                                        Text("Paste from Slot (1–10)...")
                                    }
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundColor(.black)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 38)
                                    .background(Color(hex: "#39FF14"))
                                    .cornerRadius(6)
                                }
                            }
                        }
                        .padding(14)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(hex: "#30363D"), lineWidth: 1))
                        .cornerRadius(10)
                        .padding(.horizontal)

                        // ================= 4. LIVE 10-SLOT PREVIEW =================
                        VStack(alignment: .leading, spacing: 6) {
                            Text("LIVE 10-SLOT PREVIEW (TAP 'PASTE THIS' ON ANY SLOT TO PASTE IT)")
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

                        // ================= 5. SYNC WITH ANDROID & MACOS =================
                        VStack(alignment: .leading, spacing: 8) {
                            Text("3️⃣ SYNC WITH RATT ANDROID & MACOS (TWO-WAY WI-FI SYNC)")
                                .font(.system(size: 10.5, weight: .bold))
                                .foregroundColor(Color(hex: "#39FF14"))

                            HStack(spacing: 8) {
                                Button(action: {
                                    dismissKeyboard()
                                    androidIpDraft = androidIpAddress
                                    showAndroidSyncBox.toggle()
                                }) {
                                    HStack {
                                        Image(systemName: "phone.connection.fill")
                                        Text(androidIpAddress.isEmpty ? "📱 Pair / Sync with Android" : "📱 Sync Android (\(androidIpAddress))")
                                    }
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 40)
                                    .background(Color(hex: "#2563EB"))
                                    .cornerRadius(6)
                                }

                                Button(action: {
                                    dismissKeyboard()
                                    if !pcIpAddress.isEmpty {
                                        syncWithAndroidDevice(targetIp: pcIpAddress, platformLabel: "macOS", port: 49211)
                                    } else {
                                        pairIpDraft = pcIpAddress
                                        showPairDialog = true
                                    }
                                }) {
                                    HStack {
                                        Image(systemName: "laptopcomputer")
                                        Text("💻 Sync with macOS")
                                    }
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 40)
                                    .background(Color(hex: "#7C3AED"))
                                    .cornerRadius(6)
                                }
                            }

                            if showAndroidSyncBox || !androidIpAddress.isEmpty {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Enter the green IP Address shown on your RATT Android screen (Port 49210):")
                                        .font(.system(size: 11, weight: .semibold))
                                        .foregroundColor(Color(hex: "#E6EDF3"))

                                    HStack(spacing: 8) {
                                        TextField("Android Phone IP (e.g. 10.191.126.x)", text: $androidIpDraft)
                                            .keyboardType(.numbersAndPunctuation)
                                            .autocapitalization(.none)
                                            .disableAutocorrection(true)
                                            .font(.system(size: 14, weight: .bold, design: .monospaced))
                                            .foregroundColor(Color(hex: "#39FF14"))
                                            .padding(10)
                                            .background(Color(hex: "#0D1117"))
                                            .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#2563EB"), lineWidth: 1))
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
                                            let cleanIp = (androidIpDraft.isEmpty ? androidIpAddress : androidIpDraft)
                                                .trimmingCharacters(in: .whitespacesAndNewlines)
                                            guard !cleanIp.isEmpty else {
                                                setStatus("Please enter the IP address shown on your RATT Android phone.", ok: false)
                                                return
                                            }
                                            androidIpAddress = cleanIp
                                            androidIpDraft = cleanIp
                                            UserDefaults.standard.set(cleanIp, forKey: "paired_android_ip")
                                            syncWithAndroidDevice(targetIp: cleanIp, platformLabel: "Android", port: 49210)
                                        }) {
                                            HStack {
                                                Image(systemName: "arrow.triangle.2.circlepath")
                                                Text("🔄 Sync All 10 Slots with Android Now")
                                            }
                                            .font(.system(size: 12, weight: .bold))
                                            .foregroundColor(.white)
                                            .frame(maxWidth: .infinity)
                                            .frame(height: 38)
                                            .background(Color(hex: "#10B981"))
                                            .cornerRadius(6)
                                        }
                                    }
                                }
                                .padding(10)
                                .background(Color(hex: "#0D1117"))
                                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color(hex: "#2563EB"), lineWidth: 1))
                                .cornerRadius(8)
                            }
                        }
                        .padding(14)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(hex: "#30363D"), lineWidth: 1))
                        .cornerRadius(10)
                        .padding(.horizontal)

                        // ================= 6. IP / WI-FI PC SYNC CARD =================
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
                                showPairDialog.toggle()
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

                        // ================= 7. KEYBOARD SETUP & PERMISSION DIAGNOSTICS =================
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

                        // ================= 8. EXIT & WIPE SLOTS =================
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

                // ================= IN-APP MODAL 1: CHOOSE WHICH SLOT TO PASTE (1-10) =================
                if showPasteSlotModal {
                    Color.black.opacity(0.75)
                        .ignoresSafeArea()
                        .onTapGesture {
                            showPasteSlotModal = false
                        }

                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Text("📤 Choose Slot to Paste (1–10)")
                                .font(.system(size: 16, weight: .heavy))
                                .foregroundColor(Color(hex: "#39FF14"))
                            Spacer()
                            Button(action: {
                                showPasteSlotModal = false
                            }) {
                                Image(systemName: "xmark.circle.fill")
                                    .font(.system(size: 22))
                                    .foregroundColor(Color(hex: "#8B949E"))
                            }
                        }

                        Text("Tap any slot below to load it into your iPhone Clipboard & paste it:")
                            .font(.system(size: 11.5))
                            .foregroundColor(Color(hex: "#C9D1D9"))

                        ScrollView {
                            VStack(spacing: 8) {
                                ForEach(1...10, id: \.self) { s in
                                    let txt = slotPreviews[s] ?? ""
                                    let hasData = !txt.isEmpty
                                    let isSelected = (activePasteSlot == s) && hasData
                                    let sColor = PC_SLOT_COLORS[s - 1]

                                    Button(action: {
                                        if hasData {
                                            copySlotToIphoneClipboard(slotId: s, alsoInsertInInputBox: true)
                                            showPasteSlotModal = false
                                        } else {
                                            setStatus("Slot #\(s) is empty. Save text into Slot #\(s) first.", ok: false)
                                        }
                                    }) {
                                        HStack(spacing: 10) {
                                            Text("#\(s)")
                                                .font(.system(size: 12, weight: .bold))
                                                .foregroundColor(.white)
                                                .frame(width: 34, height: 28)
                                                .background(hasData ? sColor : Color(hex: "#21262D"))
                                                .cornerRadius(5)

                                            Text(hasData ? txt : "[Empty Slot]")
                                                .font(.system(size: 13, weight: hasData ? .bold : .regular))
                                                .foregroundColor(hasData ? .white : Color(hex: "#6E7681"))
                                                .lineLimit(1)
                                                .frame(maxWidth: .infinity, alignment: .leading)

                                            if hasData {
                                                Text(isSelected ? "✓ ACTIVE" : "PASTE")
                                                    .font(.system(size: 11, weight: .heavy))
                                                    .foregroundColor(.black)
                                                    .padding(.horizontal, 10)
                                                    .padding(.vertical, 5)
                                                    .background(Color(hex: "#39FF14"))
                                                    .cornerRadius(5)
                                            }
                                        }
                                        .padding(10)
                                        .background(isSelected ? Color(hex: "#143828") : (hasData ? Color(hex: "#10241B") : Color(hex: "#12161C")))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 8)
                                                .stroke(isSelected ? Color(hex: "#39FF14") : (hasData ? sColor : Color(hex: "#21262D")), lineWidth: hasData ? 1.5 : 1)
                                        )
                                        .cornerRadius(8)
                                    }
                                }
                            }
                        }
                        .frame(maxHeight: 420)

                        Button(action: {
                            showPasteSlotModal = false
                        }) {
                            Text("Close")
                                .font(.system(size: 13, weight: .bold))
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .frame(height: 38)
                                .background(Color(hex: "#21262D"))
                                .cornerRadius(6)
                        }
                    }
                    .padding(16)
                    .background(Color(hex: "#161B22"))
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color(hex: "#39FF14"), lineWidth: 2))
                    .cornerRadius(14)
                    .padding(.horizontal, 20)
                }

                // ================= IN-APP MODAL 2: CHOOSE WHICH SLOT TO SAVE INTO (1-10) =================
                if showSaveSlotModal {
                    Color.black.opacity(0.75)
                        .ignoresSafeArea()
                        .onTapGesture {
                            showSaveSlotModal = false
                        }

                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Text("📥 Save Into Which Slot (1–10)?")
                                .font(.system(size: 16, weight: .heavy))
                                .foregroundColor(Color(hex: "#00BFFF"))
                            Spacer()
                            Button(action: {
                                showSaveSlotModal = false
                            }) {
                                Image(systemName: "xmark.circle.fill")
                                    .font(.system(size: 22))
                                    .foregroundColor(Color(hex: "#8B949E"))
                            }
                        }

                        Text("Tap a slot below to store your typed text or current clipboard item:")
                            .font(.system(size: 11.5))
                            .foregroundColor(Color(hex: "#C9D1D9"))

                        ScrollView {
                            VStack(spacing: 8) {
                                ForEach(1...10, id: \.self) { s in
                                    let txt = slotPreviews[s] ?? ""
                                    let hasData = !txt.isEmpty
                                    let sColor = PC_SLOT_COLORS[s - 1]

                                    Button(action: {
                                        saveClipboardToSlot(slotId: s)
                                        showSaveSlotModal = false
                                    }) {
                                        HStack(spacing: 10) {
                                            Text("#\(s)")
                                                .font(.system(size: 12, weight: .bold))
                                                .foregroundColor(.white)
                                                .frame(width: 34, height: 28)
                                                .background(sColor)
                                                .cornerRadius(5)

                                            Text(hasData ? "Current: \(txt)" : "[Empty — Tap to Save Here]")
                                                .font(.system(size: 13, weight: hasData ? .semibold : .regular))
                                                .foregroundColor(hasData ? .white : Color(hex: "#8B949E"))
                                                .lineLimit(1)
                                                .frame(maxWidth: .infinity, alignment: .leading)

                                            Text("SAVE")
                                                .font(.system(size: 11, weight: .heavy))
                                                .foregroundColor(.white)
                                                .padding(.horizontal, 10)
                                                .padding(.vertical, 5)
                                                .background(Color(hex: "#00BFFF"))
                                                .cornerRadius(5)
                                        }
                                        .padding(10)
                                        .background(Color(hex: "#12161C"))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 8)
                                                .stroke(sColor, lineWidth: 1)
                                        )
                                        .cornerRadius(8)
                                    }
                                }
                            }
                        }
                        .frame(maxHeight: 420)

                        Button(action: {
                            showSaveSlotModal = false
                        }) {
                            Text("Cancel")
                                .font(.system(size: 13, weight: .bold))
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .frame(height: 38)
                                .background(Color(hex: "#21262D"))
                                .cornerRadius(6)
                        }
                    }
                    .padding(16)
                    .background(Color(hex: "#161B22"))
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color(hex: "#00BFFF"), lineWidth: 2))
                    .cornerRadius(14)
                    .padding(.horizontal, 20)
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
                Text(upgradeReason.isEmpty ? "Current Plan: \(userTier.rawValue.uppercased())\n\nBasic includes 10 slots for text, links, images & SVG diagrams." : upgradeReason)
            }
        }
        .navigationViewStyle(StackNavigationViewStyle())
    }

    // ================= SUB-VIEWS =================

    @ViewBuilder
    private func quickPasteSlotButton(slotId: Int) -> some View {
        let content = slotPreviews[slotId]
        let hasData = content != nil && !content!.isEmpty
        let isSelectedForPaste = (activePasteSlot == slotId) && hasData
        let slotColor = PC_SLOT_COLORS[slotId - 1]

        Button(action: {
            dismissKeyboard()
            if hasData {
                copySlotToIphoneClipboard(slotId: slotId, alsoInsertInInputBox: false)
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
                        copySlotToIphoneClipboard(slotId: slotId, alsoInsertInInputBox: false)
                    }
            } else {
                Text("Slot \(slotId): [Empty]")
                    .font(.system(size: 12.5))
                    .foregroundColor(Color(hex: "#6E7681"))
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            if hasData {
                Button(action: {
                    dismissKeyboard()
                    copySlotToIphoneClipboard(slotId: slotId, alsoInsertInInputBox: false)
                }) {
                    Text(isSelectedForPaste ? "✓ Active" : "Paste This")
                        .font(.system(size: 10.5, weight: .bold))
                        .foregroundColor(isSelectedForPaste ? .black : .white)
                        .padding(.horizontal, 8)
                        .frame(height: 28)
                        .background(isSelectedForPaste ? Color(hex: "#39FF14") : Color(hex: "#00BFFF"))
                        .cornerRadius(4)
                }
            }

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
        self.pcIpAddress = UserDefaults.standard.string(forKey: "paired_pc_ip") ?? ""
        self.androidIpAddress = UserDefaults.standard.string(forKey: "paired_android_ip") ?? ""
        self.androidIpDraft = self.androidIpAddress
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
        // Keep the multi-representation pasteboard carrier up to date so the chosen activePasteSlot
        // is ALWAYS the string on UIPasteboard.general (not just the last copied item!)
        let activeTxt = (activePasteSlot > 0) ? (loaded[activePasteSlot] ?? "") : ""
        if !activeTxt.isEmpty {
            dataManager.syncPasteboardCarrier(activeSlotId: activePasteSlot, explicitActiveText: activeTxt)
        } else {
            dataManager.syncPasteboardCarrier()
        }
    }

    /// Saves text into `slotId` and preserves the user's chosen `activePasteSlot` on `UIPasteboard.general`.
    private func saveTextToSlot(slotId: Int, text: String) {
        let okStore = store.encryptAndStore(slot: slotId, text: text)
        let okGroup = dataManager.saveSlot(id: slotId, content: text)
        UINotificationFeedbackGenerator().notificationOccurred(.success)

        // If no active paste slot was selected yet, default to this slot; otherwise keep the user's chosen paste slot
        if activePasteSlot == 0 {
            activePasteSlot = slotId
            UserDefaults.standard.set(slotId, forKey: "ratt_active_paste_slot")
        }
        sendSlotToPc(slotId: slotId, text: text)
        sendSlotToAndroidIfPaired(slotId: slotId, text: text)
        refreshSlots()
        if okStore || okGroup {
            setStatus("✅ Saved to Slot #\(slotId)! Tap 'Choose Slot to Paste' to pick any slot (1–10) to paste.", ok: true)
        } else {
            setStatus("⚠️ Security Guard blocked unsafe link or script in Slot #\(slotId).", ok: false)
        }
    }

    /// Explicitly chooses `slotId` (1–10) as the Active Paste Slot and loads it into `UIPasteboard.general`.
    private func copySlotToIphoneClipboard(slotId: Int, alsoInsertInInputBox: Bool = false) {
        let txt = slotPreviews[slotId] ?? store.decryptSlot(slotId) ?? dataManager.loadSlot(id: slotId)?.content ?? ""
        guard !txt.isEmpty else {
            setStatus("Slot #\(slotId) is empty. Save text into Slot #\(slotId) first.", ok: false)
            return
        }
        activePasteSlot = slotId
        UserDefaults.standard.set(slotId, forKey: "ratt_active_paste_slot")
        if alsoInsertInInputBox {
            directInputText = txt
        }
        dataManager.syncPasteboardCarrier(activeSlotId: slotId, explicitActiveText: txt)
        UINotificationFeedbackGenerator().notificationOccurred(.success)
        setStatus("📋 Slot #\(slotId) (\"\(txt.prefix(24))\") is now Active in iPhone Clipboard — ready to Paste!", ok: true)
    }

    private func saveClipboardToSlot(slotId: Int) {
        let typed = directInputText.trimmingCharacters(in: .whitespacesAndNewlines)
        if !typed.isEmpty {
            saveTextToSlot(slotId: slotId, text: typed)
            directInputText = ""
            return
        }
        if let clip = UIPasteboard.general.string, !clip.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            saveTextToSlot(slotId: slotId, text: clip)
        } else {
            setStatus("Type text in the box in Section 2️⃣ first, then tap Save.", ok: false)
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
        sendSlotToAndroidIfPaired(slotId: slotId, text: "")
        refreshSlots()
        setStatus("🗑️ Cleared Slot #\(slotId)", ok: true)
    }

    private func clearAllSlots() {
        dataManager.clearAllSlots()
        store.clearAllSlots()
        activePasteSlot = 0
        UserDefaults.standard.set(0, forKey: "ratt_active_paste_slot")
        sendClearAllToPc()
        for s in 1...10 {
            sendSlotToAndroidIfPaired(slotId: s, text: "")
        }
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

    // ================= TWO-WAY WI-FI SYNC WITH RATT ANDROID (PORT 49210) =================

    private func sendSlotToAndroidIfPaired(slotId: Int, text: String) {
        guard !androidIpAddress.isEmpty else { return }
        let token = dataManager.getOrCreateSyncToken()
        guard let url = URL(string: "http://\(androidIpAddress):49210/sync_slot") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.timeoutInterval = 2.5
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
        let payload: [String: Any] = [
            "action": text.isEmpty ? "CLEAR_SLOT" : "SYNC_FROM_IOS",
            "slot_id": slotId,
            "content": text,
            "timestamp": Date().timeIntervalSince1970,
            "nonce": UUID().uuidString
        ]
        req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        URLSession.shared.dataTask(with: req).resume()
    }

    private func syncWithAndroidDevice(targetIp: String, platformLabel: String, port: Int) {
        setStatus("🔄 Connecting to \(platformLabel) (\(targetIp):\(port))...", ok: true)
        let token = dataManager.getOrCreateSyncToken()

        // 1. Push all filled iPhone slots to Android
        var pushedCount = 0
        for s in 1...10 {
            if let text = slotPreviews[s] ?? store.decryptSlot(s), !text.isEmpty {
                pushedCount += 1
                if let url = URL(string: "http://\(targetIp):\(port)/sync_slot") {
                    var req = URLRequest(url: url)
                    req.httpMethod = "POST"
                    req.timeoutInterval = 3.0
                    req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                    req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
                    let payload: [String: Any] = [
                        "action": "SYNC_FROM_IOS",
                        "slot_id": s,
                        "content": text,
                        "timestamp": Date().timeIntervalSince1970,
                        "nonce": UUID().uuidString
                    ]
                    req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
                    URLSession.shared.dataTask(with: req).resume()
                }
            }
        }

        // 2. Pull all filled Android slots into iPhone
        guard let pullUrl = URL(string: "http://\(targetIp):\(port)/get_all_slots") else { return }
        var pullReq = URLRequest(url: pullUrl)
        pullReq.httpMethod = "GET"
        pullReq.timeoutInterval = 3.5
        pullReq.setValue(token, forHTTPHeaderField: "X-RATT-Token")
        URLSession.shared.dataTask(with: pullReq) { data, resp, err in
            if let err = err {
                DispatchQueue.main.async {
                    self.setStatus("⚠️ Could not reach \(platformLabel) at \(targetIp):\(port) (\(err.localizedDescription)). Ensure both phones are on the same Wi-Fi/Hotspot.", ok: false)
                }
                return
            }
            var pulledCount = 0
            if let data = data,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let slots = json["slots"] as? [String: String] {
                for (k, v) in slots {
                    if let sId = Int(k), (1...10).contains(sId), !v.isEmpty {
                        _ = self.store.encryptAndStore(slot: sId, text: v)
                        _ = self.dataManager.saveSlot(id: sId, content: v)
                        pulledCount += 1
                    }
                }
            }
            DispatchQueue.main.async {
                self.refreshSlots()
                self.setStatus("✅ Synced with \(platformLabel) (\(targetIp)): Pushed \(pushedCount), Pulled \(pulledCount) slot(s)!", ok: true)
            }
        }.resume()
    }

    // ================= TWO-WAY WI-FI SYNC WITH RATT PC (PORT 49211 / 49210) =================

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
                    self.setStatus("✅ Pulled \(pulled) slot(s) from PC! Tap 'Choose Slot to Paste' to pick any slot.", ok: true)
                }
            }.resume()
        }
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
