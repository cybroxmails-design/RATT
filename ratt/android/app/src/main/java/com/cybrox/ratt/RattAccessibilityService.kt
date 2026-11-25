package com.cybrox.ratt

import android.accessibilityservice.AccessibilityService
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

/**
 * Android RattAccessibilityService.kt - Focus Detection & Injection
 * (`mobile_implimentation.pdf` Section 5, Option 2: Floating Assist Overlay).
 *
 * Monitors `AccessibilityEvent.TYPE_VIEW_FOCUSED` across all apps; when an editable field
 * (`node.isEditable`) receives focus, reveals the magnetic Floating Assist bubble while
 * keeping the user's primary keyboard (Samsung Keyboard or Gboard) active.
 * Injects selected slot text directly via `AccessibilityNodeInfo.ACTION_SET_TEXT`.
 */
class RattAccessibilityService : AccessibilityService() {

    companion object {
        var activeInstance: RattAccessibilityService? = null

        fun injectText(text: String) {
            activeInstance?.injectText(text)
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        activeInstance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event?.eventType == AccessibilityEvent.TYPE_VIEW_FOCUSED) {
            val node = event.source ?: return
            if (node.isEditable) {
                FloatingAssistService.revealBubble()
            }
        }
    }

    fun injectText(text: String) {
        val clean = SlotRepository.sanitizeIncomingText(text) ?: return
        val root = rootInActiveWindow ?: return
        val focused = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT) ?: return
        // AND-04: Do not silently inject clipboard content into password fields
        if (focused.isPassword) return
        val args = Bundle().apply { putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, clean) }
        focused.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    override fun onInterrupt() {
        // Required override for AccessibilityService
    }

    override fun onDestroy() {
        if (activeInstance === this) {
            activeInstance = null
        }
        super.onDestroy()
    }
}
