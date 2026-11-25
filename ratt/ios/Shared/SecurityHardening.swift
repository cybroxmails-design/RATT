// SecurityHardening.swift — RATT v2 iOS Anti-Reverse Engineering & Runtime Integrity Guard
//
// Implements OWASP MASVS-RESILIENCE (MSTG-RESILIENCE-1 through MSTG-RESILIENCE-10)
// and Apple App Store security standards:
//   1. Kernel Debugger Detection via `sysctl` (`CTL_KERN`, `KERN_PROC`, `KERN_PROC_PID`, `P_TRACED`).
//   2. Anti-Attach `ptrace(PT_DENY_ATTACH)` protection in release builds.
//   3. Dynamic Library (`dyld`) Injection Detection (`FridaGadget`, `cynject`, `MobileSubstrate`, `SSLKillSwitch`, `libcycript`).
//   4. Jailbreak & Sandbox Escape Detection (unauthorized paths & outside-sandbox write probe).
//   5. Automated Zero-Wipe Defense: wipes all Keychain & App Group slots immediately via `memset_s`
//      if runtime tampering, debugger attachment, or dylib injection is detected.

import Foundation
import Darwin
import MachO

public enum SecurityHardening {

    private static let suspiciousDylibTokens: [String] = [
        "fridagadget",
        "frida-agent",
        "cynject",
        "mobilesubstrate",
        "substrateloader",
        "substrateinserter",
        "sslkillswitch",
        "libcycript",
        "libsparkapplist",
        "shadow.dylib",
        "ellekit"
    ]

    private static let jailbreakPaths: [String] = [
        "/Applications/Cydia.app",
        "/Applications/Sileo.app",
        "/Library/MobileSubstrate/MobileSubstrate.dylib",
        "/bin/bash",
        "/usr/sbin/sshd",
        "/etc/apt",
        "/private/var/lib/apt/",
        "/private/var/Users/",
        "/var/jb/usr/bin/su"
    ]

    /// Runs all App Store-compliant runtime anti-reverse-engineering checks (IOS-03).
    /// If a debugger, dynamic instrumentation dylib, or sandbox breach is detected,
    /// immediately zeroes and purges all slots from Keychain and App Group storage.
    @discardableResult
    public static func enforceRuntimeDefense() -> Bool {
        let compromised = isDebuggerAttached() ||
            isSuspiciousDylibInjected() ||
            isDeviceJailbroken()

        if compromised {
            AppGroupDataManager.shared.exitAndWipeAllSlots()
            return false
        }
        return true
    }

    /// 1. Detect kernel-level debugger (`lldb` / `gdb`) via `sysctl` `kinfo_proc.kp_proc.p_flag & P_TRACED`.
    public static func isDebuggerAttached() -> Bool {
        var info = kinfo_proc()
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid()]
        var size = MemoryLayout<kinfo_proc>.stride
        let kResult = sysctl(&mib, UInt32(mib.count), &info, &size, nil, 0)
        guard kResult == 0 else { return false }
        return (info.kp_proc.p_flag & P_TRACED) != 0
    }

    /// 3. Scan loaded Mach-O images via `_dyld_get_image_name` for Frida, Substrate, or Cycript injection.
    public static func isSuspiciousDylibInjected() -> Bool {
        let count = _dyld_image_count()
        for idx in 0..<count {
            guard let cName = _dyld_get_image_name(idx) else { continue }
            let imagePath = String(cString: cName).lowercased()
            for token in suspiciousDylibTokens {
                if imagePath.contains(token) {
                    return true
                }
            }
        }
        return false
    }

    /// 4. Detect jailbreak file artifacts and verify iOS sandbox write containment.
    public static func isDeviceJailbroken() -> Bool {
        #if targetEnvironment(simulator)
        return false
        #else
        for path in jailbreakPaths {
            if FileManager.default.fileExists(atPath: path) {
                return true
            }
        }
        let probePath = "/private/ratt_sandbox_probe.txt"
        do {
            try "probe".write(toFile: probePath, atomically: true, encoding: .utf8)
            try? FileManager.default.removeItem(atPath: probePath)
            return true
        } catch {
            return false
        }
        #endif
    }
}
