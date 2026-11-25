package com.cybrox.ratt

import android.app.Activity
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Toast

/**
 * RATT v2 Transparent Clipboard Capture Activity (`SaveClipActivity.kt`).
 *
 * Fix for Android 10-15 Window Focus Requirement:
 * In Android 10+, `ClipboardManager.getPrimaryClip()` strictly enforces that the calling process
 * must have ACTIVE WINDOW FOCUS (`hasWindowFocus() == true`).
 *
 * In `onCreate()`, window focus is NOT yet established, which caused `primaryClip` to return null
 * and trigger the "Phone clipboard is empty!" toast.
 *
 * By attaching a minimal view and reading the clipboard inside `onWindowFocusChanged(true)`,
 * Android OS officially validates that RATT is the focused window and immediately returns
 * the real, updated clipboard text!
 */
class SaveClipActivity : Activity() {

    private var targetSlotId = 1
    private var isProcessed = false
    private var hasRetried = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        SlotRepository.init(this)
        targetSlotId = intent?.getIntExtra("target_slot_id", 1) ?: 1

        // Attaching a minimal transparent view ensures the window decor attaches and receives focus
        val dummyView = View(this).apply {
            setBackgroundColor(android.graphics.Color.TRANSPARENT)
        }
        setContentView(dummyView)

        // Safety fallback: if onWindowFocusChanged doesn't fire within 350ms, process and finish
        Handler(Looper.getMainLooper()).postDelayed({
            if (!isProcessed) {
                processClipboardAndFinish()
            }
        }, 350)
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus && !isProcessed) {
            processClipboardAndFinish()
        }
    }

    private fun processClipboardAndFinish() {
        if (isProcessed) return

        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
        val clipData = clipboard?.primaryClip

        // AND-02: Respect Android 13+ EXTRA_IS_SENSITIVE flag for passwords/OTPs
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            val isSensitive = clipData?.description?.extras?.getBoolean(
                android.content.ClipDescription.EXTRA_IS_SENSITIVE,
                false
            ) == true
            if (isSensitive) {
                isProcessed = true
                Toast.makeText(this, "Sensitive clipboard content (password/OTP) is protected and not synced.", Toast.LENGTH_SHORT).show()
                finish()
                return
            }
        }

        if (clipData != null && clipData.itemCount > 0) {
            val item = clipData.getItemAt(0)
            val uri = item.uri
            val clipMimeType = clipboard.primaryClipDescription?.let { desc ->
                if (desc.mimeTypeCount > 0) desc.getMimeType(0) else null
            } ?: ""
            if ((uri != null || clipMimeType.startsWith("image/")) && item.text.isNullOrBlank()) {
                isProcessed = true
                Toast.makeText(this, "RATT Mobile supports text and links only.", Toast.LENGTH_SHORT).show()
                finish()
                return
            }
        }

        var text = ""
        if (clipData != null && clipData.itemCount > 0) {
            val item = clipData.getItemAt(0)
            text = item.coerceToText(this)?.toString().orEmpty()
        }

        // Fallback: If primaryClip was restricted, check if recent text was cached
        if (text.isBlank()) {
            text = MainActivity.lastCopiedText
        }

        // On Samsung One UI, the clipboard daemon occasionally delivers the clip ~50ms after focus
        if (text.isBlank() && !hasRetried) {
            hasRetried = true
            Handler(Looper.getMainLooper()).postDelayed({
                processClipboardAndFinish()
            }, 60)
            return
        }

        isProcessed = true

        try {
            if (text.isNotBlank()) {
                // 1. Save into encrypted repository
                SlotRepository.put(targetSlotId, text)
                MainActivity.lastCopiedText = text

                // 2. Notify dashboard & floating assist
                MainActivity.activeInstance?.onSlotUpdated(targetSlotId, text)
                FloatingAssistService.activeInstance?.refreshOverlayMenu()
                FloatingAssistService.activeInstance?.showBubbleIfPermitted()

                // 3. Immediately send over Wi-Fi to PC
                MainActivity.sendToPc(this, targetSlotId, text)

                Toast.makeText(this, "Saved to Slot $targetSlotId! (Synced to PC)", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, "Phone clipboard is empty! Copy text in WhatsApp or Chrome first.", Toast.LENGTH_LONG).show()
            }
        } catch (e: Exception) {
            Toast.makeText(this, "Error accessing clipboard: ${e.message}", Toast.LENGTH_SHORT).show()
        } finally {
            finish()
            if (android.os.Build.VERSION.SDK_INT >= 34) {
                overrideActivityTransition(OVERRIDE_TRANSITION_CLOSE, 0, 0)
            } else {
                @Suppress("DEPRECATION")
                overridePendingTransition(0, 0)
            }
        }
    }
}
