// RattApp.swift — RATT v2 iOS Main Entry Point
// Includes App Switcher Privacy Shield (`IOS-01`), Anti-Reverse Engineering Guard,
// and Automatic Slot Zero-Wipe on App Exit (`Requirement 5`).

import SwiftUI

@main
struct RattApp: App {
    @Environment(\.scenePhase) private var scenePhase

    init() {
        _ = SecurityHardening.enforceRuntimeDefense()
    }

    var body: some Scene {
        WindowGroup {
            ZStack {
                ContentView()
                if scenePhase != .active {
                    // Privacy Shield prevents sensitive clipboard slots from being captured
                    // in the iOS App Switcher background screenshot (MASVS-STORAGE-2)
                    Color(red: 0.04, green: 0.05, blue: 0.07)
                        .ignoresSafeArea()
                        .overlay(
                            VStack(spacing: 8) {
                                Image(systemName: "lock.shield.fill")
                                    .font(.system(size: 42))
                                    .foregroundColor(Color(red: 0.0, green: 0.75, blue: 1.0))
                                Text("RATT v2 • Slots Protected")
                                    .font(.headline)
                                    .foregroundColor(.white)
                            }
                        )
                }
            }
            .onChange(of: scenePhase) { newPhase in
                switch newPhase {
                case .active:
                    _ = SecurityHardening.enforceRuntimeDefense()
                case .background:
                    // Requirement 5: Empty all slots when user exits / backgrounds the app
                    AppGroupDataManager.shared.exitAndWipeAllSlots()
                default:
                    break
                }
            }
        }
    }
}
