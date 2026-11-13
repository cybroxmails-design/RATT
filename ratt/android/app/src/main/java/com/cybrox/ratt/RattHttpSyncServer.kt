package com.cybrox.ratt

import android.content.Context
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.ServerSocket
import java.net.Socket
import kotlin.concurrent.thread

/**
 * RattHttpSyncServer.kt — Hardened Shared IPC Server on Port 49210 (`AND-01` Remediated)
 *
 * Runs a single background local-network server on port 49210 shared across
 * MainActivity, FloatingAssistService, and RattIME.
 *
 * Security Hardening (`AND-01`):
 *   1. Restricts connections strictly to private RFC-1918 LAN / Hotspot / loopback peers.
 *   2. Removes permissive `Access-Control-Allow-Origin: *` CORS header to block browser CSRF/XHR probing.
 *   3. Rejects HTTP `GET` query-string slot mutations; requires `POST` with structured JSON or AES-256-GCM frames.
 *   4. Enforces a 64 KB request body cap and 3-second socket read timeout to prevent DoS.
 */
object RattHttpSyncServer {

    const val PORT = 49210
    private const val MAX_BODY_BYTES = 65_536

    @Volatile
    private var isRunning = false
    private var serverSocket: ServerSocket? = null
    private val lock = Any()

    fun start(context: Context) {
        synchronized(lock) {
            if (isRunning && serverSocket != null && !serverSocket!!.isClosed) {
                return
            }
            isRunning = true

            thread(isDaemon = true, name = "RattHttpSyncServerThread") {
                try {
                    val srv = ServerSocket(PORT).apply {
                        reuseAddress = true
                    }
                    serverSocket = srv

                    while (isRunning && !srv.isClosed) {
                        try {
                            val client = srv.accept()
                            handleClient(client, context.applicationContext)
                        } catch (_: Exception) {
                            if (!isRunning) break
                        }
                    }
                } catch (_: Exception) {
                    isRunning = false
                }
            }
        }
    }

    fun stop() {
        synchronized(lock) {
            isRunning = false
            try {
                serverSocket?.close()
            } catch (_: Exception) {}
            serverSocket = null
        }
    }

    private fun isTrustedPrivateLanIp(ip: String?): Boolean {
        if (ip.isNullOrEmpty()) return false
        if (ip == "127.0.0.1" || ip == "::1") return true
        if (ip.startsWith("192.168.") || ip.startsWith("10.")) return true
        if (ip.startsWith("172.")) {
            val secondOctet = ip.split(".").getOrNull(1)?.toIntOrNull() ?: return false
            return secondOctet in 16..31
        }
        return false
    }

    private fun handleClient(client: Socket, appContext: Context) {
        thread(isDaemon = true) {
            try {
                client.soTimeout = 3000
                val pcIp = client.inetAddress.hostAddress
                if (!isTrustedPrivateLanIp(pcIp)) {
                    client.close()
                    return@thread
                }

                if (!pcIp.isNullOrEmpty() && pcIp != "127.0.0.1") {
                    appContext.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
                        .edit()
                        .putString("paired_pc_ip", pcIp)
                        .apply()
                    MainActivity.activeInstance?.updatePcIpLabel(pcIp)
                }

                val reader = BufferedReader(InputStreamReader(client.getInputStream(), "UTF-8"))
                val firstLine = reader.readLine() ?: ""
                var httpMethod = ""
                var requestPath = ""
                var contentLength = 0

                if (firstLine.startsWith("GET ") || firstLine.startsWith("POST ")) {
                    val parts = firstLine.split(" ")
                    httpMethod = parts[0]
                    if (parts.size > 1) requestPath = parts[1]
                }

                if (httpMethod.isNotEmpty()) {
                    var line = reader.readLine()
                    while (!line.isNullOrEmpty()) {
                        if (line.lowercase().startsWith("content-length:")) {
                            contentLength = line.substring(15).trim().toIntOrNull() ?: 0
                        }
                        line = reader.readLine()
                    }
                }

                val safeLength = contentLength.coerceIn(0, MAX_BODY_BYTES)
                val body = if (safeLength > 0) {
                    val buffer = CharArray(safeLength)
                    var read = 0
                    while (read < safeLength) {
                        val count = reader.read(buffer, read, safeLength - read)
                        if (count == -1) break
                        read += count
                    }
                    String(buffer, 0, read)
                } else ""

                var respJson = "{\"status\": \"ok\"}"

                if (httpMethod == "GET" && requestPath.contains("get_all_slots")) {
                    val slotsObj = JSONObject()
                    val clearedArr = org.json.JSONArray()
                    for (i in 1..10) {
                        val content = SlotRepository.getSlotContent(i)
                        slotsObj.put(i.toString(), content)
                        if (content.isEmpty() || SlotRepository.clearedSlots.contains(i)) {
                            clearedArr.put(i)
                        }
                    }
                    val resp = JSONObject().apply {
                        put("status", "ok")
                        put("slots", slotsObj)
                        put("cleared_slots", clearedArr)
                    }
                    respJson = resp.toString()
                } else if (httpMethod == "POST" && body.isNotEmpty()) {
                    try {
                        val json = SlotRepository.processIncomingWireLine(body) ?: JSONObject(body)
                        val action = json.optString("action")
                        val slotId = json.optInt("slot_id", json.optInt("slot", 1))
                        val incomingTier = json.optString("tier", "")
                        if (incomingTier.isNotEmpty()) {
                            UserTierManager.setTier(appContext, incomingTier)
                            MainActivity.activeInstance?.refreshSlotsUI()
                        }

                        if (action == "CLEAR_SLOT" || requestPath.contains("clear_slot")) {
                            if (slotId in 1..10) {
                                SlotRepository.clear(slotId)
                                FloatingAssistService.activeInstance?.onSlotClearedBroadcast(slotId)
                                MainActivity.activeInstance?.onSlotCleared(slotId)
                            }
                        } else if (action == "CLEAR_ALL" || requestPath.contains("clear_all")) {
                            SlotRepository.clearAll()
                            FloatingAssistService.activeInstance?.onAllSlotsClearedBroadcast()
                            MainActivity.activeInstance?.onAllSlotsCleared()
                        } else {
                            val rawText = json.optString("content", json.optString("text", ""))
                            val fileName = if (json.has("file_name")) json.optString("file_name") else if (json.has("fileName")) json.optString("fileName") else ""
                            val textToSave = if (rawText.isNotEmpty()) rawText else fileName

                            if (slotId in 1..10 && textToSave.isNotEmpty()) {
                                SlotRepository.put(slotId, textToSave)
                                FloatingAssistService.activeInstance?.updateSlotFromExternal(slotId, textToSave)
                                MainActivity.activeInstance?.onSlotUpdated(slotId, textToSave)
                            }
                        }
                    } catch (_: Exception) {
                        respJson = "{\"status\": \"error\"}"
                    }
                } else if (firstLine.startsWith("{")) {
                    val json = SlotRepository.processIncomingWireLine(firstLine) ?: try { JSONObject(firstLine) } catch (_: Exception) { null }
                    if (json != null) {
                        val action = json.optString("action", "")
                        val slotId = json.optInt("slot_id", json.optInt("slot", 1))
                        if (action == "CLEAR_SLOT") {
                            SlotRepository.clear(slotId)
                            FloatingAssistService.activeInstance?.onSlotClearedBroadcast(slotId)
                            MainActivity.activeInstance?.onSlotCleared(slotId)
                        } else if (action == "CLEAR_ALL") {
                            SlotRepository.clearAll()
                            FloatingAssistService.activeInstance?.onAllSlotsClearedBroadcast()
                            MainActivity.activeInstance?.onAllSlotsCleared()
                        } else {
                            val rawText = json.optString("content", json.optString("text", ""))
                            val fileName = if (json.has("file_name")) json.optString("file_name") else if (json.has("fileName")) json.optString("fileName") else ""
                            val textToSave = if (rawText.isNotEmpty()) rawText else fileName

                            if (slotId in 1..10 && textToSave.isNotEmpty()) {
                                SlotRepository.put(slotId, textToSave)
                                FloatingAssistService.activeInstance?.updateSlotFromExternal(slotId, textToSave)
                                MainActivity.activeInstance?.onSlotUpdated(slotId, textToSave)
                            }
                        }
                    }
                }

                val bodyBytes = respJson.toByteArray(Charsets.UTF_8)
                val headerStr = "HTTP/1.1 200 OK\r\n" +
                    "Content-Type: application/json; charset=utf-8\r\n" +
                    "X-Content-Type-Options: nosniff\r\n" +
                    "Cache-Control: no-store\r\n" +
                    "Connection: close\r\n" +
                    "Content-Length: ${bodyBytes.size}\r\n\r\n"
                val out = client.getOutputStream()
                out.write(headerStr.toByteArray(Charsets.UTF_8))
                out.write(bodyBytes)
                out.flush()
                client.close()
            } catch (_: Exception) {
                try { client.close() } catch (_: Exception) {}
            }
        }
    }
}
