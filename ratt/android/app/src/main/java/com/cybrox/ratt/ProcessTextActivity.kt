package com.cybrox.ratt

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.util.TypedValue
import android.view.Gravity
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast

/**
 * RATT v2 Android Native Highlight / Selection Handler (`ACTION_PROCESS_TEXT`).
 *
 * When a user long-presses to highlight text in ANY Android app (Chrome, WhatsApp, Samsung Notes, etc.),
 * "Copy to RATT Slot" appears in the native text selection toolbar.
 *
 * Tapping it opens this quick slot chooser dialog so the user can select which slot (1 to 10)
 * to save the highlighted text into, immediately updating the slot and syncing it with the PC.
 */
class ProcessTextActivity : Activity() {

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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(
            WindowManager.LayoutParams.FLAG_SECURE,
            WindowManager.LayoutParams.FLAG_SECURE
        )
        SlotRepository.init(this)

        val selectedText = intent?.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)?.toString().orEmpty()
        if (selectedText.isBlank()) {
            Toast.makeText(this, "No text was selected", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = roundedBg(Color.parseColor("#FFFFFF"), Color.parseColor("#D1D5DB"), 1, 12f)
            setPadding(dp(18), dp(18), dp(18), dp(18))
        }

        // Header Title
        val header = TextView(this).apply {
            text = "Copy to RATT Slot"
            textSize = 16f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#111827"))
            setPadding(0, 0, 0, dp(4))
        }
        root.addView(header)

        // Text snippet preview
        val snippet = if (selectedText.length > 50) selectedText.take(48) + "..." else selectedText
        val preview = TextView(this).apply {
            text = "\"$snippet\""
            textSize = 12f
            setTextColor(Color.parseColor("#4B5563"))
            background = roundedBg(Color.parseColor("#F3F4F6"), radiusDp = 6f)
            setPadding(dp(10), dp(6), dp(10), dp(6))
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                bottomMargin = dp(14)
            }
            layoutParams = lp
        }
        root.addView(preview)

        val subPrompt = TextView(this).apply {
            text = "Select a slot to save this text into:"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#374151"))
            setPadding(0, 0, 0, dp(8))
        }
        root.addView(subPrompt)

        val scroll = ScrollView(this)
        val slotsList = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }

        for (slotId in 1..10) {
            val existingSlot = SlotRepository.liveSlots[slotId]
            val existingPreview = existingSlot?.preview?.takeIf { it.isNotEmpty() } ?: "[Empty]"

            val slotBtn = Button(this).apply {
                text = "#$slotId  Slot $slotId: $existingPreview"
                textSize = 13f
                isAllCaps = false
                gravity = Gravity.START or Gravity.CENTER_VERTICAL
                setTextColor(Color.parseColor("#1F2937"))
                background = roundedBg(Color.parseColor("#F9FAFB"), Color.parseColor("#E5E7EB"), 1, 6f)
                setPadding(dp(12), dp(10), dp(12), dp(10))
                val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(44)).apply {
                    bottomMargin = dp(6)
                }
                layoutParams = lp

                setOnClickListener {
                    saveToSlotAndFinish(slotId, selectedText)
                }
            }
            slotsList.addView(slotBtn)
        }

        scroll.addView(slotsList)
        root.addView(scroll, LinearLayout.LayoutParams(dp(290), dp(240)))

        // Cancel button
        val cancelBtn = Button(this).apply {
            text = "Cancel"
            textSize = 13f
            setTextColor(Color.parseColor("#6B7280"))
            background = roundedBg(Color.TRANSPARENT, radiusDp = 6f)
            setOnClickListener { finish() }
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(40)).apply {
                topMargin = dp(8)
            }
            layoutParams = lp
        }
        root.addView(cancelBtn)

        setContentView(root)
    }

    private fun saveToSlotAndFinish(slotId: Int, text: String) {
        SlotRepository.put(slotId, text)
        MainActivity.activeInstance?.onSlotUpdated(slotId, text)
        MainActivity.sendToPc(this, slotId, text)
        FloatingAssistService.activeInstance?.showBubbleIfPermitted()

        Toast.makeText(this, "Saved to RATT Slot $slotId (Synced to PC!)", Toast.LENGTH_SHORT).show()
        finish()
    }
}
