// ContentView.swift — RATT v2 for iOS Container App (iPhone X through iPhone 17 Pro Max)
// Full Feature Parity with RATT Android & PC:
// 1. Compatible with iPhone X (iOS 15/16) and all newer iPhones up to iPhone 17 Pro Max
// 2. Touch anywhere outside text fields to minimize keyboard + dedicated Hide Keyboard button
// 3. Two-Way Clipboard Saving:
//    - Save typed text or current iPhone Clipboard into any RATT Slot (1-10)
//    - Tap any Slot Row or its "Copy" button to copy that Slot directly to the iPhone Clipboard
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
    @State private var directInputText: String = ""
    @State private var statusMessage: String = "RATT v2 Ready • Tap any slot to copy to iPhone Clipboard"
    @State private var statusIsSuccess: Bool = true
    @State private var showUpgradeAlert: Bool = false
    @State private var upgradeReason: String = ""
    @State private var showPairDialog: Bool = false
    @State private var pairIpDraft: String = ""
    @State private var showSlotSheet: Bool = false
    @State private var showCrossSyncAlert: Bool = false
    @State private var crossSyncTarget: String = ""
    @State private var crossSyncIpInput: String = ""
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

                        // ================= LIVE STATUS BANNER =================
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

                        // ================= 2. KEYBOARD SETUP & PERMISSION DIAGNOSTICS =================
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                HStack(spacing: 6) {
                                    Circle()
                                        .fill(Color(hex: "#39FF14"))
                                        .frame(width: 8, height: 8)
                                    Text("RATT KEYBOARD & AIR-GAP DIAGNOSTICS")
                                        .font(.system(size: 11, weight: .bold))
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

                        // ================= 3. IP / WI-FI SYNC CARD =================
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
                                // Inline iOS 15–19 Compatible PC Pairing Box (works on iPhone X through iPhone 17 Pro Max)
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Enter the PC IP shown on your RATT PC toolbar (e.g. 192.168.x.x):")
                                        .font(.system(size: 11, weight: .semibold))
                                        .foregroundColor(Color(hex: "#E6EDF3"))

                                    HStack(spacing: 8) {
                                        TextField("PC IP Address (e.g. 192.168.1.100)", text: $pairIpDraft)
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

                        // ================= 4. SAVE TEXT OR CLIPBOARD TO A SLOT =================
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("SAVE TEXT OR CLIPBOARD TO A SLOT")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(Color(hex: "#00BFFF"))
                                Spacer()
                                Button("Hide Keyboard ⌨️↓") {
                                    dismissKeyboard()
                                }
                                .font(.system(size: 10.5, weight: .bold))
                                .foregroundColor(Color(hex: "#00BFFF"))
                            }

                            Button(action: {
                                dismissKeyboard()
                                showSlotSheet = true
                            }) {
                                Text("📥 Save Current iPhone Clipboard to Slot...")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 40)
                                    .background(Color(hex: "#00BFFF"))
                                    .cornerRadius(6)
                            }

                            HStack(spacing: 6) {
                                TextField("Or type / paste text here directly...", text: $directInputText)
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

                            Text("Tap a slot number below to save typed text (or iPhone clipboard) & copy to clipboard:")
                                .font(.system(size: 10))
                                .foregroundColor(Color(hex: "#8B949E"))

                            VStack(spacing: 6) {
                                HStack(spacing: 5) {
                                    ForEach(1...5, id: \.self) { slotId in
                                        quickSlotButton(slotId: slotId)
                                    }
                                }
                                HStack(spacing: 5) {
                                    ForEach(6...10, id: \.self) { slotId in
                                        quickSlotButton(slotId: slotId)
                                    }
                                }
                            }
                        }
                        .padding(14)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(hex: "#30363D"), lineWidth: 1))
                        .cornerRadius(10)
                        .padding(.horizontal)

                        // ================= 5. LIVE 10-SLOT PREVIEW (TAP TO COPY TO CLIPBOARD) =================
                        VStack(alignment: .leading, spacing: 6) {
                            Text("LIVE 10-SLOT PREVIEW (TAP 'COPY' TO COPY TO IPHONE CLIPBOARD)")
                                .font(.system(size: 10.5, weight: .bold))
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

                        // ================= 6. CROSS-PLATFORM SYNC =================
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

                        // ================= 7. SHARE, MIRROR & TRANSLATE =================
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
            // Only wipe slots when the app is actually terminated (or via the Exit button),
            // NOT when switching apps to paste or when iOS shows the "Allow Paste" popup!
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
            .actionSheet(isPresented: $showSlotSheet) {
                var buttons: [ActionSheet.Button] = []
                for s in 1...10 {
                    buttons.append(.default(Text("Slot #\(s)")) {
                        saveClipboardToSlot(slotId: s)
                    })
                }
                buttons.append(.cancel())
                return ActionSheet(title: Text("Save Current iPhone Clipboard to Which Slot?"), buttons: buttons)
            }
        }
        .navigationViewStyle(StackNavigationViewStyle())
    }

    // ================= SUB-VIEWS =================

    @ViewBuilder
    private func quickSlotButton(slotId: Int) -> some View {
        let content = slotPreviews[slotId]
        let hasData = content != nil && !content!.isEmpty
        let slotColor = PC_SLOT_COLORS[slotId - 1]

        Button(action: {
            dismissKeyboard()
            let typed = directInputText.trimmingCharacters(in: .whitespacesAndNewlines)
            if !typed.isEmpty {
                saveTextToSlotAndClipboard(slotId: slotId, text: typed)
                directInputText = ""
            } else if hasData {
                copySlotToIphoneClipboard(slotId: slotId)
            } else {
                saveClipboardToSlot(slotId: slotId)
            }
        }) {
            Text(hasData ? "● #\(slotId)" : "Slot \(slotId)")
                .font(.system(size: 11, weight: hasData ? .bold : .regular))
                .foregroundColor(hasData ? .white : Color(hex: "#8B949E"))
                .frame(maxWidth: .infinity)
                .frame(height: 36)
                .background(hasData ? Color(hex: "#133024") : Color(hex: "#161B22"))
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(hasData ? slotColor : Color(hex: "#30363D"), lineWidth: 1)
                )
                .cornerRadius(6)
        }
    }

    @ViewBuilder
    private func slotRowCard(slotId: Int) -> some View {
        let content = slotPreviews[slotId]
        let hasData = content != nil && !content!.isEmpty
        let slotColor = PC_SLOT_COLORS[slotId - 1]

        HStack(spacing: 8) {
            RoundedRectangle(cornerRadius: 2)
                .fill(hasData ? slotColor : Color(hex: "#21262D"))
                .frame(width: 4, height: 26)

            Text("#\(slotId)")
                .font(.system(size: 11.5, weight: .bold))
                .foregroundColor(hasData ? .white : slotColor)
                .frame(width: 32, height: 24)
                .background(hasData ? slotColor : Color(hex: "#161B22"))
                .overlay(
                    RoundedRectangle(cornerRadius: 4)
                        .stroke(slotColor, lineWidth: 1)
                )
                .cornerRadius(4)

            if hasData {
                Text(content!)
                    .font(.system(size: 13, weight: .bold))
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
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "#6E7681"))
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            if hasData {
                // Dedicated Copy Button -> Writes slot directly to iPhone System Clipboard
                Button(action: {
                    dismissKeyboard()
                    copySlotToIphoneClipboard(slotId: slotId)
                }) {
                    Text("Copy")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.white)
                        .padding(.horizontal, 10)
                        .frame(height: 30)
                        .background(Color(hex: "#00BFFF"))
                        .cornerRadius(4)
                }
            }

            // Save Button -> Saves typed text or current iPhone Clipboard into this Slot
            Button(action: {
                dismissKeyboard()
                let typed = directInputText.trimmingCharacters(in: .whitespacesAndNewlines)
                if !typed.isEmpty {
                    saveTextToSlotAndClipboard(slotId: slotId, text: typed)
                    directInputText = ""
                } else {
                    saveClipboardToSlot(slotId: slotId)
                }
            }) {
                Text("Save")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(Color(hex: "#C9D1D9"))
                    .padding(.horizontal, 9)
                    .frame(height: 30)
                    .background(Color(hex: "#21262D"))
                    .cornerRadius(4)
            }

            Button(action: {
                dismissKeyboard()
                clearSlot(slotId: slotId)
            }) {
                Text("Clear")
                    .font(.system(size: 11))
                    .foregroundColor(Color(hex: "#EF4444"))
                    .padding(.horizontal, 8)
                    .frame(height: 30)
                    .background(Color(hex: "#21262D"))
                    .cornerRadius(4)
            }
        }
        .padding(8)
        .background(hasData ? Color(hex: "#10241B") : Color(hex: "#12161C"))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(hasData ? slotColor : Color(hex: "#21262D"), lineWidth: hasData ? 2 : 1)
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
    }

    /// Saves text into a RATT Slot AND copies it to the iPhone System Clipboard (`UIPasteboard.general`).
    private func saveTextToSlotAndClipboard(slotId: Int, text: String) {
        if !store.isAllowedPayloadForTier(text) {
            upgradeReason = "UPGRADE REQUIRED: Copying Document & Media files (.docx, .xls, .pdf, .mp4, etc.) is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
        }
        let okStore = store.encryptAndStore(slot: slotId, text: text)
        let okGroup = dataManager.saveSlot(id: slotId, content: text)
        UIPasteboard.general.string = text
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.success)
        sendSlotToPc(slotId: slotId, text: text)
        refreshSlots()
        if okStore || okGroup {
            setStatus("✅ Saved to Slot #\(slotId) & Copied to iPhone Clipboard!", ok: true)
        } else {
            setStatus("⚠️ Security Guard blocked unsafe link or script in Slot #\(slotId).", ok: false)
        }
    }

    /// Copies an existing RATT Slot directly into the iPhone System Clipboard (`UIPasteboard.general`).
    private func copySlotToIphoneClipboard(slotId: Int) {
        if let slotObj = dataManager.loadSlot(id: slotId) {
            if slotObj.kind == "image", let b64 = slotObj.dataBase64, let imgData = Data(base64Encoded: b64), let img = UIImage(data: imgData) {
                UIPasteboard.general.image = img
                UINotificationFeedbackGenerator().notificationOccurred(.success)
                setStatus("📋 Copied Image from Slot #\(slotId) to iPhone Clipboard!", ok: true)
                return
            }
            if !slotObj.content.isEmpty {
                UIPasteboard.general.string = slotObj.content
                UINotificationFeedbackGenerator().notificationOccurred(.success)
                setStatus("📋 Copied Slot #\(slotId) to iPhone Clipboard — ready to paste!", ok: true)
                return
            }
        }
        if let txt = slotPreviews[slotId] ?? store.decryptSlot(slotId), !txt.isEmpty {
            UIPasteboard.general.string = txt
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            setStatus("📋 Copied Slot #\(slotId) to iPhone Clipboard — ready to paste!", ok: true)
        } else {
            setStatus("Slot #\(slotId) is empty. Type text or copy something first.", ok: false)
        }
    }

    /// Reads the current iPhone System Clipboard (`UIPasteboard.general`) and saves it into `slotId`.
    private func saveClipboardToSlot(slotId: Int) {
        let typed = directInputText.trimmingCharacters(in: .whitespacesAndNewlines)
        if !typed.isEmpty {
            saveTextToSlotAndClipboard(slotId: slotId, text: typed)
            directInputText = ""
            return
        }
        if let clip = UIPasteboard.general.string, !clip.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            saveTextToSlotAndClipboard(slotId: slotId, text: clip)
        } else if let img = UIPasteboard.general.image, let pngData = img.pngData() {
            let b64 = pngData.base64EncodedString()
            let desc = "Image [\(Int(img.size.width))x\(Int(img.size.height))]"
            _ = store.encryptAndStore(slot: slotId, text: desc)
            _ = dataManager.saveSlot(id: slotId, content: desc, kind: "image", dataBase64: b64, mimeType: "image/png", byteSize: pngData.count)
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            refreshSlots()
            setStatus("✅ Saved iPhone Clipboard Image to Slot #\(slotId)!", ok: true)
        } else {
            setStatus("iPhone Clipboard is empty. Type text in the box above or copy text in any app first.", ok: false)
        }
    }

    private func clearSlot(slotId: Int) {
        dataManager.clearSlot(id: slotId)
        store.clearSlot(slotId)
        sendClearSlotToPc(slotId: slotId)
        refreshSlots()
        setStatus("🗑️ Cleared Slot #\(slotId)", ok: true)
    }

    private func clearAllSlots() {
        dataManager.clearAllSlots()
        store.clearAllSlots()
        sendClearAllToPc()
        refreshSlots()
        setStatus("🗑️ Cleared all 10 slots", ok: true)
    }

    private func emptySlotsOnExit() {
        dataManager.exitAndWipeAllSlots()
        store.exitAndWipeAllSlots()
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

    /// Handshake with RATT PC on port 49211 / 49210 to exchange sync token and synchronize all 10 slots.
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
            URLSession.shared.dataTask(with: req) { data, resp, err in
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
                    if let slot1 = self.store.decryptSlot(1), !slot1.isEmpty {
                        UIPasteboard.general.string = slot1
                    }
                    self.setStatus("✅ Pulled \(pulled) slot(s) from PC (\(self.pcIpAddress))!", ok: true)
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
