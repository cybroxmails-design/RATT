package com.cybrox.ratt

import android.content.Context

/**
 * UserTierManager.kt — Enforces RATT Commercial Licensing & PC Subscription Limitations on Android:
 *   1. Basic (Free):
 *      - Max 10 slots (1..10) for plain text, unformatted links, images, and vector diagrams (SVG).
 *      - Android <-> Windows PC local Wi-Fi sync is Free.
 *      - No Document & Media file copy/cut/paste (.docx, .xls, .pdf, .mp4, etc.).
 *      - No Android <-> iOS or Android <-> macOS cross-platform sync.
 *      - No Share & Mirror across accounts/devices.
 *      - No 9-Language Translation.
 *   2. Premium ($0.99/mo):
 *      - Custom slots (10 to 50,000).
 *      - Documents & Media files (.docx, .xls, .pdf, .mp4, etc.).
 *      - Android <-> iOS & macOS Virtual Keyboard Sync.
 *      - Share & Mirror across accounts/devices.
 *      - 9-Language Translation.
 *   3. Enterprise ($2.99/mo):
 *      - 50 base slots (expandable up to 50,000) + Team worker accounts (1 to 3,000 workers)
 *      - All Premium features included.
 */
object UserTierManager {
    const val TIER_BASIC = "basic"
    const val TIER_PREMIUM = "premium"
    const val TIER_ENTERPRISE = "enterprise"

    const val BASIC_SLOT_LIMIT = 10
    const val ENTERPRISE_BASE_SLOTS = 50
    const val PREMIUM_MAX_CUSTOM_SLOTS = 50_000
    const val ENTERPRISE_MAX_WORKERS = 3_000

    private const val PREFS_NAME = "ratt_v2_prefs"
    private const val KEY_USER_TIER = "ratt_user_tier"

    private val DOCUMENT_AND_MEDIA_EXTENSIONS = setOf(
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf",
        ".txt", ".csv", ".rtf", ".odt", ".ods", ".odp",
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
        ".mp4", ".mkv", ".mov", ".avi", ".webm",
        ".zip", ".rar", ".7z", ".tar", ".gz"
    )

    fun getTier(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getString(KEY_USER_TIER, TIER_BASIC) ?: TIER_BASIC
    }

    fun setTier(context: Context, tier: String) {
        val normalized = tier.lowercase().trim()
        val validTier = when (normalized) {
            TIER_PREMIUM -> TIER_PREMIUM
            TIER_ENTERPRISE -> TIER_ENTERPRISE
            else -> TIER_BASIC
        }
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_USER_TIER, validTier).apply()
        SlotRepository.userTier = validTier
    }

    fun hasPaidEntitlement(context: Context): Boolean {
        val tier = getTier(context)
        return tier == TIER_PREMIUM || tier == TIER_ENTERPRISE
    }

    fun isEnterprise(context: Context): Boolean {
        return getTier(context) == TIER_ENTERPRISE
    }

    fun getMaxSlots(context: Context): Int {
        return when (getTier(context)) {
            TIER_ENTERPRISE -> ENTERPRISE_BASE_SLOTS
            TIER_PREMIUM -> PREMIUM_MAX_CUSTOM_SLOTS
            else -> BASIC_SLOT_LIMIT
        }
    }

    fun getMaxEnterpriseWorkers(context: Context): Int {
        return if (isEnterprise(context)) ENTERPRISE_MAX_WORKERS else 1
    }

    fun canAccessSlot(context: Context, slotId: Int): Boolean {
        return slotId in 1..getMaxSlots(context)
    }

    // Android <-> Windows PC sync is Free
    fun canSyncWithWindowsPc(context: Context): Boolean {
        return getTier(context).isNotEmpty()
    }

    // Requirement 2: Android to iOS and macOS are ONLY available in Premium and Enterprise
    fun canSyncWithApple(context: Context): Boolean {
        return hasPaidEntitlement(context)
    }

    // Requirement 3: PC Subscription Limitation — Documents & Media files require Premium or Enterprise
    fun canCopyDocumentAndMediaFiles(context: Context): Boolean {
        return hasPaidEntitlement(context)
    }

    // Requirement 3: PC Subscription Limitation — 9-Language Translation requires Premium or Enterprise
    fun canTranslate(context: Context): Boolean {
        return hasPaidEntitlement(context)
    }

    // Requirement 3: PC Subscription Limitation — Share & Mirror require Premium or Enterprise
    fun canShareAndMirror(context: Context): Boolean {
        return hasPaidEntitlement(context)
    }

    /**
     * Checks if a payload represents a Document or Media file attachment and enforces
     * the PC subscription rule (Basic users cannot copy/paste Document & Media files).
     */
    fun isAllowedPayloadForTier(context: Context, payloadText: String): Boolean {
        if (hasPaidEntitlement(context)) return true
        val trimmed = payloadText.trim().lowercase()
        // COM-06: Never unconditionally allow [FILE] payloads on Basic tier
        if (trimmed.startsWith("[file]")) {
            for (ext in DOCUMENT_AND_MEDIA_EXTENSIONS) {
                if (trimmed.endsWith(ext)) return false
            }
        }
        for (ext in DOCUMENT_AND_MEDIA_EXTENSIONS) {
            if (trimmed.endsWith(ext) && (trimmed.startsWith("file://") || trimmed.contains("/") || trimmed.contains("\\"))) {
                return false
            }
        }
        return true
    }
}
