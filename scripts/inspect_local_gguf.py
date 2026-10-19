"""Create static GGUF/llama.cpp identity evidence without loading model weights."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from colluscope.gguf_metadata import read_gguf, summarize_gguf  # noqa: E402
from colluscope.gguf_tokenizer import GGUFChatTokenCounter  # noqa: E402
from colluscope.openai_compat_llamacpp import llama_runtime_bundle_identity  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    return {"command": command, "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def inspect(config_path: Path, output_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = tomllib.loads(config_bytes.decode("utf-8"))
    checkpoint, server, tokenizer = config["checkpoint"], config["server"], config["tokenizer"]
    model_path, binary_path = Path(checkpoint["path"]), Path(server["binary_path"])
    if model_path.stat().st_size != checkpoint["file_size_bytes"]:
        raise ValueError("local GGUF size differs from the frozen candidate")
    model_digest = sha256_file(model_path)
    if model_digest != checkpoint["file_sha256"]:
        raise ValueError("local GGUF SHA256 differs from the frozen candidate")
    document = read_gguf(model_path)
    counter = GGUFChatTokenCounter(model_path, expected_artifact_sha256=model_digest)
    expected_tokenizer = {
        "tokenizer_sha256": tokenizer["tokenizer_sha256"],
        "chat_template_sha256": tokenizer["chat_template_sha256"],
        "tokenizers_library_version": tokenizer["tokenizers_library_version"],
        "jinja2_library_version": tokenizer["jinja2_library_version"],
    }
    actual_tokenizer = {
        "tokenizer_sha256": counter.tokenizer_sha256,
        "chat_template_sha256": counter.chat_template_sha256,
        "tokenizers_library_version": counter.tokenizers_library_version,
        "jinja2_library_version": counter.jinja2_library_version,
    }
    if actual_tokenizer != expected_tokenizer:
        raise ValueError(f"embedded GGUF tokenizer identity changed: {actual_tokenizer}")
    binary_digest = sha256_file(binary_path)
    if binary_digest != server["binary_sha256"]:
        raise ValueError("llama-server launcher SHA256 differs from the frozen candidate")
    bundle = llama_runtime_bundle_identity(binary_path)
    if bundle["sha256"] != server["runtime_bundle_sha256"]:
        raise ValueError("llama.cpp runtime file bundle differs from the frozen candidate")
    version_probe = probe([str(binary_path), "--version"])
    device_probe = probe([str(binary_path), "--list-devices"])
    version_text = str(version_probe["stdout"]) + str(version_probe["stderr"])
    if version_probe["exit_code"] != 0 or server["commit"] not in version_text:
        raise ValueError("llama-server static version probe differs from the frozen build")
    if device_probe["exit_code"] != 0 or config["launch"]["gpu_device"] not in str(device_probe["stdout"]):
        raise ValueError("llama-server static device probe lacks the frozen GPU target")

    prompt_root = ROOT / "prompts" / "m1-p0-v2"
    prompt_hashes = {path.name: sha256_file(path) for path in sorted(prompt_root.iterdir()) if path.is_file()}
    messages = [{"role": "system", "content": "Offline compatibility identity check."},
                {"role": "user", "content": "Return no action; do not infer."}]
    summary = {
        "repository": {
            "branch": subprocess.run(["git", "-C", str(ROOT), "branch", "--show-current"],
                                     capture_output=True, text=True, check=True).stdout.strip(),
            "commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                      capture_output=True, text=True, check=True).stdout.strip(),
        },
        "python": {"version": sys.version, "implementation": platform.python_implementation(),
                   "platform": platform.platform()},
        "libraries": {"tokenizers": counter.tokenizers_library_version,
                      "jinja2": counter.jinja2_library_version},
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "prompt_file_sha256": prompt_hashes,
        "checkpoint": {**summarize_gguf(document), "sha256": model_digest,
                       "static_tokenizer": {
                           "tokenizer_id": counter.tokenizer_id,
                           **actual_tokenizer,
                           "tokenizer_revision": counter.tokenizer_revision,
                           "sample_rendered_prompt_sha256": hashlib.sha256(
                               counter.render_chat(messages, enable_thinking=False).encode("utf-8")).hexdigest(),
                           "sample_token_count": counter.count_chat_tokens(messages),
                       }},
        "server": {"binary_path": str(binary_path), "binary_size_bytes": binary_path.stat().st_size,
                   "binary_sha256": binary_digest, "runtime_bundle": bundle,
                   "version_probe": version_probe, "device_probe": device_probe},
        "execution_boundary": {"server_started": False, "model_weights_loaded": False,
                               "generation_calls": 0, "network_requests": 0, "paid_api_calls": 0},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "m1-p0-llama-local-draft.toml")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.config, args.out), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
