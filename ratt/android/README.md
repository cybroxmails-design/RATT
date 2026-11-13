# RATT v2 Android Floating Assist Overlay & Virtual Keyboard Companion

This module contains the production Android client application, Floating Assist Overlay (Option 2), and Virtual Keyboard (IME) for RATT v2 (`mobile_implimentation.pdf`).

## Architecture & Project Structure
- `app/src/main/java/com/cybrox/ratt/FloatingAssistService.kt`: Option 2 Floating Assist Overlay (`WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY`) with magnetic edge docking (`collapseToEdge()`), `revealBubble()`, `showRattTrayMenu()`, and `< 100ms` real-time deletion handling (`onSlotClearedBroadcast(slotId)`). Users keep **Samsung Keyboard** or **Gboard** active at all times.
- `app/src/main/java/com/cybrox/ratt/RattAccessibilityService.kt`: Monitors `AccessibilityEvent.TYPE_VIEW_FOCUSED` (`node.isEditable -> FloatingAssistService.revealBubble()`) and injects selected slot payloads directly via `AccessibilityNodeInfo.ACTION_SET_TEXT`.
- `app/src/main/java/com/cybrox/ratt/SlotRepository.kt`: Hardware-backed Android Keystore (`AES/GCM/NoPadding`, 256-bit key, 96-bit CSPRNG IV, 128-bit auth tag), Curve25519 ECDH + SHA-256 HKDF session key derivation, and `Arrays.fill()` memory sanitization on slot eviction (`MEM-003`).
- `app/src/main/java/com/cybrox/ratt/RattOverlayMenuView.kt`: 10-slot overlay grid view with live PC clipboard previews and `[Empty]` status badges.
- `app/src/main/java/com/cybrox/ratt/RattIME.kt`: Virtual keyboard service with 10-slot toolbar, `commitText()` injection, and hardware keystore encryption.
- `app/src/main/java/com/cybrox/ratt/ProcessTextActivity.kt`: Floating text selection menu integration (`ACTION_PROCESS_TEXT`).
- `app/src/main/res/xml/accessibility_service_config.xml`: Accessibility Service configuration for editable focus detection.
- `app/src/main/AndroidManifest.xml`: Declares `SYSTEM_ALERT_WINDOW`, `FloatingAssistService`, `RattAccessibilityService` (`BIND_ACCESSIBILITY_SERVICE`), `RattIME`, and `ProcessTextActivity`.

## How to Build `ratt.apk`

### Option 1: Using Android Studio (Recommended)
1. Open Android Studio.
2. Select **File -> Open...** and browse to `ratt/android`.
3. Allow Gradle to sync dependencies.
4. Click **Build -> Build Bundle(s) / APK(s) -> Build APK(s)**.
5. The generated file will be located at:
   `app/build/outputs/apk/debug/app-debug.apk` (rename to `ratt.apk`).

### Option 2: Command Line (with Android SDK & Gradle installed)
```bash
cd ratt/android
gradle assembleDebug
# or for release:
gradle assembleRelease
```

### Option 3: Automated via GitHub Actions
Pushing to your repository triggers the `.github/workflows/build-android.yml` workflow, which compiles and produces `ratt-v2-debug.apk` as a downloadable artifact automatically in the cloud.
