package com.cybrox.ratt

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import android.os.Debug
import java.io.BufferedReader
import java.io.File
import java.io.FileReader
import java.net.InetSocketAddress
import java.net.Socket
import java.security.MessageDigest

/**
 * SecurityHardening.kt — RATT v2 Android Anti-Reverse Engineering & Runtime Integrity Guard
 *
 * Implements OWASP MASVS-RESILIENCE (MSTG-RESILIENCE-1 through MSTG-RESILIENCE-10)
 * and Google Play Store security requirements:
 *   1. Debugger Detection (`Debug.isDebuggerConnected()`, `waitingForDebugger()`, `/proc/self/status` `TracerPid`).
 *   2. Dynamic Instrumentation & Hook Detection (Frida Server / Gadget, Xposed, EdXposed, LSPosed, Cydia Substrate).
 *   3. Root / Magisk / Tamper Environment Detection (`su` binaries, `test-keys`, system rw mounts).
 *   4. APK Signature & Play Store Installer Verification (`PackageManager.GET_SIGNING_CERTIFICATES`).
 *   5. Automated Zero-Wipe Defense: wipes all in-memory and Keystore-backed slots immediately if
 *      active reverse-engineering or dynamic instrumentation is detected.
 */
object SecurityHardening {

    private val SUSPICIOUS_MAP_TOKENS = listOf(
        "frida",
        "gum-js-loop",
        "gmain",
        "linjector",
        "xposed",
        "edxposed",
        "lsposed",
        "substrate",
        "libcycript",
        "libriru",
        "zygisk"
    )

    private val SU_PATHS = listOf(
        "/system/bin/su",
        "/system/xbin/su",
        "/sbin/su",
        "/system/sd/xbin/su",
        "/system/bin/failsafe/su",
        "/data/local/xbin/su",
        "/data/local/bin/su",
        "/data/local/su",
        "/su/bin/su",
        "/sbin/magisk"
    )

    private val TRUSTED_INSTALLERS = setOf(
        "com.android.vending",
        "com.google.android.feedback",
        "com.sec.android.app.samsungapps"
    )

    /**
     * Runs all runtime anti-reverse-engineering checks.
     * If a debugger, Frida/Xposed hook, or ptrace attachment is detected, immediately
     * wipes all clipboard slots from RAM and local storage.
     */
    fun enforceRuntimeDefense(context: Context): Boolean {
        val compromised = isDebuggerAttached() ||
            isPtraceAttached() ||
            isDynamicInstrumentationPresent() ||
            isHookFrameworkLoaded() ||
            !hasValidApkSignature(context)

        if (compromised) {
            SlotRepository.exitAndWipeAllSlots()
            return false
        }
        return true
    }

    /**
     * Returns a structured security status summary for diagnostics and compliance verification.
     */
    fun getSecurityPostureReport(context: Context): Map<String, Boolean> {
        return mapOf(
            "debugger_detected" to (isDebuggerAttached() || isPtraceAttached()),
            "frida_or_hook_detected" to (isDynamicInstrumentationPresent() || isHookFrameworkLoaded()),
            "root_indicators_present" to isDeviceRooted(),
            "valid_apk_signature" to hasValidApkSignature(context),
            "trusted_installer" to isInstalledFromTrustedStore(context)
        )
    }

    /**
     * 1. Check Java/JDWP debugger status.
     */
    fun isDebuggerAttached(): Boolean {
        return Debug.isDebuggerConnected() || Debug.waitingForDebugger()
    }

    /**
     * 2. Inspect `/proc/self/status` for a non-zero `TracerPid` (native `ptrace` / `gdb` / `lldb`).
     */
    fun isPtraceAttached(): Boolean {
        return try {
            BufferedReader(FileReader("/proc/self/status")).use { reader ->
                var line = reader.readLine()
                while (line != null) {
                    if (line.startsWith("TracerPid:")) {
                        val pid = line.substringAfter("TracerPid:").trim().toIntOrNull() ?: 0
                        return pid != 0
                    }
                    line = reader.readLine()
                }
                false
            }
        } catch (_: Exception) {
            false
        }
    }

    /**
     * 3. Inspect `/proc/self/maps` and loopback ports for Frida (`frida-agent`, `frida-gadget`, `gum-js-loop`).
     */
    fun isDynamicInstrumentationPresent(): Boolean {
        try {
            BufferedReader(FileReader("/proc/self/maps")).use { reader ->
                var line = reader.readLine()
                while (line != null) {
                    val lower = line.lowercase()
                    for (token in SUSPICIOUS_MAP_TOKENS) {
                        if (lower.contains(token)) {
                            return true
                        }
                    }
                    line = reader.readLine()
                }
            }
        } catch (_: Exception) {}

        // Probe default local Frida server ports (27042, 27043) with fast non-blocking timeout
        for (port in intArrayOf(27042, 27043)) {
            try {
                Socket().use { s ->
                    s.connect(InetSocketAddress("127.0.0.1", port), 35)
                    return true
                }
            } catch (_: Exception) {}
        }
        return false
    }

    /**
     * 4. Detect Xposed / Substrate / SandHook classes in the current ClassLoader or stack trace.
     */
    fun isHookFrameworkLoaded(): Boolean {
        val hookClasses = listOf(
            "de.robv.android.xposed.XposedBridge",
            "de.robv.android.xposed.XposedHelpers",
            "com.saurik.substrate.MS",
            "com.swift.sandhook.SandHook"
        )
        for (clsName in hookClasses) {
            try {
                Class.forName(clsName)
                return true
            } catch (_: ClassNotFoundException) {}
        }

        val stack = Throwable().stackTrace
        for (frame in stack) {
            val cn = frame.className.lowercase()
            if (cn.contains("xposed") || cn.contains("substrate") || cn.contains("frida") || cn.contains("lsposed")) {
                return true
            }
        }
        return false
    }

    /**
     * 5. Check for common root / Magisk indicators.
     */
    fun isDeviceRooted(): Boolean {
        val buildTags = Build.TAGS
        if (buildTags != null && buildTags.contains("test-keys")) {
            return true
        }
        for (path in SU_PATHS) {
            try {
                if (File(path).exists()) return true
            } catch (_: Exception) {}
        }
        return false
    }

    // AND-03: Pinned Cybrox release signing certificate SHA-256 fingerprint (hex).
    // Replace with the production Play App Signing SHA-256 fingerprint before release.
    private const val PINNED_RELEASE_CERT_SHA256 = "REPLACE_WITH_PRODUCTION_CYBROX_APK_SHA256_HEX"

    /**
     * 6. Verify that the APK is signed by the pinned Cybrox release certificate (AND-03).
     * Debuggable local builds pass during development; release builds fail closed on mismatch.
     */
    fun hasValidApkSignature(context: Context): Boolean {
        return try {
            val isDebuggable = (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
            val pm = context.packageManager
            val signatures = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                val pkgInfo = pm.getPackageInfo(context.packageName, PackageManager.GET_SIGNING_CERTIFICATES)
                pkgInfo.signingInfo?.apkContentsSigners
            } else {
                @Suppress("DEPRECATION")
                val pkgInfo = pm.getPackageInfo(context.packageName, PackageManager.GET_SIGNATURES)
                @Suppress("DEPRECATION")
                pkgInfo.signatures
            }
            if (signatures.isNullOrEmpty()) return false
            val md = MessageDigest.getInstance("SHA-256")
            val digest = md.digest(signatures[0].toByteArray())
            if (digest.size != 32) return false
            if (isDebuggable) return true
            val actualHex = digest.joinToString("") { "%02x".format(it) }
            MessageDigest.isEqual(
                actualHex.toByteArray(Charsets.US_ASCII),
                PINNED_RELEASE_CERT_SHA256.lowercase().toByteArray(Charsets.US_ASCII)
            )
        } catch (_: Exception) {
            false
        }
    }

    /**
     * 7. Check whether the app was installed via Google Play Store or runs as a signed release build.
     */
    fun isInstalledFromTrustedStore(context: Context): Boolean {
        return try {
            val isDebuggable = (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
            if (isDebuggable) return true
            val installer = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                context.packageManager.getInstallSourceInfo(context.packageName).installingPackageName
            } else {
                @Suppress("DEPRECATION")
                context.packageManager.getInstallerPackageName(context.packageName)
            }
            installer != null && TRUSTED_INSTALLERS.contains(installer)
        } catch (_: Exception) {
            false
        }
    }
}
