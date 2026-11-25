package com.cybrox.ratt

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONObject
import kotlin.concurrent.thread

class MainActivity : Activity() {

    companion object {
        var activeInstance: MainActivity? = null
        val liveSlots = mutableMapOf<Int, String>()
        var lastCopiedText: String = ""

        // PC-matching 10-slot color palette
        val PC_SLOT_COLORS = listOf(
            "#00BFFF", // Slot 1: Deep Cyan
            "#10B981", // Slot 2: Emerald Green
            "#F59E0B", // Slot 3: Amber / Orange
            "#8B5CF6", // Slot 4: Purple
            "#EC4899", // Slot 5: Pink
            "#3B82F6", // Slot 6: Royal Blue
            "#14B8A6", // Slot 7: Teal
            "#EF4444", // Slot 8: Coral Red
            "#EAB308", // Slot 9: Yellow Gold
            "#06B6D4"  // Slot 10: Neon Cyan
        )

        fun sendToPc(context: Context, slotId: Int, content: String) {
            val prefs = context.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
            val pcIp = prefs.getString("paired_pc_ip", null) ?: return
            thread(isDaemon = true) {
                try {
                    val url = URL("http://$pcIp:49210/sync_from_phone")
                    val conn = url.openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.doOutput = true
                    conn.connectTimeout = 2000
                    conn.readTimeout = 2000
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.setRequestProperty("X-RATT-Token", SlotRepository.getOrCreateSyncToken(context))
                    val json = JSONObject().apply {
                        if (content.isEmpty()) {
                            put("action", "CLEAR_SLOT")
                        } else {
                            put("action", "SYNC_FROM_PHONE")
                        }
                        put("slot_id", slotId)
                        put("content", content)
                    }
                    val out = conn.outputStream
                    out.write(json.toString().toByteArray(Charsets.UTF_8))
                    out.flush()
                    out.close()
                    conn.responseCode
                } catch (_: Exception) {}
            }
        }

        fun pushAllSlotsToPc(context: Context): Int {
            val prefs = context.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
            val pcIp = prefs.getString("paired_pc_ip", null) ?: return 0
            if (pcIp.isEmpty() || pcIp == "Not Paired Yet") return 0

            var sentCount = 0
            for (slotId in 1..10) {
                val content = SlotRepository.getSlotContent(slotId)
                if (content.isNotEmpty()) {
                    sendToPc(context, slotId, content)
                    sentCount++
                } else {
                    sendClearSlotToPc(context, slotId)
                }
            }
            return sentCount
        }

        fun sendClearSlotToPc(context: Context, slotId: Int) {
            val prefs = context.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
            val pcIp = prefs.getString("paired_pc_ip", null) ?: return
            val token = SlotRepository.getOrCreateSyncToken(context)
            thread(isDaemon = true) {
                try {
                    val url = URL("http://$pcIp:49210/sync_from_phone")
                    val conn = url.openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.doOutput = true
                    conn.connectTimeout = 2000
                    conn.readTimeout = 2000
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.setRequestProperty("X-RATT-Token", token)
                    val json = JSONObject().apply {
                        put("action", "CLEAR_SLOT")
                        put("slot_id", slotId)
                        put("content", "")
                    }
                    val out = conn.outputStream
                    out.write(json.toString().toByteArray(Charsets.UTF_8))
                    out.flush()
                    out.close()
                    conn.responseCode
                } catch (_: Exception) {}
            }
        }

        fun sendClearAllToPc(context: Context) {
            val prefs = context.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
            val pcIp = prefs.getString("paired_pc_ip", null) ?: return
            val token = SlotRepository.getOrCreateSyncToken(context)
            thread(isDaemon = true) {
                try {
                    val url = URL("http://$pcIp:49210/sync_from_phone")
                    val conn = url.openConnection() as HttpURLConnection
                    conn.requestMethod = "POST"
                    conn.doOutput = true
                    conn.connectTimeout = 2000
                    conn.readTimeout = 2000
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.setRequestProperty("X-RATT-Token", token)
                    val json = JSONObject().apply {
                        put("action", "CLEAR_ALL")
                        put("content", "")
                    }
                    val out = conn.outputStream
                    out.write(json.toString().toByteArray(Charsets.UTF_8))
                    out.flush()
                    out.close()
                    conn.responseCode
                } catch (_: Exception) {}
            }
        }
    }

    private var ipLabel: TextView? = null
    private var pcIpLabel: TextView? = null
    private var tierBadge: TextView? = null
    private var statusLabel: TextView? = null
    private var overlayStatusLabel: TextView? = null
    private var overlayActionBtn: Button? = null
    private val slotRowCards = mutableMapOf<Int, LinearLayout>()
    private val slotTitleViews = mutableMapOf<Int, TextView>()
    private val slotIndicatorPills = mutableMapOf<Int, View>()
    private val slotNumberBadges = mutableMapOf<Int, TextView>()
    private val quickSlotButtons = mutableMapOf<Int, TextView>()
    private val slotClearButtons = mutableMapOf<Int, Button>()
    private var clipListener: ClipboardManager.OnPrimaryClipChangedListener? = null

    private fun dp(dpVal: Int): Int {
        return TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP,
            dpVal.toFloat(),
            resources.displayMetrics
        ).toInt()
    }

    private fun createRounded(bgColor: Int, strokeColor: Int = 0, strokeWidthDp: Int = 0, radiusDp: Float = 8f): GradientDrawable {
        return GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            setColor(bgColor)
            cornerRadius = dp(radiusDp.toInt()).toFloat()
            if (strokeWidthDp > 0) setStroke(dp(strokeWidthDp), strokeColor)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Prevent task-switcher screenshots and screen recording of clipboard slots (AND-03)
        window.setFlags(
            WindowManager.LayoutParams.FLAG_SECURE,
            WindowManager.LayoutParams.FLAG_SECURE
        )
        activeInstance = this
        SlotRepository.init(this)
        SecurityHardening.enforceRuntimeDefense(this)
        RattHttpSyncServer.start(this)

        val scroll = ScrollView(this).apply {
            setBackgroundColor(Color.parseColor("#0A0D12"))
        }

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(24))
        }

        // Header with Flagship App Icon & Brand Title
        val headerRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 0, 0, dp(16))
        }

        val logoView = android.widget.ImageView(this).apply {
            setImageResource(R.drawable.ic_launcher)
            val lp = LinearLayout.LayoutParams(dp(54), dp(54)).apply {
                rightMargin = dp(14)
            }
            layoutParams = lp
        }
        headerRow.addView(logoView)

        val titleCol = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        val title = TextView(this).apply {
            text = "RATT v2"
            textSize = 24f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#00BFFF"))
        }
        titleCol.addView(title)

        val sub = TextView(this).apply {
            text = "Two-Way Clipboard Sync • Cybrox"
            textSize = 12f
            setTextColor(Color.parseColor("#8B949E"))
        }
        titleCol.addView(sub)
        headerRow.addView(titleCol)

        val spacer = View(this).apply {
            val lp = LinearLayout.LayoutParams(0, dp(1), 1f)
            layoutParams = lp
        }
        headerRow.addView(spacer)

        tierBadge = TextView(this).apply {
            val tier = UserTierManager.getTier(this@MainActivity)
            text = tier.uppercase()
            textSize = 11f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(if (UserTierManager.hasPaidEntitlement(this@MainActivity)) Color.parseColor("#39FF14") else Color.parseColor("#9CA3AF"))
            background = createRounded(
                Color.parseColor("#161B22"),
                if (UserTierManager.hasPaidEntitlement(this@MainActivity)) Color.parseColor("#10B981") else Color.parseColor("#4B5563"),
                1, 6f
            )
            setPadding(dp(10), dp(5), dp(10), dp(5))
            isClickable = true
            setOnClickListener {
                showTierUpgradeDialog()
            }
        }
        headerRow.addView(tierBadge)

        root.addView(headerRow)

        // ================= FLOATING POP-UP CONTROLLER CARD =================
        val overlayCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = createRounded(Color.parseColor("#161B22"), Color.parseColor("#30363D"), 1, 10f)
            setPadding(dp(16), dp(16), dp(16), dp(16))
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                bottomMargin = dp(16)
            }
            layoutParams = lp
        }

        val overlayTitle = TextView(this).apply {
            text = "FLOATING ASSIST POP-UP"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#00BFFF"))
        }
        overlayCard.addView(overlayTitle)

        overlayStatusLabel = TextView(this).apply {
            textSize = 12.5f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, dp(4), 0, dp(8))
        }
        overlayCard.addView(overlayStatusLabel)

        overlayActionBtn = Button(this).apply {
            textSize = 13.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = createRounded(Color.parseColor("#00BFFF"), radiusDp = 8f)
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(44)).apply {
                bottomMargin = dp(8)
            }
            layoutParams = lp
            setOnClickListener {
                handleOverlayButtonClick()
            }
        }
        overlayCard.addView(overlayActionBtn)

        val switchKbdBtn = Button(this).apply {
            text = "Keep Samsung Keyboard Active"
            textSize = 13f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#C9D1D9"))
            background = createRounded(Color.parseColor("#21262D"), radiusDp = 8f)
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(40))
            layoutParams = lp
            setOnClickListener {
                val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
                imm?.showInputMethodPicker()
            }
        }
        overlayCard.addView(switchKbdBtn)

        root.addView(overlayCard)

        // ================= IP ADDRESS / SYNC CARD =================
        val ipCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = createRounded(Color.parseColor("#161B22"), Color.parseColor("#30363D"), 1, 10f)
            setPadding(dp(16), dp(16), dp(16), dp(16))
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                bottomMargin = dp(16)
            }
            layoutParams = lp
        }

        val ipTitle = TextView(this).apply {
            text = "THIS PHONE IP ADDRESS:"
            textSize = 11f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#8B949E"))
        }
        ipCard.addView(ipTitle)

        val phoneIp = getDeviceIpAddress()
        ipLabel = TextView(this).apply {
            text = phoneIp
            textSize = 24f
            typeface = Typeface.MONOSPACE
            setTextColor(Color.parseColor("#39FF14"))
            setPadding(0, dp(4), 0, dp(4))
        }
        ipCard.addView(ipLabel)

        val savedPcIp = getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE).getString("paired_pc_ip", "Not Paired Yet")
        pcIpLabel = TextView(this).apply {
            text = "Connected PC IP: $savedPcIp"
            textSize = 12f
            typeface = Typeface.MONOSPACE
            setTextColor(Color.parseColor("#00BFFF"))
            setPadding(0, 0, 0, dp(6))
            isClickable = true
            setOnClickListener { showPairingDialog() }
        }
        ipCard.addView(pcIpLabel)

        val pairBtn = Button(this).apply {
            text = "🔗 Pair with PC IP Address"
            textSize = 12.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = createRounded(Color.parseColor("#00BFFF"), radiusDp = 6f)
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(42)).apply {
                topMargin = dp(6)
                bottomMargin = dp(8)
            }
            layoutParams = lp
            setOnClickListener {
                showPairingDialog()
            }
        }
        ipCard.addView(pairBtn)

        val pushBtn = Button(this).apply {
            text = "🔄 Push All Phone Slots to PC"
            textSize = 12.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = createRounded(Color.parseColor("#059669"), radiusDp = 6f)
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(42)).apply {
                bottomMargin = dp(8)
            }
            layoutParams = lp
            setOnClickListener {
                val count = pushAllSlotsToPc(this@MainActivity)
                if (count > 0) {
                    Toast.makeText(this@MainActivity, "Pushed $count slots to PC!", Toast.LENGTH_SHORT).show()
                } else {
                    val pcIp = getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE).getString("paired_pc_ip", "Not Paired Yet")
                    if (pcIp == "Not Paired Yet") {
                        Toast.makeText(this@MainActivity, "Please pair with PC IP first!", Toast.LENGTH_LONG).show()
                        showPairingDialog()
                    } else {
                        Toast.makeText(this@MainActivity, "Phone slots are empty. Copy some text first!", Toast.LENGTH_LONG).show()
                    }
                }
            }
        }
        ipCard.addView(pushBtn)

        statusLabel = TextView(this).apply {
            text = "Ready to sync copy/paste both ways."
            textSize = 12f
            setTextColor(Color.parseColor("#8B949E"))
            setPadding(0, dp(4), 0, 0)
        }
        ipCard.addView(statusLabel)

        root.addView(ipCard)

        // ================= DIRECT INPUT & CLIPBOARD SAVER CARD =================
        val saverCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = createRounded(Color.parseColor("#161B22"), Color.parseColor("#00BFFF"), 1, 10f)
            setPadding(dp(16), dp(16), dp(16), dp(16))
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                bottomMargin = dp(16)
            }
            layoutParams = lp
        }

        val saverTitle = TextView(this).apply {
            text = "SAVE TEXT OR CLIPBOARD TO A SLOT"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#00BFFF"))
        }
        saverCard.addView(saverTitle)

        // Updated button: User decides which slot to save current phone clipboard into!
        val quickClipBtn = Button(this).apply {
            text = "Save Current Phone Clipboard to Slot..."
            textSize = 13.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = createRounded(Color.parseColor("#00BFFF"), radiusDp = 6f)
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(44)).apply {
                topMargin = dp(8)
                bottomMargin = dp(10)
            }
            layoutParams = lp
            setOnClickListener {
                showSlotPickerForClipboard()
            }
        }
        saverCard.addView(quickClipBtn)

        val directInput = EditText(this).apply {
            hint = "Or type / paste text here directly..."
            setHintTextColor(Color.parseColor("#6B7280"))
            setTextColor(Color.WHITE)
            textSize = 13f
            background = createRounded(Color.parseColor("#0D1117"), Color.parseColor("#30363D"), 1, 6f)
            setPadding(dp(12), dp(10), dp(12), dp(10))
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                bottomMargin = dp(8)
            }
            layoutParams = lp
        }
        saverCard.addView(directInput)

        val choosePrompt = TextView(this).apply {
            text = "Tap a slot number below to save typed text or clipboard into it:"
            textSize = 11f
            setTextColor(Color.parseColor("#8B949E"))
            setPadding(0, 0, 0, dp(6))
        }
        saverCard.addView(choosePrompt)

        // 10 Slot Quick Action Badges with PC-style Color Indication
        val buttonsRow1 = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                bottomMargin = dp(6)
            }
            layoutParams = lp
        }
        for (i in 1..5) {
            val sBadge = createQuickSlotBadge(i, directInput)
            quickSlotButtons[i] = sBadge
            val lp = LinearLayout.LayoutParams(0, dp(38), 1f).apply {
                if (i > 1) leftMargin = dp(4)
            }
            sBadge.layoutParams = lp
            buttonsRow1.addView(sBadge)
        }
        saverCard.addView(buttonsRow1)

        val buttonsRow2 = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        for (i in 6..10) {
            val sBadge = createQuickSlotBadge(i, directInput)
            quickSlotButtons[i] = sBadge
            val lp = LinearLayout.LayoutParams(0, dp(38), 1f).apply {
                if (i > 6) leftMargin = dp(4)
            }
            sBadge.layoutParams = lp
            buttonsRow2.addView(sBadge)
        }
        saverCard.addView(buttonsRow2)

        root.addView(saverCard)

        // ================= SLOTS PREVIEW WITH PC COLOR INDICATION =================
        val slotsHeading = TextView(this).apply {
            text = "LIVE 10-SLOT PREVIEW (PC COLOR CODED)"
            textSize = 13f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#8B949E"))
            setPadding(0, 0, 0, dp(8))
        }
        root.addView(slotsHeading)

        for (i in 1..10) {
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                background = createRounded(Color.parseColor("#12161C"), Color.parseColor("#21262D"), 1, 8f)
                setPadding(dp(10), dp(10), dp(10), dp(10))
                val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                    bottomMargin = dp(8)
                }
                layoutParams = lp
            }
            slotRowCards[i] = card

            // Left Color Stripe (PC color indicator)
            val stripe = View(this).apply {
                background = createRounded(Color.parseColor(PC_SLOT_COLORS[i - 1]), radiusDp = 2f)
                val lp = LinearLayout.LayoutParams(dp(4), dp(28)).apply {
                    rightMargin = dp(8)
                }
                layoutParams = lp
            }
            slotIndicatorPills[i] = stripe
            card.addView(stripe)

            // Prominent Slot Number Badge: "#1" .. "#10"
            val numBadge = TextView(this).apply {
                text = "#$i"
                textSize = 11.5f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor(PC_SLOT_COLORS[i - 1]))
                gravity = Gravity.CENTER
                includeFontPadding = false
                background = createRounded(Color.parseColor("#161B22"), Color.parseColor(PC_SLOT_COLORS[i - 1]), 1, 4f)
                val lp = LinearLayout.LayoutParams(dp(32), dp(24)).apply {
                    rightMargin = dp(8)
                }
                layoutParams = lp
            }
            slotNumberBadges[i] = numBadge
            card.addView(numBadge)

            val sTitle = TextView(this).apply {
                text = "Slot $i: [Empty]"
                textSize = 13f
                setTextColor(Color.parseColor("#6E7681"))
                val lp = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                layoutParams = lp
            }
            slotTitleViews[i] = sTitle
            card.addView(sTitle)

            val saveClipBtn = Button(this).apply {
                text = "Save Clip"
                textSize = 11f
                isAllCaps = false
                setTextColor(Color.parseColor("#C9D1D9"))
                background = createRounded(Color.parseColor("#21262D"), radiusDp = 4f)
                val lp = LinearLayout.LayoutParams(dp(75), dp(34))
                layoutParams = lp
                setOnClickListener {
                    saveClipboardIntoSlot(i)
                }
            }
            card.addView(saveClipBtn)

            val clearBtn = Button(this).apply {
                text = "Clear"
                textSize = 11f
                isAllCaps = false
                setTextColor(Color.parseColor("#EF4444"))
                background = createRounded(Color.parseColor("#21262D"), radiusDp = 4f)
                val lp = LinearLayout.LayoutParams(dp(54), dp(34)).apply {
                    leftMargin = dp(6)
                }
                layoutParams = lp
                setOnClickListener {
                    clearSlotFromUser(i)
                }
            }
            slotClearButtons[i] = clearBtn
            card.addView(clearBtn)

            root.addView(card)
        }

        // Action Buttons: Clear All, Cross-Platform Sync, Exit RATT
        val clearAllBtn = Button(this).apply {
            text = "🗑️ Clear All Slots"
            textSize = 12.5f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#EF4444"))
            background = createRounded(Color.parseColor("#161B22"), Color.parseColor("#EF4444"), 1, 6f)
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(42)).apply {
                topMargin = dp(8)
                bottomMargin = dp(12)
            }
            layoutParams = lp
            setOnClickListener {
                clearAllSlotsFromUser()
            }
        }
        root.addView(clearAllBtn)

        val crossPlatformHeading = TextView(this).apply {
            text = "CROSS-PLATFORM SYNC (PREMIUM & ENTERPRISE)"
            textSize = 11f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#8B949E"))
            setPadding(0, dp(8), 0, dp(6))
        }
        root.addView(crossPlatformHeading)

        val crossSyncRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                bottomMargin = dp(12)
            }
            layoutParams = lp
        }

        val syncIosBtn = Button(this).apply {
            text = "📱 Sync with iOS"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = createRounded(Color.parseColor("#2563EB"), radiusDp = 6f)
            val lp = LinearLayout.LayoutParams(0, dp(42), 1f).apply {
                rightMargin = dp(4)
            }
            layoutParams = lp
            setOnClickListener {
                handleCrossPlatformSync("iOS")
            }
        }
        crossSyncRow.addView(syncIosBtn)

        val syncMacBtn = Button(this).apply {
            text = "💻 Sync with macOS"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = createRounded(Color.parseColor("#7C3AED"), radiusDp = 6f)
            val lp = LinearLayout.LayoutParams(0, dp(42), 1f).apply {
                leftMargin = dp(4)
            }
            layoutParams = lp
            setOnClickListener {
                handleCrossPlatformSync("macOS")
            }
        }
        crossSyncRow.addView(syncMacBtn)
        root.addView(crossSyncRow)

        // Share & Mirror section (Rule 4: Premium & Enterprise)
        val shareMirrorHeading = TextView(this).apply {
            text = "SHARE & MIRROR (PREMIUM & ENTERPRISE)"
            textSize = 11f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#8B949E"))
            setPadding(0, dp(4), 0, dp(6))
        }
        root.addView(shareMirrorHeading)

        val shareMirrorRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                bottomMargin = dp(14)
            }
            layoutParams = lp
        }

        val shareBtn = Button(this).apply {
            text = "🔗 Share with Account"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = createRounded(Color.parseColor("#059669"), radiusDp = 6f)
            val lp = LinearLayout.LayoutParams(0, dp(42), 1f).apply {
                rightMargin = dp(4)
            }
            layoutParams = lp
            setOnClickListener {
                handleShareRequest()
            }
        }
        shareMirrorRow.addView(shareBtn)

        val mirrorBtn = Button(this).apply {
            text = "🪞 Mirror Devices"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = createRounded(Color.parseColor("#D97706"), radiusDp = 6f)
            val lp = LinearLayout.LayoutParams(0, dp(42), 1f).apply {
                leftMargin = dp(4)
            }
            layoutParams = lp
            setOnClickListener {
                handleMirrorRequest()
            }
        }
        shareMirrorRow.addView(mirrorBtn)
        root.addView(shareMirrorRow)

        val exitBtn = Button(this).apply {
            text = "🚪 Exit RATT (Wipe All Slots on Exit)"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#9CA3AF"))
            background = createRounded(Color.parseColor("#161B22"), Color.parseColor("#30363D"), 1, 6f)
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(40)).apply {
                bottomMargin = dp(24)
            }
            layoutParams = lp
            setOnClickListener {
                emptySlotsAndExit()
            }
        }
        root.addView(exitBtn)

        scroll.addView(root)
        setContentView(scroll)

        startFloatingService()
        registerClipboardSyncListener()
        refreshOverlayStatus()
    }

    private fun createQuickSlotBadge(slotId: Int, inputField: EditText): TextView {
        return TextView(this).apply {
            text = "Slot $slotId"
            textSize = 11f
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            maxLines = 1
            isSingleLine = true
            includeFontPadding = false
            setTextColor(Color.parseColor("#8B949E"))
            background = createRounded(Color.parseColor("#161B22"), Color.parseColor("#30363D"), 1, 6f)
            setPadding(0, 0, 0, 0)
            isClickable = true
            setOnClickListener {
                val typed = inputField.text.toString().trim()
                if (typed.isNotEmpty()) {
                    SlotRepository.put(slotId, typed)
                    onSlotUpdated(slotId, typed)
                    sendToPc(this@MainActivity, slotId, typed)
                    inputField.setText("")
                    Toast.makeText(this@MainActivity, "Saved typed text into Slot $slotId!", Toast.LENGTH_SHORT).show()
                } else {
                    saveClipboardIntoSlot(slotId)
                }
            }
        }
    }

    private fun showSlotPickerForClipboard() {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
        val text = clipboard?.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString().orEmpty()
        val textToSave = if (text.isNotBlank()) text else lastCopiedText

        if (textToSave.isBlank()) {
            Toast.makeText(this, "Phone clipboard is empty! Copy text first.", Toast.LENGTH_LONG).show()
            return
        }

        // Rule 1: 10 Free Slots for everyone
        val slotOptions = Array(10) { i ->
            val slotNum = i + 1
            val slot = SlotRepository.liveSlots[slotNum]
            if (slot != null && slot.preview.isNotEmpty()) {
                "#$slotNum  Slot $slotNum: ● ${slot.preview}"
            } else {
                "#$slotNum  Slot $slotNum: [Empty]"
            }
        }

        AlertDialog.Builder(this)
            .setTitle("Save Clipboard to Which Slot?")
            .setItems(slotOptions) { _, which ->
                val chosenSlot = which + 1
                SlotRepository.put(chosenSlot, textToSave)
                lastCopiedText = textToSave
                onSlotUpdated(chosenSlot, textToSave)
                sendToPc(this, chosenSlot, textToSave)
                Toast.makeText(this, "Saved clipboard to Slot $chosenSlot! (Synced to PC)", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showPairingDialog() {
        val prefs = getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
        val curIp = prefs.getString("paired_pc_ip", "") ?: ""
        val phonePin = SlotRepository.generatePairingPin()

        val inputIp = EditText(this).apply {
            hint = "PC IP Address (e.g. 192.168.x.x)"
            textSize = 15f
            setTextColor(Color.parseColor("#39FF14"))
            typeface = Typeface.MONOSPACE
            background = createRounded(Color.parseColor("#0D1117"), Color.parseColor("#30363D"), 1, 6f)
            setPadding(dp(12), dp(12), dp(12), dp(12))
            if (curIp.isNotEmpty() && curIp != "Not Paired Yet") {
                setText(curIp)
            }
            setSelection(text.length)
        }

        val inputPin = EditText(this).apply {
            hint = "6-Digit Pairing PIN from PC"
            textSize = 15f
            setTextColor(Color.parseColor("#00BFFF"))
            typeface = Typeface.MONOSPACE
            background = createRounded(Color.parseColor("#0D1117"), Color.parseColor("#30363D"), 1, 6f)
            setPadding(dp(12), dp(12), dp(12), dp(12))
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(12), dp(20), dp(4))
            addView(inputIp)
            val spacer = View(this@MainActivity).apply {
                layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(10))
            }
            addView(spacer)
            addView(inputPin)
        }

        AlertDialog.Builder(this)
            .setTitle("🔗 Secure Pair with Windows PC")
            .setMessage("On PC, click 'Pair Android' to get your PC IP and 6-digit PIN.\n(Phone Pairing PIN: $phonePin)")
            .setView(container)
            .setPositiveButton("Pair & Sync") { _, _ ->
                val enteredIp = inputIp.text.toString().trim()
                val enteredPin = inputPin.text.toString().trim()
                if (enteredIp.isEmpty()) return@setPositiveButton
                thread(isDaemon = true) {
                    var pairedOk = false
                    var errMsg = "Could not reach PC on port 49210"
                    try {
                        val url = URL("http://$enteredIp:49210/pair")
                        val conn = url.openConnection() as HttpURLConnection
                        conn.requestMethod = "POST"
                        conn.doOutput = true
                        conn.connectTimeout = 3000
                        conn.readTimeout = 3000
                        conn.setRequestProperty("Content-Type", "application/json")
                        val body = JSONObject().apply {
                            put("action", "PAIR")
                            put("pin", enteredPin)
                        }
                        conn.outputStream.use {
                            it.write(body.toString().toByteArray(Charsets.UTF_8))
                            it.flush()
                        }
                        val code = conn.responseCode
                        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                        val respText = stream?.bufferedReader()?.readText().orEmpty()
                        if (code == 200) {
                            val respJson = JSONObject(respText)
                            val token = respJson.optString("sync_token", "")
                            if (token.length >= 16) {
                                SlotRepository.setSyncToken(this@MainActivity, token)
                                prefs.edit().putString("paired_pc_ip", enteredIp).apply()
                                pairedOk = true
                            } else {
                                errMsg = "PC did not return a valid sync token"
                            }
                        } else {
                            errMsg = try { JSONObject(respText).optString("error", "Pairing rejected ($code)") } catch (_: Exception) { "Pairing rejected ($code)" }
                        }
                    } catch (e: Exception) {
                        errMsg = e.message ?: errMsg
                    }
                    runOnUiThread {
                        if (pairedOk) {
                            pcIpLabel?.text = "Connected PC IP: $enteredIp"
                            val count = pushAllSlotsToPc(this@MainActivity)
                            Toast.makeText(this@MainActivity, "Paired securely with PC ($enteredIp)! Synced $count slots.", Toast.LENGTH_LONG).show()
                        } else {
                            Toast.makeText(this@MainActivity, "Pairing failed: $errMsg", Toast.LENGTH_LONG).show()
                        }
                    }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun saveClipboardIntoSlot(slotId: Int) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
        val clipData = clipboard?.primaryClip
        if (clipData == null || clipData.itemCount == 0) {
            val fallback = lastCopiedText
            if (fallback.isNotBlank()) {
                saveTextToSlot(slotId, fallback)
            } else {
                Toast.makeText(this, "Phone clipboard is empty! Copy text or image first.", Toast.LENGTH_LONG).show()
            }
            return
        }

        val item = clipData.getItemAt(0)
        val uri = item.uri
        val clipMimeType = clipboard.primaryClipDescription?.let { desc ->
            if (desc.mimeTypeCount > 0) desc.getMimeType(0) else null
        } ?: ""

        if ((uri != null || clipMimeType.startsWith("image/")) && item.text.isNullOrBlank()) {
            Toast.makeText(this, "RATT Mobile supports text and links only.", Toast.LENGTH_SHORT).show()
            return
        }

        val text = item.coerceToText(this)?.toString().orEmpty()
        val textToSave = if (text.isNotBlank()) text else lastCopiedText
        if (textToSave.isNotBlank()) {
            saveTextToSlot(slotId, textToSave)
        } else {
            Toast.makeText(this, "Phone clipboard is empty! Copy text first.", Toast.LENGTH_LONG).show()
        }
    }

    private fun saveTextToSlot(slotId: Int, textToSave: String) {
        if (!UserTierManager.isAllowedPayloadForTier(this, textToSave)) {
            showTierUpgradeDialog("UPGRADE REQUIRED: Copying Document & Media files (.docx, .xls, .pdf, .mp4, etc.) is limited to Premium and Enterprise subscribers.")
            return
        }
        SlotRepository.put(slotId, textToSave)
        lastCopiedText = textToSave
        onSlotUpdated(slotId, textToSave)
        sendToPc(this, slotId, textToSave)
        Toast.makeText(this, "Saved clipboard into Slot $slotId! (Synced to PC)", Toast.LENGTH_SHORT).show()
    }

    override fun onResume() {
        super.onResume()
        SecurityHardening.enforceRuntimeDefense(this)
        RattHttpSyncServer.start(this)
        refreshOverlayStatus()
        refreshSlotsUI()
        val savedPcIp = getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE).getString("paired_pc_ip", "Not Paired Yet")
        pcIpLabel?.text = "Connected PC IP: $savedPcIp"
        if (canDrawOverlays()) {
            startFloatingService()
        }
    }

    private fun registerClipboardSyncListener() {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager ?: return
        clipListener = ClipboardManager.OnPrimaryClipChangedListener {
            try {
                val desc = clipboard.primaryClipDescription
                if (desc != null && (desc.hasMimeType("image/*") || desc.hasMimeType("video/*"))) {
                    // Do not block UI thread coercing media to text; media is saved via Slot buttons
                    return@OnPrimaryClipChangedListener
                }
                val clip = clipboard.primaryClip
                val text = clip?.getItemAt(0)?.coerceToText(this)?.toString().orEmpty()
                if (text.isNotBlank() && text != lastCopiedText) {
                    lastCopiedText = text
                    SlotRepository.put(1, text)
                    onSlotUpdated(1, text)
                    sendToPc(this, 1, text)
                    Toast.makeText(this, "Copied on Phone -> Synced to PC (Slot 1)", Toast.LENGTH_SHORT).show()
                }
            } catch (_: Exception) {}
        }
        clipboard.addPrimaryClipChangedListener(clipListener)
    }

    private fun canDrawOverlays(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Settings.canDrawOverlays(this)
        } else {
            true
        }
    }

    private fun refreshOverlayStatus() {
        if (canDrawOverlays()) {
            overlayStatusLabel?.text = "STATUS: ACTIVE (Floating Pop-up Enabled)"
            overlayStatusLabel?.setTextColor(Color.parseColor("#39FF14"))
            overlayActionBtn?.text = "Show Floating Pop-Up Bubble Now"
        } else {
            overlayStatusLabel?.text = "STATUS: PERMISSION REQUIRED ('Appear on top')"
            overlayStatusLabel?.setTextColor(Color.parseColor("#FF5252"))
            overlayActionBtn?.text = "Grant 'Appear On Top' Permission"
        }
    }

    private fun handleOverlayButtonClick() {
        if (!canDrawOverlays()) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                val intent = Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:$packageName")
                )
                startActivity(intent)
                Toast.makeText(this, "Turn ON 'Appear on top' for RATT, then return here", Toast.LENGTH_LONG).show()
            }
        } else {
            startFloatingService()
            FloatingAssistService.revealBubble()
            Toast.makeText(this, "RATT Floating Bubble is on your screen edge!", Toast.LENGTH_SHORT).show()
        }
    }

    private fun startFloatingService() {
        try {
            val intent = Intent(this, FloatingAssistService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
        } catch (_: Exception) {}
    }

    /**
     * Refreshes UI with PC-matching Color Indication:
     *   - Empty slots: Dimmed dark background with subtle border.
     *   - Slots with data: Glowing vibrant border, colored accent stripe, bold white text, and badge indicator!
     */
    fun refreshSlotsUI() {
        Handler(Looper.getMainLooper()).post {
            val isPaid = UserTierManager.hasPaidEntitlement(this)
            val currentTier = UserTierManager.getTier(this)
            tierBadge?.text = currentTier.uppercase()
            tierBadge?.setTextColor(if (isPaid) Color.parseColor("#39FF14") else Color.parseColor("#9CA3AF"))
            tierBadge?.background = createRounded(
                Color.parseColor("#161B22"),
                if (isPaid) Color.parseColor("#10B981") else Color.parseColor("#4B5563"),
                1, 6f
            )

            for (i in 1..10) {
                val slotColor = Color.parseColor(PC_SLOT_COLORS[i - 1])
                val slot = SlotRepository.liveSlots[i]
                val hasData = slot != null && slot.preview.isNotEmpty()

                // 1. Update Live Slot Row Card
                val rowCard = slotRowCards[i]
                val titleView = slotTitleViews[i]
                val stripe = slotIndicatorPills[i]
                val numBadge = slotNumberBadges[i]
                val clearBtn = slotClearButtons[i]

                if (hasData) {
                    rowCard?.background = createRounded(Color.parseColor("#10241B"), slotColor, 2, 8f)
                    titleView?.text = "Slot $i: ${slot!!.preview}"
                    titleView?.typeface = Typeface.DEFAULT_BOLD
                    titleView?.setTextColor(Color.WHITE)
                    stripe?.visibility = View.VISIBLE
                    stripe?.background = createRounded(slotColor, radiusDp = 2f)
                    numBadge?.background = createRounded(slotColor, radiusDp = 4f)
                    numBadge?.setTextColor(Color.WHITE)
                    numBadge?.text = "#$i"
                    clearBtn?.visibility = View.VISIBLE
                } else {
                    rowCard?.background = createRounded(Color.parseColor("#12161C"), Color.parseColor("#21262D"), 1, 8f)
                    titleView?.text = "Slot $i: [Empty]"
                    titleView?.typeface = Typeface.DEFAULT
                    titleView?.setTextColor(Color.parseColor("#6E7681"))
                    stripe?.visibility = View.VISIBLE
                    stripe?.background = createRounded(Color.parseColor("#21262D"), radiusDp = 2f)
                    numBadge?.background = createRounded(Color.parseColor("#161B22"), Color.parseColor("#30363D"), 1, 4f)
                    numBadge?.setTextColor(Color.parseColor("#8B949E"))
                    numBadge?.text = "#$i"
                    clearBtn?.visibility = View.VISIBLE
                }

                // 2. Update Quick Slot Button Badge
                val badge = quickSlotButtons[i]
                if (hasData) {
                    badge?.text = "● Slot $i"
                    badge?.typeface = Typeface.DEFAULT_BOLD
                    badge?.setTextColor(Color.WHITE)
                    badge?.background = createRounded(Color.parseColor("#133024"), slotColor, 1, 6f)
                } else {
                    badge?.text = "Slot $i"
                    badge?.typeface = Typeface.DEFAULT
                    badge?.setTextColor(Color.parseColor("#8B949E"))
                    badge?.background = createRounded(Color.parseColor("#161B22"), Color.parseColor("#30363D"), 1, 6f)
                }
            }
        }
    }

    fun clearSlotFromUser(slotId: Int) {
        SlotRepository.clear(slotId)
        FloatingAssistService.activeInstance?.onSlotClearedBroadcast(slotId)
        sendClearSlotToPc(this, slotId)
        sendToPc(this, slotId, "")
        statusLabel?.text = "Slot $slotId was cleared."
        statusLabel?.setTextColor(Color.parseColor("#FF5252"))
        refreshSlotsUI()
        Toast.makeText(this, "Slot $slotId cleared", Toast.LENGTH_SHORT).show()
    }

    fun clearAllSlotsFromUser() {
        SlotRepository.clearAll()
        FloatingAssistService.activeInstance?.onAllSlotsClearedBroadcast()
        sendClearAllToPc(this)
        for (i in 1..10) {
            sendToPc(this, i, "")
        }
        statusLabel?.text = "ALL slots were cleared."
        statusLabel?.setTextColor(Color.parseColor("#FF5252"))
        refreshSlotsUI()
        Toast.makeText(this, "All slots cleared", Toast.LENGTH_SHORT).show()
    }

    fun emptySlotsAndExit() {
        // Requirement 5: Empty all slots when user exits app
        SlotRepository.exitAndWipeAllSlots()
        sendClearAllToPc(this)
        for (i in 1..10) {
            sendToPc(this, i, "")
        }
        FloatingAssistService.activeInstance?.let { srv ->
            srv.stopSelf()
        }
        Toast.makeText(this, "Slots wiped from memory. Exiting RATT...", Toast.LENGTH_SHORT).show()
        finishAffinity()
    }

    fun showTierUpgradeDialog(customMessage: String? = null) {
        val currentTier = UserTierManager.getTier(this).uppercase()
        val options = arrayOf(
            "Basic (Free) - 10 Slots + Android to Windows PC Sync Free",
            "Premium ($0.99/mo) - Android to macOS & iOS Sync + Share & Mirror",
            "Enterprise ($2.99/mo) - Unlimited Slots + Team Sync & Workers"
        )
        val msg = (customMessage?.let { "$it\n\n" } ?: "") +
                "Current Plan: $currentTier\n\n" +
                "Choose a plan below to activate:"

        AlertDialog.Builder(this)
            .setTitle("⭐ RATT Subscription & Licensing")
            .setMessage(msg)
            .setItems(options) { _, which ->
                val newTier = when (which) {
                    1 -> UserTierManager.TIER_PREMIUM
                    2 -> UserTierManager.TIER_ENTERPRISE
                    else -> UserTierManager.TIER_BASIC
                }
                UserTierManager.setTier(this, newTier)
                Toast.makeText(this, "Plan updated to ${newTier.uppercase()}!", Toast.LENGTH_SHORT).show()
                refreshSlotsUI()
            }
            .setNegativeButton("Close", null)
            .show()
    }

    fun handleCrossPlatformSync(targetPlatform: String) {
        if (!UserTierManager.canSyncWithApple(this)) {
            AlertDialog.Builder(this)
                .setTitle("⭐ Upgrade to Premium or Enterprise")
                .setMessage("Android to Windows PC sync is 100% Free!\n\nCross-platform sync from Android to macOS and iOS is limited to Premium and Enterprise subscribers.\n\nPlease upgrade your plan to unlock instant syncing with $targetPlatform!")
                .setPositiveButton("Upgrade Now") { _, _ ->
                    showTierUpgradeDialog()
                }
                .setNegativeButton("Cancel", null)
                .show()
            return
        }

        val prefs = getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
        val lastTargetIp = prefs.getString("last_${targetPlatform.lowercase()}_ip", "") ?: ""

        val input = EditText(this).apply {
            hint = "e.g. <target-device-ip>"
            textSize = 15f
            setTextColor(Color.parseColor("#39FF14"))
            typeface = Typeface.MONOSPACE
            background = createRounded(Color.parseColor("#0D1117"), Color.parseColor("#30363D"), 1, 6f)
            setPadding(dp(12), dp(12), dp(12), dp(12))
            if (lastTargetIp.isNotEmpty()) setText(lastTargetIp)
            setSelection(text.length)
        }

        val container = FrameLayout(this).apply {
            setPadding(dp(20), dp(12), dp(20), dp(4))
            addView(input)
        }

        AlertDialog.Builder(this)
            .setTitle("Sync Android Slots with $targetPlatform")
            .setMessage("Enter the IP address of your $targetPlatform device running RATT:")
            .setView(container)
            .setPositiveButton("Sync Now") { _, _ ->
                val targetIp = input.text.toString().trim()
                if (targetIp.isNotEmpty()) {
                    prefs.edit().putString("last_${targetPlatform.lowercase()}_ip", targetIp).apply()
                    performCrossSyncToTarget(targetIp, targetPlatform)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun performCrossSyncToTarget(targetIp: String, platformName: String) {
        thread(isDaemon = true) {
            var sent = 0
            val ports = if (platformName == "iOS") listOf(49211, 49210) else listOf(49211, 49210)
            for (slotId in 1..10) {
                val content = SlotRepository.getSlotContent(slotId)
                if (content.isNotEmpty()) {
                    for (port in ports) {
                        try {
                            val url = URL("http://$targetIp:$port/sync_slot")
                            val conn = url.openConnection() as HttpURLConnection
                            conn.requestMethod = "POST"
                            conn.doOutput = true
                            conn.connectTimeout = 1500
                            conn.readTimeout = 1500
                            conn.setRequestProperty("Content-Type", "application/json")
                            val json = JSONObject().apply {
                                put("action", "SYNC_FROM_ANDROID")
                                put("slot_id", slotId)
                                put("content", content)
                                put("tier", UserTierManager.getTier(this@MainActivity))
                            }
                            val out = conn.outputStream
                            out.write(json.toString().toByteArray(Charsets.UTF_8))
                            out.flush()
                            out.close()
                            if (conn.responseCode in 200..299) {
                                sent++
                                break
                            }
                        } catch (_: Exception) {}
                    }
                } else {
                    for (port in ports) {
                        try {
                            val url = URL("http://$targetIp:$port/sync_slot")
                            val conn = url.openConnection() as HttpURLConnection
                            conn.requestMethod = "POST"
                            conn.doOutput = true
                            conn.connectTimeout = 1200
                            conn.readTimeout = 1200
                            conn.setRequestProperty("Content-Type", "application/json")
                            val json = JSONObject().apply {
                                put("action", "CLEAR_SLOT")
                                put("slot_id", slotId)
                                put("tier", UserTierManager.getTier(this@MainActivity))
                            }
                            val out = conn.outputStream
                            out.write(json.toString().toByteArray(Charsets.UTF_8))
                            out.flush()
                            out.close()
                            if (conn.responseCode in 200..299) break
                        } catch (_: Exception) {}
                    }
                }
            }
            Handler(Looper.getMainLooper()).post {
                Toast.makeText(this@MainActivity, "Cross-Platform Sync: Synchronized slots with $platformName ($targetIp)!", Toast.LENGTH_SHORT).show()
            }
        }
    }

    fun handleShareRequest() {
        if (!UserTierManager.canShareAndMirror(this)) {
            AlertDialog.Builder(this)
                .setTitle("⭐ Share - Premium & Enterprise Feature")
                .setMessage("Share allows you to copy, cut, and paste clipboard contents directly to a different RATT account.\n\nSharing across accounts is limited to Premium and Enterprise subscribers.\n\nPlease upgrade your plan to unlock cross-account sharing!")
                .setPositiveButton("Upgrade Now") { _, _ ->
                    showTierUpgradeDialog()
                }
                .setNegativeButton("Cancel", null)
                .show()
            return
        }
        Toast.makeText(this, "Cross-account Share is active", Toast.LENGTH_SHORT).show()
    }

    fun handleMirrorRequest() {
        if (!UserTierManager.canShareAndMirror(this)) {
            AlertDialog.Builder(this)
                .setTitle("⭐ Mirror - Premium & Enterprise Feature")
                .setMessage("Device Mirroring allows you to mirror your active clipboard slots across multiple devices in real-time.\n\nMirroring is limited to Premium and Enterprise subscribers.\n\nPlease upgrade your plan to unlock Device Mirroring!")
                .setPositiveButton("Upgrade Now") { _, _ ->
                    showTierUpgradeDialog()
                }
                .setNegativeButton("Cancel", null)
                .show()
            return
        }
        Toast.makeText(this, "Device Mirroring is active", Toast.LENGTH_SHORT).show()
    }

    fun onSlotUpdated(slotId: Int, content: String) {
        Handler(Looper.getMainLooper()).post {
            statusLabel?.text = "Slot $slotId updated! (${content.length} chars)"
            statusLabel?.setTextColor(Color.parseColor("#39FF14"))
            refreshSlotsUI()
        }
    }

    fun onSlotCleared(slotId: Int) {
        SlotRepository.clear(slotId)
        Handler(Looper.getMainLooper()).post {
            statusLabel?.text = "Slot $slotId was CLEARED."
            statusLabel?.setTextColor(Color.parseColor("#FF5252"))
            refreshSlotsUI()
        }
    }

    fun onAllSlotsCleared() {
        SlotRepository.clearAll()
        Handler(Looper.getMainLooper()).post {
            statusLabel?.text = "ALL slots were CLEARED."
            statusLabel?.setTextColor(Color.parseColor("#FF5252"))
            refreshSlotsUI()
        }
    }

    fun updatePcIpLabel(ip: String) {
        Handler(Looper.getMainLooper()).post {
            pcIpLabel?.text = "Connected PC IP: $ip"
        }
    }

    private fun getDeviceIpAddress(): String {
        return try {
            val interfaces = java.net.NetworkInterface.getNetworkInterfaces()
            var privateIp = ""
            var fallbackIp = ""
            while (interfaces.hasMoreElements()) {
                val iface = interfaces.nextElement()
                if (iface.isLoopback || !iface.isUp) continue
                val name = iface.name.lowercase()
                val addrs = iface.inetAddresses
                while (addrs.hasMoreElements()) {
                    val addr = addrs.nextElement()
                    if (!addr.isLoopbackAddress && addr is java.net.Inet4Address) {
                        val host = addr.hostAddress
                        if (!host.isNullOrEmpty() && host != "127.0.0.1") {
                            // Prioritize Hotspot (ap, swlan, softap) or Wi-Fi (wlan) interfaces
                            if (name.contains("ap") || name.contains("softap") || name.contains("swlan") || name.contains("wlan")) {
                                return host
                            }
                            if (host.startsWith("192.168.") || host.startsWith("10.") || host.startsWith("172.")) {
                                if (privateIp.isEmpty()) privateIp = host
                            } else {
                                if (fallbackIp.isEmpty()) fallbackIp = host
                            }
                        }
                    }
                }
            }
            if (privateIp.isNotEmpty()) privateIp else if (fallbackIp.isNotEmpty()) fallbackIp else "127.0.0.1"
        } catch (_: Exception) {
            "127.0.0.1"
        }
    }

    override fun onDestroy() {
        if (clipListener != null) {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            clipboard?.removePrimaryClipChangedListener(clipListener)
        }
        // Requirement 5: Empty all slots in RATT Android when user exits app
        SlotRepository.exitAndWipeAllSlots()
        if (activeInstance === this) activeInstance = null
        super.onDestroy()
    }
}
