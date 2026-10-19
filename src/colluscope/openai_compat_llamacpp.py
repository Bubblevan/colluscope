"""Strict local llama.cpp backend for the frozen M1-P0 V2 runtime."""

from __future__ import annotations

import ipaddress
import json
import math
import socket
import threading
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from .m1_runtime import (AgentRequest, BackendResponse, RuntimeConfig, TimeoutBackendError,
                         TransientTransportError, _parse_action)
from .openai_compat_vllm import BackendResponseError


ROOT = Path(__file__).resolve().parents[2]
ACTION_SCHEMA_ROOT = ROOT / "prompts" / "m1-p0-v2"
FROZEN_SAMPLERS = ("top_k", "top_p", "min_p", "temperature")


@dataclass(frozen=True)
class LlamaCppBackendConfig:
    model_calls_enabled: bool
    preflight_enabled: bool
    preflight_approval_id: str
    full_pilot_approval_id: str
    max_api_spend_usd: float
    base_url: str
    model_id: str
    artifact_path: str
    artifact_sha256: str
    upstream_repository: str
    upstream_revision: str
    server_binary_path: str
    server_binary_sha256: str
    runtime_bundle_sha256: str
    server_version: str
    server_commit: str
    server_build_info: str
    tokenizer_id: str
    tokenizer_revision: str
    tokenizer_sha256: str
    chat_template_sha256: str
    tokenizer_metadata: dict[str, Any]
    tokenizers_library_version: str
    jinja2_library_version: str
    context_length: int
    input_budget_tokens: int
    message_max_output_tokens: int
    ballot_max_output_tokens: int
    temperature: float
    top_p: float
    top_k: int
    min_p: float
    sampler_chain: tuple[str, ...]
    thinking_mode: str
    timeout_seconds: int
    max_attempts_per_request: int
    max_logical_requests: int
    max_total_attempts: int
    preflight_max_logical_requests: int
    preflight_max_attempts: int
    preflight_max_completion_attempts: int
    launch: dict[str, Any]
    retention_policy: str

    @property
    def sampling(self) -> dict[str, Any]:
        return {"temperature": self.temperature, "top_p": self.top_p,
                "top_k": self.top_k, "min_p": self.min_p,
                "samplers": list(self.sampler_chain)}

    def output_limit(self, action_kind: str) -> int:
        if action_kind == "message":
            return self.message_max_output_tokens
        if action_kind == "ballot":
            return self.ballot_max_output_tokens
        raise ValueError("action_kind must be message or ballot")

    def bind_runtime(self, base_config: RuntimeConfig) -> RuntimeConfig:
        if not self.model_calls_enabled or not self.full_pilot_approval_id:
            raise PermissionError("full pilot calls require a separate explicit approval")
        if base_config.raw.get("prompt_version") != "m1-p0-frozen-v2":
            raise ValueError("local llama.cpp backend can bind only to frozen M1-P0 V2")
        raw = {**base_config.raw,
               "model_calls_enabled": True,
               "model": {"runtime": "openai-compatible-llama.cpp-local",
                         "model_id": self.model_id, "external_enabled": False},
               "sampling": self.sampling,
               "limits": {"timeout_seconds": self.timeout_seconds,
                          "max_attempts_per_request": self.max_attempts_per_request,
                          "max_logical_requests": self.max_logical_requests,
                          "max_total_attempts": self.max_total_attempts}}
        return replace(base_config, raw=raw, model_id=self.model_id,
                       runtime="openai-compatible-llama.cpp-local", sampling=self.sampling,
                       timeout_seconds=self.timeout_seconds,
                       max_attempts_per_request=self.max_attempts_per_request,
                       max_logical_requests=self.max_logical_requests,
                       max_total_attempts=self.max_total_attempts)


def load_llamacpp_backend_config(path: Path) -> LlamaCppBackendConfig:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    expected = {"model_calls_enabled", "preflight_enabled", "preflight_approval_id",
                "full_pilot_approval_id", "max_api_spend_usd", "status", "checkpoint",
                "server", "tokenizer", "launch", "sampling", "limits", "retention",
                "authorization"}
    if set(raw) != expected:
        raise ValueError("llama.cpp config has missing or unknown top-level keys")
    checkpoint, server = raw["checkpoint"], raw["server"]
    tokenizer, launch = raw["tokenizer"], raw["launch"]
    sampling, limits = raw["sampling"], raw["limits"]
    if set(checkpoint) != {"path", "repository", "upstream_revision", "format", "identity_kind",
                           "file_sha256", "file_size_bytes"}:
        raise ValueError("GGUF artifact identity is incomplete or contains unknown keys")
    if set(server) != {"kind", "binary_path", "binary_sha256", "runtime_bundle_sha256",
                       "version", "commit", "build_info",
                       "base_url", "model_id"}:
        raise ValueError("llama.cpp server identity is incomplete or contains unknown keys")
    if set(tokenizer) != {"source", "add_bos_token", "architecture", "model", "pretokenizer", "vocabulary_count",
                          "merges_count", "token_types_sha256", "vocabulary_sha256", "merges_sha256",
                          "tokenizer_sha256", "chat_template_sha256", "tokenizers_library_version",
                          "jinja2_library_version", "server_parity"}:
        raise ValueError("embedded GGUF tokenizer provenance is incomplete or contains unknown keys")
    if set(launch) != {"host", "port", "context_length", "parallel_slots", "gpu_device", "gpu_layers",
                       "fit", "offline", "webui", "warmup", "reasoning", "reasoning_format",
                       "thinking_mode"}:
        raise ValueError("llama.cpp launch settings are incomplete or contain unknown keys")
    if set(sampling) != {"temperature", "top_p", "top_k", "min_p", "sampler_chain", "seed_scheme"}:
        raise ValueError("sampling parameters must be explicit and complete")
    if set(limits) != {"input_budget_tokens", "message_max_output_tokens", "ballot_max_output_tokens",
                       "timeout_seconds", "max_attempts_per_request", "full_pilot_logical_requests",
                       "full_pilot_max_attempts", "engineering_preflight_logical_requests",
                       "engineering_preflight_max_attempts", "engineering_preflight_max_completion_attempts",
                       "comprehension_probe_calls"}:
        raise ValueError("llama.cpp request and preflight limits are incomplete")
    if set(raw["retention"]) != {"policy"} or set(raw["authorization"]) != {
            "live_preflight", "full_25_episode_pilot", "m2_detector_evaluation"}:
        raise ValueError("retention or authorization metadata is incomplete")

    if raw["model_calls_enabled"] is not False and not raw["full_pilot_approval_id"]:
        raise PermissionError("full model calls require a user-approved pilot ID")
    if raw["preflight_enabled"] is not False and not raw["preflight_approval_id"]:
        raise PermissionError("live preflight requires a user-approved preflight ID")
    if raw["max_api_spend_usd"] != 0.0:
        raise ValueError("local llama.cpp backend must retain a zero external API spend ceiling")
    if checkpoint["identity_kind"] != "sha256_file":
        raise ValueError("GGUF byte identity must use the exact local file SHA256")
    if tokenizer["source"] != "embedded_gguf_metadata":
        raise ValueError("tokenizer provenance must identify the embedded GGUF metadata")
    if not isinstance(tokenizer["add_bos_token"], bool):
        raise ValueError("GGUF tokenizer BOS policy must be an explicit boolean")
    if tokenizer["server_parity"] != "not_verified_live_preflight_required":
        raise ValueError("GGUF tokenizer parity cannot be claimed before live preflight")
    if limits["comprehension_probe_calls"] != 0:
        raise ValueError("comprehension probes are outside the frozen protocol")

    settings = LlamaCppBackendConfig(
        model_calls_enabled=raw["model_calls_enabled"], preflight_enabled=raw["preflight_enabled"],
        preflight_approval_id=raw["preflight_approval_id"],
        full_pilot_approval_id=raw["full_pilot_approval_id"],
        max_api_spend_usd=raw["max_api_spend_usd"], base_url=server["base_url"],
        model_id=server["model_id"], artifact_path=checkpoint["path"],
        artifact_sha256=checkpoint["file_sha256"], upstream_repository=checkpoint["repository"],
        upstream_revision=checkpoint["upstream_revision"], server_binary_path=server["binary_path"],
        server_binary_sha256=server["binary_sha256"],
        runtime_bundle_sha256=server["runtime_bundle_sha256"], server_version=server["version"],
        server_commit=server["commit"], server_build_info=server["build_info"],
        tokenizer_id=f"gguf-embedded:{tokenizer['architecture']}:{tokenizer['model']}/{tokenizer['pretokenizer']}",
        tokenizer_revision=f"sha256:{tokenizer['tokenizer_sha256']}",
        tokenizer_sha256=tokenizer["tokenizer_sha256"],
        chat_template_sha256=tokenizer["chat_template_sha256"], tokenizer_metadata=tokenizer,
        tokenizers_library_version=tokenizer["tokenizers_library_version"],
        jinja2_library_version=tokenizer["jinja2_library_version"],
        context_length=launch["context_length"], input_budget_tokens=limits["input_budget_tokens"],
        message_max_output_tokens=limits["message_max_output_tokens"],
        ballot_max_output_tokens=limits["ballot_max_output_tokens"],
        temperature=sampling["temperature"], top_p=sampling["top_p"], top_k=sampling["top_k"],
        min_p=sampling["min_p"], sampler_chain=tuple(sampling["sampler_chain"]),
        thinking_mode=launch["thinking_mode"], timeout_seconds=limits["timeout_seconds"],
        max_attempts_per_request=limits["max_attempts_per_request"],
        max_logical_requests=limits["full_pilot_logical_requests"],
        max_total_attempts=limits["full_pilot_max_attempts"],
        preflight_max_logical_requests=limits["engineering_preflight_logical_requests"],
        preflight_max_attempts=limits["engineering_preflight_max_attempts"],
        preflight_max_completion_attempts=limits["engineering_preflight_max_completion_attempts"],
        launch=launch, retention_policy=raw["retention"]["policy"])
    _validate_config(settings)
    return settings


def _is_sha256(value: str) -> bool:
    return (isinstance(value, str) and len(value) == 64 and
            all(ch in "0123456789abcdef" for ch in value.lower()))


def llama_runtime_bundle_identity(server_binary_path: str | Path) -> dict[str, Any]:
    """Hash every regular file beside the launcher, including llama.cpp DLLs."""
    binary = Path(server_binary_path).resolve()
    if not binary.is_file():
        raise FileNotFoundError(f"llama.cpp server launcher is absent: {binary}")
    entries: list[dict[str, Any]] = []
    for path in sorted((item for item in binary.parent.iterdir() if item.is_file()),
                       key=lambda item: item.name.casefold()):
        digest = sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        entries.append({"name": path.name, "size_bytes": path.stat().st_size,
                        "sha256": digest.hexdigest()})
    manifest = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"directory": str(binary.parent), "file_count": len(entries), "files": entries,
            "sha256": sha256(manifest).hexdigest()}


def _validate_config(config: LlamaCppBackendConfig) -> None:
    parsed = urllib.parse.urlsplit(config.base_url)
    if (parsed.scheme != "http" or parsed.username or parsed.password or parsed.path != "/v1" or
            parsed.query or parsed.fragment):
        raise ValueError("base_url must be plain HTTP loopback ending exactly in /v1")
    try:
        is_loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        is_loopback = (parsed.hostname or "").lower() == "localhost"
    if not is_loopback or parsed.hostname != "127.0.0.1":
        raise ValueError("only the frozen 127.0.0.1 local endpoint is permitted")
    if parsed.port != config.launch.get("port"):
        raise ValueError("llama.cpp endpoint port differs from the frozen launch port")
    if config.max_api_spend_usd != 0.0:
        raise ValueError("local backend must have a $0.00 API spend ceiling")
    if not config.model_id or config.model_id == "FILL_AFTER_APPROVAL":
        raise ValueError("a fixed local model alias is required")
    if (not _is_sha256(config.artifact_sha256) or not _is_sha256(config.server_binary_sha256) or
            not _is_sha256(config.runtime_bundle_sha256)):
        raise ValueError("model and complete server runtime identities must be exact SHA256 digests")
    if len(config.upstream_revision) != 40 or any(ch not in "0123456789abcdef" for ch in config.upstream_revision.lower()):
        raise ValueError("upstream repository revision must be a separate immutable 40-character commit")
    if not _is_sha256(config.tokenizer_sha256) or not _is_sha256(config.chat_template_sha256):
        raise ValueError("tokenizer and template identities must be 64-character SHA256 digests")
    if config.tokenizer_revision != f"sha256:{config.tokenizer_sha256}":
        raise ValueError("embedded tokenizer identity must use its metadata SHA256, not a fake repository commit")
    if config.server_version != "10068" or config.server_commit != "571d0d540":
        raise ValueError("server build differs from the inspected Windows llama.cpp binary")
    expected_launch = {"host": "127.0.0.1", "context_length": 4096, "parallel_slots": 1,
                       "gpu_device": "Vulkan1", "gpu_layers": "all", "fit": "off", "offline": True,
                       "webui": False, "warmup": False, "reasoning": "off",
                       "reasoning_format": "none", "thinking_mode": "disabled"}
    launch_without_port = {key: value for key, value in config.launch.items() if key != "port"}
    port = config.launch.get("port")
    approved_preflight_port = (port == 8081 and config.preflight_enabled and
                               bool(config.preflight_approval_id) and not config.model_calls_enabled)
    if launch_without_port != expected_launch or port not in (8080, 8081) or (
            port != 8080 and not approved_preflight_port):
        raise ValueError("launch settings differ from the inspected, frozen local candidate")
    if (config.context_length != 4096 or config.input_budget_tokens != 3072 or
            config.message_max_output_tokens != 512 or config.ballot_max_output_tokens != 256):
        raise ValueError("context and per-stage token limits differ from the frozen candidate")
    if (config.temperature != 0.0 or config.top_p != 1.0 or config.top_k != 0 or
            config.min_p != 0.0 or config.sampler_chain != FROZEN_SAMPLERS):
        raise ValueError("sampling settings differ from the frozen greedy-decoding candidate")
    if config.thinking_mode != "disabled":
        raise ValueError("Qwen3 reasoning must be explicitly disabled")
    if config.input_budget_tokens + max(config.message_max_output_tokens,
                                        config.ballot_max_output_tokens) > config.context_length:
        raise ValueError("input budget plus stage output exceeds the context")
    if (config.max_attempts_per_request != 2 or config.max_logical_requests != 95 or
            config.max_total_attempts != 190):
        raise ValueError("full pilot request budget differs from the frozen 95/190 ceiling")
    if (config.preflight_max_logical_requests != 6 or config.preflight_max_attempts != 12 or
            config.preflight_max_completion_attempts != 4):
        raise ValueError("engineering preflight ceiling differs from 6 logical / 12 attempts / 4 completions")
    if (config.preflight_enabled and not config.preflight_approval_id) or (
            config.model_calls_enabled and not config.full_pilot_approval_id):
        raise PermissionError("live execution requires the matching separate approval ID")


def llama_server_command(config: LlamaCppBackendConfig) -> list[str]:
    """Return the exact candidate command; this function never starts it."""
    _validate_config(config)
    launch = config.launch
    return [config.server_binary_path, "--model", config.artifact_path,
            "--alias", config.model_id, "--offline", "--host", launch["host"],
            "--port", str(launch["port"]), "--no-webui", "--no-warmup", "--jinja",
            "--ctx-size", str(config.context_length), "--parallel", str(launch["parallel_slots"]),
            "--device", launch["gpu_device"], "--n-gpu-layers", launch["gpu_layers"],
            "--fit", launch["fit"], "--reasoning", launch["reasoning"],
            "--reasoning-format", launch["reasoning_format"], "--temp", str(config.temperature),
            "--top-p", str(config.top_p), "--top-k", str(config.top_k), "--min-p", str(config.min_p),
            "--samplers", ";".join(config.sampler_chain)]


@dataclass
class LlamaCppPreflightBudget:
    """Separate explicit 6-logical / 12-HTTP-attempt / 4-generation ceiling."""
    enabled: bool = False
    max_logical_requests: int = 6
    max_attempts: int = 12
    max_completion_attempts: int = 4
    logical_ids: set[str] = field(default_factory=set)
    attempts_by_request: dict[str, int] = field(default_factory=dict)
    attempts: int = 0
    completion_attempts: int = 0
    records: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 1 <= self.max_logical_requests <= 6 or not 1 <= self.max_attempts <= 12:
            raise ValueError("preflight budget cannot exceed 6 logical requests / 12 HTTP attempts")
        if not 1 <= self.max_completion_attempts <= 4:
            raise ValueError("preflight budget cannot exceed four model completion attempts")

    def reserve(self, request_id: str, attempt: int, *, completion: bool = False) -> None:
        if not self.enabled:
            raise PermissionError("live llama.cpp preflight budget is disabled")
        expected_attempt = self.attempts_by_request.get(request_id, 0) + 1
        if attempt != expected_attempt or attempt > 2:
            raise ValueError("preflight attempt sequence exceeds two attempts per request")
        if request_id not in self.logical_ids and len(self.logical_ids) >= self.max_logical_requests:
            raise RuntimeError("preflight logical-request hard limit reached")
        if self.attempts >= self.max_attempts:
            raise RuntimeError("preflight HTTP-attempt hard limit reached")
        if completion and self.completion_attempts >= self.max_completion_attempts:
            raise RuntimeError("preflight model-completion hard limit reached")
        self.logical_ids.add(request_id)
        self.attempts_by_request[request_id] = attempt
        self.attempts += 1
        if completion:
            self.completion_attempts += 1


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LocalLlamaCppBackend:
    """OpenAI-compatible chat adapter that can contact only local llama.cpp."""

    def __init__(self, config: LlamaCppBackendConfig, token_counter: Any,
                 opener: Any | None = None, *,
                 listener_guard: Callable[[], bool] | None = None,
                 preflight_event_hook: Callable[[dict[str, Any]], None] | None = None):
        _validate_config(config)
        self.config = config
        self.token_counter = token_counter
        self.listener_guard = listener_guard
        self.preflight_event_hook = preflight_event_hook
        self.tokenizer_metadata = dict(config.tokenizer_metadata)
        for attr, expected in (("artifact_sha256", config.artifact_sha256),
                               ("tokenizer_id", config.tokenizer_id),
                               ("tokenizer_revision", config.tokenizer_revision),
                               ("tokenizer_sha256", config.tokenizer_sha256),
                               ("chat_template_sha256", config.chat_template_sha256),
                               ("tokenizers_library_version", config.tokenizers_library_version),
                               ("jinja2_library_version", config.jinja2_library_version)):
            if getattr(token_counter, attr, None) != expected:
                raise ValueError(f"GGUF token counter {attr} differs from frozen local backend config")
        self.opener = opener or urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect())
        self._prepared: dict[str, tuple[AgentRequest, bytes, dict[str, Any], int, list[dict[str, str]]]] = {}
        self._full_pilot_lock = threading.Lock()
        self._full_pilot_logical_ids: set[str] = set()
        self._full_pilot_attempts_by_request: dict[str, int] = {}
        self._full_pilot_attempts = 0
        self._full_pilot_terminal_ids: set[str] = set()

    def _messages(self, prompt: str) -> list[dict[str, str]]:
        if "\n\n" not in prompt:
            raise ValueError("rendered prompt lacks the frozen system/user boundary")
        system, user = prompt.split("\n\n", 1)
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _payload(self, request: AgentRequest) -> tuple[dict[str, Any], int, bytes, list[dict[str, str]], str]:
        if request.model_id != self.config.model_id:
            raise ValueError("request model ID differs from the frozen local llama.cpp alias")
        if request.sampling != self.config.sampling:
            raise ValueError("request sampling differs from the frozen local llama.cpp settings")
        if request.timeout_seconds > self.config.timeout_seconds:
            raise ValueError("request timeout exceeds the frozen local transport deadline")
        messages = self._messages(request.prompt)
        rendered = self.token_counter.render_chat(messages, enable_thinking=False)
        token_ids = self.token_counter.encode_chat(messages, enable_thinking=False)
        token_count = len(token_ids)
        if token_count > self.config.input_budget_tokens:
            raise ValueError("rendered prompt exceeds the frozen input-token budget")
        output_tokens = self.config.output_limit(request.action_kind)
        if token_count + output_tokens > self.config.context_length:
            raise ValueError("rendered prompt plus stage output exceeds the frozen model context")
        if (not isinstance(request.generation_seed, int) or isinstance(request.generation_seed, bool) or
                not 0 <= request.generation_seed <= 0x7FFFFFFF):
            raise ValueError("request must carry its frozen 31-bit matched-block generation seed")
        schema_filename = ("communication.schema.json" if request.action_kind == "message" else
                           "ballot.schema.json" if request.action_kind == "ballot" else None)
        if schema_filename is None:
            raise ValueError("action_kind must be message or ballot")
        schema_bytes = (ACTION_SCHEMA_ROOT / schema_filename).read_bytes()
        schema_text = schema_bytes.decode("utf-8")
        if schema_text not in request.prompt:
            raise ValueError("rendered V2 prompt does not contain the exact action schema")
        schema = json.loads(schema_text)
        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "min_p": self.config.min_p,
            "samplers": list(self.config.sampler_chain),
            "seed": request.generation_seed,
            "max_tokens": output_tokens,
            "stream": False,
            "cache_prompt": False,
            "response_format": {"type": "json_schema", "schema": schema},
            "chat_template_kwargs": {"enable_thinking": False},
            "reasoning_format": "none",
        }
        return payload, token_count, schema_bytes, messages, rendered

    def _prepare(self, request: AgentRequest) -> tuple[bytes, dict[str, Any], int, list[dict[str, str]]]:
        cached = self._prepared.get(request.request_id)
        if cached is not None:
            if cached[0] != request:
                raise ValueError("logical request ID was reused with different request content")
            return cached[1], cached[2], cached[3], cached[4]
        payload, token_count, schema_bytes, messages, rendered = self._payload(request)
        payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        metadata = {
            "backend": "openai-compatible-llama.cpp-local",
            "endpoint": self.config.base_url.rstrip("/") + "/chat/completions",
            "method": "POST", "role_mapping": ["system", "user"],
            "model_id": self.config.model_id,
            "model_artifact_path": self.config.artifact_path,
            "model_artifact_sha256": self.config.artifact_sha256,
            "upstream_repository": self.config.upstream_repository,
            "upstream_revision": self.config.upstream_revision,
            "server_version_expected": self.config.server_version,
            "server_commit_expected": self.config.server_commit,
            "server_binary_sha256": self.config.server_binary_sha256,
            "runtime_bundle_sha256": self.config.runtime_bundle_sha256,
            "tokenizer_id": self.config.tokenizer_id,
            "tokenizer_revision": self.config.tokenizer_revision,
            "tokenizer_sha256": self.config.tokenizer_sha256,
            "chat_template_sha256": self.config.chat_template_sha256,
            "tokenizers_library_version": self.config.tokenizers_library_version,
            "jinja2_library_version": self.config.jinja2_library_version,
            "context_length": self.config.context_length,
            "input_budget_tokens": self.config.input_budget_tokens,
            "prompt_tokens_local": token_count,
            "rendered_prompt_sha256": sha256(rendered.encode("utf-8")).hexdigest(),
            "thinking_mode": "disabled",
            "action_kind": request.action_kind,
            "max_output_tokens": self.config.output_limit(request.action_kind),
            "generation_seed": request.generation_seed,
            "action_schema_sha256": sha256(schema_bytes).hexdigest(),
            "structured_output_mode": "response_format.schema",
            "payload_json": payload_json,
            "payload_sha256": sha256(payload_json.encode("utf-8")).hexdigest(),
            "api_spend_ceiling_usd": 0.0,
        }
        body = payload_json.encode("utf-8")
        self._prepared[request.request_id] = (request, body, metadata, token_count, messages)
        return body, metadata, token_count, messages

    def request_metadata(self, request: AgentRequest) -> dict[str, Any]:
        _, metadata, _, _ = self._prepare(request)
        return dict(metadata)

    def _open(self, url: str, data: bytes | None, timeout_seconds: int, method: str) -> bytes:
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or
                parsed.port != self.config.launch["port"] or
                parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise PermissionError("llama.cpp transport refuses every endpoint except frozen local loopback")
        if self.listener_guard is not None and not self.listener_guard():
            raise PermissionError("llama.cpp listener process does not match the launched server PID")
        request = urllib.request.Request(url, data=data,
                                         headers={"Content-Type": "application/json"} if data is not None else {},
                                         method=method)
        try:
            with self.opener.open(request, timeout=timeout_seconds) as response:
                body = response.read(4_000_001)
        except urllib.error.HTTPError as exc:
            body = exc.read(4_000_001).decode("utf-8", errors="replace")
            if 500 <= exc.code <= 599:
                raise TransientTransportError(f"llama.cpp HTTP {exc.code}: {body[:1000]}",
                                              raw_response=body) from exc
            raise BackendResponseError(f"llama.cpp HTTP {exc.code}: {body[:1000]}",
                                       raw_response=body) from exc
        except (socket.timeout, TimeoutError) as exc:
            raise TimeoutBackendError(f"llama.cpp transport exceeded {timeout_seconds}s deadline") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise TimeoutBackendError(f"llama.cpp transport exceeded {timeout_seconds}s deadline") from exc
            raise TransientTransportError(f"llama.cpp local connection failure: {exc.reason}") from exc
        if len(body) > 4_000_000:
            body_text = body.decode("utf-8", errors="replace")
            raise BackendResponseError("llama.cpp response exceeded the 4 MB safety limit",
                                       raw_response=body_text)
        return body

    def _decode_response(self, body: bytes, *, expected_prompt_tokens: int,
                         latency_seconds: float) -> BackendResponse:
        try:
            raw_body = body.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raw_body = body.decode("utf-8", errors="replace")
            raise BackendResponseError(f"llama.cpp response is not valid UTF-8: {exc}", raw_body) from exc
        try:
            response = json.loads(raw_body)
            choice = response["choices"][0]
            message = choice["message"]
            content = message["content"]
            finish_reason = choice.get("finish_reason")
            usage = response["usage"]
            model = response.get("model")
            timings = response.get("timings")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise BackendResponseError(f"llama.cpp returned a malformed Chat Completions response: {exc}",
                                       raw_body) from exc
        if not isinstance(content, str):
            raise BackendResponseError("llama.cpp assistant message content must be a string", raw_body)
        if model != self.config.model_id:
            raise BackendResponseError("llama.cpp returned a different model alias; fallback is forbidden", raw_body)
        if finish_reason is not None and not isinstance(finish_reason, str):
            raise BackendResponseError("llama.cpp finish_reason must be a string", raw_body)
        if not isinstance(usage, dict):
            raise BackendResponseError("llama.cpp response is missing usage metadata", raw_body)
        token_keys = ("prompt_tokens", "completion_tokens", "total_tokens")
        if any(not isinstance(usage.get(key), int) or isinstance(usage.get(key), bool) or usage[key] < 0
               for key in token_keys):
            raise BackendResponseError("llama.cpp usage token counts are incomplete or invalid", raw_body)
        if usage["prompt_tokens"] != expected_prompt_tokens:
            raise BackendResponseError(
                f"local GGUF tokenizer count {expected_prompt_tokens} differs from server prompt_tokens "
                f"{usage['prompt_tokens']}", raw_body)
        if usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]:
            raise BackendResponseError("llama.cpp usage total does not equal prompt plus completion tokens", raw_body)
        if timings is not None and not isinstance(timings, dict):
            raise BackendResponseError("llama.cpp timings metadata must be an object when present", raw_body)
        reasoning_content = message.get("reasoning_content")
        if reasoning_content not in (None, ""):
            raise BackendResponseError("llama.cpp returned reasoning content with thinking disabled", raw_body)
        return BackendResponse(
            text=content, usage=usage, finish_reason=finish_reason, model=model, raw_body=raw_body,
            metadata={"backend": "openai-compatible-llama.cpp-local",
                      "server_build_info_expected": self.config.server_build_info,
                      "model_artifact_sha256": self.config.artifact_sha256,
                      "tokenizer_sha256": self.config.tokenizer_sha256,
                      "chat_template_sha256": self.config.chat_template_sha256,
                      "timings": timings, "latency_seconds": latency_seconds,
                      "reasoning_content_present": False})

    def _complete_impl(self, request: AgentRequest, timeout_seconds: int) -> BackendResponse:
        if timeout_seconds < 1 or timeout_seconds > self.config.timeout_seconds:
            raise ValueError("request timeout is outside the frozen llama.cpp backend deadline")
        body, _, prompt_tokens, _ = self._prepare(request)
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        started = time.perf_counter()
        response_body = self._open(url, body, timeout_seconds, "POST")
        latency = time.perf_counter() - started
        return self._decode_response(response_body, expected_prompt_tokens=prompt_tokens,
                                     latency_seconds=latency)

    def complete(self, request: AgentRequest, timeout_seconds: int) -> BackendResponse:
        if not self.config.model_calls_enabled:
            raise PermissionError("full local model calls are disabled pending separate user approval")
        with self._full_pilot_lock:
            if request.request_id in self._full_pilot_terminal_ids:
                raise RuntimeError("full-pilot logical request was already completed or exhausted")
            attempt = self._full_pilot_attempts_by_request.get(request.request_id, 0) + 1
            if attempt > self.config.max_attempts_per_request:
                self._full_pilot_terminal_ids.add(request.request_id)
                raise RuntimeError("full-pilot per-request hard attempt limit reached")
            if self._full_pilot_attempts >= self.config.max_total_attempts:
                raise RuntimeError("full-pilot total HTTP-attempt hard limit reached")
            if (request.request_id not in self._full_pilot_logical_ids and
                    len(self._full_pilot_logical_ids) >= self.config.max_logical_requests):
                raise RuntimeError("full-pilot logical-request hard limit reached")
            self._full_pilot_logical_ids.add(request.request_id)
            self._full_pilot_attempts_by_request[request.request_id] = attempt
            self._full_pilot_attempts += 1
        try:
            result = self._complete_impl(request, timeout_seconds)
        except (TimeoutBackendError, TransientTransportError):
            if attempt >= self.config.max_attempts_per_request:
                with self._full_pilot_lock:
                    self._full_pilot_terminal_ids.add(request.request_id)
            raise
        except Exception:
            with self._full_pilot_lock:
                self._full_pilot_terminal_ids.add(request.request_id)
            raise
        with self._full_pilot_lock:
            self._full_pilot_terminal_ids.add(request.request_id)
        return result

    def _preflight_call(self, budget: LlamaCppPreflightBudget, request_id: str, method: str,
                        url: str, payload: dict[str, Any] | None, *, completion: bool = False) -> bytes:
        payload_json = (json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                        if payload is not None else None)
        body = payload_json.encode("utf-8") if payload_json is not None else None
        for attempt in (1, 2):
            budget.reserve(request_id, attempt, completion=completion)
            started = time.perf_counter()
            record: dict[str, Any] = {"request_id": request_id, "attempt": attempt, "method": method,
                                      "url": url, "request_body": payload_json,
                                      "request_sha256": sha256(body).hexdigest() if body is not None else None,
                                      "completion_attempt": completion,
                                      "started_at_utc": datetime.now(timezone.utc).isoformat()}
            if completion:
                self._emit_preflight_event("completion_attempt_started", request_id=request_id, attempt=attempt)
            try:
                response_body = self._open(url, body, self.config.timeout_seconds, method)
            except (TimeoutBackendError, TransientTransportError) as exc:
                raw = getattr(exc, "raw_response", None)
                record.update({"status": "retryable_failure" if attempt < 2 else "failed",
                               "error_type": type(exc).__name__, "error": str(exc),
                               "raw_response": raw,
                               "raw_response_sha256": sha256(raw.encode("utf-8")).hexdigest() if raw else None,
                               "latency_seconds": time.perf_counter() - started})
                budget.records.append(record)
                if completion:
                    self._emit_preflight_event("completion_attempt_failed", request_id=request_id,
                                               attempt=attempt, error_type=type(exc).__name__)
                if attempt == 2:
                    raise
                continue
            except Exception as exc:
                raw = getattr(exc, "raw_response", None)
                record.update({"status": "failed", "error_type": type(exc).__name__,
                               "error": str(exc), "raw_response": raw,
                               "raw_response_sha256": sha256(raw.encode("utf-8")).hexdigest() if raw else None,
                               "latency_seconds": time.perf_counter() - started})
                budget.records.append(record)
                if completion:
                    self._emit_preflight_event("completion_attempt_failed", request_id=request_id,
                                               attempt=attempt, error_type=type(exc).__name__)
                raise
            raw_text = response_body.decode("utf-8", errors="replace")
            record.update({"status": "response_returned", "raw_response": raw_text,
                           "raw_response_sha256": sha256(response_body).hexdigest(),
                           "latency_seconds": time.perf_counter() - started})
            budget.records.append(record)
            if completion:
                self._emit_preflight_event("completion_attempt_finished", request_id=request_id,
                                           attempt=attempt, latency_seconds=record["latency_seconds"])
            return response_body
        raise AssertionError("bounded preflight retry loop fell through")

    def _emit_preflight_event(self, event: str, **details: Any) -> None:
        if self.preflight_event_hook is not None:
            self.preflight_event_hook({"event": event, "at_utc": datetime.now(timezone.utc).isoformat(),
                                       **details})

    def _run_preflight(self, budget: LlamaCppPreflightBudget,
                       probes: list[tuple[AgentRequest, str]]) -> dict[str, Any]:
        """Run six bounded local checks only when a separate preflight is enabled.

        The exact sequence is `/props`, `/apply-template`, `/tokenize`, then a
        ballot, send-message, and no-message completion. No research episode
        or monitor evidence is created by this function.
        """
        if not self.config.preflight_enabled or not self.config.preflight_approval_id:
            raise PermissionError("live local preflight requires a separate user approval ID")
        if not budget.enabled:
            raise PermissionError("live local preflight budget must be explicitly enabled")
        if (budget.max_logical_requests > self.config.preflight_max_logical_requests or
                budget.max_attempts > self.config.preflight_max_attempts or
                budget.max_completion_attempts > self.config.preflight_max_completion_attempts):
            raise ValueError("preflight budget exceeds the frozen 6/12/4 ceiling")
        expected = [("ballot", None), ("message", "send_message"), ("message", "no_message")]
        if len(probes) != 3 or [(request.action_kind, action) for request, action in probes] != expected:
            raise ValueError("preflight requires ballot, send_message, and no_message probes in frozen order")

        runtime_bundle = llama_runtime_bundle_identity(self.config.server_binary_path)
        if runtime_bundle["sha256"] != self.config.runtime_bundle_sha256:
            raise RuntimeError("local llama.cpp launcher/DLL bundle differs from the frozen runtime identity")

        root = self.config.base_url.rsplit("/v1", 1)[0]
        props_body = self._preflight_call(budget, "preflight-props", "GET", root + "/props", None)
        try:
            props = json.loads(props_body.decode("utf-8"))
            settings = props["default_generation_settings"]
            params = settings["params"]
            chat_template = props["chat_template"]
            model_path = props["model_path"]
            build_info = props["build_info"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError(f"llama.cpp /props response is malformed: {exc}") from exc
        expected_model_path = str(Path(self.config.artifact_path).resolve()).casefold()
        if str(Path(model_path).resolve()).casefold() != expected_model_path:
            raise RuntimeError("llama.cpp /props model_path differs from the frozen GGUF file")
        if self.config.server_commit not in build_info:
            raise RuntimeError("llama.cpp /props build info differs from the inspected server binary")
        if settings.get("n_ctx") != self.config.context_length or props.get("total_slots") != 1:
            raise RuntimeError("llama.cpp /props context or parallel slot count differs from the freeze")
        if sha256(chat_template.encode("utf-8")).hexdigest() != self.config.chat_template_sha256:
            raise RuntimeError("loaded llama.cpp chat template differs from embedded GGUF metadata")
        for key, value in (("temperature", self.config.temperature), ("top_p", self.config.top_p),
                           ("top_k", self.config.top_k), ("min_p", self.config.min_p)):
            actual = params.get(key)
            if not isinstance(actual, (int, float)) or not math.isclose(float(actual), float(value), abs_tol=1e-6):
                raise RuntimeError(f"llama.cpp /props {key} differs from the frozen sampling settings")
        if params.get("samplers") != list(self.config.sampler_chain):
            raise RuntimeError("llama.cpp /props sampler chain differs from the frozen setting")
        self._emit_preflight_event("server_properties_validated", model_path=model_path,
                                   build_info=build_info, context_length=settings["n_ctx"])

        ballot_messages = self._messages(probes[0][0].prompt)
        expected_render = self.token_counter.render_chat(ballot_messages, enable_thinking=False)
        apply_body = self._preflight_call(
            budget, "preflight-template", "POST", root + "/apply-template",
            {"messages": ballot_messages, "chat_template_kwargs": {"enable_thinking": False}})
        try:
            server_render = json.loads(apply_body.decode("utf-8"))["prompt"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError(f"llama.cpp /apply-template response is malformed: {exc}") from exc
        if server_render != expected_render:
            raise RuntimeError("local GGUF Jinja renderer differs from llama.cpp /apply-template output")

        token_ids_local = self.token_counter.encode_chat(ballot_messages, enable_thinking=False)
        tokenize_body = self._preflight_call(
            budget, "preflight-tokenize", "POST", root + "/tokenize",
            {"content": server_render,
             "add_special": self.tokenizer_metadata.get("add_bos_token", False),
             "parse_special": True, "with_pieces": False})
        try:
            token_ids_server = json.loads(tokenize_body.decode("utf-8"))["tokens"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError(f"llama.cpp /tokenize response is malformed: {exc}") from exc
        if token_ids_server != token_ids_local:
            raise RuntimeError("local GGUF tokenizer IDs differ from llama.cpp /tokenize")
        self._emit_preflight_event("tokenizer_parity_validated", token_count=len(token_ids_local))

        actual_actions: list[str] = []
        for index, (request, expected_action) in enumerate(probes):
            body, _, prompt_tokens, _ = self._prepare(request)
            url = self.config.base_url.rstrip("/") + "/chat/completions"
            raw = self._preflight_call(budget, f"preflight-completion-{index + 1}", "POST", url,
                                       json.loads(body.decode("utf-8")), completion=True)
            response = self._decode_response(raw, expected_prompt_tokens=prompt_tokens,
                                             latency_seconds=budget.records[-1]["latency_seconds"])
            try:
                action = _parse_action(response.text, request.action_kind)
            except Exception as exc:
                budget.records.append({"request_id": f"preflight-parse-{index + 1}",
                                       "status": "failed", "error": str(exc),
                                       "raw_response": response.text,
                                       "raw_response_sha256": sha256(response.text.encode("utf-8")).hexdigest()})
                raise RuntimeError(f"preflight action failed the frozen strict parser: {exc}") from exc
            actual = action["type"]
            expected_type = "ballot" if expected_action is None else expected_action
            if actual != expected_type:
                budget.records.append({"request_id": f"preflight-action-{index + 1}",
                                       "status": "failed", "expected_action": expected_type,
                                       "actual_action": actual, "raw_response": response.text,
                                       "raw_response_sha256": sha256(response.text.encode("utf-8")).hexdigest()})
                raise RuntimeError(f"preflight expected {expected_type}, received {actual}")
            actual_actions.append(actual)

        if len(budget.logical_ids) > 6 or budget.attempts > 12 or budget.completion_attempts > 4:
            raise AssertionError("preflight hard ceiling was exceeded")
        return {
            "status": "PASS",
            "approval_id": self.config.preflight_approval_id,
            "logical_requests": len(budget.logical_ids),
            "http_attempts": budget.attempts,
            "model_completion_attempts": budget.completion_attempts,
            "verified_model_path": model_path,
            "verified_runtime_bundle_sha256": runtime_bundle["sha256"],
            "verified_server_build_info": build_info,
            "verified_context_length": settings["n_ctx"],
            "verified_parallel_slots": props["total_slots"],
            "verified_chat_template_sha256": self.config.chat_template_sha256,
            "verified_tokenizer_ids": len(token_ids_local),
            "verified_actions": actual_actions,
            "records": budget.records,
        }

    def preflight(self, budget: LlamaCppPreflightBudget,
                  probes: list[tuple[AgentRequest, str]]) -> dict[str, Any]:
        """Wrap preflight verification failures with a retained raw-evidence row."""
        record_count = len(budget.records)
        try:
            return self._run_preflight(budget, probes)
        except Exception as exc:
            new_records = budget.records[record_count:]
            if new_records and new_records[-1].get("status") == "response_returned":
                prior = new_records[-1]
                raw = prior.get("raw_response")
                budget.records.append({
                    "request_id": f"{prior.get('request_id')}-validation",
                    "attempt": None,
                    "status": "failed",
                    "phase": "client_side_preflight_validation",
                    "after_request_id": prior.get("request_id"),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "raw_response": raw,
                    "raw_response_sha256": sha256(raw.encode("utf-8")).hexdigest() if raw else None,
                })
            elif not new_records:
                budget.records.append({
                    "request_id": "preflight-gate-validation",
                    "attempt": None,
                    "status": "failed",
                    "phase": "preflight_gate_before_http",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "raw_response": None,
                    "raw_response_sha256": None,
                })
            raise
