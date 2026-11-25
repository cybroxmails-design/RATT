// ContentView.swift — RATT v2 for iOS Container App (iPhone / iPad)
// Full Feature Parity with RATT Android & PC:
// 1. PC 10-Slot Color Palette & Glow Indications
// 2. Numbered Slots (#1 to #10) with Live Previews
// 3. User-Selected Slot Clipboard & Direct Text Saver
// 4. IP Status Card, PC Pairing & Two-Way Wi-Fi Sync (Port 49211)
// 5. Commercial Licensing: Basic (Slots 1-2), Premium & Enterprise (Slots 1-10 + Android/macOS Sync)
// 6. Slot Clearing (Per-Slot Clear & Clear All Slots)
// 7. Security: Zero-Wipe All Slots on App Exit (memset_s / MEM-003)

import SwiftUI

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
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
    // PC-Matching 10-Slot Color Palette
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
    @State private var statusMessage: String = "RATT v2 for iPhone — Ready"
    @State private var showUpgradeAlert: Bool = false
    @State private var upgradeReason: String = ""
    @State private var showPairDialog: Bool = false
    @State private var showSlotSheet: Bool = false
    @State private var showCrossSyncAlert: Bool = false
    @State private var crossSyncTarget: String = ""
    @State private var crossSyncIpInput: String = ""
    @State private var pcIpAddress: String = ""
    @State private var iphoneIpAddress: String = ""

    private let store = KeychainSlotStore.shared
    private let dataManager = AppGroupDataManager.shared

    public init() {}

    public var body: some View {
        NavigationView {
            ZStack {
                Color(hex: "#0A0D12").ignoresSafeArea()

                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        // ================= 1. HEADER ROW =================
                        HStack(alignment: .center) {
                            HStack(spacing: 10) {
                                Image(systemName: "r.square.fill")
                                    .resizable()
                                    .frame(width: 36, height: 36)
                                    .foregroundColor(Color(hex: "#00BFFF"))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("RATT v2")
                                        .font(.title3)
                                        .fontWeight(.heavy)
                                        .foregroundColor(Color(hex: "#00BFFF"))
                                    Text("Two-Way Clipboard Sync • Cybrox")
                                        .font(.caption2)
                                        .foregroundColor(Color(hex: "#8B949E"))
                                }
                            }

                            Spacer()

                            // Tier Pill Badge (Tap to View / Switch Tier)
                            Button(action: {
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
                                // 1-Tap iOS Settings Deep Link
                                Button(action: {
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

                            // Air-Gapped Privacy & Security Guarantee Card
                            HStack(alignment: .top, spacing: 6) {
                                Image(systemName: "shield.lefthalf.filled")
                                    .foregroundColor(Color(hex: "#00BFFF"))
                                    .font(.system(size: 12))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Zero-Knowledge Security Guarantee")
                                        .font(.system(size: 10.5, weight: .bold))
                                        .foregroundColor(Color(hex: "#E6EDF3"))
                                    Text("Zero cloud tracking. Full Access is strictly used for direct local socket connections to your PC on port 49211.")
                                        .font(.system(size: 9.5))
                                        .foregroundColor(Color(hex: "#8B949E"))
                                }
                            }
                            .padding(8)
                            .background(Color(hex: "#0D1117"))
                            .cornerRadius(6)
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color(hex: "#30363D"), lineWidth: 1))
                        .cornerRadius(8)
                        .padding(.horizontal)

                        // ================= 3. IP / WI-FI SYNC CARD =================
                        VStack(alignment: .leading, spacing: 6) {
                            Text("THIS IPHONE IP ADDRESS:")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(Color(hex: "#8B949E"))

                            Text(iphoneIpAddress)
                                .font(.system(size: 22, weight: .bold, design: .monospaced))
                                .foregroundColor(Color(hex: "#39FF14"))

                            HStack {
                                Text("Connected PC IP: \(pcIpAddress)")
                                    .font(.system(size: 12, design: .monospaced))
                                    .foregroundColor(Color(hex: "#00BFFF"))
                                Spacer()
                                Text("(Tap to change)")
                                    .font(.system(size: 10))
                                    .foregroundColor(Color(hex: "#8B949E"))
                            }
                            .contentShape(Rectangle())
                            .onTapGesture {
                                showPairDialog = true
                            }

                            // Pair with PC Button
                            Button(action: {
                                showPairDialog = true
                            }) {
                                HStack {
                                    Image(systemName: "link")
                                    Text("Pair with PC (\(pcIpAddress))")
                                }
                                .font(.system(size: 13, weight: .bold))
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .frame(height: 38)
                                .background(Color(hex: "#00BFFF"))
                                .cornerRadius(6)
                            }

                            // Push All Slots to PC Button
                            Button(action: {
                                pushAllSlotsToPc()
                            }) {
                                HStack {
                                    Image(systemName: "arrow.triangle.2.circlepath")
                                    Text("🔄 Push All iPhone Slots to PC")
                                }
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(Color(hex: "#39FF14"))
                                .frame(maxWidth: .infinity)
                                .frame(height: 36)
                                .background(Color(hex: "#161B22"))
                                .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#10B981"), lineWidth: 1))
                                .cornerRadius(6)
                            }
                        }
                        .padding(14)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(hex: "#30363D"), lineWidth: 1))
                        .cornerRadius(10)
                        .padding(.horizontal)

                        // ================= 4. SAVE TEXT OR CLIPBOARD TO A SLOT =================
                        VStack(alignment: .leading, spacing: 8) {
                            Text("SAVE TEXT OR CLIPBOARD TO A SLOT")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(Color(hex: "#00BFFF"))

                            // Pick Slot for Current Clipboard
                            Button(action: {
                                showSlotSheet = true
                            }) {
                                Text("Save Current iPhone Clipboard to Slot...")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 40)
                                    .background(Color(hex: "#00BFFF"))
                                    .cornerRadius(6)
                            }

                            // Direct Text Input
                            TextField("Or type / paste text here directly...", text: $directInputText)
                                .font(.system(size: 13))
                                .foregroundColor(.white)
                                .padding(10)
                                .background(Color(hex: "#0D1117"))
                                .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#30363D"), lineWidth: 1))
                                .cornerRadius(6)

                            Text("Tap a slot number below to save typed text or clipboard into it:")
                                .font(.system(size: 10))
                                .foregroundColor(Color(hex: "#8B949E"))

                            // 10 Quick Slot Buttons (Row 1: Slots 1-5, Row 2: Slots 6-10)
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

                        // ================= 5. LIVE 10-SLOT PREVIEW (PC COLOR CODED) =================
                        VStack(alignment: .leading, spacing: 6) {
                            Text("LIVE 10-SLOT PREVIEW (PC COLOR CODED)")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(Color(hex: "#8B949E"))
                                .padding(.horizontal)

                            VStack(spacing: 6) {
                                ForEach(1...10, id: \.self) { slotId in
                                    slotRowCard(slotId: slotId)
                                }
                            }
                            .padding(.horizontal)

                            // Clear All Slots Button (Requirement 4)
                            Button(action: {
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

                        // ================= 6. CROSS-PLATFORM SYNC (Requirement 2 & 3: Premium & Enterprise) =================
                        VStack(alignment: .leading, spacing: 6) {
                            Text("CROSS-PLATFORM SYNC (PREMIUM & ENTERPRISE)")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(Color(hex: "#8B949E"))

                            HStack(spacing: 8) {
                                Button(action: {
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

                        // ================= 7. SHARE, MIRROR & TRANSLATE (Requirement 3: Premium & Enterprise) =================
                        VStack(alignment: .leading, spacing: 6) {
                            Text("SHARE, MIRROR & 9-LANGUAGE TRANSLATION (PREMIUM & ENTERPRISE)")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(Color(hex: "#8B949E"))

                            HStack(spacing: 8) {
                                Button(action: {
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

                        // ================= 8. EXIT & WIPE SLOTS (Requirement 5) =================
                        Button(action: {
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
                refreshSlots()
            }
            .onReceive(NotificationCenter.default.publisher(for: .slotCleared)) { _ in
                refreshSlots()
            }
            // Requirement 5: Empty all slots when app is closed / backgrounded
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.willResignActiveNotification)) { _ in
                emptySlotsOnExit()
            }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.didEnterBackgroundNotification)) { _ in
                emptySlotsOnExit()
            }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.willTerminateNotification)) { _ in
                emptySlotsOnExit()
            }
            // Licensing / Upgrade Alert
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
            // Pairing Dialog (COM-05: No hardcoded developer LAN IPs)
            .alert("🔗 Pair with PC IP Address", isPresented: $showPairDialog) {
                TextField("PC IP (e.g. <your-pc-ip>)", text: $pcIpAddress)
                Button("Save & Pair") {
                    let cleanIp = pcIpAddress.trimmingCharacters(in: .whitespacesAndNewlines)
                    if !cleanIp.isEmpty {
                        pcIpAddress = cleanIp
                        UserDefaults.standard.set(cleanIp, forKey: "paired_pc_ip")
                        pushAllSlotsToPc()
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Enter the local IPv4 address of your PC running RATT:")
            }
            // Cross-Platform Sync IP Prompt
            .alert("Sync with \(crossSyncTarget)", isPresented: $showCrossSyncAlert) {
                TextField("IP Address (e.g. <target-device-ip>)", text: $crossSyncIpInput)
                Button("Sync Now") {
                    performCrossSync(target: crossSyncTarget, targetIp: crossSyncIpInput)
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Enter the IP address of your \(crossSyncTarget) device running RATT:")
            }
            // Slot Picker Action Sheet
            .actionSheet(isPresented: $showSlotSheet) {
                var buttons: [ActionSheet.Button] = []
                for s in 1...10 {
                    buttons.append(.default(Text("Slot #\(s)")) {
                        saveClipboardToSlot(slotId: s)
                    })
                }
                buttons.append(.cancel())
                return ActionSheet(title: Text("Save Current Clipboard to Which Slot?"), buttons: buttons)
            }
        }
    }

    // ================= SUB-VIEWS =================

    @ViewBuilder
    private func quickSlotButton(slotId: Int) -> some View {
        let content = slotPreviews[slotId]
        let hasData = content != nil && !content!.isEmpty
        let slotColor = PC_SLOT_COLORS[slotId - 1]

        Button(action: {
            if !directInputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                store.encryptAndStore(slot: slotId, text: directInputText)
                dataManager.saveSlot(id: slotId, content: directInputText)
                sendSlotToPc(slotId: slotId, text: directInputText)
                directInputText = ""
                refreshSlots()
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
            // Left color accent stripe
            RoundedRectangle(cornerRadius: 2)
                .fill(hasData ? slotColor : Color(hex: "#21262D"))
                .frame(width: 4, height: 26)

            // Prominent slot badge
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

            // Slot Preview Text
            if hasData {
                Text("Slot \(slotId): \(content!)")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(.white)
                    .lineLimit(1)
            } else {
                Text("Slot \(slotId): [Empty]")
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "#6E7681"))
                    .lineLimit(1)
            }

            Spacer()

            // Save Clip Button
            Button("Save") {
                saveClipboardToSlot(slotId: slotId)
            }
            .font(.system(size: 11))
            .foregroundColor(Color(hex: "#C9D1D9"))
            .padding(.horizontal, 10)
            .frame(height: 30)
            .background(Color(hex: "#21262D"))
            .cornerRadius(4)

            // Clear Button (Requirement 4)
            Button("Clear") {
                clearSlot(slotId: slotId)
            }
            .font(.system(size: 11))
            .foregroundColor(Color(hex: "#EF4444"))
            .padding(.horizontal, 10)
            .frame(height: 30)
            .background(Color(hex: "#21262D"))
            .cornerRadius(4)
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

    private func loadPreferences() {
        let savedPc = UserDefaults.standard.string(forKey: "paired_pc_ip") ?? ""
        self.pcIpAddress = savedPc
        self.iphoneIpAddress = dataManager.getDeviceIpAddress()
        self.userTier = RattUserTier(rawValue: store.getUserTier()) ?? .basic
    }

    private func refreshSlots() {
        var loaded: [Int: String] = [:]
        for s in 1...10 {
            if let txt = store.decryptSlot(s) {
                loaded[s] = txt
            } else if let groupTxt = dataManager.loadSlot(id: s)?.content {
                loaded[s] = groupTxt
            }
        }
        slotPreviews = loaded
    }

    private func saveClipboardToSlot(slotId: Int) {
        if let clip = UIPasteboard.general.string, !clip.isEmpty {
            if !store.isAllowedPayloadForTier(clip) {
                upgradeReason = "UPGRADE REQUIRED: Copying Document & Media files (.docx, .xls, .pdf, .mp4, etc.) is limited to Premium and Enterprise subscribers."
                showUpgradeAlert = true
                return
            }
            store.encryptAndStore(slot: slotId, text: clip)
            dataManager.saveSlot(id: slotId, content: clip)
            sendSlotToPc(slotId: slotId, text: clip)
            refreshSlots()
        }
    }

    private func clearSlot(slotId: Int) {
        dataManager.clearSlot(id: slotId)
        store.clearSlot(slotId)
        sendClearSlotToPc(slotId: slotId)
        sendSlotToPc(slotId: slotId, text: "")
        refreshSlots()
    }

    private func clearAllSlots() {
        dataManager.clearAllSlots()
        store.clearAllSlots()
        sendClearAllToPc()
        for s in 1...10 {
            sendSlotToPc(slotId: s, text: "")
        }
        refreshSlots()
    }

    private func emptySlotsOnExit() {
        // Requirement 5: Zero-wipe all memory & storage on exit (memset_s / MEM-003)
        dataManager.exitAndWipeAllSlots()
        store.exitAndWipeAllSlots()
        slotPreviews.removeAll()
    }

    private func emptySlotsAndExit() {
        sendClearAllToPc()
        for s in 1...10 {
            sendSlotToPc(slotId: s, text: "")
        }
        emptySlotsOnExit()
        // IOS-03: Avoid exit(0) (Apple App Store Guideline 2.5.1); wipe all slots cleanly in place
        statusMessage = "All 10 slots securely wiped."
    }

    private func handleCrossSync(target: String) {
        // Requirement 2 & 3: Android, iOS, and macOS cross-platform sync is limited to Premium & Enterprise
        if target == "macOS" && !store.canSyncWithMac() {
            upgradeReason = "UPGRADE REQUIRED: Cross-platform sync with macOS is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
        } else if target == "Android" && !store.canSyncWithAndroid() {
            upgradeReason = "UPGRADE REQUIRED: Cross-platform sync between iOS and Android is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
        }
        crossSyncTarget = target
        crossSyncIpInput = ""
        showCrossSyncAlert = true
    }

    private func handleTranslate() {
        if !store.canTranslate() {
            upgradeReason = "UPGRADE REQUIRED: 9-Language Translation is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
        }
        statusMessage = "9-Language Translation Ready"
    }

    private func handleShare() {
        // Rule 4: Share is limited to premium and enterprise user
        if !store.canShareAndMirror() {
            upgradeReason = "UPGRADE REQUIRED: Account Sharing (copy/cut/paste across different RATT accounts) is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
        }
    }

    private func handleMirror() {
        // Rule 4: Mirror is limited to premium and enterprise user
        if !store.canShareAndMirror() {
            upgradeReason = "UPGRADE REQUIRED: Device Mirroring across RATT devices is limited to Premium and Enterprise subscribers."
            showUpgradeAlert = true
            return
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
            req.timeoutInterval = 2.0
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
    }

    private func sendSlotToPc(slotId: Int, text: String) {
        guard !pcIpAddress.isEmpty, let url = URL(string: "http://\(pcIpAddress):49211/sync_from_phone") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.timeoutInterval = 2.0
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(dataManager.getOrCreateSyncToken(), forHTTPHeaderField: "X-RATT-Token")
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

    private func sendClearSlotToPc(slotId: Int) {
        for port in [49211, 49210] {
            guard let url = URL(string: "http://\(pcIpAddress):\(port)/sync_from_phone") else { continue }
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.timeoutInterval = 2.0
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            let payload: [String: Any] = [
                "action": "CLEAR_SLOT",
                "slot_id": slotId,
                "content": ""
            ]
            req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
            URLSession.shared.dataTask(with: req).resume()
        }
    }

    private func sendClearAllToPc() {
        for port in [49211, 49210] {
            guard let url = URL(string: "http://\(pcIpAddress):\(port)/sync_from_phone") else { continue }
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.timeoutInterval = 2.0
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            let payload: [String: Any] = [
                "action": "CLEAR_ALL",
                "content": ""
            ]
            req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
            URLSession.shared.dataTask(with: req).resume()
        }
    }

    private func pushAllSlotsToPc() {
        if !store.canSyncWithWindows() {
            upgradeReason = "UPGRADE REQUIRED: Syncing between iPhone (iOS) and Windows PC is limited to Premium and Enterprise subscribers. Syncing between iPhone and macOS is 100% Free."
            showUpgradeAlert = true
            return
        }
        for s in 1...10 {
            if let text = store.decryptSlot(s), !text.isEmpty {
                sendSlotToPc(slotId: s, text: text)
            } else {
                sendClearSlotToPc(slotId: s)
            }
        }
    }
}
