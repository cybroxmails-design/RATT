package com.cybrox.ratt

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.widget.Toast

/**
 * ShareReceiverActivity — Ingests text and links shared from other Android apps.
 * Files, images, and media are restricted to text-only per design.
 */
class ShareReceiverActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        SlotRepository.init(this)

        val action = intent.action
        val type = intent.type

        if (Intent.ACTION_SEND == action && type != null) {
            val text = intent.getStringExtra(Intent.EXTRA_TEXT)
            if (!text.isNullOrBlank()) {
                promptSlotSelection(text.trim())
            } else {
                Toast.makeText(this, "RATT Mobile supports text and links only.", Toast.LENGTH_SHORT).show()
                finish()
            }
        } else {
            finish()
        }
    }

    private fun promptSlotSelection(textToSave: String) {
        val slotOptions = Array(10) { i -> "Slot #${i + 1}" }

        AlertDialog.Builder(this)
            .setTitle("Save Text to RATT Slot")
            .setItems(slotOptions) { _, which ->
                val slotId = which + 1
                SlotRepository.put(slotId, textToSave)
                MainActivity.activeInstance?.onSlotUpdated(slotId, textToSave)
                MainActivity.sendToPc(this, slotId, textToSave)
                Toast.makeText(this, "Saved to Slot #$slotId (Synced to PC)", Toast.LENGTH_SHORT).show()
                finish()
            }
            .setOnCancelListener { finish() }
            .show()
    }
}
