"""DeepSeek-first M4 runtime primitives (one request, no retry, fail closed).

This is a new provider-specific runtime.  It does not modify the historical
Qwen/llama.cpp M4 runtime or its artifacts.  Raw prompts/responses belong only
in Git-ignored, ACL-restricted run directories.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

MODEL = "deepseek-flash"
STRICT_ENDPOINT = "https://api.deepseek.com/beta/chat/completions"
JSON_ENDPOINT = "https://api.deepseek.com/chat/completions"
ALLOWED_MODELS = {"deepseek-flash", "DeepSeek-V4.1-Flash-1017"}
INPUT_RATE = Decimal("0.30")
OUTPUT_RATE = Decimal("1.20")
GLOBAL_REQUEST_LIMIT = 900
GLOBAL_COST_LIMIT = Decimal("5.00")
MAX_INPUT_UPPER_BOUND = 15_000
OUTPUT_LIMIT = 512
TIMEOUT_SECONDS = 90


class DeepSeekRuntimeError(RuntimeError):
    pass


class DeepSeekRequestError(DeepSeekRuntimeError):
    def __init__(self, status: str, message: str, *, fatal: bool = False):
        super().__init__(message)
        self.status = status
        self.fatal = fatal


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        stream.write(canonical(row) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line.strip():
            raise DeepSeekRuntimeError(f"blank append-only ledger row at {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise DeepSeekRuntimeError(f"non-object ledger row at {path}:{line_number}")
        rows.append(value)
    return rows


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DeepSeekRequestError("DUPLICATE_JSON_KEY", f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> None:
    raise DeepSeekRequestError("NONSTANDARD_JSON_CONSTANT", f"non-standard JSON constant: {value}")


def load_json_strict(raw: str) -> Any:
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)


def agent_tool(action_kind: str) -> tuple[str, dict[str, Any]]:
    string_task = {"type": "string", "enum": ["T1", "T2", "T3"]}
    if action_kind == "message":
        return "submit_message", {
            "type": "object", "required": ["action", "text"], "additionalProperties": False,
            "properties": {"action": {"type": "string", "enum": ["send_message", "no_message"]},
                           "text": {"type": "string"}},
        }
    if action_kind == "ballot":
        return "submit_ballot", {
            "type": "object", "required": ["assignment"], "additionalProperties": False,
            "properties": {"assignment": {
                "type": "object", "required": ["A", "B", "C"], "additionalProperties": False,
                "properties": {agent: string_task for agent in ("A", "B", "C")},
            }},
        }
    if action_kind == "positive_control":
        return "submit_choice", {
            "type": "object", "required": ["choice"], "additionalProperties": False,
            "properties": {"choice": {"type": "string", "enum": ["T1", "T2"]}},
        }
    raise ValueError(f"unknown agent action kind {action_kind!r}")


def monitor_tool(allowed_labels: list[str]) -> tuple[str, dict[str, Any]]:
    return "report_evidence", {
        "type": "object", "required": ["label", "evidence_refs"], "additionalProperties": False,
        "properties": {
            "label": {"type": "string", "enum": list(allowed_labels)},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_agent_arguments(action_kind: str, args: Any) -> dict[str, Any]:
    try:
        import jsonschema
        name, schema = agent_tool(action_kind)
        jsonschema.validate(args, schema)
    except Exception as exc:
        raise DeepSeekRequestError("INVALID_TOOL_ARGUMENTS", f"tool arguments violate schema: {exc}") from exc
    if action_kind == "message":
        action, text = args["action"], args["text"]
        if action == "no_message":
            if text != "":
                raise DeepSeekRequestError("INVALID_TOOL_ARGUMENTS", "no_message requires empty text")
            return {"type": "no_message"}
        if not 1 <= len(text) <= 1000:
            raise DeepSeekRequestError("INVALID_TOOL_ARGUMENTS", "send_message text must contain 1..1000 characters")
        return {"type": "send_message", "text": text}
    if action_kind == "ballot":
        mapping = args["assignment"]
        if set(mapping.values()) != {"T1", "T2", "T3"}:
            raise DeepSeekRequestError("INVALID_TOOL_ARGUMENTS", "ballot must be a complete task permutation")
        return {"type": "ballot", "assignment": mapping}
    if action_kind == "positive_control":
        return {"choice": args["choice"]}
    raise AssertionError(action_kind)


def validate_monitor_arguments(task: str, allowed_labels: list[str], args: Any) -> dict[str, Any]:
    try:
        import jsonschema
        _, schema = monitor_tool(allowed_labels)
        jsonschema.validate(args, schema)
    except Exception as exc:
        raise DeepSeekRequestError("INVALID_TOOL_ARGUMENTS", f"monitor tool arguments violate schema: {exc}") from exc
    if args["label"] not in allowed_labels or len(args["evidence_refs"]) != len(set(args["evidence_refs"])):
        raise DeepSeekRequestError("INVALID_TOOL_ARGUMENTS", f"invalid label or duplicate event reference for {task}")
    return args


def request_payload(*, interface: str, messages: list[dict[str, str]],
                    tool_name: str, schema: dict[str, Any], output_limit: int = OUTPUT_LIMIT) -> dict[str, Any]:
    if interface not in {"strict_function_calling", "json_object_fallback"}:
        raise ValueError("unknown frozen interface")
    body: dict[str, Any] = {
        "model": MODEL, "messages": messages, "thinking": {"type": "disabled"},
        "temperature": 0.0, "max_tokens": output_limit, "stream": False,
    }
    if interface == "strict_function_calling":
        body["tools"] = [{"type": "function", "function": {
            "name": tool_name, "description": "Submit exactly one validated research action.",
            "parameters": schema, "strict": True,
        }}]
        body["tool_choice"] = {"type": "function", "function": {"name": tool_name}}
    else:
        body["response_format"] = {"type": "json_object"}
    return body


def parse_completion(response: dict[str, Any], *, interface: str, tool_name: str,
                     schema: dict[str, Any]) -> tuple[Any, str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise DeepSeekRequestError("PROVIDER_RESPONSE_SHAPE", "expected exactly one completion choice")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise DeepSeekRequestError("PROVIDER_RESPONSE_SHAPE", "completion message is missing")
    finish = choice.get("finish_reason")
    if message.get("reasoning_content") not in (None, ""):
        raise DeepSeekRequestError("THINKING_NOT_DISABLED", "provider returned reasoning content")
    if interface == "strict_function_calling":
        if finish != "tool_calls":
            raise DeepSeekRequestError("NO_FORCED_TOOL_CALL", f"strict response finish_reason={finish!r}")
        if message.get("content") not in (None, ""):
            raise DeepSeekRequestError("FREE_TEXT_ACTION", "strict action must be a tool call without free-text content")
        calls = message.get("tool_calls")
        if not isinstance(calls, list) or len(calls) != 1 or not isinstance(calls[0], dict):
            raise DeepSeekRequestError("TOOL_CALL_COUNT", "strict response must contain exactly one tool call")
        call = calls[0]
        function = call.get("function")
        if call.get("type") != "function" or not isinstance(function, dict) or function.get("name") != tool_name:
            raise DeepSeekRequestError("TOOL_NAME_MISMATCH", "strict response called the wrong function")
        raw_args = function.get("arguments")
        if not isinstance(raw_args, str):
            raise DeepSeekRequestError("INVALID_TOOL_ARGUMENTS", "function arguments are not a JSON string")
        args = load_json_strict(raw_args)
        try:
            import jsonschema
            jsonschema.validate(args, schema)
        except Exception as exc:
            raise DeepSeekRequestError("INVALID_TOOL_ARGUMENTS", f"function arguments violate schema: {exc}") from exc
        return args, str(finish)
    if finish != "stop":
        raise DeepSeekRequestError("NONTERMINAL_JSON_OUTPUT", f"fallback response finish_reason={finish!r}")
    if message.get("tool_calls") not in (None, []):
        raise DeepSeekRequestError("UNEXPECTED_TOOL_CALL", "JSON fallback must not return tool_calls")
    content = message.get("content")
    if not isinstance(content, str) or not content:
        raise DeepSeekRequestError("EMPTY_JSON_OUTPUT", "JSON fallback content is empty")
    args = load_json_strict(content)
    try:
        import jsonschema
        jsonschema.validate(args, schema)
    except Exception as exc:
        raise DeepSeekRequestError("INVALID_TOOL_ARGUMENTS", f"fallback JSON violates schema: {exc}") from exc
    return args, str(finish)


def request_cost_bound(body: bytes, output_limit: int = OUTPUT_LIMIT) -> tuple[int, Decimal]:
    # Strict upper estimate: at most two tokenizer units per UTF-8 byte plus
    # 256 provider/chat-framing tokens. We reject oversized serialized inputs.
    input_upper = len(body) * 2 + 256
    if input_upper > MAX_INPUT_UPPER_BOUND:
        raise DeepSeekRequestError("INPUT_BOUND_EXCEEDED", "request exceeds frozen conservative input-token bound", fatal=True)
    reserve = (Decimal(input_upper) * INPUT_RATE + Decimal(output_limit) * OUTPUT_RATE) / Decimal(1_000_000)
    return input_upper, reserve


def usage_cost(response: dict[str, Any]) -> tuple[int, int, Decimal]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        raise DeepSeekRequestError("USAGE_MISSING", "provider usage object is required for cost audit", fatal=True)
    prompt_tokens, completion_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if type(prompt_tokens) is not int or type(completion_tokens) is not int or min(prompt_tokens, completion_tokens) < 0:
        raise DeepSeekRequestError("USAGE_INVALID", "provider token usage fields are invalid", fatal=True)
    if prompt_tokens > MAX_INPUT_UPPER_BOUND or completion_tokens > OUTPUT_LIMIT:
        raise DeepSeekRequestError("USAGE_BOUND_EXCEEDED", "provider token usage exceeded frozen per-request bounds", fatal=True)
    cost = (Decimal(prompt_tokens) * INPUT_RATE + Decimal(completion_tokens) * OUTPUT_RATE) / Decimal(1_000_000)
    return prompt_tokens, completion_tokens, cost


def _budget_rows(path: Path) -> list[dict[str, Any]]:
    return read_jsonl(path)


class DeepSeekClient:
    """Single-attempt DeepSeek client with append-only evidence and global budget."""

    def __init__(self, *, run_dir: Path, budget_ledger: Path, api_key: str,
                 interface: str, timeout: int = TIMEOUT_SECONDS,
                 transport: Callable[..., tuple[int, bytes, float]] | None = None):
        if interface not in {"strict_function_calling", "json_object_fallback"}:
            raise ValueError("interface must be frozen before execution")
        self.run_dir = Path(run_dir).resolve()
        self.budget_ledger = Path(budget_ledger).resolve()
        self.api_key = api_key
        self.interface = interface
        self.timeout = timeout
        self.transport = transport or self._http_once
        self.run_dir.mkdir(parents=True, exist_ok=True)
        for name in ("requests", "responses"):
            (self.run_dir / name).mkdir(exist_ok=True)

    @staticmethod
    def _http_once(endpoint: str, body: bytes, api_key: str, timeout: int) -> tuple[int, bytes, float]:
        expected = STRICT_ENDPOINT if endpoint == STRICT_ENDPOINT else JSON_ENDPOINT
        if endpoint != expected or endpoint not in {STRICT_ENDPOINT, JSON_ENDPOINT}:
            raise DeepSeekRequestError("ENDPOINT_MISMATCH", "request target is not an approved official DeepSeek endpoint", fatal=True)
        req = urllib.request.Request(endpoint, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {api_key}",
        })

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        started = time.perf_counter()
        try:
            with opener.open(req, timeout=timeout) as response:
                return response.status, response.read(), time.perf_counter() - started
        except urllib.error.HTTPError as exc:
            try:
                return int(exc.code), exc.read(), time.perf_counter() - started
            finally:
                exc.close()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise DeepSeekRequestError("TRANSPORT_ERROR", f"{type(exc).__name__}: {exc}") from exc

    def _prior_rows(self) -> list[dict[str, Any]]:
        return read_jsonl(self.run_dir / "attempts.jsonl")

    def _resume_cached(self, request_id: str, body: bytes, tool_name: str, schema: dict[str, Any],
                       semantic: Callable[[Any], Any]) -> tuple[Any, dict[str, Any]] | None:
        rows = [row for row in self._prior_rows() if row.get("request_id") == request_id]
        started = [row for row in rows if row.get("event") == "attempt_started"]
        if not started:
            return None
        if len(started) != 1:
            raise DeepSeekRuntimeError(f"duplicate attempts detected for {request_id}")
        request_path = self.run_dir / "requests" / f"{request_id}.bin"
        if not request_path.is_file() or request_path.read_bytes() != body:
            raise DeepSeekRuntimeError(f"resumed request bytes changed for {request_id}")
        terminal = [row for row in rows if row.get("event") == "attempt_terminal"]
        if len(terminal) != 1 or terminal[0].get("status") != "COMPLETED":
            raise DeepSeekRequestError("UNKNOWN_OR_FAILED_PRIOR_ATTEMPT", "started request is terminal or has ambiguous billing; it will not be resent", fatal=False)
        response_path = self.run_dir / "responses" / f"{request_id}.bin"
        response = json.loads(response_path.read_bytes())
        args, finish = parse_completion(response, interface=self.interface, tool_name=tool_name, schema=schema)
        result = semantic(args)
        return result, {**terminal[0], "finish_reason": finish, "resumed_from_saved_response": True}

    def call(self, *, request_id: str, role: str, messages: list[dict[str, str]],
             tool_name: str, schema: dict[str, Any], semantic: Callable[[Any], Any],
             metadata: dict[str, Any] | None = None, output_limit: int = OUTPUT_LIMIT,
             expected_request_sha256: str | None = None,
             run_request_limit: int | None = None) -> tuple[Any, dict[str, Any]]:
        if role not in {"agent", "monitor"} or not request_id or "/" in request_id or "\\" in request_id:
            raise ValueError("invalid role or request id")
        endpoint = STRICT_ENDPOINT if self.interface == "strict_function_calling" else JSON_ENDPOINT
        payload = request_payload(interface=self.interface, messages=messages,
                                  tool_name=tool_name, schema=schema, output_limit=output_limit)
        body = canonical(payload)
        if expected_request_sha256 is not None and sha(body) != expected_request_sha256:
            raise DeepSeekRequestError("FROZEN_REQUEST_HASH_MISMATCH",
                "constructed request differs from the pre-inference pilot freeze", fatal=True)
        if self.api_key.encode("utf-8") in body or b"LLM_API_KEY" in body or b"Authorization" in body:
            raise DeepSeekRequestError("SECRET_IN_REQUEST", "credential or auth header appeared in request body", fatal=True)
        input_upper, reserve = request_cost_bound(body, output_limit)
        cached = self._resume_cached(request_id, body, tool_name, schema, semantic)
        if cached is not None:
            return cached
        if run_request_limit is not None:
            if type(run_request_limit) is not int or run_request_limit < 1:
                raise ValueError("run_request_limit must be a positive integer")
            run_started = sum(row.get("event") == "attempt_started"
                              for row in self._prior_rows())
            if run_started >= run_request_limit:
                raise DeepSeekRequestError("RUN_REQUEST_CAP",
                    f"per-run physical request cap of {run_request_limit} reached", fatal=True)
        request_path = self.run_dir / "requests" / f"{request_id}.bin"
        request_meta_path = self.run_dir / "requests" / f"{request_id}.meta.json"
        if request_path.exists() or request_meta_path.exists():
            raise DeepSeekRuntimeError(f"unstarted request path already exists for {request_id}")
        write_once(request_path, body)
        request_meta = {"request_id": request_id, "role": role, "endpoint": endpoint,
                        "request_sha256": sha(body), "serialized_request_bytes": len(body),
                        "prompt_sha256": sha(canonical(messages)),
                        "conservative_prompt_token_upper_bound": input_upper,
                        "max_output_tokens": output_limit, "interface": self.interface,
                        "metadata_not_sent": metadata or {}, "auth_header_saved": False}
        write_once(request_meta_path, canonical(request_meta) + b"\n")
        budget_rows = _budget_rows(self.budget_ledger)
        existing_ids = {row.get("request_id") for row in budget_rows
                        if row.get("event") == "physical_request_started"}
        if request_id in existing_ids:
            raise DeepSeekRuntimeError(f"global ledger already contains request {request_id}")
        if len(existing_ids) >= GLOBAL_REQUEST_LIMIT:
            raise DeepSeekRequestError("GLOBAL_REQUEST_CAP", "900 physical inference request cap reached", fatal=True)
        reserved = sum(Decimal(row["reserved_peak_cost_usd"]) for row in budget_rows
                       if row.get("event") == "physical_request_started")
        if reserved + reserve > GLOBAL_COST_LIMIT:
            raise DeepSeekRequestError("GLOBAL_COST_CAP", "$5 peak-rate request reservation would be exceeded", fatal=True)
        started = {"event": "attempt_started", "request_id": request_id,
                   "endpoint_host": "api.deepseek.com", "role": role, "interface": self.interface,
                   "request_sha256": sha(body), "reserved_peak_cost_usd": str(reserve),
                   "at_utc": now_utc(), "auth_header_saved": False, "retry": False}
        append_jsonl(self.run_dir / "attempts.jsonl", started)
        append_jsonl(self.budget_ledger, {**started, "event": "physical_request_started"})
        raw: bytes | None = None
        http_status: int | None = None
        elapsed = 0.0
        try:
            http_status, raw, elapsed = self.transport(endpoint, body, self.api_key, self.timeout)
            response_path = self.run_dir / "responses" / f"{request_id}.bin"
            write_once(response_path, raw)
            response_hash = sha(raw)
            if http_status != 200:
                terminal = {"event": "attempt_terminal", "request_id": request_id,
                            "status": f"HTTP_{http_status}", "http_status": http_status,
                            "response_sha256": response_hash, "elapsed_seconds": elapsed,
                            "retry": False, "auth_header_saved": False}
                append_jsonl(self.run_dir / "attempts.jsonl", terminal)
                append_jsonl(self.budget_ledger, {**terminal, "event": "physical_request_terminal"})
                raise DeepSeekRequestError(f"HTTP_{http_status}", f"DeepSeek returned HTTP {http_status}")
            try:
                response = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise DeepSeekRequestError("PROVIDER_RESPONSE_NOT_JSON", "provider response was not JSON", fatal=True) from exc
            model = response.get("model")
            fingerprint = response.get("system_fingerprint")
            if model not in ALLOWED_MODELS or not isinstance(fingerprint, str) or not fingerprint.strip():
                raise DeepSeekRequestError("PROVIDER_IDENTITY_INVALID", "returned model or system fingerprint is missing/unknown", fatal=True)
            identity_path = self.budget_ledger.parent / "provider_identity.json"
            identity = {"model": model, "system_fingerprint": fingerprint}
            if identity_path.exists():
                previous = json.loads(identity_path.read_bytes())
                if previous != identity:
                    raise DeepSeekRequestError("PROVIDER_IDENTITY_DRIFT", "provider model/fingerprint changed", fatal=True)
            else:
                write_once(identity_path, canonical(identity) + b"\n")
            input_tokens, output_tokens, actual_cost = usage_cost(response)
            if input_tokens > input_upper:
                raise DeepSeekRequestError("INPUT_BOUND_UNDERESTIMATED", "provider input token usage exceeded reserved upper bound", fatal=True)
            args, finish = parse_completion(response, interface=self.interface, tool_name=tool_name, schema=schema)
            result = semantic(args)
            response_meta = {"request_id": request_id, "status": "COMPLETED",
                             "response_sha256": response_hash, "http_status": http_status,
                             "request_sha256": sha(body),
                             "prompt_sha256": sha(canonical(messages)),
                             "finish_reason": finish, "returned_model": model,
                             "system_fingerprint": fingerprint,
                             "prompt_tokens": input_tokens, "completion_tokens": output_tokens,
                             "estimated_peak_cost_usd": str(actual_cost),
                             "elapsed_seconds": elapsed, "auth_header_saved": False,
                             "raw_response_path": f"responses/{request_id}.bin"}
            write_once(self.run_dir / "responses" / f"{request_id}.meta.json", canonical(response_meta) + b"\n")
            terminal = {"event": "attempt_terminal", **response_meta, "retry": False, "at_utc": now_utc()}
            append_jsonl(self.run_dir / "attempts.jsonl", terminal)
            append_jsonl(self.budget_ledger, {**terminal, "event": "physical_request_terminal"})
            return result, response_meta
        except DeepSeekRequestError as exc:
            if any(row.get("event") == "attempt_terminal" and row.get("request_id") == request_id
                   for row in self._prior_rows()):
                raise
            raw_hash = sha(raw) if raw is not None else None
            diagnostics: dict[str, Any] = {}
            if raw is not None:
                response_path = self.run_dir / "responses" / f"{request_id}.bin"
                if not response_path.exists():
                    write_once(response_path, raw)
                try:
                    parsed_raw = json.loads(raw)
                    diagnostics["returned_model"] = parsed_raw.get("model")
                    diagnostics["system_fingerprint"] = parsed_raw.get("system_fingerprint")
                    choices = parsed_raw.get("choices")
                    if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict):
                        diagnostics["finish_reason"] = choices[0].get("finish_reason")
                    usage = parsed_raw.get("usage")
                    if isinstance(usage, dict):
                        diagnostics["prompt_tokens"] = usage.get("prompt_tokens")
                        diagnostics["completion_tokens"] = usage.get("completion_tokens")
                        if (type(usage.get("prompt_tokens")) is int
                                and type(usage.get("completion_tokens")) is int):
                            diagnostics["estimated_peak_cost_usd"] = str(
                                (Decimal(usage["prompt_tokens"]) * INPUT_RATE
                                 + Decimal(usage["completion_tokens"]) * OUTPUT_RATE)
                                / Decimal(1_000_000))
                except Exception:
                    diagnostics["provider_json_parse"] = "failed"
            error_metadata = {"request_id": request_id, "status": exc.status,
                "response_sha256": raw_hash, "http_status": http_status,
                "elapsed_seconds": elapsed, **diagnostics,
                "error_type": type(exc).__name__, "error_message": str(exc),
                "auth_header_saved": False}
            error_meta_path = self.run_dir / "responses" / f"{request_id}.meta.json"
            if not error_meta_path.exists():
                write_once(error_meta_path, canonical(error_metadata) + b"\n")
            terminal = {"event": "attempt_terminal", "request_id": request_id,
                        "status": exc.status, "http_status": http_status,
                        "response_sha256": raw_hash, "elapsed_seconds": elapsed,
                        **diagnostics,
                        "error_type": type(exc).__name__, "error_message": str(exc),
                        "fatal": exc.fatal, "retry": False, "auth_header_saved": False,
                        "at_utc": now_utc()}
            append_jsonl(self.run_dir / "attempts.jsonl", terminal)
            append_jsonl(self.budget_ledger, {**terminal, "event": "physical_request_terminal"})
            raise
        except BaseException as exc:
            raw_hash = sha(raw) if raw is not None else None
            if raw is not None:
                response_path = self.run_dir / "responses" / f"{request_id}.bin"
                if not response_path.exists():
                    write_once(response_path, raw)
            terminal = {"event": "attempt_terminal", "request_id": request_id,
                        "status": "INTERRUPTED_UNKNOWN", "http_status": http_status,
                        "response_sha256": raw_hash, "elapsed_seconds": elapsed,
                        "error_type": type(exc).__name__, "auth_header_saved": False,
                        "retry": False, "at_utc": now_utc()}
            append_jsonl(self.run_dir / "attempts.jsonl", terminal)
            append_jsonl(self.budget_ledger, {**terminal, "event": "physical_request_terminal"})
            raise DeepSeekRequestError("INTERRUPTED_UNKNOWN", "request may have been billed; never resent", fatal=False) from exc

