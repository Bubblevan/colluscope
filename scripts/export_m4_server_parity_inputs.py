#!/usr/bin/env python3
"""Export offline Mock prompts and local GGUF token IDs for a server parity audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.gguf_tokenizer import GGUFChatTokenCounter  # noqa: E402
from colluscope.openai_compat_llamacpp import llama_runtime_bundle_identity  # noqa: E402
from scripts.audit_m4_v2_token_matching import _focal_receiver, _requests  # noqa: E402
from scripts.run_m4_offline import load_documents  # noqa: E402


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def export(mock_run: Path, output: Path) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite token parity inputs: {output}")
    config, _scenarios, splits, _positive = load_documents(ROOT / "configs/m4-runtime-v2.json")
    counter = GGUFChatTokenCounter(Path(config["model"]["path"]),
                                   expected_artifact_sha256=config["model"]["sha256"])
    server_path = Path(config["runtime"]["binary_path"])
    server_sha = _file_sha(server_path)
    runtime_bundle = llama_runtime_bundle_identity(server_path)
    if server_sha != config["runtime"]["binary_sha256"]:
        raise ValueError("frozen llama-server binary SHA256 mismatch")
    if runtime_bundle["sha256"] != config["runtime"]["bundle_sha256"]:
        raise ValueError("frozen llama.cpp runtime bundle SHA256 mismatch")
    request_records = _requests(mock_run)
    selected_inputs = []
    for group in splits["groups"]:
        group_id = group["split_group_id"]
        receiver = _focal_receiver(mock_run, group_id)
        request_ids = (
            f"{group_id}-baseline-ballot-{receiver}",
            f"{group_id}-focal-retained_history_neutral",
            f"{group_id}-positive-information",
            f"{group_id}-positive-neutral",
        )
        for request_id in request_ids:
            record = request_records[request_id]
            selected_inputs.append((request_id, record["model_input"]["messages"], record["action_kind"]))
    prompt_rows = []
    for request_id, messages, action_kind in selected_inputs:
        local_prompt = counter.render_chat(messages, enable_thinking=False)
        token_ids = counter.encode_chat(messages, enable_thinking=False)
        prompt_rows.append({
            "request_id": request_id, "action_kind": action_kind,
            "messages": messages, "local_rendered_prompt": local_prompt,
            "local_token_count": len(token_ids), "local_token_ids": token_ids,
            "local_prompt_sha256": _sha(local_prompt.encode("utf-8")),
            "local_token_ids_sha256": _sha(",".join(map(str, token_ids)).encode("ascii")),
        })
    if len(prompt_rows) != 96:
        raise ValueError(f"expected 96 M4 focal/positive-control prompt rows; got {len(prompt_rows)}")
    result = {
        "schema_version": "m4-token-parity-inputs-v1",
        "claim_scope": "offline Mock prompts only; no model generations or network requests",
        "real_model_generations": 0, "network_requests": 0,
        "model_sha256": counter.artifact_sha256,
        "server_binary_sha256": server_sha,
        "runtime_bundle_sha256": runtime_bundle["sha256"],
        "runtime_config_sha256": _sha((ROOT / "configs/m4-runtime-v2.json").read_bytes()),
        "prompt_file_sha256": {
            path.relative_to(ROOT).as_posix(): _sha(path.read_bytes())
            for path in (
                ROOT / "prompts/m4-v1/system.txt",
                ROOT / "prompts/m4-v1/ballot.txt",
                ROOT / "prompts/m4-v1/positive_control.txt",
                ROOT / "prompts/m4-v1/ballot.schema.json",
                ROOT / "prompts/m4-v1/positive_control.schema.json",
            )
        },
        "tokenizer_sha256": counter.tokenizer_sha256,
        "chat_template_sha256": counter.chat_template_sha256,
        "tokenizers_version": counter.tokenizers_library_version,
        "jinja2_version": counter.jinja2_library_version,
        "split_manifest_sha256": _sha((ROOT / config["schedule"]["split_manifest"]).read_bytes()),
        "assigned_groups": len(splits["groups"]), "prompt_count": len(prompt_rows),
        "prompts": prompt_rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mock-run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = export(args.mock_run, args.out)
    print(json.dumps({key: result[key] for key in (
        "prompt_count", "assigned_groups", "model_sha256", "tokenizer_sha256",
        "chat_template_sha256", "real_model_generations", "network_requests",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
