"""Independently revalidate the local M1-P0 Interface V3 Run 02 package.

This verifier is read-only with respect to the run directory and never opens a
network connection. Its summary is written outside the immutable raw run tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "src"))

from colluscope.gguf_tokenizer import GGUFChatTokenCounter  # noqa: E402
from colluscope.m1_runtime import _parse_action  # noqa: E402
from colluscope.openai_compat_llamacpp import (  # noqa: E402
    llama_runtime_bundle_identity,
    load_llamacpp_backend_config,
)
from scripts.run_m1_p0_local_preflight import (  # noqa: E402
    APPROVAL_ID,
    EXPECTED_BUNDLE_SHA256,
    EXPECTED_MODEL_SHA256,
    EXPECTED_SERVER_SHA256,
    _listener_rows,
    _sha256_file,
)


EXPECTED_CONFIG_SHA256 = "db7a793bb2cd9b93215bc367fa1de635f24e85f68b0e2a882449af68103d3a9e"
EXPECTED_COMMIT = "2f495ffd4aa7e7b4982587e00818b2d282da8b4c"
EXPECTED_REQUEST_IDS = [
    "preflight-props",
    "preflight-template",
    "preflight-tokenize",
    "preflight-completion-1",
    "preflight-completion-2",
    "preflight-completion-3",
]
EXPECTED_URL_PATHS = [
    "/props",
    "/apply-template",
    "/tokenize",
    "/v1/chat/completions",
    "/v1/chat/completions",
    "/v1/chat/completions",
]


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _verify_manifest(run_dir: Path) -> dict[str, Any]:
    manifest = _read_json(run_dir / "manifest.json")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("manifest has no file inventory")
    declared = set(files)
    actual = {
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    if actual != declared:
        raise ValueError(f"manifest inventory differs; undeclared={sorted(actual - declared)}, missing={sorted(declared - actual)}")
    for relative, metadata in files.items():
        path = (run_dir / relative).resolve()
        if not path.is_relative_to(run_dir.resolve()):
            raise ValueError(f"manifest path escapes run directory: {relative}")
        if path.stat().st_size != metadata.get("size_bytes") or _sha256_file(path) != metadata.get("sha256"):
            raise ValueError(f"manifest file hash/size mismatch: {relative}")
    return manifest


def verify(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    if not run_dir.is_relative_to(ROOT / "runs" / "m1_p0_local"):
        raise ValueError("run directory must remain inside this repository's local research runs folder")
    manifest = _verify_manifest(run_dir)
    result = _read_json(run_dir / "preflight-result.json")
    terminal = _read_json(run_dir / "terminal-status.json")
    environment = _read_json(run_dir / "environment.json")
    approved_config = run_dir / "approved-config.toml"
    config_hash = _sha256_file(approved_config)
    if config_hash != EXPECTED_CONFIG_SHA256 or environment.get("config_sha256") != EXPECTED_CONFIG_SHA256:
        raise ValueError("approved config digest changed")
    if environment.get("git_head") != EXPECTED_COMMIT:
        raise ValueError("run source commit differs from the frozen preflight commit")
    if environment.get("model_sha256") != EXPECTED_MODEL_SHA256:
        raise ValueError("GGUF digest differs from the frozen model")
    if environment.get("server_sha256") != EXPECTED_SERVER_SHA256:
        raise ValueError("llama-server digest differs from the frozen launcher")
    bundle = environment.get("runtime_bundle", {})
    if bundle.get("sha256") != EXPECTED_BUNDLE_SHA256 or bundle.get("file_count") != 53:
        raise ValueError("runtime bundle identity differs from the frozen build")

    backend = load_llamacpp_backend_config(approved_config)
    if (backend.base_url != "http://127.0.0.1:8081/v1" or backend.launch.get("host") != "127.0.0.1" or
            backend.launch.get("port") != 8081 or backend.model_calls_enabled or backend.full_pilot_approval_id):
        raise ValueError("run config violates the approved local-only preflight scope")
    if (backend.preflight_max_logical_requests, backend.preflight_max_attempts,
            backend.preflight_max_completion_attempts) != (6, 12, 4):
        raise ValueError("preflight config does not enforce the approved 6/12/4 ceiling")
    command = environment.get("launch_command", [])
    if ("--offline" not in command or command[command.index("--host") + 1] != "127.0.0.1" or
            command[command.index("--port") + 1] != "8081"):
        raise ValueError("server launch command is not offline and loopback-only")
    network = environment.get("network_boundary", {})
    if (network.get("inference_endpoint") != backend.base_url or network.get("loopback_only") is not True or
            network.get("llama_cpp_offline") is not True or network.get("third_party_api_calls") is not False or
            network.get("proxy_discovery_disabled_for_client") is not True):
        raise ValueError("network-boundary attestation is incomplete")

    if result.get("approval_id") != APPROVAL_ID or result.get("protocol_id") != "m1-p0-interface-v3":
        raise ValueError("approval or protocol identity mismatch")
    if result.get("status") != "PASS_INTERFACE" or result.get("schema_transport_status") != "PASS":
        raise ValueError("interface/schema transport did not pass")
    records = result.get("records")
    if not isinstance(records, list) or [row.get("request_id") for row in records] != EXPECTED_REQUEST_IDS:
        raise ValueError("actual request sequence differs from the frozen six-request sequence")
    if result.get("reused_prior_setup_requests") != 0:
        raise ValueError("this run must use its own request/response evidence")

    props = json.loads(records[0]["raw_response"])
    try:
        server_settings = props["default_generation_settings"]
        server_params = server_settings["params"]
    except (KeyError, TypeError) as exc:
        raise ValueError("/props response lacks server settings") from exc
    if (str(Path(props.get("model_path", "")).resolve()).casefold() !=
            str(Path(backend.artifact_path).resolve()).casefold() or
            backend.server_commit not in props.get("build_info", "") or
            props.get("model_alias") != backend.model_id or
            server_settings.get("n_ctx") != backend.context_length or props.get("total_slots") != 1):
        raise ValueError("/props model, build, context, alias, or slot identity mismatch")
    if hashlib.sha256(props.get("chat_template", "").encode("utf-8")).hexdigest() != backend.chat_template_sha256:
        raise ValueError("server-loaded chat template differs from the frozen tokenizer template")
    for key, expected in (("temperature", backend.temperature), ("top_p", backend.top_p),
                          ("top_k", backend.top_k), ("min_p", backend.min_p)):
        if server_params.get(key) != expected:
            raise ValueError(f"/props sampling mismatch for {key}")
    if server_params.get("samplers") != list(backend.sampler_chain):
        raise ValueError("/props sampler chain differs from the frozen config")

    url_paths: list[str] = []
    for row, expected_path in zip(records, EXPECTED_URL_PATHS, strict=True):
        parsed = urlsplit(row.get("url", ""))
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port != 8081:
            raise ValueError(f"non-loopback request found: {row.get('request_id')}")
        url_paths.append(parsed.path)
        if parsed.path != expected_path or row.get("status") != "response_returned" or row.get("attempt") != 1:
            raise ValueError(f"request failed, retried, or changed order: {row.get('request_id')}")
        raw = row.get("raw_response")
        if not isinstance(raw, str) or hashlib.sha256(raw.encode("utf-8")).hexdigest() != row.get("raw_response_sha256"):
            raise ValueError(f"raw response hash mismatch: {row.get('request_id')}")
        request_body = row.get("request_body")
        if request_body is not None:
            if not isinstance(request_body, str) or hashlib.sha256(request_body.encode("utf-8")).hexdigest() != row.get("request_sha256"):
                raise ValueError(f"raw request hash mismatch: {row.get('request_id')}")
    if "/health" in url_paths:
        raise ValueError("unbudgeted health request found outside the frozen sequence")

    budget = result.get("budget_state", {})
    if (budget.get("logical_requests"), budget.get("http_attempts"), budget.get("completion_attempts")) != (6, 6, 3):
        raise ValueError("observed request usage differs from the recorded 6/6/3 totals")
    if result.get("logical_requests") != 6 or result.get("http_attempts") != 6 or result.get("model_completion_attempts") != 3:
        raise ValueError("top-level usage totals disagree")
    if (terminal.get("status") != "PASS_INTERFACE" or terminal.get("logical_preflight_http_requests") != 6 or
            terminal.get("local_completion_attempts") != 3 or terminal.get("external_model_calls") != 0 or
            terminal.get("full_pilot_authorized") is not False or terminal.get("m2_authorized") is not False):
        raise ValueError("terminal status or authorization boundary mismatch")
    if manifest.get("research_episodes") != 0 or manifest.get("paid_api_calls") != 0:
        raise ValueError("manifest reports a research episode or paid API call")

    inputs = _read_json(run_dir / "preflight-inputs.json")
    if inputs.get("requested_actions") != ["ballot", "send_message", "no_message"]:
        raise ValueError("probe action instruction sequence changed")
    prompt_rows = inputs.get("prompts", [])
    if len(prompt_rows) != 3:
        raise ValueError("exact prompt observations are missing")
    prompt_by_id = {row.get("request_id"): row for row in prompt_rows}
    for prompt_row in prompt_rows:
        if hashlib.sha256(prompt_row["prompt"].encode("utf-8")).hexdigest() != prompt_row.get("prompt_sha256"):
            raise ValueError(f"frozen prompt hash mismatch: {prompt_row.get('request_id')}")
        if hashlib.sha256(prompt_row["observation_canonical_json"].encode("utf-8")).hexdigest() != prompt_row.get("observation_sha256"):
            raise ValueError(f"agent observation hash mismatch: {prompt_row.get('request_id')}")
        if json.loads(prompt_row["observation_canonical_json"]) != prompt_row.get("observation"):
            raise ValueError(f"canonical agent observation mismatch: {prompt_row.get('request_id')}")
        forbidden_keys = {"condition_id", "seed_block_id", "oracle", "oracle_label",
                          "hidden_label", "treatment_label", "private_reward_rule"}
        stack = [prompt_row["observation"]]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                if forbidden_keys.intersection(value):
                    raise ValueError(f"hidden research metadata in agent observation: {prompt_row.get('request_id')}")
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
        if prompt_row["observation_canonical_json"] not in prompt_row["prompt"]:
            raise ValueError(f"prompt does not contain its hashed observation: {prompt_row.get('request_id')}")
    template_record = records[1]
    tokenize_record = records[2]
    template_request = json.loads(template_record["request_body"])
    tokenize_request = json.loads(tokenize_record["request_body"])
    rendered_by_server = json.loads(template_record["raw_response"])["prompt"]
    token_ids_by_server = json.loads(tokenize_record["raw_response"])["tokens"]
    messages = template_request["messages"]
    local_tokenizer = GGUFChatTokenCounter(
        Path(backend.artifact_path), expected_artifact_sha256=EXPECTED_MODEL_SHA256)
    rendered_locally = local_tokenizer.render_chat(
        messages, enable_thinking=template_request["chat_template_kwargs"]["enable_thinking"])
    local_token_ids = local_tokenizer.encode_chat(
        messages, enable_thinking=template_request["chat_template_kwargs"]["enable_thinking"])
    if rendered_by_server != rendered_locally or tokenize_request.get("content") != rendered_by_server:
        raise ValueError("server and local chat template output differ")
    if token_ids_by_server != local_token_ids or len(token_ids_by_server) != 447:
        raise ValueError("server and local tokenizer IDs differ")
    if result.get("verified_tokenizer_ids") != len(token_ids_by_server):
        raise ValueError("tokenizer parity count differs from the run result")
    if local_tokenizer.tokenizer_sha256 != backend.tokenizer_sha256 or local_tokenizer.chat_template_sha256 != backend.chat_template_sha256:
        raise ValueError("GGUF tokenizer/template hash differs from approved config")

    prompt_types: list[str] = []
    schema_root = ROOT / "prompts" / "m1-p0-v2"
    for index, (row, action_kind) in enumerate(zip(records[3:], ("ballot", "message", "message"), strict=True)):
        response = json.loads(row["raw_response"])
        if len(response.get("choices", [])) != 1:
            raise ValueError(f"completion did not return exactly one choice: {row['request_id']}")
        choice = response["choices"][0]
        if choice.get("finish_reason") == "length":
            raise ValueError(f"completion was truncated: {row['request_id']}")
        content = choice.get("message", {}).get("content")
        action = _parse_action(content, action_kind)
        prompt_types.append(action["type"])
        if row.get("completion_attempt") is not True:
            raise ValueError(f"completion not counted against completion budget: {row['request_id']}")
        request = json.loads(row["request_body"])
        prompt_row = prompt_rows[index]
        if prompt_by_id.get(prompt_row.get("request_id")) is not prompt_row:
            raise ValueError(f"prompt row order is inconsistent: {row['request_id']}")
        prompt_text = prompt_row["prompt"]
        if prompt_text.count("\n\n") < 1:
            raise ValueError(f"frozen prompt lacks the system/user boundary: {row['request_id']}")
        system_text, user_text = prompt_text.split("\n\n", 1)
        if request.get("messages") != [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text}]:
            raise ValueError(f"wire prompt differs from frozen prompt evidence: {row['request_id']}")
        schema_filename = "ballot.schema.json" if action_kind == "ballot" else "communication.schema.json"
        expected_schema = json.loads((schema_root / schema_filename).read_text(encoding="utf-8"))
        if request.get("response_format") != {"type": "json_schema", "schema": expected_schema}:
            raise ValueError(f"wire schema differs from frozen schema file: {row['request_id']}")
        expected_max_tokens = backend.ballot_max_output_tokens if action_kind == "ballot" else backend.message_max_output_tokens
        expected_generation = {
            "model": backend.model_id,
            "temperature": backend.temperature,
            "top_p": backend.top_p,
            "top_k": backend.top_k,
            "min_p": backend.min_p,
            "samplers": list(backend.sampler_chain),
            "seed": prompt_row["generation_seed"],
            "max_tokens": expected_max_tokens,
            "stream": False,
            "cache_prompt": False,
            "chat_template_kwargs": {"enable_thinking": False},
            "reasoning_format": "none",
        }
        if any(request.get(key) != expected for key, expected in expected_generation.items()):
            raise ValueError(f"wire sampling/seed/output metadata differs from the frozen config: {row['request_id']}")
        if prompt_row.get("requested_action") != inputs["requested_actions"][index]:
            raise ValueError(f"requested-action metadata differs from the prompt: {row['request_id']}")
    if prompt_types != result.get("verified_actions"):
        raise ValueError("independent action parsing differs from the runner result")

    diagnostics = result.get("action_choice_diagnostics", [])
    if len(diagnostics) != 3:
        raise ValueError("instruction-compliance diagnostics missing")
    for diagnostic, actual in zip(diagnostics, prompt_types, strict=True):
        if (diagnostic.get("actual_action") != actual or
                diagnostic.get("followed_instruction") is not (diagnostic.get("requested_action") == actual) or
                diagnostic.get("role") != "descriptive_instruction_compliance_only"):
            raise ValueError("action choice diagnostic is inconsistent or misclassified")
    send_request_diagnostic = diagnostics[1]
    if (send_request_diagnostic.get("requested_action") != "send_message" or
            send_request_diagnostic.get("actual_action") not in {"send_message", "no_message"}):
        raise ValueError("the positive-message schema probe is not represented as a valid legal action")
    if result.get("positive_send_message_model_output") != (
            "OBSERVED" if send_request_diagnostic["actual_action"] == "send_message" else "UNVERIFIED"):
        raise ValueError("positive-send evidence label overstates the observed response")

    readiness = _read_json(run_dir / "server-readiness.json")
    launch = _read_json(run_dir / "launch.json")
    owner_rows = _read_jsonl(run_dir / "listener-owner-attestations.jsonl")
    if readiness.get("http_probe_sent") is not False or readiness.get("status") != "PROCESS_AND_LOOPBACK_OWNER_VERIFIED":
        raise ValueError("readiness record includes a hidden HTTP probe or lacks process attestation")
    expected_owner = [{"LocalAddress": "127.0.0.1", "LocalPort": 8081, "OwningProcess": launch.get("pid")}]
    if readiness.get("listener_rows") != expected_owner or owner_rows[0].get("listener_rows") != expected_owner:
        raise ValueError("8081 listener PID/address does not match the launched process")
    if Path(launch.get("image_path", "")).resolve() != Path(backend.server_binary_path).resolve():
        raise ValueError("launched process image differs from the frozen server")
    shutdown = _read_json(run_dir / "shutdown.json")
    if shutdown.get("pid") != launch.get("pid") or shutdown.get("terminated") is not True:
        raise ValueError("the runner did not stop its own server process")
    if _listener_rows(8081):
        raise ValueError("the run left a listener on approved port 8081")

    ledger_path = ROOT / "runs" / "m1_p0_local" / "approval-ledger" / (
        hashlib.sha256(APPROVAL_ID.encode("utf-8")).hexdigest() + ".json")
    ledger = _read_json(ledger_path)
    manifest_hash = _sha256_file(run_dir / "manifest.json")
    if (ledger.get("status") != "CONSUMED" or ledger.get("terminal_status") != "PASS_INTERFACE" or
            ledger.get("evidence_manifest_sha256") != manifest_hash):
        raise ValueError("single-use approval ledger does not match the terminal evidence manifest")

    return {
        "verification": "PASS_INTERFACE_EVIDENCE_INDEPENDENTLY_RECOMPUTED",
        "protocol_id": result["protocol_id"],
        "approval_id": APPROVAL_ID,
        "source_commit": EXPECTED_COMMIT,
        "manifest_sha256": manifest_hash,
        "request_order": EXPECTED_REQUEST_IDS,
        "url_paths": url_paths,
        "logical_requests": 6,
        "http_attempts": 6,
        "completion_attempts": 3,
        "verified_tokenizer_ids": len(token_ids_by_server),
        "actions": prompt_types,
        "action_choice_diagnostics": diagnostics,
        "positive_send_message_model_output": result["positive_send_message_model_output"],
        "research_episodes": 0,
        "external_model_calls": 0,
        "paid_api_calls": 0,
        "pilot_authorized": False,
        "m2_authorized": False,
        "local_raw_responses_and_logs": True,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"expected nonempty JSONL object rows: {path}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path,
                        default=ROOT / "runs" / "m1_p0_local" / "m1-p0-interface-v3-local-preflight-run-02")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "runs" / "m1_p0_local" / "interface-v3-run02-preflight-readiness" / "independent-verification.json")
    args = parser.parse_args()
    summary = verify(args.run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
