"""
RATT Network & Socket Stress Test
Tests socket concurrency, large file transfers, and socket limits.
"""

import socket
import threading
import time
import json
import os

def test_socket_loopback_throughput():
    print("--- 5. BENCHMARKING LAN TCP LOOPBACK THROUGHPUT ---")
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    port = server_sock.getsockname()[1]
    server_sock.listen(128)
    
    transferred_bytes = 0
    server_done = threading.Event()
    
    def server_thread():
        nonlocal transferred_bytes
        conn, _ = server_sock.accept()
        total = 0
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            total += len(chunk)
        transferred_bytes = total
        conn.close()
        server_sock.close()
        server_done.set()
        
    t = threading.Thread(target=server_thread, daemon=True)
    t.start()
    
    # Send 50 MB
    payload_size = 50 * 1024 * 1024
    chunk_data = b"R" * 65536
    chunks_count = payload_size // len(chunk_data)
    
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(("127.0.0.1", port))
    
    start = time.perf_counter()
    for _ in range(chunks_count):
        client_sock.sendall(chunk_data)
    client_sock.shutdown(socket.SHUT_WR)
    client_sock.close()
    
    server_done.wait(timeout=5.0)
    duration = time.perf_counter() - start
    mb_s = (payload_size / (1024 * 1024)) / duration
    print(f"Loopback TCP Throughput: {mb_s:.2f} MB/s (50MB in {duration:.3f}s)")
    return {"tcp_mb_s": mb_s, "duration": duration}

def test_connection_churn():
    print("\n--- 6. BENCHMARKING CONNECTION HANDSHAKE CHURN (CONNECT/DISCONNECT) ---")
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    port = server_sock.getsockname()[1]
    server_sock.listen(256)
    
    running = True
    def srv():
        while running:
            try:
                c, _ = server_sock.accept()
                c.sendall(b"OK\n")
                c.close()
            except Exception:
                break
                
    st = threading.Thread(target=srv, daemon=True)
    st.start()
    
    num_connections = 500
    start = time.perf_counter()
    for _ in range(num_connections):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", port))
        resp = s.recv(16)
        s.close()
    duration = time.perf_counter() - start
    handshakes_per_sec = num_connections / duration
    print(f"Handshake & Teardown Rate: {handshakes_per_sec:.2f} handshakes/sec (Latency: {(duration/num_connections)*1e3:.2f} ms/conn)")
    
    running = False
    server_sock.close()
    return {"handshakes_per_sec": handshakes_per_sec}

if __name__ == "__main__":
    t_res = test_socket_loopback_throughput()
    h_res = test_connection_churn()
    with open("network_benchmark.json", "w") as f:
        json.dump({"throughput": t_res, "handshakes": h_res}, f, indent=2)
