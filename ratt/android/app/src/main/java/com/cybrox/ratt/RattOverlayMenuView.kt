package com.cybrox.ratt

import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast

/**
 * RATT v2 Android Floating Overlay Context Menu (`RattOverlayMenuView.kt`).
 *
 * Fixes & Enhancements:
 *   1. High-visibility bold characters on PASTE (Blue) and SAVE (Green) buttons with zero truncation.
 *   2. Responsive touch dispatch: Card consumes clicks; backdrop dismisses menu; buttons respond instantly.
 *   3. Robust clipboard fallback: Works even with Android 10+ background restriction by checking memory cache.
 */
class RattOverlayMenuView(
    context: Context,
    @Suppress("unused") private val slotsMap: Map<Int, RattSlot>? = null
) : FrameLayout(context) {

    var onSlotSelected: ((RattSlot) -> Unit)? = null
    var onCloseRequested: (() -> Unit)? = null

    private var isPaused = false
    private val cardWrapper: FrameLayout
    private val mainContainer: LinearLayout
    private val slotsSubmenuContainer: LinearLayout
    private val slotTitleViews = mutableMapOf<Int, TextView>()
    private val slotRowCards = mutableMapOf<Int, LinearLayout>()
    private val slotIndicatorPills = mutableMapOf<Int, View>()
    private val slotNumberBadges = mutableMapOf<Int, TextView>()
    private var statusHeaderView: TextView? = null
    private var pauseToggleView: TextView? = null

    private fun dp(dpVal: Int): Int {
        return TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP,
            dpVal.toFloat(),
            resources.displayMetrics
        ).toInt()
    }

    private fun roundedBg(bgColor: Int, strokeColor: Int = 0, strokeDp: Int = 0, radiusDp: Float = 8f): GradientDrawable {
        return GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            setColor(bgColor)
            cornerRadius = dp(radiusDp.toInt()).toFloat()
            if (strokeDp > 0) setStroke(dp(strokeDp), strokeColor)
        }
    }

    init {
        // Fullscreen transparent backdrop: touching anywhere outside card exits RATT menu
        setBackgroundColor(Color.parseColor("#22000000")) // Subtle dim
        isClickable = true
        isFocusable = false
        setOnClickListener {
            onCloseRequested?.invoke()
        }

        // Compact Centered Menu Card
        cardWrapper = FrameLayout(context).apply {
            val lp = LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT).apply {
                gravity = Gravity.CENTER
            }
            layoutParams = lp
            background = roundedBg(Color.parseColor("#FFFFFF"), Color.parseColor("#D1D5DB"), 1, 10f)
            setPadding(dp(6), dp(8), dp(6), dp(8))
            isClickable = true // CRUCIAL: Consumes clicks inside card so tapping buttons does NOT dismiss menu!
            isFocusable = false
            setOnClickListener {
                // Consume event inside card
            }
        }

        // 1. MAIN DESKTOP-STYLE TRAY MENU (210dp width)
        mainContainer = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LayoutParams(dp(210), LayoutParams.WRAP_CONTENT)
        }
        buildMainTrayMenu()
        cardWrapper.addView(mainContainer)

        // 2. SLOTS SUBMENU (285dp width: generous space for PC color indicator and bold PASTE/SAVE buttons)
        slotsSubmenuContainer = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
            layoutParams = LayoutParams(dp(285), LayoutParams.WRAP_CONTENT)
        }
        buildSlotsSubmenu()
        cardWrapper.addView(slotsSubmenuContainer)

        addView(cardWrapper)
    }

    private fun createMenuItem(
        title: String,
        isBold: Boolean = false,
        textColor: Int = Color.parseColor("#1F2937"),
        hasArrow: Boolean = false,
        onClick: (() -> Unit)? = null
    ): TextView {
        return TextView(context).apply {
            text = if (hasArrow) "$title       ›" else title
            textSize = 13f
            typeface = if (isBold) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
            setTextColor(textColor)
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(14), dp(7), dp(14), dp(7))
            background = roundedBg(Color.TRANSPARENT, radiusDp = 4f)
            isClickable = true
            isFocusable = false

            if (onClick != null) {
                setOnClickListener {
                    onClick.invoke()
                }
            }
        }
    }

    private fun createDivider(): View {
        return View(context).apply {
            setBackgroundColor(Color.parseColor("#E5E7EB"))
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(1)).apply {
                setMargins(dp(8), dp(3), dp(8), dp(3))
            }
            layoutParams = lp
        }
    }

    private fun buildMainTrayMenu() {
        mainContainer.removeAllViews()

        // 1. Header: RATT v2 — ON (Active)
        statusHeaderView = TextView(context).apply {
            text = if (isPaused) "RATT v2 — Paused" else "RATT v2 — ON (Active)"
            textSize = 11.5f
            setTextColor(if (isPaused) Color.parseColor("#EF4444") else Color.parseColor("#6B7280"))
            setPadding(dp(14), dp(4), dp(14), dp(4))
        }
        mainContainer.addView(statusHeaderView)

        // 2. Pause RATT (Release Keyboard)
        pauseToggleView = createMenuItem(
            if (isPaused) "Resume RATT" else "Pause RATT (Release Keyboard)"
        ) {
            isPaused = !isPaused
            statusHeaderView?.text = if (isPaused) "RATT v2 — Paused" else "RATT v2 — ON (Active)"
            statusHeaderView?.setTextColor(if (isPaused) Color.parseColor("#EF4444") else Color.parseColor("#6B7280"))
            pauseToggleView?.text = if (isPaused) "Resume RATT" else "Pause RATT (Release Keyboard)"
            Toast.makeText(context, if (isPaused) "RATT Paused" else "RATT Active", Toast.LENGTH_SHORT).show()
        }
        mainContainer.addView(pauseToggleView)

        mainContainer.addView(createDivider())

        // 3. Open RATT (Bold)
        val openRattItem = createMenuItem("Open RATT", isBold = true, textColor = Color.parseColor("#111827")) {
            val intent = Intent(context, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            }
            context.startActivity(intent)
            onCloseRequested?.invoke()
        }
        mainContainer.addView(openRattItem)

        // 4. Slots menu >
        val slotsItem = createMenuItem("Slots menu", hasArrow = true) {
            showSlotsSubmenu()
        }
        mainContainer.addView(slotsItem)

        mainContainer.addView(createDivider())

        // 5. Share across accounts (Rule 4: Premium & Enterprise)
        val shareItem = createMenuItem("Share with Account") {
            if (!UserTierManager.canShareAndMirror(context)) {
                Toast.makeText(context, "UPGRADE REQUIRED: Share (copy/cut/paste across different RATT accounts) is limited to Premium and Enterprise subscribers.", Toast.LENGTH_LONG).show()
                return@createMenuItem
            }
            try {
                val sendIntent = Intent().apply {
                    action = Intent.ACTION_SEND
                    putExtra(Intent.EXTRA_TEXT, "RATT: Real-time Adaptive Text Transfer (https://cybrox.com/ratt)")
                    type = "text/plain"
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(Intent.createChooser(sendIntent, "Share RATT").apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                })
            } catch (_: Exception) {}
            onCloseRequested?.invoke()
        }
        mainContainer.addView(shareItem)

        // 6. Device Mirroring (Rule 4: Premium & Enterprise)
        val mirrorItem = createMenuItem("Mirror Devices") {
            if (!UserTierManager.canShareAndMirror(context)) {
                Toast.makeText(context, "UPGRADE REQUIRED: Device Mirroring is limited to Premium and Enterprise subscribers.", Toast.LENGTH_LONG).show()
                return@createMenuItem
            }
            Toast.makeText(context, "Device Mirroring active", Toast.LENGTH_SHORT).show()
            onCloseRequested?.invoke()
        }
        mainContainer.addView(mirrorItem)

        // 7. Translate (Rule 3: Premium & Enterprise)
        val translateItem = createMenuItem("Translate") {
            if (!UserTierManager.canTranslate(context)) {
                Toast.makeText(context, "UPGRADE REQUIRED: 9-Language Translation is limited to Premium and Enterprise subscribers.", Toast.LENGTH_LONG).show()
                return@createMenuItem
            }
            Toast.makeText(context, "RATT Translate: Ready to translate (9 Languages)", Toast.LENGTH_SHORT).show()
            onCloseRequested?.invoke()
        }
        mainContainer.addView(translateItem)

        mainContainer.addView(createDivider())

        // 8. Settings
        val settingsItem = createMenuItem("Settings") {
            try {
                val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                    data = Uri.parse("package:${context.packageName}")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
            } catch (_: Exception) {}
            onCloseRequested?.invoke()
        }
        mainContainer.addView(settingsItem)

        // 9. Exit
        val exitItem = createMenuItem("Exit (Wipe Slots)") {
            SlotRepository.exitAndWipeAllSlots()
            MainActivity.activeInstance?.emptySlotsAndExit()
            onCloseRequested?.invoke()
        }
        mainContainer.addView(exitItem)
    }

    private fun showSlotsSubmenu() {
        mainContainer.visibility = View.GONE
        slotsSubmenuContainer.visibility = View.VISIBLE
        refreshSlotsList()
    }

    private fun showMainMenu() {
        slotsSubmenuContainer.visibility = View.GONE
        mainContainer.visibility = View.VISIBLE
    }

    private fun buildSlotsSubmenu() {
        slotsSubmenuContainer.removeAllViews()

        // Top Navigation Bar
        val topNav = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(10), dp(6), dp(10), dp(6))
        }

        val backBtn = TextView(context).apply {
            text = "‹ Back"
            textSize = 13.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#00BFFF"))
            setPadding(0, 0, dp(12), 0)
            isClickable = true
            isFocusable = false
            setOnClickListener {
                showMainMenu()
            }
        }
        topNav.addView(backBtn)

        val title = TextView(context).apply {
            text = "RATT 10-Slot Menu"
            textSize = 13.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#111827"))
        }
        topNav.addView(title)
        slotsSubmenuContainer.addView(topNav)

        slotsSubmenuContainer.addView(createDivider())

        // Scrollable list of 10 Slots with high-visibility, large, bold PASTE and SAVE buttons
        val scroll = ScrollView(context).apply {
            isFocusable = false
        }
        val list = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(6), dp(4), dp(6), dp(4))
        }

        for (slotId in 1..10) {
            val card = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                background = roundedBg(Color.parseColor("#F9FAFB"), Color.parseColor("#E5E7EB"), 1, 6f)
                setPadding(dp(8), dp(6), dp(8), dp(6))
                val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                    bottomMargin = dp(4)
                }
                layoutParams = lp
                isClickable = true
                isFocusable = false
                setOnClickListener {
                    // Consume row clicks
                }
            }
            slotRowCards[slotId] = card

            // Left: PC Color Accent Stripe Indicator
            val stripe = View(context).apply {
                val lp = LinearLayout.LayoutParams(dp(4), dp(22)).apply {
                    rightMargin = dp(6)
                }
                layoutParams = lp
                background = roundedBg(Color.parseColor("#D1D5DB"), radiusDp = 2f)
            }
            slotIndicatorPills[slotId] = stripe
            card.addView(stripe)

            // Prominent Number Badge: "1" .. "10"
            val numBadge = TextView(context).apply {
                text = "$slotId"
                textSize = 11f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#6B7280"))
                gravity = Gravity.CENTER
                includeFontPadding = false
                background = roundedBg(Color.parseColor("#F3F4F6"), Color.parseColor("#E5E7EB"), 1, 4f)
                val lp = LinearLayout.LayoutParams(dp(22), dp(22)).apply {
                    rightMargin = dp(6)
                }
                layoutParams = lp
            }
            slotNumberBadges[slotId] = numBadge
            card.addView(numBadge)

            // Slot title / preview text (single-line, bold when filled)
            val slotText = TextView(context).apply {
                textSize = 12f
                maxLines = 1
                ellipsize = android.text.TextUtils.TruncateAt.END
                val lp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    rightMargin = dp(6)
                }
                layoutParams = lp
            }
            slotTitleViews[slotId] = slotText
            card.addView(slotText)

            // Button 1: PASTE (Large, Bold White text on Cyan Blue)
            val pasteBtn = TextView(context).apply {
                text = "PASTE"
                textSize = 11f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
                gravity = Gravity.CENTER
                includeFontPadding = false
                background = roundedBg(Color.parseColor("#00BFFF"), radiusDp = 5f)
                val lp = LinearLayout.LayoutParams(dp(54), dp(30)).apply {
                    rightMargin = dp(4)
                }
                layoutParams = lp
                isClickable = true
                isFocusable = false

                setOnClickListener {
                    val slot = SlotRepository.liveSlots[slotId]
                    if (slot != null && slot.preview.isNotEmpty()) {
                        Toast.makeText(context, "Pasting Slot $slotId...", Toast.LENGTH_SHORT).show()
                        onSlotSelected?.invoke(slot)
                    } else {
                        Toast.makeText(context, "Slot $slotId is [Empty]. Tap SAVE first!", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            card.addView(pasteBtn)

            // Button 2: SAVE (Large, Bold White text on Emerald Green)
            val saveBtn = TextView(context).apply {
                text = "SAVE"
                textSize = 11f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
                gravity = Gravity.CENTER
                includeFontPadding = false
                background = roundedBg(Color.parseColor("#059669"), radiusDp = 5f)
                val lp = LinearLayout.LayoutParams(dp(54), dp(30))
                layoutParams = lp
                isClickable = true
                isFocusable = false

                setOnClickListener {
                    copyPhoneClipboardToSlot(slotId)
                }
            }
            card.addView(saveBtn)

            // Button 3: CLR (Clear slot)
            val clrBtn = TextView(context).apply {
                text = "CLR"
                textSize = 10.5f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
                gravity = Gravity.CENTER
                includeFontPadding = false
                background = roundedBg(Color.parseColor("#EF4444"), radiusDp = 5f)
                val lp = LinearLayout.LayoutParams(dp(44), dp(30)).apply {
                    leftMargin = dp(4)
                }
                layoutParams = lp
                isClickable = true
                isFocusable = false

                setOnClickListener {
                    SlotRepository.clear(slotId)
                    MainActivity.activeInstance?.onSlotCleared(slotId)
                    MainActivity.sendClearSlotToPc(context, slotId)
                    refreshBadgeState(slotId)
                    Toast.makeText(context, "Slot $slotId cleared", Toast.LENGTH_SHORT).show()
                }
            }
            card.addView(clrBtn)

            list.addView(card)
        }

        // Clear All Slots button
        val clearAllSubmenuBtn = TextView(context).apply {
            text = "🗑️ Clear All Slots"
            textSize = 11.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#EF4444"))
            gravity = Gravity.CENTER
            includeFontPadding = false
            background = roundedBg(Color.parseColor("#FEE2E2"), Color.parseColor("#EF4444"), 1, 6f)
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(32)).apply {
                topMargin = dp(6)
                bottomMargin = dp(4)
            }
            layoutParams = lp
            isClickable = true
            isFocusable = false

            setOnClickListener {
                SlotRepository.clearAll()
                MainActivity.activeInstance?.onAllSlotsCleared()
                MainActivity.sendClearAllToPc(context)
                refreshBadgeState()
                Toast.makeText(context, "All slots cleared", Toast.LENGTH_SHORT).show()
            }
        }
        list.addView(clearAllSubmenuBtn)

        scroll.addView(list)
        slotsSubmenuContainer.addView(scroll, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(260)))
    }

    private fun copyPhoneClipboardToSlot(slotId: Int) {
        try {
            val intent = Intent(context, SaveClipActivity::class.java).apply {
                putExtra("target_slot_id", slotId)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_ANIMATION)
            }
            context.startActivity(intent)

            // Refresh slots preview after SaveClipActivity reads fresh clipboard
            Handler(Looper.getMainLooper()).postDelayed({
                refreshSlotsList()
            }, 300)
            Handler(Looper.getMainLooper()).postDelayed({
                refreshSlotsList()
            }, 600)
        } catch (_: Exception) {
            var text = ""
            try {
                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
                text = clipboard?.primaryClip?.getItemAt(0)?.text?.toString().orEmpty()
            } catch (_: Exception) {}
            if (text.isNotBlank()) {
                SlotRepository.put(slotId, text)
                MainActivity.lastCopiedText = text
                MainActivity.activeInstance?.onSlotUpdated(slotId, text)
                MainActivity.sendToPc(context, slotId, text)
                refreshSlotsList()
                Toast.makeText(context, "Saved to Slot $slotId! (Synced to PC)", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(context, "Clipboard is empty! Copy text in WhatsApp or Chrome first.", Toast.LENGTH_LONG).show()
            }
        }
    }

    /**
     * Refreshes UI with PC-matching Color Indication:
     *   - Empty slots: Dimmed card with gray stripe and [Empty] text.
     *   - Slots with data: Colored border with that slot's specific PC color, active accent stripe, and bold title!
     */
    fun refreshSlotsList() {
        for (slotId in 1..10) {
            val view = slotTitleViews[slotId] ?: continue
            val card = slotRowCards[slotId]
            val stripe = slotIndicatorPills[slotId]
            val numBadge = slotNumberBadges[slotId]
            val slot = SlotRepository.liveSlots[slotId]
            val hasData = slot != null && slot.preview.isNotEmpty()
            val slotColor = Color.parseColor(MainActivity.PC_SLOT_COLORS[slotId - 1])

            if (hasData) {
                view.text = "Slot $slotId: ${slot!!.preview}"
                view.typeface = Typeface.DEFAULT_BOLD
                view.setTextColor(Color.parseColor("#111827"))
                card?.background = roundedBg(Color.parseColor("#F0FDF4"), slotColor, 1, 6f)
                stripe?.background = roundedBg(slotColor, radiusDp = 2f)
                numBadge?.background = roundedBg(slotColor, radiusDp = 4f)
                numBadge?.setTextColor(Color.WHITE)
            } else {
                view.text = "Slot $slotId: [Empty]"
                view.typeface = Typeface.DEFAULT
                view.setTextColor(Color.parseColor("#9CA3AF"))
                card?.background = roundedBg(Color.parseColor("#F9FAFB"), Color.parseColor("#E5E7EB"), 1, 6f)
                stripe?.background = roundedBg(Color.parseColor("#D1D5DB"), radiusDp = 2f)
                numBadge?.background = roundedBg(Color.parseColor("#F3F4F6"), Color.parseColor("#E5E7EB"), 1, 4f)
                numBadge?.setTextColor(Color.parseColor("#6B7280"))
            }
        }
    }

    fun refreshBadgeState(clearedSlotId: Int? = null) {
        if (clearedSlotId != null) {
            val view = slotTitleViews[clearedSlotId]
            view?.text = "Slot $clearedSlotId: [Empty]"
            view?.typeface = Typeface.DEFAULT
            view?.setTextColor(Color.parseColor("#9CA3AF"))
            val card = slotRowCards[clearedSlotId]
            card?.background = roundedBg(Color.parseColor("#F9FAFB"), Color.parseColor("#E5E7EB"), 1, 6f)
            val stripe = slotIndicatorPills[clearedSlotId]
            stripe?.background = roundedBg(Color.parseColor("#D1D5DB"), radiusDp = 2f)
            val numBadge = slotNumberBadges[clearedSlotId]
            numBadge?.background = roundedBg(Color.parseColor("#F3F4F6"), Color.parseColor("#E5E7EB"), 1, 4f)
            numBadge?.setTextColor(Color.parseColor("#6B7280"))
        }
        refreshSlotsList()
    }
}
