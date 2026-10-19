"""Ephemeral local llama.cpp API key handling for bounded research runs."""

from __future__ import annotations

import csv
import hashlib
import os
import secrets
import subprocess
from pathlib import Path
from typing import Any


def create_api_key_file(run_dir: Path) -> tuple[str, Path, dict[str, Any]]:
    """Create a per-run API key and restrict its NTFS ACL to the current user."""
    if os.name != "nt":
        raise RuntimeError("local llama.cpp key-file ACL setup is supported only on Windows")
    key = secrets.token_urlsafe(32)
    key_path = run_dir / "private" / "llama-api-key.txt"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        key_path.open("x", encoding="ascii").close()
        identity = subprocess.run(["whoami.exe", "/user", "/fo", "csv", "/nh"],
                                  capture_output=True, text=True, timeout=10, check=True)
        rows = list(csv.reader(identity.stdout.splitlines()))
        if len(rows) != 1 or len(rows[0]) < 2 or not rows[0][1].startswith("S-"):
            raise RuntimeError("whoami did not return one valid current-user SID")
        identity_name, sid = rows[0][0], rows[0][1]
        acl = subprocess.run(["icacls.exe", str(key_path), "/inheritance:r", "/grant:r",
                              f"*{sid}:(F)"], capture_output=True, text=True,
                             timeout=10, check=False)
        if acl.returncode != 0:
            raise RuntimeError(f"icacls failed to restrict the API key file: {acl.stderr.strip()}")
        audit = subprocess.run(["icacls.exe", str(key_path)], capture_output=True,
                               text=True, timeout=10, check=True)
        acl_compact = audit.stdout.replace(" ", "").replace("\t", "").casefold()
        expected_acl = f"{identity_name}:(F)".replace(" ", "").casefold()
        if expected_acl not in acl_compact:
            raise RuntimeError("API key file ACL does not attest full access for the current-user SID")
        key_path.write_text(key + "\n", encoding="ascii", newline="\n")
        return key, key_path, {
            "path": str(key_path.resolve()),
            "sha256": hashlib.sha256(key.encode("ascii")).hexdigest(),
            "current_user_sid": sid,
            "current_user_name": identity_name,
            "acl_restriction": "inheritance removed; current user SID granted full control",
            "acl_command_exit_code": acl.returncode,
            "acl_assignment_verified": True,
            "secret_content_recorded": False,
        }
    except Exception:
        key_path.unlink(missing_ok=True)
        raise


def remove_api_key_file(path: Path) -> dict[str, Any]:
    """Remove the ephemeral key after the server has stopped."""
    try:
        path.unlink(missing_ok=True)
        return {"status": "REMOVED", "path": str(path.resolve()), "exists_after_cleanup": path.exists()}
    except OSError as exc:
        return {"status": "CLEANUP_FAILED", "path": str(path.resolve()),
                "exists_after_cleanup": path.exists(), "error_type": type(exc).__name__,
                "error": str(exc)}
