"""Ephemeral local llama.cpp API key handling for bounded research runs."""

from __future__ import annotations

import csv
import hashlib
import os
import secrets
import subprocess
from pathlib import Path
from typing import Any


def verify_private_directory_acl(path: Path) -> dict[str, Any]:
    """Read-only verification that every existing run-tree object is current-user-only."""
    if os.name != "nt":
        raise RuntimeError("private M3 run-directory ACL verification is supported only on Windows")
    path = path.resolve()
    if not path.is_dir():
        raise ValueError("private run ACL target must be an existing directory")
    identity = subprocess.run(["whoami.exe", "/user", "/fo", "csv", "/nh"],
                              capture_output=True, text=True, timeout=10, check=True)
    rows = list(csv.reader(identity.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) < 2 or not rows[0][1].startswith("S-"):
        raise PermissionError("whoami did not return one valid current-user SID")
    account, sid = rows[0][0], rows[0][1]
    objects = [path] + [item for item in path.rglob("*") if not item.is_symlink()]
    digest = hashlib.sha256()
    for item in sorted(objects, key=lambda value: value.as_posix().casefold()):
        audit = subprocess.run(["icacls.exe", str(item)], capture_output=True, text=True,
                               timeout=10, check=True)
        ace_lines = [line.strip() for line in audit.stdout.splitlines() if ":(" in line]
        if not ace_lines:
            raise PermissionError("M3 run artifact has no verifiable access-control entry")
        principals = [line.rsplit(":", 1)[0].split()[-1].replace(" ", "").casefold()
                      for line in ace_lines]
        expected = account.replace(" ", "").casefold()
        if any(principal != expected for principal in principals):
            raise PermissionError("M3 run artifact ACL grants access to an identity other than the current user")
        if not all("(f)" in line.rsplit(":", 1)[-1].replace(" ", "").casefold()
                   for line in ace_lines):
            raise PermissionError("M3 run artifact ACL does not grant current-user full control")
        digest.update(audit.stdout.encode("utf-8"))
        digest.update(b"\0")
    return {"path": str(path), "current_user_sid": sid,
            "acl_policy": "only current-user explicit full-control ACEs; directories inherit to children",
            "verified_object_count": len(objects), "acl_output_sha256": digest.hexdigest(),
            "verified": True}


def restrict_private_directory_acl(path: Path) -> dict[str, Any]:
    """Restrict an existing private run tree to the current Windows user and verify every object."""
    if os.name != "nt":
        raise RuntimeError("private M3 run-directory ACL setup is supported only on Windows")
    path = path.resolve()
    if not path.is_dir():
        raise ValueError("private run ACL target must be an existing directory")
    identity = subprocess.run(["whoami.exe", "/user", "/fo", "csv", "/nh"],
                              capture_output=True, text=True, timeout=10, check=True)
    rows = list(csv.reader(identity.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) < 2 or not rows[0][1].startswith("S-"):
        raise PermissionError("whoami did not return one valid current-user SID")
    sid = rows[0][1]
    direct = subprocess.run(["icacls.exe", str(path), "/T", "/C", "/inheritance:r", "/grant:r",
                             f"*{sid}:(F)"], capture_output=True, text=True, timeout=30, check=False)
    if direct.returncode != 0:
        raise PermissionError("could not restrict all existing M3 run artifacts to the current user")
    directories = [path] + [item for item in path.rglob("*") if item.is_dir() and not item.is_symlink()]
    for directory in directories:
        inherited = subprocess.run(["icacls.exe", str(directory), "/inheritance:r", "/grant:r",
                                    f"*{sid}:(OI)(CI)F"], capture_output=True, text=True,
                                   timeout=10, check=False)
        if inherited.returncode != 0:
            raise PermissionError("could not set current-user-only M3 run-directory ACL inheritance")
    return verify_private_directory_acl(path)


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
