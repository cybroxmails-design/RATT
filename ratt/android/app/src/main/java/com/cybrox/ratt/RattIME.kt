package com.cybrox.ratt

import android.content.ClipboardManager
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.inputmethodservice.InputMethodService
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.TypedValue
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.TextView
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * RATT v2 Android Virtual Keyboard (Input Method Editor — RattIME.kt).
 *
 * Production Mobile Input Method:
 *   1. Zero-Padding Key Views: Fixes Android button text truncation (dots).
 *   2. Non-Focusable IME Touch Controls: Prevents losing text field focus in Google Messages / WhatsApp.
 *   3. 10-Slot Top-Bar: Real-time visual feedback on-screen.
 *   4. Pre-populated Slots 1 & 2: Instant out-of-the-box paste testing.
 *   5. Full QWERTY Keyboard with Shift, Space, Backspace, Enter, and 🌐 Switcher.
 */
class RattIME : InputMethodService() {

    companion object {
        private const val KEYSTORE_ALIAS = "RattSlotMasterKeyV2"
        private val BLOCKED_SCHEMES = listOf(
            "javascript:", "vbscript:", "data:", "file:", "intent:", "content:", "shell:"
        )
    }

    private data class EncryptedSlot(val iv: ByteArray, val cipherText: ByteArray, val preview: String)
    private val slots = mutableMapOf<Int, EncryptedSlot>()
    private val slotViews = mutableMapOf<Int, TextView>()
    private var isShifted = false
    private val letterViews = mutableListOf<TextView>()
    private var statusBanner: TextView? = null

    private fun dp(dpVal: Int): Int {
        return TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP,
            dpVal.toFloat(),
            resources.displayMetrics
        ).toInt()
    }

    private fun createRoundedBg(bgColor: Int, strokeColor: Int = 0, strokeWidth: Int = 0, cornerRadiusDp: Float = 6f): GradientDrawable {
        return GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            setColor(bgColor)
            cornerRadius = dp(cornerRadiusDp.toInt()).toFloat()
            if (strokeWidth > 0) {
                setStroke(dp(strokeWidth), strokeColor)
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        SlotRepository.init(this)
        SecurityHardening.enforceRuntimeDefense(this)
        try {
            val s1 = "RATT Universal Clipboard"
            slots[1] = encryptInHardwareKeystore(s1.toByteArray(Charsets.UTF_8), s1)
            val s2 = "https://cybrox.com"
            slots[2] = encryptInHardwareKeystore(s2.toByteArray(Charsets.UTF_8), s2)
        } catch (_: Exception) {}

        startSyncReceiver()
    }

    private fun startSyncReceiver() {
        RattHttpSyncServer.start(this)
    }

    override fun onCreateInputView(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#0A0D12"))
            setPadding(dp(4), dp(4), dp(4), dp(8))
            isFocusable = false
            isFocusableInTouchMode = false
        }

        // ========================================================
        // 1. TOP BAR: 10 RATT SLOTS (SCROLLABLE)
        // ========================================================
        val slotScroll = HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            isFocusable = false
            isFocusableInTouchMode = false
        }
        val slotBar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(2), 0, dp(4))
            isFocusable = false
            isFocusableInTouchMode = false
        }

        for (slotNum in 1..10) {
            val tv = TextView(this).apply {
                val liveVal = MainActivity.liveSlots[slotNum]
                val hasData = liveVal != null || slots.containsKey(slotNum)
                val previewStr = liveVal ?: slots[slotNum]?.preview ?: ""
                text = if (hasData) "Slot $slotNum: $previewStr" else "Slot $slotNum"
                textSize = 12f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(if (hasData) Color.parseColor("#39FF14") else Color.parseColor("#00BFFF"))
                gravity = Gravity.CENTER
                setPadding(dp(12), dp(8), dp(12), dp(8))
                background = createRoundedBg(
                    Color.parseColor("#161B22"),
                    if (hasData) Color.parseColor("#39FF14") else Color.parseColor("#30363D"),
                    1,
                    6f
                )
                val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, dp(38)).apply {
                    setMargins(dp(3), 0, dp(3), 0)
                }
                layoutParams = lp
                isFocusable = false
                isFocusableInTouchMode = false

                setOnClickListener { onSlotPasteRequested(slotNum) }
                setOnLongClickListener {
                    onSlotCopyRequested(slotNum)
                    true
                }
            }
            slotViews[slotNum] = tv
            slotBar.addView(tv)
        }

        // Clear All Slots button directly in the IME top bar (Requirement 4)
        val clearAllBtn = TextView(this).apply {
            text = "🗑️ Clear All"
            textSize = 11.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#EF4444"))
            gravity = Gravity.CENTER
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = createRoundedBg(Color.parseColor("#161B22"), Color.parseColor("#EF4444"), 1, 6f)
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, dp(38)).apply {
                setMargins(dp(4), 0, dp(4), 0)
            }
            layoutParams = lp
            isFocusable = false
            isFocusableInTouchMode = false
            setOnClickListener {
                clearAllImeSlots()
            }
        }
        slotBar.addView(clearAllBtn)

        slotScroll.addView(slotBar)
        root.addView(slotScroll)

        // ========================================================
        // 2. ON-SCREEN STATUS BANNER (Guaranteed Visual Feedback)
        // ========================================================
        statusBanner = TextView(this).apply {
            text = "Tap slot to paste • Long-press slot to save copy"
            textSize = 11f
            setTextColor(Color.parseColor("#8B949E"))
            gravity = Gravity.CENTER
            setPadding(0, dp(2), 0, dp(4))
            isFocusable = false
            isFocusableInTouchMode = false
        }
        root.addView(statusBanner)

        // ========================================================
        // 3. FULL QWERTY TYPING ROWS (ZERO-PADDING TEXTVIEWS)
        // ========================================================
        letterViews.clear()

        val row1 = listOf("q", "w", "e", "r", "t", "y", "u", "i", "o", "p")
        val row2 = listOf("a", "s", "d", "f", "g", "h", "j", "k", "l")
        val row3 = listOf("z", "x", "c", "v", "b", "n", "m")

        root.addView(createRow1(row1))
        root.addView(createRow2(row2))
        root.addView(createRow3(row3))
        root.addView(createRow4())

        return root
    }

    private fun createRow1(keys: List<String>): LinearLayout {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(46))
            isFocusable = false
            isFocusableInTouchMode = false
        }
        for (k in keys) {
            row.addView(createLetterKey(k))
        }
        return row
    }

    private fun createRow2(keys: List<String>): LinearLayout {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(dp(16), 0, dp(16), 0)
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(46))
            isFocusable = false
            isFocusableInTouchMode = false
        }
        for (k in keys) {
            row.addView(createLetterKey(k))
        }
        return row
    }

    private fun createLetterKey(charStr: String): TextView {
        val tv = TextView(this).apply {
            text = if (isShifted) charStr.uppercase() else charStr.lowercase()
            textSize = 19f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            includeFontPadding = false
            setPadding(0, 0, 0, 0)
            background = createRoundedBg(Color.parseColor("#21262D"), cornerRadiusDp = 5f)
            val lp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1.0f).apply {
                setMargins(dp(2), dp(3), dp(2), dp(3))
            }
            layoutParams = lp
            isFocusable = false
            isFocusableInTouchMode = false

            setOnClickListener {
                val toCommit = if (isShifted) charStr.uppercase() else charStr.lowercase()
                currentInputConnection?.commitText(toCommit, 1)
            }
        }
        letterViews.add(tv)
        return tv
    }

    private fun createRow3(keys: List<String>): LinearLayout {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(46))
            isFocusable = false
            isFocusableInTouchMode = false
        }

        // Shift Key (⇧)
        val shiftKey = TextView(this).apply {
            text = "⇧"
            textSize = 20f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#00BFFF"))
            gravity = Gravity.CENTER
            includeFontPadding = false
            setPadding(0, 0, 0, 0)
            background = createRoundedBg(Color.parseColor("#161B22"), cornerRadiusDp = 5f)
            layoutParams = LinearLayout.LayoutParams(dp(44), LinearLayout.LayoutParams.MATCH_PARENT).apply {
                setMargins(dp(2), dp(3), dp(2), dp(3))
            }
            isFocusable = false
            isFocusableInTouchMode = false

            setOnClickListener {
                isShifted = !isShifted
                for (view in letterViews) {
                    val rawChar = view.text.toString()
                    view.text = if (isShifted) rawChar.uppercase() else rawChar.lowercase()
                }
                setTextColor(if (isShifted) Color.parseColor("#39FF14") else Color.parseColor("#00BFFF"))
            }
        }
        row.addView(shiftKey)

        for (k in keys) {
            row.addView(createLetterKey(k))
        }

        // Backspace Key (⌫)
        val backKey = TextView(this).apply {
            text = "⌫"
            textSize = 18f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#FF6B6B"))
            gravity = Gravity.CENTER
            includeFontPadding = false
            setPadding(0, 0, 0, 0)
            background = createRoundedBg(Color.parseColor("#161B22"), cornerRadiusDp = 5f)
            layoutParams = LinearLayout.LayoutParams(dp(44), LinearLayout.LayoutParams.MATCH_PARENT).apply {
                setMargins(dp(2), dp(3), dp(2), dp(3))
            }
            isFocusable = false
            isFocusableInTouchMode = false

            setOnClickListener {
                currentInputConnection?.deleteSurroundingText(1, 0)
            }
        }
        row.addView(backKey)

        return row
    }

    private fun createRow4(): LinearLayout {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(46))
            isFocusable = false
            isFocusableInTouchMode = false
        }

        // 1. Period / Dot (.)
        val dotKey = TextView(this).apply {
            text = "."
            textSize = 22f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            includeFontPadding = false
            setPadding(0, 0, 0, 0)
            background = createRoundedBg(Color.parseColor("#21262D"), cornerRadiusDp = 5f)
            layoutParams = LinearLayout.LayoutParams(dp(38), LinearLayout.LayoutParams.MATCH_PARENT).apply {
                setMargins(dp(2), dp(3), dp(2), dp(3))
            }
            isFocusable = false
            isFocusableInTouchMode = false
            setOnClickListener {
                currentInputConnection?.commitText(".", 1)
            }
        }
        row.addView(dotKey)

        // 2. Switch Keyboard Button (🌐)
        val switchKey = TextView(this).apply {
            text = "🌐"
            textSize = 18f
            gravity = Gravity.CENTER
            includeFontPadding = false
            setPadding(0, 0, 0, 0)
            background = createRoundedBg(Color.parseColor("#161B22"), cornerRadiusDp = 5f)
            layoutParams = LinearLayout.LayoutParams(dp(44), LinearLayout.LayoutParams.MATCH_PARENT).apply {
                setMargins(dp(2), dp(3), dp(2), dp(3))
            }
            isFocusable = false
            isFocusableInTouchMode = false

            setOnClickListener {
                val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
                imm?.showInputMethodPicker()
            }
        }
        row.addView(switchKey)

        // 3. Spacebar (RATT Space)
        val spaceKey = TextView(this).apply {
            text = "RATT Space"
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#8B949E"))
            gravity = Gravity.CENTER
            includeFontPadding = false
            setPadding(0, 0, 0, 0)
            background = createRoundedBg(Color.parseColor("#21262D"), cornerRadiusDp = 5f)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1.0f).apply {
                setMargins(dp(3), dp(3), dp(3), dp(3))
            }
            isFocusable = false
            isFocusableInTouchMode = false

            setOnClickListener {
                currentInputConnection?.commitText(" ", 1)
            }
        }
        row.addView(spaceKey)

        // 4. Enter Key (↵)
        val enterKey = TextView(this).apply {
            text = "↵"
            textSize = 20f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            includeFontPadding = false
            setPadding(0, 0, 0, 0)
            background = createRoundedBg(Color.parseColor("#00BFFF"), cornerRadiusDp = 5f)
            layoutParams = LinearLayout.LayoutParams(dp(54), LinearLayout.LayoutParams.MATCH_PARENT).apply {
                setMargins(dp(2), dp(3), dp(2), dp(3))
            }
            isFocusable = false
            isFocusableInTouchMode = false

            setOnClickListener {
                val action = currentInputEditorInfo?.actionId ?: EditorInfo.IME_NULL
                if (action != EditorInfo.IME_NULL && action != EditorInfo.IME_ACTION_NONE) {
                    currentInputConnection?.performEditorAction(action)
                } else {
                    currentInputConnection?.sendKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_ENTER))
                    currentInputConnection?.sendKeyEvent(KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_ENTER))
                }
            }
        }
        row.addView(enterKey)

        return row
    }

    private fun isSafeUnformattedText(raw: String): Pair<Boolean, String> {
        val clean = raw.replace(Regex("<[^>]+>"), "")
            .replace(Regex("[\\u200B-\\u200F\\u202A-\\u202E\\uFEFF]"), "")
        val lower = clean.trim().lowercase()
        for (scheme in BLOCKED_SCHEMES) {
            if (lower.startsWith(scheme) || lower.contains(" $scheme")) {
                return Pair(false, "")
            }
        }
        return Pair(true, clean)
    }

    fun onSlotCopyRequested(slotNum: Int) {
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
        val clip = cm?.primaryClip
        if (clip == null || clip.itemCount <= 0) {
            setStatus("Clipboard empty! Copy text in an app first, then long-press.", "#FFC107")
            return
        }
        val desc = cm.primaryClipDescription
        if (desc != null && (desc.hasMimeType("image/*") || desc.hasMimeType("video/*"))) {
            setStatus("Media copied! Use RATT Floating Menu to save to slot.", "#00D5FE")
            return
        }
        val rawText = clip.getItemAt(0).coerceToText(this)?.toString() ?: return
        val (safe, cleanText) = isSafeUnformattedText(rawText)
        if (!safe || cleanText.isEmpty()) {
            setStatus("Security Guard: Blocked unsafe link/payload.", "#FF6B6B")
            return
        }
        val preview = if (cleanText.length > 10) cleanText.take(10) + ".." else cleanText
        slots[slotNum] = encryptInHardwareKeystore(cleanText.toByteArray(Charsets.UTF_8), preview)

        // Update Slot Button label & highlight neon green
        slotViews[slotNum]?.let { v ->
            v.text = "Slot $slotNum: $preview"
            v.setTextColor(Color.parseColor("#39FF14"))
            v.background = createRoundedBg(Color.parseColor("#161B22"), Color.parseColor("#39FF14"), 1, 6f)
        }
        setStatus("Saved to Slot #$slotNum! Tap it to paste anytime.", "#39FF14")
    }

    private fun onSlotPasteRequested(slotNum: Int) {
        val liveSync = MainActivity.liveSlots[slotNum]
        if (!liveSync.isNullOrEmpty()) {
            val (safeLive, cleanLive) = isSafeUnformattedText(liveSync)
            if (safeLive && cleanLive.isNotEmpty()) {
                currentInputConnection?.commitText(cleanLive, 1)
                setStatus("Pasted Slot #$slotNum: $cleanLive", "#39FF14")
                return
            }
        }
        val enc = slots[slotNum]
        if (enc == null) {
            setStatus("Slot #$slotNum is empty! Long-press this slot to save what you copied.", "#FFC107")
            return
        }
        val plain = decryptFromHardwareKeystore(enc).toString(Charsets.UTF_8)
        val (safe, cleanText) = isSafeUnformattedText(plain)
        if (!safe) {
            setStatus("Security Guard: Blocked unsafe paste.", "#FF6B6B")
            return
        }
        currentInputConnection?.commitText(cleanText, 1)
        setStatus("Pasted Slot #$slotNum: $cleanText", "#39FF14")
    }

    fun clearImeSlot(slotNum: Int) {
        slots.remove(slotNum)
        SlotRepository.clear(slotNum)
        MainActivity.sendClearSlotToPc(this, slotNum)
        slotViews[slotNum]?.let { v ->
            v.text = "Slot $slotNum"
            v.setTextColor(Color.parseColor("#00BFFF"))
            v.background = createRoundedBg(Color.parseColor("#161B22"), Color.parseColor("#30363D"), 1, 6f)
        }
        setStatus("Cleared Slot #$slotNum", "#FF6B6B")
    }

    fun clearAllImeSlots() {
        slots.clear()
        SlotRepository.clearAll()
        MainActivity.sendClearAllToPc(this)
        for (slotNum in 1..10) {
            slotViews[slotNum]?.let { v ->
                v.text = "Slot $slotNum"
                v.setTextColor(Color.parseColor("#00BFFF"))
                v.background = createRoundedBg(Color.parseColor("#161B22"), Color.parseColor("#30363D"), 1, 6f)
            }
        }
        setStatus("All slots cleared", "#FF6B6B")
    }

    override fun onDestroy() {
        slots.clear()
        SlotRepository.exitAndWipeAllSlots()
        super.onDestroy()
    }

    private fun setStatus(msg: String, colorHex: String) {
        statusBanner?.let { sb ->
            sb.text = msg
            sb.setTextColor(Color.parseColor(colorHex))
        }
    }

    private fun getOrCreateHardwareKey(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = ks.getEntry(KEYSTORE_ALIAS, null) as? KeyStore.SecretKeyEntry
        if (existing != null) return existing.secretKey

        val keyGen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        val spec = KeyGenParameterSpec.Builder(
            KEYSTORE_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()
        keyGen.init(spec)
        return keyGen.generateKey()
    }

    private fun encryptInHardwareKeystore(plain: ByteArray, preview: String): EncryptedSlot {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateHardwareKey())
        return EncryptedSlot(cipher.iv, cipher.doFinal(plain), preview)
    }

    private fun decryptFromHardwareKeystore(slot: EncryptedSlot): ByteArray {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val spec = GCMParameterSpec(128, slot.iv)
        cipher.init(Cipher.DECRYPT_MODE, getOrCreateHardwareKey(), spec)
        return cipher.doFinal(slot.cipherText)
    }
}
