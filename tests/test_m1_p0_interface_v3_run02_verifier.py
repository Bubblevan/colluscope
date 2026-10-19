from __future__ import annotations

import hashlib
import json

import pytest

from scripts.verify_m1_p0_interface_v3_run02 import _verify_manifest


def _write_manifest(directory, files):
    inventory = {
        path.name: {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_bytes": path.stat().st_size,
        }
        for path in files
    }
    (directory / "manifest.json").write_text(
        json.dumps({"files": inventory}, sort_keys=True), encoding="utf-8")


def test_run02_verifier_accepts_exact_manifested_files(tmp_path):
    artifact = tmp_path / "evidence.txt"
    artifact.write_text("frozen evidence\n", encoding="utf-8")
    _write_manifest(tmp_path, [artifact])

    assert _verify_manifest(tmp_path)["files"]["evidence.txt"]["size_bytes"] == artifact.stat().st_size


def test_run02_verifier_rejects_tampered_manifested_response(tmp_path):
    response = tmp_path / "raw-response.json"
    response.write_text('{"type":"no_message"}\n', encoding="utf-8")
    _write_manifest(tmp_path, [response])
    response.write_text('{"type":"send_message","text":"changed"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="manifest file hash/size mismatch"):
        _verify_manifest(tmp_path)


def test_run02_verifier_rejects_undeclared_extra_artifact(tmp_path):
    response = tmp_path / "raw-response.json"
    response.write_text('{"type":"no_message"}\n', encoding="utf-8")
    _write_manifest(tmp_path, [response])
    (tmp_path / "unmanifested.log").write_text("extra\n", encoding="utf-8")

    with pytest.raises(ValueError, match="manifest inventory differs"):
        _verify_manifest(tmp_path)
