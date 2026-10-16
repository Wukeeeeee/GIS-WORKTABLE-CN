"""Verify detection, backup, and reconstruction of copied/broken .venv."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    print("=== Testing Copied / Broken .venv Detection & Recovery ===")
    venv_dir = ROOT / ".venv"
    backup_venv = ROOT / ".venv_temp_save"
    bootstrap_dir = ROOT / ".bootstrap"

    # Step 1: Temporarily stash the current working venv
    if venv_dir.exists():
        if backup_venv.exists():
            shutil.rmtree(backup_venv)
        print("  Stashing current working .venv to .venv_temp_save...")
        shutil.move(venv_dir, backup_venv)

    try:
        # Step 2: Create a simulated broken .venv copied from another machine
        print("  Simulating an invalid .venv copied from another user's machine...")
        venv_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir = venv_dir / "Scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        pyvenv_cfg = venv_dir / "pyvenv.cfg"
        pyvenv_cfg.write_text("home = C:\\NonExistentUser\\Python313\nversion = 3.13.0\n")
        # Dummy python.exe that fails
        dummy_exe = scripts_dir / "python.exe"
        dummy_exe.write_text("corrupted binary dummy")

        # Step 3: Run bootstrap_windows.ps1
        print("  Running bootstrap_windows.ps1 to verify auto-detection and recovery...")
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\\bootstrap_windows.ps1"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"  Bootstrap exited with code: {res.returncode}")
        print("  Bootstrap stdout:")
        for line in res.stdout.splitlines():
            if any(k in line for k in ("WARN", "BACKUP", "READY", "Rebuilding", "1/3", "2/3", "3/3")):
                print(f"    {line}")

        # Step 4: Verify recovery assertions
        assert res.returncode == 0, f"Bootstrap should succeed in recovering .venv, stderr: {res.stderr}"
        assert (venv_dir / "Scripts" / "python.exe").exists(), "A fresh .venv/Scripts/python.exe must be created"

        # Check that backup was created in .bootstrap/old-venv-*
        old_venvs = list(bootstrap_dir.glob("old-venv-*"))
        assert len(old_venvs) > 0, "Broken venv should be backed up to .bootstrap/old-venv-*"
        print(f"  [PASS] Successfully backed up broken venv to: {old_venvs[-1].name}")

        # Check runtime check passes on rebuilt venv
        checker = ROOT / "scripts" / "check_runtime.py"
        py_path = venv_dir / "Scripts" / "python.exe"
        chk_res = subprocess.run([str(py_path), str(checker)], cwd=str(ROOT))
        assert chk_res.returncode == 0, "Rebuilt venv must pass check_runtime.py"
        print("  [PASS] Rebuilt .venv passed full runtime dependency verification.")

        print("\nCopied / broken .venv auto-detection, backup, and rebuild passed completely!")
        return 0

    finally:
        # Step 5: Clean up old-venvs from test, and restore original working venv if needed
        for p in bootstrap_dir.glob("old-venv-*"):
            try:
                shutil.rmtree(p)
            except Exception:
                pass
        if backup_venv.exists():
            if venv_dir.exists():
                shutil.rmtree(venv_dir)
            print("  Restoring original working .venv...")
            shutil.move(backup_venv, venv_dir)

if __name__ == "__main__":
    sys.exit(main())
