"""
RATT Deep Bottleneck & Load Benchmark Suite
Empirically measures latency, CPU saturation, RAM footprint, and concurrency limits across:
1. PBKDF2 Key Derivation (Work factor vs CPU bottleneck)
2. AES-256-GCM Symmetric Crypto Throughput
3. Local ClipboardManager Slot Operations & Contention
4. Ephemeral Relay Mailbox Concurrent Throughput & Lock Contention
5. Memory Footprint Scaling (10k - 100k active payloads)
"""

import time
import os
import sys
import threading
import multiprocessing
import json
import ctypes
from ctypes import wintypes
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def get_process_memory():
    """Get current process memory in bytes on Windows."""
    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ('cb', wintypes.DWORD),
            ('PageFaultCount', wintypes.DWORD),
            ('PeakWorkingSetSize', ctypes.c_size_t),
            ('WorkingSetSize', ctypes.c_size_t),
            ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
            ('QuotaPagedPoolUsage', ctypes.c_size_t),
            ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
            ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
            ('PagefileUsage', ctypes.c_size_t),
            ('PeakPagefileUsage', ctypes.c_size_t),
        ]
    try:
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize
    except Exception:
        pass
    return 0

# Ensure ratt is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from ratt.remote_relay import (
    derive_share_secret,
    E2EESecurityChannel,
    EphemeralRelayMailbox,
    EncryptedEnvelope
)
from ratt.clipboard_manager import ClipboardManager

def benchmark_kdf():
    print("--- 1. BENCHMARKING KEY DERIVATION FUNCTION (PBKDF2-HMAC-SHA256, 100k iter) ---")
    start = time.perf_counter()
    iterations = 20
    for i in range(iterations):
        derive_share_secret(f"RT-{i:06d}")
    elapsed = time.perf_counter() - start
    per_op_ms = (elapsed / iterations) * 1000
    ops_per_sec_single_core = iterations / elapsed
    num_cores = multiprocessing.cpu_count()
    est_cluster_ops = ops_per_sec_single_core * num_cores
    
    print(f"Single KDF Duration: {per_op_ms:.2f} ms")
    print(f"Single-Core KDF Throughput: {ops_per_sec_single_core:.2f} ops/sec")
    print(f"Host Multi-Core ({num_cores} cores) Capacity: {est_cluster_ops:.2f} ops/sec")
    return {
        "kdf_latency_ms": per_op_ms,
        "kdf_single_core_ops": ops_per_sec_single_core,
        "kdf_multi_core_ops": est_cluster_ops,
        "cpu_cores": num_cores
    }

def benchmark_aes_gcm():
    print("\n--- 2. BENCHMARKING AES-256-GCM THROUGHPUT ---")
    shared_secret = os.urandom(32)
    channel = E2EESecurityChannel(shared_secret=shared_secret, mailbox_id="MB-BENCHMARK-001")
    payload_sizes = [1024, 64 * 1024, 1024 * 1024, 10 * 1024 * 1024] # 1KB, 64KB, 1MB, 10MB
    results = {}
    
    for size in payload_sizes:
        raw_text = "X" * size
        payload = {"type": "text", "content": raw_text, "meta": {"size": size}}
        start = time.perf_counter()
        count = 200 if size <= 64*1024 else (20 if size <= 1024*1024 else 4)
        for _ in range(count):
            env = channel.pack(payload)
            dec = channel.unpack(env)
            assert dec["content"] == raw_text
        duration = time.perf_counter() - start
        mb_processed = (size * count * 2) / (1024 * 1024) # encrypt + decrypt
        mb_per_sec = mb_processed / duration
        results[size] = {
            "size_bytes": size,
            "duration_s": duration,
            "count": count,
            "throughput_mb_s": mb_per_sec
        }
        print(f"Payload {size//1024} KB: {mb_per_sec:.2f} MB/s ({count} cycles in {duration:.3f}s)")
    return results

def benchmark_clipboard_manager():
    print("\n--- 3. BENCHMARKING LOCAL CLIPBOARD MANAGER (10 SLOTS) ---")
    from ratt.config import AppConfig, UserTier
    cfg = AppConfig()
    cfg.user.tier = UserTier.PREMIUM
    cfg.user.premium_slots = 50
    cfg.enable_vault = False # isolate slot memory/DPAPI engine
    cm = ClipboardManager(cfg)
    
    # Measure slot write/read ops/sec with CryptProtectMemory DPAPI
    num_ops = 500
    start = time.perf_counter()
    for i in range(num_ops):
        slot = (i % 10) + 1
        cm.copy_to_slot(slot, text=f"Content snippet {i} with metadata payload")
        val = cm.get_slot_text(slot)
    duration = time.perf_counter() - start
    ops_per_sec = (num_ops * 2) / duration
    print(f"Local Slot Read/Write Ops/Sec (with Windows DPAPI CryptProtectMemory): {ops_per_sec:.2f} ops/sec (Latency: {(duration/(num_ops*2))*1e3:.2f} ms/op)")
    
    # Measure with Vault enabled (SQLite commit + AES encryption)
    cfg.enable_vault = True
    cm_vault = ClipboardManager(cfg)
    vault_ops = 50
    start = time.perf_counter()
    for i in range(vault_ops):
        slot = (i % 10) + 1
        cm_vault.copy_to_slot(slot, text=f"Vault recorded snippet {i}")
    vault_duration = time.perf_counter() - start
    vault_ops_per_sec = vault_ops / vault_duration
    print(f"Slot Copy with Encrypted SQLite Vault Persistence: {vault_ops_per_sec:.2f} ops/sec (Latency: {(vault_duration/vault_ops)*1e3:.2f} ms/op)")

    return {
        "dpapi_slot_ops_per_sec": ops_per_sec,
        "vault_persistence_ops_per_sec": vault_ops_per_sec
    }

def benchmark_relay_mailbox():
    print("\n--- 4. BENCHMARKING EPHEMERAL RELAY MAILBOX CONCURRENCY & MEMORY ---")
    mailbox = EphemeralRelayMailbox()
    initial_mem = get_process_memory()
    
    num_items = 50000
    dummy_envelope = EncryptedEnvelope(
        version=1,
        mailbox_id="MB-TEST",
        nonce_b64="AAAAAAAAAAAAAAAAAAAAAA==",
        ciphertext_b64="VGVzdENpcGhlcnRleHRGYWtlUGF5bG9hZFBhZGRpbmdFeGFtcGxlMTIzNDU2Nzg5MA==",
        counter=1,
        timestamp=time.time()
    )
    
    # Concurrent write benchmark
    workers = 32
    def poster(start_idx, count):
        for i in range(start_idx, start_idx + count):
            dummy_envelope.mailbox_id = f"MB-{i:07d}"
            mailbox.post_envelope(dummy_envelope.to_json())
            
    chunk = num_items // workers
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(poster, w * chunk, chunk) for w in range(workers)]
        for f in futures:
            f.result()
    post_time = time.perf_counter() - start
    post_ops_sec = num_items / post_time
    print(f"Concurrent Mailbox Posts (32 threads): {post_ops_sec:.2f} posts/sec (Latency: {(post_time/num_items)*1e6:.2f} µs/post)")
    
    # Check RAM with 50k envelopes
    active_mem = get_process_memory()
    mem_delta_mb = (active_mem - initial_mem) / (1024 * 1024)
    bytes_per_item = (active_mem - initial_mem) / num_items if num_items > 0 else 0
    print(f"Memory for {num_items} active envelopes: {mem_delta_mb:.2f} MB (~{bytes_per_item:.1f} bytes/envelope in RAM)")
    
    # Concurrent retrieve & burn-on-read benchmark
    def getter(start_idx, count):
        for i in range(start_idx, start_idx + count):
            _ = mailbox.fetch_envelope(f"MB-{i:07d}")
            
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(getter, w * chunk, chunk) for w in range(workers)]
        for f in futures:
            f.result()
    get_time = time.perf_counter() - start
    get_ops_sec = num_items / get_time
    print(f"Concurrent Mailbox Burn-on-Read (32 threads): {get_ops_sec:.2f} retrieves/sec (Latency: {(get_time/num_items)*1e6:.2f} µs/retrieve)")
    print(f"Remaining active envelopes after Burn-on-Read: {len(mailbox._mailboxes)}")
    
    return {
        "post_ops_sec": post_ops_sec,
        "get_ops_sec": get_ops_sec,
        "bytes_per_envelope": bytes_per_item,
        "mem_delta_mb": mem_delta_mb,
        "items": num_items
    }

if __name__ == "__main__":
    kdf_res = benchmark_kdf()
    aes_res = benchmark_aes_gcm()
    cm_res = benchmark_clipboard_manager()
    relay_res = benchmark_relay_mailbox()
    
    out = {
        "kdf": kdf_res,
        "aes": {str(k): v for k, v in aes_res.items()},
        "clipboard": cm_res,
        "relay": relay_res
    }
    with open("benchmark_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nBenchmark completed and written to benchmark_results.json")
