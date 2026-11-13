package com.cybrox.ratt

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.provider.Settings
import android.util.TypedValue
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.TextView

/**
 * Android FloatingAssistService.kt - Magnetic Floating Bubble & Direct Injection
 * (`mobile_implimentation.pdf` Section 5, Option 2: Floating Assist Overlay).
 *
 * On Android, RATT operates as a background service rendering a small floating assist bubble
 * (`WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY`) whenever an editable input field
 * receives focus. The user keeps Samsung Keyboard or Gboard active at all times, retaining
 * full autocorrect, swipe gestures, and voice dictation.
 */
class FloatingAssistService : Service() {

    companion object {
        var activeInstance: FloatingAssistService? = null

        fun revealBubble() {
            Handler(Looper.getMainLooper()).post {
                activeInstance?.showBubbleIfPermitted()
            }
        }
    }

    private lateinit var windowManager: WindowManager
    private lateinit var bubbleView: BubbleBadgeView
    private var overlayMenuView: RattOverlayMenuView? = null
    private var bubbleAttached = false
    private lateinit var bubbleParams: WindowManager.LayoutParams
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null

    /**
     * Custom View wrapper with `updateBadgeState()` to repaint UI to `[Empty]` in < 100ms (`DEL-002`).
     */
    class BubbleBadgeView(context: Context) : TextView(context) {
        fun updateBadgeState() {
            val count = SlotRepository.liveSlots.size
            text = if (count > 0) "RATT ($count)" else "RATT [Empty]"
        }
    }

    private fun dp(dpVal: Int): Int {
        return TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP,
            dpVal.toFloat(),
            resources.displayMetrics
        ).toInt()
    }

    override fun onCreate() {
        super.onCreate()
        activeInstance = this
        SlotRepository.init(this)
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager

        startForegroundSyncNotification()
        acquireWakeAndWifiLocks()
        RattHttpSyncServer.start(this)

        bubbleView = BubbleBadgeView(this).apply {
            text = "RATT"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            setPadding(dp(12), dp(8), dp(12), dp(8))
            background = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = dp(20).toFloat()
                setColor(Color.parseColor("#0D1117"))
                setStroke(dp(2), Color.parseColor("#00BFFF"))
            }
            updateBadgeState()
            setOnClickListener {
                showRattTrayMenu()
            }
        }

        val overlayType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        bubbleParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            overlayType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 0
            y = dp(220)
        }

        enableMagneticDrag(bubbleView)
        registerClipboardListener()
        showBubbleIfPermitted()
    }

    private fun startForegroundSyncNotification() {
        val channelId = "ratt_foreground_sync"
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "RATT Background Sync",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps RATT clipboard sync active even when screen is locked"
                setShowBadge(false)
            }
            notificationManager.createNotificationChannel(channel)
        }

        val launchIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            launchIntent,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0
        )

        val notification = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, channelId)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }.apply {
            setContentTitle("RATT Background Sync Active")
            setContentText("Syncing copy/paste with PC on port 49210")
            setSmallIcon(R.drawable.ic_launcher)
            setContentIntent(pendingIntent)
            setOngoing(true)
        }.build()

        try {
            if (Build.VERSION.SDK_INT >= 34) {
                startForeground(1001, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
            } else {
                startForeground(1001, notification)
            }
        } catch (_: Exception) {
            try {
                startForeground(1001, notification)
            } catch (_: Exception) {}
        }
    }

    private fun acquireWakeAndWifiLocks() {
        try {
            if (wakeLock == null) {
                val pm = getSystemService(Context.POWER_SERVICE) as? PowerManager
                wakeLock = pm?.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "RATT:SyncWakeLock")?.apply {
                    setReferenceCounted(false)
                    acquire(24 * 60 * 60 * 1000L) // 24 hours
                }
            }

            if (wifiLock == null) {
                val wm = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
                @Suppress("DEPRECATION")
                val wifiMode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    WifiManager.WIFI_MODE_FULL_LOW_LATENCY
                } else {
                    WifiManager.WIFI_MODE_FULL_HIGH_PERF
                }
                wifiLock = wm?.createWifiLock(wifiMode, "RATT:SyncWifiLock")?.apply {
                    setReferenceCounted(false)
                    acquire()
                }
            }
        } catch (_: Exception) {}
    }

    private var clipListener: android.content.ClipboardManager.OnPrimaryClipChangedListener? = null

    private fun registerClipboardListener() {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? android.content.ClipboardManager ?: return
        clipListener = android.content.ClipboardManager.OnPrimaryClipChangedListener {
            try {
                val clip = clipboard.primaryClip
                val text = clip?.getItemAt(0)?.text?.toString().orEmpty()
                if (text.isNotBlank() && text != MainActivity.lastCopiedText) {
                    MainActivity.lastCopiedText = text
                    SlotRepository.put(1, text)
                    MainActivity.activeInstance?.onSlotUpdated(1, text)
                    MainActivity.sendToPc(this, 1, text)
                    bubbleView.updateBadgeState()
                    android.widget.Toast.makeText(this, "Copied on Phone -> Synced to PC (Slot 1)", android.widget.Toast.LENGTH_SHORT).show()
                }
            } catch (_: Exception) {}
        }
        clipboard.addPrimaryClipChangedListener(clipListener)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForegroundSyncNotification()
        acquireWakeAndWifiLocks()
        RattHttpSyncServer.start(this)
        showBubbleIfPermitted()
        return START_STICKY
    }

    private fun enableMagneticDrag(view: View) {
        var initialX = 0
        var initialY = 0
        var touchX = 0f
        var touchY = 0f
        var moved = false

        view.setOnTouchListener { v, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = bubbleParams.x
                    initialY = bubbleParams.y
                    touchX = event.rawX
                    touchY = event.rawY
                    moved = false
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (event.rawX - touchX).toInt()
                    val dy = (event.rawY - touchY).toInt()
                    if (kotlin.math.abs(dx) > 8 || kotlin.math.abs(dy) > 8) {
                        moved = true
                    }
                    bubbleParams.x = initialX + dx
                    bubbleParams.y = initialY + dy
                    if (bubbleAttached) {
                        try {
                            windowManager.updateViewLayout(bubbleView, bubbleParams)
                        } catch (_: Exception) {}
                    }
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (!moved) {
                        v.performClick()
                    } else {
                        collapseToEdge()
                    }
                    true
                }
                else -> false
            }
        }
    }

    fun showBubbleIfPermitted() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
            return
        }
        bubbleView.updateBadgeState()
        if (!bubbleAttached) {
            try {
                windowManager.addView(bubbleView, bubbleParams)
                bubbleAttached = true
            } catch (_: Exception) {}
        } else {
            bubbleView.visibility = View.VISIBLE
        }
    }

    fun showRattTrayMenu() {
        // Inflates 10-slot grid with PC clipboard previews and Clear status
        dismissOverlayMenu()
        val menu = RattOverlayMenuView(this, SlotRepository.liveSlots)
        menu.onSlotSelected = { slot ->
            try {
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                val clip = android.content.ClipData.newPlainText("RATT Slot", slot.content)
                clipboard.setPrimaryClip(clip)
            } catch (_: Exception) {}
            RattAccessibilityService.injectText(slot.content)
            android.widget.Toast.makeText(this, "Slot ${slot.id} ready to paste!", android.widget.Toast.LENGTH_SHORT).show()
            collapseToEdge()
        }
        menu.onCloseRequested = {
            collapseToEdge()
        }
        overlayMenuView = menu

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(this)) {
            val overlayType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE
            }
            val menuParams = WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.MATCH_PARENT,
                overlayType,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT
            )
            try {
                windowManager.addView(menu, menuParams)
            } catch (_: Exception) {}
        }
    }

    fun collapseToEdge() {
        dismissOverlayMenu()
        val screenWidth = resources.displayMetrics.widthPixels
        bubbleParams.x = if (bubbleParams.x + bubbleView.width / 2 >= screenWidth / 2) {
            screenWidth - bubbleView.width
        } else {
            0
        }
        if (bubbleAttached) {
            try {
                windowManager.updateViewLayout(bubbleView, bubbleParams)
            } catch (_: Exception) {}
        }
    }

    private fun dismissOverlayMenu() {
        overlayMenuView?.let { menu ->
            try {
                windowManager.removeView(menu)
            } catch (_: Exception) {}
        }
        overlayMenuView = null
    }

    fun onSlotClearedBroadcast(slotId: Int) {
        SlotRepository.clear(slotId) // Zeroes memory array immediately
        Handler(Looper.getMainLooper()).post {
            bubbleView.updateBadgeState() // Repaints UI to [Empty]
            overlayMenuView?.refreshBadgeState(slotId)
        }
    }

    fun refreshOverlayMenu() {
        Handler(Looper.getMainLooper()).post {
            bubbleView.updateBadgeState()
            overlayMenuView?.refreshSlotsList()
        }
    }

    fun onAllSlotsClearedBroadcast() {
        SlotRepository.clearAll()
        Handler(Looper.getMainLooper()).post {
            bubbleView.updateBadgeState()
            overlayMenuView?.refreshBadgeState(null)
        }
    }

    fun updateSlotFromExternal(slotId: Int, content: String) {
        if (slotId in 1..10 && content.isNotEmpty()) {
            SlotRepository.put(slotId, content)
        }
        Handler(Looper.getMainLooper()).post {
            bubbleView.updateBadgeState()
            overlayMenuView?.refreshBadgeState(slotId)
            overlayMenuView?.refreshSlotsList()
        }
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // Requirement 5: Empty all slots when the user swipes/closes the RATT app from Recents
        SlotRepository.exitAndWipeAllSlots()
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        try {
            wakeLock?.let { if (it.isHeld) it.release() }
            wifiLock?.let { if (it.isHeld) it.release() }
        } catch (_: Exception) {}
        if (clipListener != null) {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? android.content.ClipboardManager
            clipboard?.removePrimaryClipChangedListener(clipListener)
        }
        dismissOverlayMenu()
        if (bubbleAttached) {
            try {
                windowManager.removeView(bubbleView)
            } catch (_: Exception) {}
            bubbleAttached = false
        }
        // Requirement 5: Empty slots in RATT Android when service/app is closed
        SlotRepository.exitAndWipeAllSlots()
        if (activeInstance === this) {
            activeInstance = null
        }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
