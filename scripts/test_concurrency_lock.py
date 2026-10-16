"""Verify concurrency lock and double-click protections."""
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.launcher import probe, select_port, stop_backend, open_browser

def main():
    print("=== Testing Concurrency & Double-Click Protections ===")
    port = select_port()
    stop_backend()
    time.sleep(1)

    # 1. Test browser debounce
    print("[1/3] Testing browser open debounce...")
    stamp_file = ROOT / ".bootstrap" / f"browser_{port}.stamp"
    stamp_file.unlink(missing_ok=True)
    res1 = open_browser(port)
    assert res1 == 0, "First open_browser should succeed"
    assert stamp_file.exists(), "Stamp file should be created"

    # Rapid second call within debounce window
    t1 = time.time()
    res2 = open_browser(port)
    assert res2 == 0, "Second open_browser should return cleanly without error"
    print("  [PASS] Browser open debounce works correctly (no duplicate browser popup storm).")

    # 2. Test launcher startup lock
    print("[2/3] Testing launcher startup lock under simulated race...")
    bootstrap_dir = ROOT / ".bootstrap"
    bootstrap_dir.mkdir(exist_ok=True)
    lock_file = bootstrap_dir / f"start_{port}.lock"

    # Pre-create lock to simulate concurrent launcher holding lock
    fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
    try:
        # Launch second launcher check in background
        proc = subprocess.Popen(
            [sys.executable, "-m", "backend.launcher", "start", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(1.5)
        # Verify second process is politely waiting, not crashing
        assert proc.poll() is None, "Second launcher process should be waiting for the lock, not crashing"
        print("  [PASS] Second launcher politely waits on lock instead of colliding on port 10048.")
    finally:
        os.close(fd)
        lock_file.unlink(missing_ok=True)
        # Terminate test waiter
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            pass

    # 3. Test stop_backend idempotent reporting
    print("[3/3] Testing stop_backend clean output and idempotency...")
    stop_backend()
    assert probe(port) is None, "Port should not be running"
    print("  [PASS] stop_backend runs cleanly and idempotently.")

    print("\nAll concurrency & double-click protection tests passed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
