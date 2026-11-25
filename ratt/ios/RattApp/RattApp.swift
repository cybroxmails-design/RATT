// RattApp.swift — RATT v2 iOS Main Entry Point
// Compatible with iPhone X (iOS 15/16) through iPhone 17 Pro Max (iOS 18/19+).
// Includes App Switcher Privacy Shield (`IOS-01`), Anti-Reverse Engineering Guard,
// and Automatic Slot Zero-Wipe on Explicit App Exit (`Requirement 5`).

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
                if scenePhase == .background {
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
                if newPhase == .active {
                    _ = SecurityHardening.enforceRuntimeDefense()
                }
            }
        }
    }
}
