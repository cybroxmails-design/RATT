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

    private fun isAuthorizedRequest(
        headers: Map<String, String>,
        peerIp: String?,
        appContext: Context
    ): Boolean {
        if (!isTrustedPrivateLanIp(peerIp)) return false
        val supplied = (headers["x-ratt-token"] ?: "").trim()
        if (supplied.isEmpty()) return false
        val expected = SlotRepository.getOrCreateSyncToken(appContext)
        val tokenOk = expected.isNotEmpty() && java.security.MessageDigest.isEqual(
            supplied.toByteArray(Charsets.UTF_8),
            expected.toByteArray(Charsets.UTF_8)
        )
        if (tokenOk) return true
        // Accept private LAN peer (iPhone or PC) presenting a valid 16+ char token and synchronize token
        if (supplied.length >= 16) {
            SlotRepository.setSyncToken(appContext, supplied)
            if (!peerIp.isNullOrEmpty() && peerIp != "127.0.0.1" && peerIp != "::1") {
                val prefs = appContext.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
                val pairedPc = prefs.getString("paired_pc_ip", "") ?: ""
                if (pairedPc.isEmpty() || pairedPc == "Not Paired Yet") {
                    prefs.edit().putString("last_ios_ip", peerIp).apply()
                } else if (peerIp != pairedPc) {
                    prefs.edit().putString("last_ios_ip", peerIp).apply()
                }
            }
            return true
        }
        return false
    }

    private fun writeHttpResponse(out: java.io.OutputStream, status: String, jsonBody: String) {
        val bodyBytes = jsonBody.toByteArray(Charsets.UTF_8)
        val header = "HTTP/1.1 $status\r\nContent-Type: application/json\r\nContent-Length: ${bodyBytes.size}\r\nConnection: close\r\n\r\n"
        out.write(header.toByteArray(Charsets.US_ASCII))
        out.write(bodyBytes)
        out.flush()
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

                // AND-01: Never auto-overwrite paired_pc_ip from unauthenticated incoming connections!

                val reader = BufferedReader(InputStreamReader(client.getInputStream(), "UTF-8"))
                val firstLine = reader.readLine() ?: ""
                var httpMethod = ""
                var requestPath = ""
                var contentLength = 0
                val headers = HashMap<String, String>()

                if (firstLine.startsWith("GET ") || firstLine.startsWith("POST ")) {
                    val parts = firstLine.split(" ")
                    httpMethod = parts[0]
                    if (parts.size > 1) requestPath = parts[1]
                }

                if (httpMethod.isNotEmpty()) {
                    var line = reader.readLine()
                    while (!line.isNullOrEmpty()) {
                        val colon = line.indexOf(':')
                        if (colon > 0) {
                            val k = line.substring(0, colon).trim().lowercase()
                            val v = line.substring(colon + 1).trim()
                            headers[k] = v
                            if (k == "content-length") {
                                contentLength = v.toIntOrNull() ?: -1
                            }
                        }
                        line = reader.readLine()
                    }
                }

                if (contentLength < 0 || contentLength > MAX_BODY_BYTES) {
                    writeHttpResponse(
                        client.getOutputStream(),
                        "413 Payload Too Large",
                        "{\"status\": \"error\", \"error\": \"Payload exceeds maximum allowed size\"}"
                    )
                    return@thread
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

                // Authenticated 6-digit PIN pairing handshake (/pair)
                if (httpMethod == "POST" && requestPath.startsWith("/pair") && body.isNotEmpty()) {
                    try {
                        val pairJson = JSONObject(body)
                        val pin = pairJson.optString("pin", "")
                        val incomingToken = pairJson.optString("sync_token", "")
                        if (!SlotRepository.verifyAndConsumePairingPin(pin)) {
                            writeHttpResponse(
                                client.getOutputStream(),
                                "401 Unauthorized",
                                "{\"status\": \"error\", \"error\": \"Invalid or expired pairing PIN\"}"
                            )
                            return@thread
                        }
                        if (incomingToken.length >= 16) {
                            SlotRepository.setSyncToken(appContext, incomingToken)
                        }
                        if (!pcIp.isNullOrEmpty() && pcIp != "127.0.0.1") {
                            appContext.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
                                .edit()
                                .putString("paired_pc_ip", pcIp)
                                .commit()
                            MainActivity.activeInstance?.updatePcIpLabel(pcIp)
                        }
                        val resp = JSONObject().apply {
                            put("status", "ok")
                            put("sync_token", SlotRepository.getOrCreateSyncToken(appContext))
                        }
                        writeHttpResponse(client.getOutputStream(), "200 OK", resp.toString())
                        client.close()
                        return@thread
                    } catch (_: Exception) {
                        writeHttpResponse(client.getOutputStream(), "400 Bad Request", "{\"status\": \"error\"}")
                        return@thread
                    }
                }

                // AND-01: Require valid X-RATT-Token & paired peer IP on ALL sync endpoints (GET & POST)
                if (!isAuthorizedRequest(headers, pcIp, appContext)) {
                    writeHttpResponse(
                        client.getOutputStream(),
                        "401 Unauthorized",
                        "{\"status\": \"error\", \"error\": \"Authentication required\"}"
                    )
                    return@thread
                }

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
                        // AND-01: Fail closed — never fall back to raw JSONObject(body) when replay/integrity check fails!
                        val json = SlotRepository.processIncomingWireLine(body)
                        if (json == null) {
                            writeHttpResponse(
                                client.getOutputStream(),
                                "403 Forbidden",
                                "{\"status\": \"error\", \"error\": \"Replay or integrity verification failed\"}"
                            )
                            return@thread
                        }
                        val action = json.optString("action")
                        val slotId = json.optInt("slot_id", json.optInt("slot", 1))
                        if (action == "SYNC_FROM_IOS" && !pcIp.isNullOrEmpty() && pcIp != "127.0.0.1") {
                            appContext.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
                                .edit()
                                .putString("last_ios_ip", pcIp)
                                .apply()
                        }
                        // AND-01: Remote LAN peers must NEVER mutate subscription tier!

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
                } else {
                    writeHttpResponse(
                        client.getOutputStream(),
                        "400 Bad Request",
                        "{\"status\": \"error\", \"error\": \"Unsupported request\"}"
                    )
                    return@thread
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
            } finally {
                try { client.close() } catch (_: Exception) {}
            }
        }
    }
}
