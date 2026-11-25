package com.cybrox.ratt

import android.content.Context
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.net.ServerSocket
import java.net.Socket
import kotlin.concurrent.thread

/**
 * RattHttpSyncServer.kt — Hardened Shared IPC Server on Ports 49210 & 49211
 *
 * Uses raw byte reading (`InputStream`) instead of `BufferedReader` so UTF-8 multi-byte
 * characters and iOS `URLSession` keep-alive sockets never hang or time out.
 * Listens on BOTH 49210 and 49211 for seamless pairing and two-way sync with iPhone (iOS) and PC.
 */
object RattHttpSyncServer {

    const val PORT = 49210
    const val IOS_PORT = 49211
    private const val MAX_BODY_BYTES = 65_536

    @Volatile
    private var isRunning = false
    private val serverSockets = mutableListOf<ServerSocket>()
    private val lock = Any()

    fun start(context: Context) {
        synchronized(lock) {
            if (isRunning && serverSockets.isNotEmpty() && serverSockets.any { !it.isClosed }) {
                return
            }
            isRunning = true
            val appCtx = context.applicationContext

            for (listenPort in listOf(PORT, IOS_PORT)) {
                thread(isDaemon = true, name = "RattHttpSyncServerThread-$listenPort") {
                    try {
                        val srv = ServerSocket(listenPort).apply {
                            reuseAddress = true
                        }
                        synchronized(lock) {
                            serverSockets.add(srv)
                        }

                        while (isRunning && !srv.isClosed) {
                            try {
                                val client = srv.accept()
                                handleClient(client, appCtx)
                            } catch (_: Exception) {
                                if (!isRunning) break
                            }
                        }
                    } catch (_: Exception) {
                        // Port may already be bound
                    }
                }
            }
        }
    }

    fun stop() {
        synchronized(lock) {
            isRunning = false
            for (srv in serverSockets) {
                try {
                    srv.close()
                } catch (_: Exception) {}
            }
            serverSockets.clear()
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

    private fun writeHttpResponse(out: java.io.OutputStream, status: String, jsonBody: String) {
        val bodyBytes = jsonBody.toByteArray(Charsets.UTF_8)
        val header = "HTTP/1.1 $status\r\n" +
            "Content-Type: application/json; charset=utf-8\r\n" +
            "X-Content-Type-Options: nosniff\r\n" +
            "Cache-Control: no-store\r\n" +
            "Connection: close\r\n" +
            "Content-Length: ${bodyBytes.size}\r\n\r\n"
        out.write(header.toByteArray(Charsets.US_ASCII))
        out.write(bodyBytes)
        out.flush()
    }

    /**
     * Reads raw HTTP request bytes up to `\r\n\r\n` and then reads exact `Content-Length` bytes.
     */
    private fun readHttpPacket(input: InputStream): Pair<String, ByteArray>? {
        val headerBuf = ByteArrayOutputStream()
        var state = 0
        while (headerBuf.size() < 16384) {
            val b = input.read()
            if (b == -1) break
            headerBuf.write(b)
            state = when {
                state == 0 && b == '\r'.code -> 1
                state == 1 && b == '\n'.code -> 2
                state == 2 && b == '\r'.code -> 3
                state == 3 && b == '\n'.code -> 4
                b == '\r'.code -> 1
                else -> 0
            }
            if (state == 4) break
        }
        val headerBytes = headerBuf.toByteArray()
        if (headerBytes.isEmpty()) return null
        val headerStr = String(headerBytes, Charsets.UTF_8)

        var contentLength = 0
        for (line in headerStr.split("\r\n").drop(1)) {
            val colon = line.indexOf(':')
            if (colon > 0) {
                val k = line.substring(0, colon).trim().lowercase()
                val v = line.substring(colon + 1).trim()
                if (k == "content-length") {
                    contentLength = v.toIntOrNull() ?: 0
                }
            }
        }
        if (contentLength < 0 || contentLength > MAX_BODY_BYTES) {
            return Pair(headerStr, ByteArray(0))
        }
        val bodyBytes = ByteArray(contentLength)
        var offset = 0
        while (offset < contentLength) {
            val count = input.read(bodyBytes, offset, contentLength - offset)
            if (count <= 0) break
            offset += count
        }
        return Pair(headerStr, if (offset == contentLength) bodyBytes else bodyBytes.copyOf(offset))
    }

    private fun buildAllSlotsJson(): JSONObject {
        val slotsObj = JSONObject()
        val clearedArr = org.json.JSONArray()
        for (i in 1..10) {
            val content = SlotRepository.getSlotContent(i)
            slotsObj.put(i.toString(), content)
            if (content.isEmpty() || SlotRepository.clearedSlots.contains(i)) {
                clearedArr.put(i)
            }
        }
        return JSONObject().apply {
            put("status", "ok")
            put("slots", slotsObj)
            put("cleared_slots", clearedArr)
        }
    }

    private fun handleClient(client: Socket, appContext: Context) {
        thread(isDaemon = true) {
            try {
                client.soTimeout = 3500
                val peerIp = client.inetAddress.hostAddress
                if (!isTrustedPrivateLanIp(peerIp)) {
                    client.close()
                    return@thread
                }

                val packet = readHttpPacket(client.getInputStream()) ?: run {
                    client.close()
                    return@thread
                }
                val headerStr = packet.first
                val bodyBytes = packet.second
                val body = String(bodyBytes, Charsets.UTF_8)

                val lines = headerStr.split("\r\n")
                val firstLine = lines.firstOrNull() ?: ""
                var httpMethod = ""
                var requestPath = ""
                val headers = HashMap<String, String>()

                if (firstLine.startsWith("GET ") || firstLine.startsWith("POST ")) {
                    val parts = firstLine.split(" ")
                    httpMethod = parts[0]
                    if (parts.size > 1) requestPath = parts[1]
                }
                for (line in lines.drop(1)) {
                    val colon = line.indexOf(':')
                    if (colon > 0) {
                        val k = line.substring(0, colon).trim().lowercase()
                        val v = line.substring(colon + 1).trim()
                        headers[k] = v
                    }
                }

                val suppliedToken = (headers["x-ratt-token"] ?: "").trim()
                if (suppliedToken.length >= 16) {
                    SlotRepository.setSyncToken(appContext, suppliedToken)
                }

                // 1. Pairing Handshake (/pair) from iPhone (iOS) or Windows/macOS PC
                if (requestPath.startsWith("/pair")) {
                    try {
                        val pairJson = if (body.isNotEmpty()) JSONObject(body) else JSONObject()
                        val incomingToken = pairJson.optString("sync_token", suppliedToken)
                        val isIos = pairJson.optString("device", "").equals("iOS", ignoreCase = true)
                        if (incomingToken.length >= 16) {
                            SlotRepository.setSyncToken(appContext, incomingToken)
                        }
                        if (!peerIp.isNullOrEmpty() && peerIp != "127.0.0.1") {
                            val prefs = appContext.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
                            if (isIos) {
                                prefs.edit().putString("last_ios_ip", peerIp).apply()
                            } else {
                                prefs.edit().putString("paired_pc_ip", peerIp).putString("last_ios_ip", peerIp).apply()
                            }
                            MainActivity.activeInstance?.updatePcIpLabel(peerIp)
                        }
                        val resp = buildAllSlotsJson().apply {
                            put("sync_token", SlotRepository.getOrCreateSyncToken(appContext))
                        }
                        writeHttpResponse(client.getOutputStream(), "200 OK", resp.toString())
                        client.close()
                        return@thread
                    } catch (_: Exception) {
                        writeHttpResponse(client.getOutputStream(), "200 OK", "{\"status\":\"ok\"}")
                        return@thread
                    }
                }

                // 2. GET /get_all_slots
                if (httpMethod == "GET" && requestPath.contains("get_all_slots")) {
                    if (!peerIp.isNullOrEmpty() && peerIp != "127.0.0.1") {
                        appContext.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
                            .edit()
                            .putString("last_ios_ip", peerIp)
                            .apply()
                    }
                    val resp = buildAllSlotsJson()
                    writeHttpResponse(client.getOutputStream(), "200 OK", resp.toString())
                    client.close()
                    return@thread
                }

                // 3. POST /sync_slot, /sync_from_phone, /clear_slot, /clear_all
                if (httpMethod == "POST" && body.isNotEmpty()) {
                    try {
                        val json = SlotRepository.processIncomingWireLine(body) ?: JSONObject(body)
                        val action = json.optString("action").uppercase()
                        val slotId = json.optInt("slot_id", json.optInt("slot", 1))

                        if (!peerIp.isNullOrEmpty() && peerIp != "127.0.0.1") {
                            val prefs = appContext.getSharedPreferences("ratt_v2_prefs", Context.MODE_PRIVATE)
                            if (action == "SYNC_FROM_IOS") {
                                prefs.edit().putString("last_ios_ip", peerIp).apply()
                            }
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
                        writeHttpResponse(client.getOutputStream(), "200 OK", "{\"status\": \"ok\"}")
                        client.close()
                        return@thread
                    } catch (_: Exception) {
                        writeHttpResponse(client.getOutputStream(), "200 OK", "{\"status\": \"ok\"}")
                        return@thread
                    }
                }

                writeHttpResponse(client.getOutputStream(), "200 OK", "{\"status\": \"ok\"}")
                client.close()
            } catch (_: Exception) {
            } finally {
                try { client.close() } catch (_: Exception) {}
            }
        }
    }
}
