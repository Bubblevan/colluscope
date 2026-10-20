#!/usr/bin/env python3
"""Independently replay the local llama.cpp template/tokenizer parity receipt.

This consumes raw /apply-template and /tokenize responses only. It never calls
the server and never invokes model generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROUTES = {"/apply-template", "/tokenize"}
MAX_HTTP_ATTEMPTS = 192


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_ledger(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Require one successful, loopback-only terminal per permitted request."""
    starts: dict[str, dict[str, Any]] = {}
    terminals: dict[str, dict[str, Any]] = {}
    for row in rows:
        event = row.get("event")
        request_id = row.get("request_id")
        if not request_id:
            raise ValueError("HTTP ledger row has no request_id")
        if event == "attempt_started":
            if request_id in starts:
                raise ValueError(f"duplicate attempt_started: {request_id}")
            if row.get("method") != "POST" or row.get("route") not in ALLOWED_ROUTES:
                raise ValueError(f"non-token route or method in ledger: {request_id}")
            if row.get("url") != f"http://127.0.0.1:8081{row['route']}":
                raise ValueError(f"non-frozen endpoint in ledger: {request_id}")
            if row.get("auth_header_saved") is not False or row.get("proxy_disabled") is not True:
                raise ValueError(f"unsafe request metadata in ledger: {request_id}")
            starts[request_id] = row
        elif event == "attempt_terminal":
            if request_id in terminals:
                raise ValueError(f"duplicate attempt_terminal: {request_id}")
            if row.get("authorization_header_persisted") is not False:
                raise ValueError(f"authorization header persistence flag is not false: {request_id}")
            if row.get("http_status") != 200 or row.get("error"):
                raise ValueError(f"HTTP attempt failed: {request_id}")
            terminals[request_id] = row
        else:
            raise ValueError(f"unknown HTTP ledger event: {event}")
    if len(starts) > MAX_HTTP_ATTEMPTS:
        raise ValueError(f"HTTP attempt ceiling exceeded: {len(starts)}")
    if starts.keys() != terminals.keys():
        missing_terminal = sorted(starts.keys() - terminals.keys())
        missing_start = sorted(terminals.keys() - starts.keys())
        raise ValueError(f"unpaired HTTP events: missing_terminal={missing_terminal}, missing_start={missing_start}")
    if len(starts) != len(rows) // 2 or len(rows) % 2:
        raise ValueError("unexpected attempt-event cardinality")
    return {request_id: {"start": starts[request_id], "terminal": terminals[request_id]}
            for request_id in starts}


def validate_cleanup_metadata(
    cleanup: dict[str, Any], runner_error: dict[str, Any], expected_pid: int, expected_binary_sha256: str
) -> None:
    """Validate a post-run cleanup check when runner finalization itself failed."""
    if runner_error.get("type") != "ArgumentException" or runner_error.get("script_line") != 321:
        raise ValueError("missing runner-finalization failure record for the known reporting defect")
    if "Argument types do not match" not in runner_error.get("message", ""):
        raise ValueError("runner-finalization failure does not match the preserved raw error")
    if cleanup.get("checked_server_pid") != expected_pid or cleanup.get("checked_server_binary_sha256") != expected_binary_sha256:
        raise ValueError("post-run cleanup check does not identify the frozen server instance")
    if cleanup.get("process_still_running") is not False or cleanup.get("listener_rows") != []:
        raise ValueError("frozen llama-server process/listener is not confirmed stopped")
    if cleanup.get("temporary_api_key_exists") is not False:
        raise ValueError("temporary local API key cleanup is not confirmed")


def validate_owner_checks(rows: list[dict[str, Any]], expected_request_count: int) -> tuple[int, str]:
    """Allow failed startup polling only; every pre-request ownership check must pass."""
    if not rows:
        raise ValueError("listener ownership log is empty")
    pids = {row.get("expected_pid") for row in rows}
    binaries = {row.get("expected_executable", "").lower() for row in rows}
    if len(pids) != 1 or None in pids or len(binaries) != 1 or "" in binaries:
        raise ValueError("listener ownership log has inconsistent server identity")
    startup_rows = [row for row in rows if row.get("phase") == "startup"]
    request_rows = [row for row in rows if str(row.get("phase", "")).startswith("before:")]
    if len(request_rows) != expected_request_count:
        raise ValueError("listener ownership log does not verify every HTTP request")
    if not startup_rows or startup_rows[-1].get("exact_owner_match") is not True:
        raise ValueError("startup never recorded a successful exact-owner check")
    if any(row.get("exact_owner_match") is not True for row in request_rows):
        raise ValueError("a pre-request listener ownership check failed")
    for row in rows:
        if row not in startup_rows and row not in request_rows:
            raise ValueError(f"unknown listener ownership phase: {row.get('phase')}")
        if row.get("phase") == "startup" and row.get("exact_owner_match") is False:
            if row.get("observed_owners") != []:
                raise ValueError("failed startup poll observed an unexpected listener")
            continue
        observed = row.get("observed_owners", [])
        if len(observed) != 1 or observed[0].get("LocalAddress") != "127.0.0.1" or observed[0].get("LocalPort") != 8081 or observed[0].get("OwningProcess") != next(iter(pids)) or observed[0].get("ExecutablePath", "").lower() != next(iter(binaries)):
            raise ValueError("listener owner log does not match the exact frozen loopback process")
    return int(next(iter(pids))), next(iter(binaries))


def audit(run_dir: Path, output: Path) -> dict[str, Any]:
    expected_path = run_dir / "expected-prompts.json"
    report_path = run_dir / "parity-report.json"
    error_path = run_dir / "unhandled-error.json"
    cleanup_path = run_dir / "post-run-cleanup-check.json"
    ledger_path = run_dir / "http-ledger.jsonl"
    owners_path = run_dir / "listener-ownership.jsonl"
    expected = _json(expected_path)
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ledger = validate_ledger(rows)
    owner_rows = [json.loads(line) for line in owners_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    expected_pid, expected_binary = validate_owner_checks(owner_rows, expected_request_count=len(ledger))
    report = _json(report_path) if report_path.exists() else None
    prompts = expected.get("prompts", [])
    if len(prompts) != 96 or expected.get("prompt_count") != 96:
        raise ValueError("frozen parity input must contain exactly 96 prompt rows")
    if report is not None:
        if report.get("status") != "PASS_LLAMA_SERVER_TOKENIZER_PARITY":
            raise ValueError("server runner did not report parity PASS")
        if report.get("prompts_checked") != 96 or report.get("template_exact_matches") != 96 or report.get("token_id_exact_matches") != 96:
            raise ValueError("runner report does not claim exact equality for all prompt rows")
        if report.get("real_model_generations") != 0 or report.get("external_network_requests") != 0:
            raise ValueError("runner report indicates generation or external network use")
        if report.get("generation_routes_used") != []:
            raise ValueError("a generation route appears in the runner report")
        if report.get("http_attempts") != 192 or report.get("http_terminal_records") != 192:
            raise ValueError("runner report does not account for the exact 192 token-only HTTP attempts")
        if report.get("shutdown_cleanup_pass") is not True or report.get("listener_rows_after_shutdown") != []:
            raise ValueError("server shutdown or listener cleanup did not pass")
        if report.get("api_key_removed") is not True or report.get("api_key_content_saved") is not False:
            raise ValueError("temporary local API key cleanup/persistence check failed")
    else:
        if not error_path.exists() or not cleanup_path.exists():
            raise ValueError("runner report is absent and no preserved error/cleanup recovery evidence exists")
        validate_cleanup_metadata(_json(cleanup_path), _json(error_path), expected_pid,
                                  "3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb")
    if (run_dir / "private" / "llama-api-key.txt").exists():
        raise ValueError("temporary local API key still exists")

    runtime_config_path = ROOT / "configs/m4-runtime-v2.json"
    runtime_config = _json(runtime_config_path)
    if sha256(runtime_config_path.read_bytes()) != expected.get("runtime_config_sha256"):
        raise ValueError("runtime config changed after the prompt manifest was frozen")
    if runtime_config["model"]["sha256"] != expected["model_sha256"]:
        raise ValueError("prompt manifest model identity differs from runtime v2 config")
    if runtime_config["runtime"]["binary_sha256"] != expected["server_binary_sha256"] or runtime_config["runtime"]["bundle_sha256"] != expected["runtime_bundle_sha256"]:
        raise ValueError("prompt manifest server identity differs from runtime v2 config")
    split_path = ROOT / runtime_config["schedule"]["split_manifest"]
    if sha256(split_path.read_bytes()) != expected.get("split_manifest_sha256"):
        raise ValueError("frozen M4 split manifest changed after input export")
    for relative, digest in expected.get("prompt_file_sha256", {}).items():
        if sha256((ROOT / relative).read_bytes()) != digest:
            raise ValueError(f"frozen prompt/schema changed since export: {relative}")

    request_dir, response_dir = run_dir / "requests", run_dir / "responses"
    exact_prompts = 0
    exact_token_ids = 0
    response_hash_links = 0
    for index, item in enumerate(prompts):
        prefix = f"{index:03d}-{item['request_id']}"
        template_id, tokenize_id = f"{prefix}-apply-template", f"{prefix}-tokenize"
        for request_id in (template_id, tokenize_id):
            if request_id not in ledger:
                raise ValueError(f"missing HTTP ledger entry for {request_id}")
        template_request = _json(request_dir / f"{template_id}.json")
        token_request = _json(request_dir / f"{tokenize_id}.json")
        for request_id, request, route in (
            (template_id, template_request, "/apply-template"),
            (tokenize_id, token_request, "/tokenize"),
        ):
            if request.get("request_id") != request_id or request.get("method") != "POST" or request.get("route") != route:
                raise ValueError(f"raw request identity/method/route mismatch: {request_id}")
            if request.get("url") != f"http://127.0.0.1:8081{route}":
                raise ValueError(f"raw request endpoint mismatch: {request_id}")
            allowed_request_keys = {"request_id", "method", "route", "url", "body", "body_sha256", "authorization_header_saved"}
            if set(request) != allowed_request_keys:
                raise ValueError(f"unexpected request-envelope fields, possible credential/header persistence: {request_id}")
            body_sha = sha256(json.dumps(request["body"], ensure_ascii=True, separators=(",", ":")).encode("utf-8"))
            if body_sha != request.get("body_sha256") or body_sha != ledger[request_id]["start"].get("request_body_sha256"):
                raise ValueError(f"raw request body hash does not match its HTTP ledger: {request_id}")
        if template_request.get("authorization_header_saved") is not False or token_request.get("authorization_header_saved") is not False:
            raise ValueError("request record contains an authorization persistence violation")
        template_body = template_request.get("body", {})
        if template_body.get("messages") != item["messages"]:
            raise ValueError(f"template input differs from frozen prompt row: {item['request_id']}")
        if template_body.get("chat_template_kwargs") != {"enable_thinking": False}:
            raise ValueError(f"template settings differ from the frozen parity input: {item['request_id']}")

        template_bytes = (response_dir / f"{template_id}.bin").read_bytes()
        token_bytes = (response_dir / f"{tokenize_id}.bin").read_bytes()
        template_http, token_http = ledger[template_id], ledger[tokenize_id]
        if sha256(template_bytes) != template_http["terminal"].get("response_body_sha256"):
            raise ValueError(f"raw template response hash mismatch: {item['request_id']}")
        if sha256(token_bytes) != token_http["terminal"].get("response_body_sha256"):
            raise ValueError(f"raw tokenize response hash mismatch: {item['request_id']}")
        response_hash_links += 2
        rendered = json.loads(template_bytes.decode("utf-8")).get("prompt")
        if rendered != item["local_rendered_prompt"]:
            raise ValueError(f"server-rendered prompt differs from frozen local prompt: {item['request_id']}")
        exact_prompts += 1
        tokenize_body = token_request.get("body", {})
        if tokenize_body != {
            "content": rendered, "add_special": True, "parse_special": True, "with_pieces": False
        }:
            raise ValueError(f"tokenize request is not the frozen exact rendered prompt: {item['request_id']}")
        token_ids = json.loads(token_bytes.decode("utf-8")).get("tokens")
        if token_ids != item["local_token_ids"]:
            raise ValueError(f"llama.cpp token IDs differ from local GGUF tokenizer: {item['request_id']}")
        exact_token_ids += 1

    if len(ledger) != 192:
        raise ValueError(f"expected 192 token-only HTTP requests, found {len(ledger)}")
    if len(list(request_dir.glob("*.json"))) != 192 or len(list(response_dir.glob("*.bin"))) != 192:
        raise ValueError("raw request/response files do not match the 192 HTTP attempts")
    routes_used = sorted({row["start"]["route"] for row in ledger.values()})
    if routes_used != ["/apply-template", "/tokenize"]:
        raise ValueError(f"unexpected token parity routes: {routes_used}")
    if report is not None:
        if report.get("routes_used") != routes_used:
            raise ValueError("runner report route list differs from raw HTTP ledger")
    result = {
        "schema_version": "m4-server-token-parity-independent-audit-v1",
        "status": "PASS_LLAMA_SERVER_TOKENIZER_PARITY_INDEPENDENT_REPLAY_RECOVERED" if report is None else "PASS_LLAMA_SERVER_TOKENIZER_PARITY_INDEPENDENT_REPLAY",
        "scope": "96 offline Mock prompt inputs; exact chat-template string and token-ID parity; zero generations",
        "prompts_checked": len(prompts),
        "server_template_exact_matches": exact_prompts,
        "server_token_id_exact_matches": exact_token_ids,
        "http_attempts": len(ledger),
        "http_terminal_records": len(ledger),
        "listener_ownership_checks": len(owner_rows),
        "routes_used": routes_used,
        "generation_routes_used": [],
        "real_model_generations": 0,
        "external_network_requests": 0,
        "shutdown_cleanup_pass": True,
        "temporary_api_key_removed": True,
        "runner_final_report_written": report is not None,
        "runner_finalization_error_sha256": sha256(error_path.read_bytes()) if error_path.exists() else None,
        "post_run_cleanup_check_sha256": sha256(cleanup_path.read_bytes()) if cleanup_path.exists() else None,
        "model_sha256": expected["model_sha256"],
        "server_binary_sha256": expected["server_binary_sha256"],
        "runtime_bundle_sha256": expected["runtime_bundle_sha256"],
        "runtime_config_sha256": expected["runtime_config_sha256"],
        "split_manifest_sha256": expected["split_manifest_sha256"],
        "prompt_file_sha256": expected["prompt_file_sha256"],
        "tokenizer_sha256": expected["tokenizer_sha256"],
        "chat_template_sha256": expected["chat_template_sha256"],
        "tokenizers_version": expected["tokenizers_version"],
        "jinja2_version": expected["jinja2_version"],
        "python_version": platform.python_version(),
        "host_platform": platform.platform(),
        "corrected_runner_source_sha256_at_audit": sha256((ROOT / "scripts/verify_m4_llama_token_parity.ps1").read_bytes()),
        "independent_auditor_source_sha256": sha256(Path(__file__).read_bytes()),
        "expected_prompts_sha256": sha256(expected_path.read_bytes()),
        "raw_http_ledger_sha256": sha256(ledger_path.read_bytes()),
        "runner_report_sha256": sha256(report_path.read_bytes()) if report_path.exists() else None,
        "raw_response_hash_links_verified": response_hash_links,
        "raw_request_and_response_contents_retained_locally": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/results/sprint-execution-readiness/m4-v2-server-tokenizer-parity-audit.json")
    args = parser.parse_args()
    result = audit(args.run, args.out)
    print(json.dumps({key: result[key] for key in (
        "status", "prompts_checked", "server_template_exact_matches", "server_token_id_exact_matches",
        "http_attempts", "real_model_generations", "external_network_requests", "shutdown_cleanup_pass",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
