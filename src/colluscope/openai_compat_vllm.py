"""Local-only OpenAI-compatible vLLM adapter, disabled until explicit approval.

No provider SDK, credential lookup, environment proxy, remote endpoint, model
fallback, or streaming path is used. Real requests must pass through the shared
RequestAdapter so its logical/physical request ceilings are enforced.
"""

from __future__ import annotations

import ipaddress
import json
import math
import socket
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

from .m1_runtime import (AgentRequest, BackendResponse, RuntimeConfig, TimeoutBackendError,
                         TransientTransportError)

ROOT = Path(__file__).resolve().parents[2]
ACTION_SCHEMA_ROOT = ROOT / "prompts" / "m1-p0-v2"


class ChatTokenCounter(Protocol):
    tokenizer_id: str
    tokenizer_revision: str
    tokenizer_sha256: str
    chat_template_sha256: str

    def count_chat_tokens(self, messages: list[dict[str, str]]) -> int: ...


class BackendResponseError(RuntimeError):
    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


@dataclass(frozen=True)
class VLLMBackendConfig:
    model_calls_enabled: bool
    max_api_spend_usd: float
    base_url: str
    model_id: str
    model_revision: str
    server_version: str
    tokenizer_id: str
    tokenizer_revision: str
    tokenizer_sha256: str
    chat_template_sha256: str
    context_length: int
    input_budget_tokens: int
    thinking_mode: str
    thinking_mode_parameter: str
    temperature: float
    top_p: float
    top_k: int
    message_max_output_tokens: int
    ballot_max_output_tokens: int
    timeout_seconds: int
    max_attempts_per_request: int
    max_logical_requests: int
    max_total_attempts: int

    @property
    def sampling(self) -> dict[str, Any]:
        return {"temperature": self.temperature, "top_p": self.top_p, "top_k": self.top_k}

    def output_limit(self, action_kind: str) -> int:
        if action_kind == "message":
            return self.message_max_output_tokens
        if action_kind == "ballot":
            return self.ballot_max_output_tokens
        raise ValueError("action_kind must be message or ballot")

    def bind_runtime(self, base_config: RuntimeConfig) -> RuntimeConfig:
        """Bind approved model settings to the v2 task without changing treatments."""
        _validate_config(self)
        if base_config.raw.get("prompt_version") != "m1-p0-frozen-v2":
            raise ValueError("the real backend can bind only to the explicitly versioned v2 protocol")
        raw = {**base_config.raw, "model_calls_enabled": True,
               "model": {"runtime": "openai-compatible-vllm-local", "model_id": self.model_id,
                         "external_enabled": False}, "sampling": self.sampling,
               "limits": {"timeout_seconds": self.timeout_seconds,
                          "max_attempts_per_request": self.max_attempts_per_request,
                          "max_logical_requests": self.max_logical_requests,
                          "max_total_attempts": self.max_total_attempts}}
        return replace(base_config, raw=raw, model_id=self.model_id, runtime="openai-compatible-vllm-local",
                       sampling=self.sampling, timeout_seconds=self.timeout_seconds,
                       max_attempts_per_request=self.max_attempts_per_request,
                       max_logical_requests=self.max_logical_requests,
                       max_total_attempts=self.max_total_attempts)


def load_vllm_backend_config(path: Path) -> VLLMBackendConfig:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    if raw.get("model_calls_enabled") is not True:
        raise PermissionError("real model calls are disabled; this template is not an execution approval")
    if raw.get("max_api_spend_usd") != 0.0:
        raise ValueError("local vLLM adapter requires a $0.00 API spend ceiling")
    if set(raw) != {"model_calls_enabled", "max_api_spend_usd", "backend", "thinking", "sampling",
                    "stage_limits", "limits"}:
        raise ValueError("vLLM config has missing or unknown top-level keys")
    backend, thinking, sampling = raw["backend"], raw["thinking"], raw["sampling"]
    stage_limits, limits = raw["stage_limits"], raw["limits"]
    if set(backend) != {"kind", "base_url", "model_id", "model_revision", "server_version",
                        "tokenizer_id", "tokenizer_revision", "tokenizer_sha256",
                        "chat_template_sha256", "context_length"}:
        raise ValueError("vLLM backend identity is incomplete or has unknown keys")
    if backend["kind"] != "openai-compatible-vllm":
        raise ValueError("only the local OpenAI-compatible vLLM backend is supported")
    if set(sampling) != {"temperature", "top_p", "top_k", "input_budget_tokens"}:
        raise ValueError("sampling settings must be explicit and complete")
    if set(stage_limits) != {"message_max_output_tokens", "ballot_max_output_tokens"}:
        raise ValueError("message and ballot output-token limits must be frozen separately")
    if set(thinking) != {"mode", "request_parameter"}:
        raise ValueError("thinking mode and its vLLM request field must be explicit")
    if set(limits) != {"timeout_seconds", "max_attempts_per_request", "max_logical_requests",
                       "max_total_attempts", "comprehension_probe_calls"}:
        raise ValueError("call limits must be explicit and complete")
    if limits["comprehension_probe_calls"] != 0:
        raise ValueError("comprehension probes are outside the frozen M1-P0 call graph")
    config = VLLMBackendConfig(
        model_calls_enabled=True, max_api_spend_usd=0.0, base_url=backend["base_url"],
        model_id=backend["model_id"], model_revision=backend["model_revision"],
        server_version=backend["server_version"], tokenizer_id=backend["tokenizer_id"],
        tokenizer_revision=backend["tokenizer_revision"], tokenizer_sha256=backend["tokenizer_sha256"],
        chat_template_sha256=backend["chat_template_sha256"], context_length=backend["context_length"],
        input_budget_tokens=sampling["input_budget_tokens"],
        thinking_mode=thinking["mode"], thinking_mode_parameter=thinking["request_parameter"],
        temperature=sampling["temperature"], top_p=sampling["top_p"], top_k=sampling["top_k"],
        message_max_output_tokens=stage_limits["message_max_output_tokens"],
        ballot_max_output_tokens=stage_limits["ballot_max_output_tokens"],
        timeout_seconds=limits["timeout_seconds"],
        max_attempts_per_request=limits["max_attempts_per_request"],
        max_logical_requests=limits["max_logical_requests"], max_total_attempts=limits["max_total_attempts"])
    _validate_config(config)
    return config


def _validate_config(config: VLLMBackendConfig) -> None:
    parsed = urllib.parse.urlsplit(config.base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("base_url must be an unauthenticated HTTP(S) URL on loopback")
    if parsed.path.rstrip("/") != "/v1" or parsed.query or parsed.fragment:
        raise ValueError("base_url must end exactly in /v1 and contain no query or fragment")
    hostname = parsed.hostname.lower()
    try:
        loopback = ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        loopback = hostname == "localhost"
    if not loopback:
        raise ValueError("remote endpoints are forbidden; use a local loopback vLLM server")
    if not config.model_calls_enabled:
        raise PermissionError("real model calls are disabled")
    if config.max_api_spend_usd != 0.0:
        raise ValueError("local vLLM adapter requires a $0.00 API spend ceiling")
    if config.thinking_mode not in {"disabled", "enabled"}:
        raise ValueError("thinking_mode must be explicitly set to disabled or enabled")
    if config.thinking_mode_parameter != "chat_template_kwargs.enable_thinking":
        raise ValueError("vLLM thinking mode must use chat_template_kwargs.enable_thinking")
    if (not config.model_id or config.model_id == "FILL_AFTER_APPROVAL" or
            not config.server_version or config.server_version == "FILL_AFTER_APPROVAL" or
            not config.tokenizer_id or config.tokenizer_id == "FILL_AFTER_APPROVAL"):
        raise ValueError("model, server, and tokenizer identities must be fixed before execution")
    if (not isinstance(config.model_revision, str) or len(config.model_revision) != 40 or
            any(ch not in "0123456789abcdef" for ch in config.model_revision.lower()) or
            not isinstance(config.tokenizer_revision, str) or len(config.tokenizer_revision) != 40 or
            any(ch not in "0123456789abcdef" for ch in config.tokenizer_revision.lower())):
        raise ValueError("model and tokenizer revisions must be immutable 40-character commit IDs")
    for digest in (config.tokenizer_sha256, config.chat_template_sha256):
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest.lower()):
            raise ValueError("tokenizer and chat-template SHA256 values must be exact 64-character digests")
    if not isinstance(config.context_length, int) or isinstance(config.context_length, bool) or config.context_length < 1:
        raise ValueError("model context length must be a positive integer")
    if (not isinstance(config.input_budget_tokens, int) or isinstance(config.input_budget_tokens, bool) or
            config.input_budget_tokens < 1):
        raise ValueError("input token budget must be a positive integer")
    if (isinstance(config.temperature, bool) or not isinstance(config.temperature, (int, float)) or
            not math.isfinite(config.temperature) or config.temperature < 0):
        raise ValueError("temperature must be a finite non-negative number")
    if (isinstance(config.top_p, bool) or not isinstance(config.top_p, (int, float)) or
            not math.isfinite(config.top_p) or not 0 < config.top_p <= 1):
        raise ValueError("top_p must be a finite value in (0, 1]")
    if not isinstance(config.top_k, int) or isinstance(config.top_k, bool) or config.top_k < 1:
        raise ValueError("top_k must be a positive integer")
    for stage_limit in (config.message_max_output_tokens, config.ballot_max_output_tokens):
        if (not isinstance(stage_limit, int) or isinstance(stage_limit, bool) or
                not 1 <= stage_limit < config.context_length):
            raise ValueError("stage output token limits must be positive and below the context length")
    if config.input_budget_tokens + max(config.message_max_output_tokens,
                                        config.ballot_max_output_tokens) > config.context_length:
        raise ValueError("input budget plus largest stage output exceeds the frozen model context")
    if not isinstance(config.timeout_seconds, int) or isinstance(config.timeout_seconds, bool) or config.timeout_seconds < 1:
        raise ValueError("transport timeout must be positive")
    if not isinstance(config.max_attempts_per_request, int) or config.max_attempts_per_request != 2:
        raise ValueError("M1-P0 freezes at most two attempts per logical request")
    if (not isinstance(config.max_logical_requests, int) or isinstance(config.max_logical_requests, bool) or
            not 1 <= config.max_logical_requests <= 95):
        raise ValueError("logical-request ceiling cannot exceed the frozen 95-call graph")
    if (not isinstance(config.max_total_attempts, int) or isinstance(config.max_total_attempts, bool) or
            not 1 <= config.max_total_attempts <= min(190, 2 * config.max_logical_requests)):
        raise ValueError("physical-attempt ceiling cannot exceed the frozen 190-attempt cap")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class EngineeringPreflightBudget:
    """Separate opt-in ceiling for server metadata and schema probes.

    Constructing the default budget does not authorize network use. Callers
    must explicitly set enabled=True; the shipped draft leaves it disabled.
    """
    enabled: bool = False
    max_logical_requests: int = 6
    max_attempts: int = 12
    logical_ids: set[str] = field(default_factory=set)
    attempts_by_request: dict[str, int] = field(default_factory=dict)
    attempts: int = 0

    def __post_init__(self):
        if not 1 <= self.max_logical_requests <= 6 or not 1 <= self.max_attempts <= 12:
            raise ValueError("engineering preflight ceiling cannot exceed 6 logical / 12 attempts")

    def reserve(self, request_id: str, attempt: int = 1) -> None:
        if not self.enabled:
            raise PermissionError("engineering preflight budget is disabled")
        expected = self.attempts_by_request.get(request_id, 0) + 1
        if attempt != expected or not 1 <= attempt <= 2:
            raise ValueError("preflight attempt sequence exceeds the two-attempt bound")
        if request_id not in self.logical_ids and len(self.logical_ids) >= self.max_logical_requests:
            raise RuntimeError("engineering preflight logical-request ceiling reached")
        if self.attempts >= self.max_attempts:
            raise RuntimeError("engineering preflight attempt ceiling reached")
        self.logical_ids.add(request_id)
        self.attempts_by_request[request_id] = attempt
        self.attempts += 1


class LocalVLLMBackend:
    """Strict loopback-only vLLM chat-completions backend.

    ``token_counter`` must use the configured immutable tokenizer and chat
    template. A matching token count plus max output tokens must fit the
    configured context before any HTTP request is sent.
    """

    def __init__(self, config: VLLMBackendConfig, token_counter: ChatTokenCounter,
                 opener: Any | None = None):
        _validate_config(config)
        self.config = config
        self.token_counter = token_counter
        if (token_counter.tokenizer_id != config.tokenizer_id or
                token_counter.tokenizer_revision != config.tokenizer_revision or
                token_counter.tokenizer_sha256 != config.tokenizer_sha256 or
                token_counter.chat_template_sha256 != config.chat_template_sha256):
            raise ValueError("token counter identity/hash differs from the frozen backend config")
        self.opener = opener or urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect())
        self._prepared: dict[str, tuple[AgentRequest, bytes, dict[str, Any]]] = {}

    def _messages(self, prompt: str) -> list[dict[str, str]]:
        if "\n\n" not in prompt:
            raise ValueError("rendered prompt lacks the frozen system/user boundary")
        system, user = prompt.split("\n\n", 1)
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _payload(self, request: AgentRequest) -> tuple[dict[str, Any], int, bytes]:
        if request.model_id != self.config.model_id:
            raise ValueError("request model ID differs from the approved backend model ID")
        if request.sampling != self.config.sampling:
            raise ValueError("request sampling differs from the approved backend sampling")
        if request.timeout_seconds > self.config.timeout_seconds:
            raise ValueError("request timeout exceeds the approved transport timeout")
        messages = self._messages(request.prompt)
        token_count = self.token_counter.count_chat_tokens(messages)
        if not isinstance(token_count, int) or isinstance(token_count, bool) or token_count < 0:
            raise ValueError("token counter returned an invalid prompt length")
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
            raise ValueError("rendered v2 prompt does not contain the exact API action schema")
        schema = json.loads(schema_text)
        schema_name = "m1_p0_communication_action" if request.action_kind == "message" else "m1_p0_ballot_action"
        payload = {"model": self.config.model_id, "messages": messages,
                   "temperature": self.config.temperature, "top_p": self.config.top_p,
                   "top_k": self.config.top_k, "seed": request.generation_seed,
                   "max_tokens": output_tokens, "stream": False,
                   "response_format": {"type": "json_schema", "json_schema": {
                       "name": schema_name, "schema": schema}},
                   "chat_template_kwargs": {
                       "enable_thinking": self.config.thinking_mode == "enabled"}}
        return payload, token_count, schema_bytes

    def _prepare(self, request: AgentRequest) -> tuple[bytes, dict[str, Any]]:
        cached = self._prepared.get(request.request_id)
        if cached is not None and cached[0] == request:
            return cached[1], cached[2]
        payload, prompt_tokens, schema_bytes = self._payload(request)
        payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        metadata = {
            "backend": "openai-compatible-vllm-local",
            "endpoint": self.config.base_url.rstrip("/") + "/chat/completions",
            "method": "POST", "role_mapping": ["system", "user"],
            "model_id": self.config.model_id, "model_revision": self.config.model_revision,
            "server_version_expected": self.config.server_version,
            "tokenizer_id": self.config.tokenizer_id,
            "tokenizer_revision": self.config.tokenizer_revision,
            "tokenizer_sha256": self.config.tokenizer_sha256,
            "chat_template_sha256": self.config.chat_template_sha256,
            "context_length": self.config.context_length, "input_budget_tokens": self.config.input_budget_tokens,
            "prompt_tokens": prompt_tokens,
            "thinking_mode": self.config.thinking_mode,
            "thinking_mode_parameter": self.config.thinking_mode_parameter,
            "action_kind": request.action_kind, "max_output_tokens": self.config.output_limit(request.action_kind),
            "generation_seed": request.generation_seed,
            "action_schema_sha256": sha256(schema_bytes).hexdigest(),
            "structured_output_mode": "response_format.json_schema",
            "payload_json": payload_json,
            "payload_sha256": sha256(payload_json.encode("utf-8")).hexdigest(),
            "api_spend_ceiling_usd": 0.0,
        }
        body = payload_json.encode("utf-8")
        self._prepared[request.request_id] = (request, body, metadata)
        return body, metadata

    def request_metadata(self, request: AgentRequest) -> dict[str, Any]:
        _, metadata = self._prepare(request)
        return dict(metadata)

    def _open(self, url: str, data: bytes | None, timeout_seconds: int) -> bytes:
        request = urllib.request.Request(url, data=data,
                                         headers={"Content-Type": "application/json"} if data is not None else {},
                                         method="POST" if data is not None else "GET")
        try:
            with self.opener.open(request, timeout=timeout_seconds) as response:
                body = response.read(4_000_001)
        except urllib.error.HTTPError as exc:
            body = exc.read(4_000_001).decode("utf-8", errors="replace")
            if 500 <= exc.code <= 599:
                raise TransientTransportError(f"vLLM HTTP {exc.code}: {body[:1000]}", raw_response=body) from exc
            raise BackendResponseError(f"vLLM HTTP {exc.code}: {body[:1000]}", raw_response=body) from exc
        except (socket.timeout, TimeoutError) as exc:
            raise TimeoutBackendError(f"vLLM transport exceeded {timeout_seconds}s deadline") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise TimeoutBackendError(f"vLLM transport exceeded {timeout_seconds}s deadline") from exc
            raise TransientTransportError(f"vLLM local connection failure: {exc.reason}") from exc
        if len(body) > 4_000_000:
            body_text = body.decode("utf-8", errors="replace")
            raise BackendResponseError("vLLM response exceeded the 4 MB safety limit",
                                       raw_response=body_text)
        return body

    def complete(self, request: AgentRequest, timeout_seconds: int) -> BackendResponse:
        if timeout_seconds < 1 or timeout_seconds > self.config.timeout_seconds:
            raise ValueError("request timeout is outside the frozen backend deadline")
        body, _ = self._prepare(request)
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        body_bytes = self._open(url, body, timeout_seconds)
        try:
            raw_body = body_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raw_body = body_bytes.decode("utf-8", errors="replace")
            raise BackendResponseError(f"vLLM response is not valid UTF-8: {exc}",
                                       raw_response=raw_body) from exc
        try:
            response = json.loads(raw_body)
            choice = response["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
            usage = response.get("usage")
            model = response.get("model")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise BackendResponseError(f"vLLM returned a malformed Chat Completions response: {exc}",
                                       raw_response=raw_body) from exc
        if not isinstance(content, str):
            raise BackendResponseError("vLLM assistant message content must be a string", raw_body)
        if model != self.config.model_id:
            raise BackendResponseError("vLLM returned a different model ID; model fallback is forbidden", raw_body)
        if finish_reason is not None and not isinstance(finish_reason, str):
            raise BackendResponseError("vLLM finish_reason must be a string when present", raw_body)
        if usage is not None and not isinstance(usage, dict):
            raise BackendResponseError("vLLM usage metadata must be an object when present", raw_body)
        return BackendResponse(text=content, usage=usage, finish_reason=finish_reason, model=model,
                               raw_body=raw_body,
                               metadata={"backend": "openai-compatible-vllm-local",
                                         "server_version_expected": self.config.server_version,
                                         "model_revision_configured": self.config.model_revision})

    def preflight(self, budget: EngineeringPreflightBudget) -> dict[str, Any]:
        """Explicit bounded engineering check; never called automatically."""
        budget.reserve("preflight-vllm-version")
        root = self.config.base_url.rsplit("/v1", 1)[0]
        version_body = self._open(root + "/version", None, self.config.timeout_seconds)
        budget.reserve("preflight-vllm-models")
        models_body = self._open(self.config.base_url.rstrip("/") + "/models", None,
                                 self.config.timeout_seconds)
        try:
            version = json.loads(version_body.decode("utf-8"))["version"]
            models = json.loads(models_body.decode("utf-8"))["data"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError(f"vLLM preflight metadata response is malformed: {exc}") from exc
        model_ids = [row.get("id") for row in models if isinstance(row, dict)]
        if version != self.config.server_version:
            raise ValueError("local vLLM server version differs from the frozen config")
        if self.config.model_id not in model_ids:
            raise ValueError("configured model ID is not listed by the local vLLM server")
        return {"server_version": version, "model_ids": model_ids,
                "model_revision_verification": "configured immutable revision is not attested by OpenAI-compatible metadata",
                "preflight_logical_requests": len(budget.logical_ids),
                "preflight_attempts": budget.attempts,
                "external_api_calls": 0, "model_completion_calls": 0}
