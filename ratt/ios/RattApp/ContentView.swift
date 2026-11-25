// ContentView.swift — RATT v2 for iOS (iPhone X through iPhone 17 Pro Max)
// Simple, zero-setup user experience:
// - When the user clicks "📋 Paste from Slot", the slots that contain data are displayed
//   right on top of the keyboard in a transparent black background for the user to choose from.
// - Red 'X' button immediately clears any slot.
// - Touch anywhere to minimize the keyboard.
// - Direct Two-Way Wi-Fi Sync with RATT Android and RATT PC.

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
    @State private var statusMessage: String = "RATT v2 Ready • Click 'Paste from Slot' to choose a slot"
    @State private var statusIsSuccess: Bool = true
    @State private var showUpgradeAlert: Bool = false
    @State private var upgradeReason: String = ""
    @State private var showPairDialog: Bool = false
    @State private var pairIpDraft: String = ""
    @State private var androidIpDraft: String = ""
    @State private var androidIpAddress: String = ""
    @State private var showPasteOverlayAboveKeyboard: Bool = false
    @State private var showInlineSaveSlotsInput: Bool = false
    @State private var pcIpAddress: String = ""
    @State private var iphoneIpAddress: String = ""

    private let store = KeychainSlotStore.shared
    private let dataManager = AppGroupDataManager.shared
    private let autoSyncTimer = Timer.publish(every: 2.5, on: .main, in: .common).autoconnect()

    public init() {}

    /// Dismiss the iOS on-screen keyboard from anywhere in the app.
    private func dismissKeyboard() {
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }

    /// Returns only the slots (1..10) that currently contain data, in slot order.
    private var filledSlotsList: [(Int, String)] {
        var list: [(Int, String)] = []
        for s in 1...10 {
            if let txt = slotPreviews[s], !txt.isEmpty {
                list.append((s, txt))
            }
        }
        return list
    }

    public var body: some View {
        NavigationView {
            ZStack(alignment: .bottom) {
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
                                Text("📌 Active Paste Slot: Slot #\(activePasteSlot) (\"\(activeTxt)\")")
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

                        // ================= 2. TYPE, SAVE TO SLOT, OR PASTE FROM SLOT =================
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("SAVE TO SLOT OR PASTE FROM SLOT")
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
                                TextField("Type text here or click Paste from Slot...", text: $directInputText)
                                    .font(.system(size: 13))
                                    .foregroundColor(.white)
                                    .padding(10)
                                    .background(Color(hex: "#0D1117"))
                                    .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color(hex: "#30363D"), lineWidth: 1))
                                    .cornerRadius(6)

                                if !directInputText.isEmpty {
                                    Button(action: {
                                        directInputText = ""
                                    }) {
                                        Image(systemName: "xmark.circle.fill")
                                            .foregroundColor(Color(hex: "#8B949E"))
                                            .font(.system(size: 18))
                                    }
                                }
                            }

                            HStack(spacing: 8) {
                                Button(action: {
                                    showPasteOverlayAboveKeyboard = false
                                    showInlineSaveSlotsInput.toggle()
                                }) {
                                    HStack(spacing: 4) {
                                        Image(systemName: "square.and.arrow.down.fill")
                                        Text("Save to Slot")
                                    }
                                    .font(.system(size: 12.5, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 42)
                                    .background(Color(hex: "#00BFFF"))
                                    .cornerRadius(6)
                                }

                                Button(action: {
                                    showInlineSaveSlotsInput = false
                                    showPasteOverlayAboveKeyboard.toggle()
                                }) {
                                    HStack(spacing: 4) {
                                        Image(systemName: "doc.on.clipboard.fill")
                                        Text("Paste from Slot")
                                    }
                                    .font(.system(size: 12.5, weight: .bold))
                                    .foregroundColor(.black)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 42)
                                    .background(Color(hex: "#39FF14"))
                                    .cornerRadius(6)
                                }
                            }

                            if showInlineSaveSlotsInput {
                                VStack(alignment: .leading, spacing: 6) {
                                    HStack {
                                        Text("Tap which slot (1–10) to save into:")
                                            .font(.system(size: 11.5, weight: .bold))
                                            .foregroundColor(Color(hex: "#00BFFF"))
                                        Spacer()
                                        Button("Close ✕") {
                                            showInlineSaveSlotsInput = false
                                        }
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(Color(hex: "#8B949E"))
                                    }
                                    HStack(spacing: 5) {
                                        ForEach(1...5, id: \.self) { s in
                                            Button("Slot #\(s)") {
                                                saveClipboardToSlot(slotId: s)
                                                showInlineSaveSlotsInput = false
                                            }
                                            .font(.system(size: 11, weight: .bold))
                                            .foregroundColor(.white)
                                            .frame(maxWidth: .infinity)
                                            .frame(height: 34)
                                            .background(PC_SLOT_COLORS[s - 1])
                                            .cornerRadius(6)
                                        }
                                    }
                                    HStack(spacing: 5) {
                                        ForEach(6...10, id: \.self) { s in
                                            Button("Slot #\(s)") {
                                                saveClipboardToSlot(slotId: s)
                                                showInlineSaveSlotsInput = false
                                            }
                                            .font(.system(size: 11, weight: .bold))
                                            .foregroundColor(.white)
                                            .frame(maxWidth: .infinity)
                                            .frame(height: 34)
                                            .background(PC_SLOT_COLORS[s - 1])
                                            .cornerRadius(6)
                                        }
                                    }
                                }
                                .padding(10)
                                .background(Color.black.opacity(0.85))
                                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color(hex: "#00BFFF"), lineWidth: 1.5))
                                .cornerRadius(8)
                            }
                        }
                        .padding(14)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(hex: "#30363D"), lineWidth: 1))
                        .cornerRadius(10)
                        .padding(.horizontal)

                        // ================= 3. LIVE 10-SLOT PREVIEW =================
                        VStack(alignment: .leading, spacing: 6) {
                            Text("LIVE 10-SLOT PREVIEW (TAP 'PASTE' OR RED 'X' TO CLEAR)")
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

                        // ================= 4. PAIR & SYNC WITH RATT ANDROID =================
                        VStack(alignment: .leading, spacing: 8) {
                            Text("PAIR & SYNC WITH RATT ANDROID (TWO-WAY WI-FI SYNC)")
                                .font(.system(size: 10.5, weight: .bold))
                                .foregroundColor(Color(hex: "#39FF14"))

                            VStack(alignment: .leading, spacing: 8) {
                                Text("Enter the green IP Address shown on your RATT Android screen:")
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
                                    syncWithRemoteDevice(targetIp: cleanIp, platformLabel: "Android")
                                }) {
                                    HStack {
                                        Image(systemName: "arrow.triangle.2.circlepath")
                                        Text(androidIpAddress.isEmpty ? "🔗 Pair & Sync with Android Now" : "🔄 Sync All 10 Slots with Android (\(androidIpAddress))")
                                    }
                                    .font(.system(size: 12.5, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .frame(height: 40)
                                    .background(Color(hex: "#2563EB"))
                                    .cornerRadius(6)
                                }
                            }
                            .padding(10)
                            .background(Color(hex: "#0D1117"))
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color(hex: "#2563EB"), lineWidth: 1))
                            .cornerRadius(8)
                        }
                        .padding(14)
                        .background(Color(hex: "#161B22"))
                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color(hex: "#30363D"), lineWidth: 1))
                        .cornerRadius(10)
                        .padding(.horizontal)

                        // ================= 5. IP / WI-FI PC SYNC CARD =================
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
                                    Text("Enter the PC (or Android) IP Address:")
                                        .font(.system(size: 11, weight: .semibold))
                                        .foregroundColor(Color(hex: "#E6EDF3"))

                                    HStack(spacing: 8) {
                                        TextField("IP Address (e.g. 10.191.126.253)", text: $pairIpDraft)
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
                                                setStatus("Please enter a valid IP address.", ok: false)
                                                return
                                            }
                                            pcIpAddress = cleanIp
                                            UserDefaults.standard.set(cleanIp, forKey: "paired_pc_ip")
                                            showPairDialog = false
                                            syncWithRemoteDevice(targetIp: cleanIp, platformLabel: "PC / Phone")
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
                                        Text("Push Slots")
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
                                        Text("Pull Slots")
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

                        // ================= 6. EXIT & WIPE SLOTS =================
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
                        .padding(.bottom, 90)
                    }
                }

                // ================= TRANSPARENT BLACK OVERLAY ON TOP OF KEYBOARD =================
                // Appears directly on top of the keyboard in a transparent black background
                // when the user clicks "Paste from Slot"!
                if showPasteOverlayAboveKeyboard {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("📋 Choose Slot to Paste:")
                                .font(.system(size: 13, weight: .heavy))
                                .foregroundColor(Color(hex: "#39FF14"))
                            Spacer()
                            Button(action: {
                                showPasteOverlayAboveKeyboard = false
                            }) {
                                Text("Close ✕")
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(.white)
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 4)
                                    .background(Color.white.opacity(0.18))
                                    .cornerRadius(6)
                            }
                        }

                        if filledSlotsList.isEmpty {
                            Text("No slots contain data yet. Save text into a slot first.")
                                .font(.system(size: 12.5, weight: .medium))
                                .foregroundColor(.white)
                                .padding(.vertical, 8)
                        } else {
                            ScrollView(.vertical, showsIndicators: true) {
                                VStack(spacing: 6) {
                                    ForEach(filledSlotsList, id: \.0) { (sId, sText) in
                                        let sColor = PC_SLOT_COLORS[sId - 1]
                                        let isSelected = (activePasteSlot == sId)
                                        Button(action: {
                                            copySlotToIphoneClipboard(slotId: sId, alsoInsertInInputBox: true)
                                            showPasteOverlayAboveKeyboard = false
                                        }) {
                                            HStack(spacing: 8) {
                                                Text("#\(sId)")
                                                    .font(.system(size: 12, weight: .bold))
                                                    .foregroundColor(.white)
                                                    .frame(width: 34, height: 28)
                                                    .background(sColor)
                                                    .cornerRadius(5)

                                                Text(sText)
                                                    .font(.system(size: 13.5, weight: .bold))
                                                    .foregroundColor(.white)
                                                    .lineLimit(1)
                                                    .frame(maxWidth: .infinity, alignment: .leading)

                                                Text(isSelected ? "✓ ACTIVE" : "PASTE")
                                                    .font(.system(size: 10.5, weight: .heavy))
                                                    .foregroundColor(.black)
                                                    .padding(.horizontal, 9)
                                                    .padding(.vertical, 5)
                                                    .background(Color(hex: "#39FF14"))
                                                    .cornerRadius(5)
                                            }
                                            .padding(8)
                                            .background(Color.black.opacity(0.65))
                                            .overlay(RoundedRectangle(cornerRadius: 7).stroke(sColor, lineWidth: 1.5))
                                            .cornerRadius(7)
                                        }
                                        .buttonStyle(PlainButtonStyle())
                                    }
                                }
                            }
                            .frame(maxHeight: 190)
                        }
                    }
                    .padding(12)
                    .background(Color.black.opacity(0.84))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color(hex: "#39FF14"), lineWidth: 1.5)
                    )
                    .cornerRadius(12)
                    .padding(.horizontal, 10)
                    .padding(.bottom, 6)
                    .shadow(color: Color.black.opacity(0.6), radius: 10, x: 0, y: -3)
                }
            }
            .navigationBarHidden(true)
            .onAppear {
                _ = SecurityHardening.enforceRuntimeDefense()
                dataManager.startSyncListener(port: 49211)
                loadPreferences()
                refreshSlots()
            }
            .onReceive(autoSyncTimer) { _ in
                backgroundPollPairedPeers()
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
                Text(upgradeReason.isEmpty ? "Current Plan: \(userTier.rawValue.uppercased())" : upgradeReason)
            }
        }
        .navigationViewStyle(StackNavigationViewStyle())
    }

    // ================= SUB-VIEWS =================

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
                        copySlotToIphoneClipboard(slotId: slotId, alsoInsertInInputBox: true)
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
                    copySlotToIphoneClipboard(slotId: slotId, alsoInsertInInputBox: true)
                }) {
                    Text(isSelectedForPaste ? "✓ Active" : "Paste")
                        .font(.system(size: 10.5, weight: .bold))
                        .foregroundColor(isSelectedForPaste ? .black : .white)
                        .padding(.horizontal, 8)
                        .frame(height: 30)
                        .background(isSelectedForPaste ? Color(hex: "#39FF14") : Color(hex: "#00BFFF"))
                        .cornerRadius(4)
                }
                .buttonStyle(PlainButtonStyle())
            }

            Button(action: {
                saveClipboardToSlot(slotId: slotId)
            }) {
                Text("Save")
                    .font(.system(size: 10.5, weight: .semibold))
                    .foregroundColor(Color(hex: "#C9D1D9"))
                    .padding(.horizontal, 8)
                    .frame(height: 30)
                    .background(Color(hex: "#21262D"))
                    .cornerRadius(4)
            }
            .buttonStyle(PlainButtonStyle())

            // Red X Button — Immediately clears this slot
            Button(action: {
                clearSlot(slotId: slotId)
            }) {
                Text("X")
                    .font(.system(size: 11.5, weight: .heavy))
                    .foregroundColor(.white)
                    .frame(width: 30, height: 30)
                    .background(hasData ? Color(hex: "#EF4444") : Color(hex: "#21262D"))
                    .cornerRadius(4)
            }
            .buttonStyle(PlainButtonStyle())
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
        if self.androidIpDraft.isEmpty && !self.androidIpAddress.isEmpty {
            self.androidIpDraft = self.androidIpAddress
        }
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
            UserDefaults.standard.set(0, forKey: "ratt_active_paste_slot")
        }
        let activeTxt = (activePasteSlot > 0) ? (loaded[activePasteSlot] ?? "") : ""
        dataManager.syncPasteboardCarrier(activeSlotId: activePasteSlot, explicitActiveText: activeTxt)
    }

    private func saveTextToSlot(slotId: Int, text: String) {
        let okStore = store.encryptAndStore(slot: slotId, text: text)
        let okGroup = dataManager.saveSlot(id: slotId, content: text)
        UINotificationFeedbackGenerator().notificationOccurred(.success)

        if activePasteSlot == 0 {
            activePasteSlot = slotId
            UserDefaults.standard.set(slotId, forKey: "ratt_active_paste_slot")
        }
        sendSlotToAllPairedPeers(slotId: slotId, text: text)
        refreshSlots()
        if okStore || okGroup {
            setStatus("✅ Saved to Slot #\(slotId)! Click 'Paste from Slot' to choose which slot to paste.", ok: true)
        } else {
            setStatus("⚠️ Security Guard blocked unsafe link or script in Slot #\(slotId).", ok: false)
        }
    }

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
        setStatus("📋 Selected Slot #\(slotId) (\"\(txt.prefix(24))\") for Paste!", ok: true)
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
            setStatus("Type text in the box first, then tap Save to Slot.", ok: false)
        }
    }

    private func clearSlot(slotId: Int) {
        slotPreviews.removeValue(forKey: slotId)
        if activePasteSlot == slotId {
            activePasteSlot = 0
            UserDefaults.standard.set(0, forKey: "ratt_active_paste_slot")
        }
        store.clearSlot(slotId)
        dataManager.clearSlot(id: slotId)
        UINotificationFeedbackGenerator().notificationOccurred(.warning)
        sendClearSlotToAllPairedPeers(slotId: slotId)
        refreshSlots()
        setStatus("🗑️ Cleared Slot #\(slotId)", ok: true)
    }

    private func clearAllSlots() {
        slotPreviews.removeAll()
        activePasteSlot = 0
        UserDefaults.standard.set(0, forKey: "ratt_active_paste_slot")
        store.clearAllSlots()
        dataManager.clearAllSlots()
        sendClearAllToAllPairedPeers()
        refreshSlots()
        setStatus("🗑️ Cleared all 10 slots", ok: true)
    }

    private func emptySlotsOnExit() {
        slotPreviews.removeAll()
        activePasteSlot = 0
        dataManager.exitAndWipeAllSlots()
        store.exitAndWipeAllSlots()
    }

    private func emptySlotsAndExit() {
        sendClearAllToAllPairedPeers()
        emptySlotsOnExit()
        setStatus("🔒 All 10 slots securely wiped.", ok: true)
    }

    // ================= UNIFIED WI-FI PAIRING & SYNC (ANDROID PORT 49210 & PC PORT 49211) =================

    private var allPairedIps: [String] {
        var ips: [String] = []
        if !pcIpAddress.isEmpty { ips.append(pcIpAddress) }
        if !androidIpAddress.isEmpty && !ips.contains(androidIpAddress) { ips.append(androidIpAddress) }
        return ips
    }

    private func sendSlotToAllPairedPeers(slotId: Int, text: String) {
        let token = dataManager.getOrCreateSyncToken()
        for ip in allPairedIps {
            for port in [49210, 49211] {
                guard let url = URL(string: "http://\(ip):\(port)/sync_slot") else { continue }
                var req = URLRequest(url: url)
                req.httpMethod = "POST"
                req.timeoutInterval = 2.5
                req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
                let payload: [String: Any] = [
                    "action": text.isEmpty ? "CLEAR_SLOT" : "SYNC_FROM_IOS",
                    "slot_id": slotId,
                    "content": text,
                    "timestamp": Int(Date().timeIntervalSince1970),
                    "nonce": UUID().uuidString
                ]
                req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
                URLSession.shared.dataTask(with: req).resume()
            }
        }
    }

    private func sendClearSlotToAllPairedPeers(slotId: Int) {
        let token = dataManager.getOrCreateSyncToken()
        for ip in allPairedIps {
            for port in [49210, 49211] {
                guard let url = URL(string: "http://\(ip):\(port)/sync_slot") else { continue }
                var req = URLRequest(url: url)
                req.httpMethod = "POST"
                req.timeoutInterval = 2.0
                req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
                let payload: [String: Any] = [
                    "action": "CLEAR_SLOT",
                    "slot_id": slotId,
                    "content": "",
                    "timestamp": Int(Date().timeIntervalSince1970),
                    "nonce": UUID().uuidString
                ]
                req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
                URLSession.shared.dataTask(with: req).resume()
            }
        }
    }

    private func sendClearAllToAllPairedPeers() {
        let token = dataManager.getOrCreateSyncToken()
        for ip in allPairedIps {
            for port in [49210, 49211] {
                guard let url = URL(string: "http://\(ip):\(port)/sync_slot") else { continue }
                var req = URLRequest(url: url)
                req.httpMethod = "POST"
                req.timeoutInterval = 2.0
                req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
                let payload: [String: Any] = [
                    "action": "CLEAR_ALL",
                    "content": "",
                    "timestamp": Int(Date().timeIntervalSince1970),
                    "nonce": UUID().uuidString
                ]
                req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
                URLSession.shared.dataTask(with: req).resume()
            }
        }
    }

    private func syncWithRemoteDevice(targetIp: String, platformLabel: String) {
        setStatus("🔄 Connecting to \(platformLabel) (\(targetIp))...", ok: true)
        let myIp = dataManager.getDeviceIpAddress()
        let token = dataManager.getOrCreateSyncToken()

        for port in [49210, 49211] {
            if let pairUrl = URL(string: "http://\(targetIp):\(port)/pair") {
                var req = URLRequest(url: pairUrl)
                req.httpMethod = "POST"
                req.timeoutInterval = 2.5
                req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
                let payload: [String: Any] = [
                    "action": "PAIR",
                    "device": "iOS",
                    "phone_ip": myIp,
                    "sync_token": token,
                    "timestamp": Int(Date().timeIntervalSince1970),
                    "nonce": UUID().uuidString
                ]
                req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
                URLSession.shared.dataTask(with: req) { data, _, _ in
                    if let data = data,
                       let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                        if let remoteTok = json["sync_token"] as? String, !remoteTok.isEmpty {
                            self.dataManager.setSyncToken(remoteTok)
                        }
                        if let slots = json["slots"] as? [String: String] {
                            for (k, v) in slots {
                                if let sId = Int(k), (1...10).contains(sId), !v.isEmpty {
                                    _ = self.store.encryptAndStore(slot: sId, text: v)
                                    _ = self.dataManager.saveSlot(id: sId, content: v)
                                }
                            }
                            DispatchQueue.main.async {
                                self.refreshSlots()
                            }
                        }
                    }
                }.resume()
            }
        }

        var pushedCount = 0
        for s in 1...10 {
            if let text = slotPreviews[s] ?? store.decryptSlot(s), !text.isEmpty {
                pushedCount += 1
                for port in [49210, 49211] {
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
                            "timestamp": Int(Date().timeIntervalSince1970),
                            "nonce": UUID().uuidString
                        ]
                        req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
                        URLSession.shared.dataTask(with: req).resume()
                    }
                }
            }
        }

        for port in [49210, 49211] {
            guard let pullUrl = URL(string: "http://\(targetIp):\(port)/get_all_slots") else { continue }
            var pullReq = URLRequest(url: pullUrl)
            pullReq.httpMethod = "GET"
            pullReq.timeoutInterval = 3.5
            pullReq.setValue(token, forHTTPHeaderField: "X-RATT-Token")
            URLSession.shared.dataTask(with: pullReq) { data, resp, _ in
                guard let httpResp = resp as? HTTPURLResponse, httpResp.statusCode == 200,
                      let data = data,
                      let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let slots = json["slots"] as? [String: String] else {
                    return
                }
                var pulledCount = 0
                for (k, v) in slots {
                    if let sId = Int(k), (1...10).contains(sId), !v.isEmpty {
                        _ = self.store.encryptAndStore(slot: sId, text: v)
                        _ = self.dataManager.saveSlot(id: sId, content: v)
                        pulledCount += 1
                    }
                }
                DispatchQueue.main.async {
                    self.refreshSlots()
                    self.setStatus("✅ Synced with \(platformLabel) (\(targetIp)): Pushed \(pushedCount), Pulled \(pulledCount) slot(s)!", ok: true)
                }
            }.resume()
        }
    }

    private func backgroundPollPairedPeers() {
        let ips = allPairedIps
        guard !ips.isEmpty else { return }
        let token = dataManager.getOrCreateSyncToken()
        for ip in ips {
            for port in [49210, 49211] {
                guard let url = URL(string: "http://\(ip):\(port)/get_all_slots") else { continue }
                var req = URLRequest(url: url)
                req.httpMethod = "GET"
                req.timeoutInterval = 1.5
                req.setValue(token, forHTTPHeaderField: "X-RATT-Token")
                URLSession.shared.dataTask(with: req) { data, resp, _ in
                    guard let httpResp = resp as? HTTPURLResponse, httpResp.statusCode == 200,
                          let data = data,
                          let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                          let slots = json["slots"] as? [String: String] else {
                        return
                    }
                    var changed = false
                    for (k, v) in slots {
                        if let sId = Int(k), (1...10).contains(sId), !v.isEmpty {
                            let existing = self.store.decryptSlot(sId) ?? ""
                            if existing != v {
                                _ = self.store.encryptAndStore(slot: sId, text: v)
                                _ = self.dataManager.saveSlot(id: sId, content: v)
                                changed = true
                            }
                        }
                    }
                    if changed {
                        DispatchQueue.main.async {
                            self.refreshSlots()
                        }
                    }
                }.resume()
            }
        }
    }

    private func pullAllSlotsFromPc() {
        let ips = allPairedIps
        guard let target = ips.first else {
            showPairDialog = true
            setStatus("Please enter your PC or Android IP address first.", ok: false)
            return
        }
        syncWithRemoteDevice(targetIp: target, platformLabel: "Paired Device")
    }

    private func pushAllSlotsToPc() {
        let ips = allPairedIps
        guard let target = ips.first else {
            showPairDialog = true
            setStatus("Please enter your PC or Android IP address first.", ok: false)
            return
        }
        syncWithRemoteDevice(targetIp: target, platformLabel: "Paired Device")
    }
}
