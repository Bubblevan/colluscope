"""Narrow runtime compatibility fixes for the pinned Colosseum local runner.

This module is deliberately an opt-in monkey patch. It does not alter the
upstream checkout and it never turns a malformed tool call into a successful
tool execution.
"""
from __future__ import annotations

import json
from typing import Any


class CompatibilityProtocolError(RuntimeError):
    """The model/runtime exchange cannot be interpreted as a valid action."""


def _tool_calls(response: Any) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        raise CompatibilityProtocolError("completion response is not an object")
    choices = response.get("choices") or []
    if not choices:
        return []
    if not isinstance(choices, list) or not isinstance(choices[0], dict):
        raise CompatibilityProtocolError("completion choices are malformed")
    message = choices[0].get("message") or {}
    if not isinstance(message, dict):
        raise CompatibilityProtocolError("completion message is malformed")
    calls = message.get("tool_calls") or []
    if not isinstance(calls, list):
        raise CompatibilityProtocolError("tool_calls must be a list")
    parsed: list[dict[str, Any]] = []
    for index, call in enumerate(calls):
        if not isinstance(call, dict):
            raise CompatibilityProtocolError(f"tool call {index} is not an object")
        function = call.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("name"), str) or not function["name"]:
            raise CompatibilityProtocolError(f"tool call {index} has no function name")
        if "arguments" not in function:
            raise CompatibilityProtocolError(f"tool call {index} has no arguments field")
        raw = function["arguments"]
        # The pinned TogetherClient calls json.loads(arguments_raw). Accepting
        # an already-decoded object here would pass validation and then fail
        # inside the upstream processor (which expects the OpenAI wire type).
        if not isinstance(raw, str):
            raise CompatibilityProtocolError(
                f"tool call {index} arguments must be a JSON string"
            )
        try:
            arguments = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CompatibilityProtocolError(
                f"tool call {index} arguments are not valid JSON"
            ) from exc
        if not isinstance(arguments, dict):
            raise CompatibilityProtocolError(f"tool call {index} arguments must decode to an object")
        parsed.append({"name": function["name"], "arguments": arguments})
    return parsed


async def strict_process_tool_calls(client: Any, response: dict[str, Any], context: list[dict[str, Any]], callback: Any):
    """Prevalidate every call before the upstream client can invoke any tool."""
    calls = _tool_calls(response)
    before = len(context)
    result = client._colluscope_original_process_tool_calls(response, context, callback)
    if hasattr(result, "__await__"):
        result = await result
    if not isinstance(result, tuple) or len(result) != 3:
        raise CompatibilityProtocolError("upstream tool processor returned an invalid result")
    processed_context = result[1]
    if not isinstance(processed_context, list):
        raise CompatibilityProtocolError("upstream tool processor returned an invalid context")
    executed_count = result[0]
    if not isinstance(executed_count, int) or isinstance(executed_count, bool) or executed_count != len(calls):
        raise CompatibilityProtocolError("upstream tool processor returned an inconsistent execution count")
    # TogetherClient serializes callback results into tool-role messages. An
    # upstream tool error is not a valid action and must terminate the episode.
    for item in processed_context[before:]:
        if not isinstance(item, dict) or item.get("role") != "tool":
            continue
        content = item.get("content")
        try:
            decoded = json.loads(content) if isinstance(content, str) else content
        except json.JSONDecodeError as exc:
            raise CompatibilityProtocolError("tool callback returned malformed JSON") from exc
        if _tool_result_rejected(decoded):
            raise CompatibilityProtocolError("environment rejected a tool call")
    return result


def _tool_result_rejected(value: Any) -> bool:
    """Recognize explicit upstream tool refusal shapes without guessing intent."""
    if isinstance(value, dict):
        if "error" in value or str(value.get("status", "")).lower() in {
            "error", "rejected", "invalid",
        }:
            return True
        return any(_tool_result_rejected(child) for child in value.values())
    if isinstance(value, list):
        return any(_tool_result_rejected(child) for child in value)
    return False


def _finish_reason(response: dict[str, Any]) -> str | None:
    choices = response.get("choices") or []
    if choices and isinstance(choices[0], dict):
        value = choices[0].get("finish_reason")
        return str(value) if value is not None else None
    return None


def _validate_finish_reason(response: dict[str, Any]) -> str | None:
    reason = _finish_reason(response)
    if reason is None:
        return "missing_finish_reason"
    if reason in {"length", "content_filter"}:
        return f"nonterminal_finish_reason:{reason}"
    calls = _tool_calls(response)
    if reason == "tool_calls" and not calls:
        return "tool_call_finish_reason_without_tool_calls"
    if reason != "tool_calls" and calls:
        return f"tool_calls_with_inconsistent_finish_reason:{reason}"
    return None


def require_valid_turn(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("protocol_error"):
        raise CompatibilityProtocolError(str(result["protocol_error"]))
    return result


async def compatible_multi_step_response_generation(self: Any, system_prompt: str, user_prompt: str):
    """Use a valid terminal assistant response instead of requesting a 400.

    A planning response without a tool call is an explicit no-message outcome.
    An execution response without a committed environment tool remains an
    explicit protocol error; the communication wrapper raises it at episode
    scope. Errors during continuation are raised, never converted into a
    successful partial turn.
    """
    from terrarium.async_utils import run_blocking

    if self.current_phase is None:
        raise CompatibilityProtocolError("agent phase was not initialized")
    env_tools = self.toolset_discovery.get_tools_for_environment(self.environment_name, self.current_phase)
    blackboard_tools = self.toolset_discovery.get_tools_for_blackboard(self.current_phase)
    params = self._build_generation_params(tool_set=env_tools + blackboard_tools)
    context = self.client.init_context(system_prompt, user_prompt)
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    response, response_str = await run_blocking(self.client.generate_response, input=context, params=params)
    total_usage = self.client.get_usage(response, total_usage)
    current_response = response
    conversation_steps = 1
    total_tools_executed = 0
    trajectory: dict[str, Any] = {"step_1": {"reasoning": response_str}}
    terminal_reason = "max_conversation_steps"
    committed = False

    for step in range(self.max_conversation_steps):
        self._env_state_committed = False
        finish_error = _validate_finish_reason(current_response)
        if finish_error:
            raise CompatibilityProtocolError(finish_error)
        tool_calls_executed, context, step_tools = await self.client.process_tool_calls(
            current_response, context, self._execute_tool_call
        )
        total_tools_executed += tool_calls_executed
        if step_tools:
            trajectory.setdefault(f"step_{step + 1}", {})["tools"] = step_tools
        if self._env_state_committed:
            terminal_reason = "environment_action_committed"
            committed = True
            break
        if not step_tools:
            terminal_reason = "no_tool_call"
            break
        if step >= self.max_conversation_steps - 1:
            break
        # A continuation failure is an episode failure. Do not return a result
        # object that the caller could mistake for a valid partial turn.
        response, response_str = await run_blocking(
            self.client.generate_response, input=context, params=params
        )
        total_usage = self.client.get_usage(response, total_usage)
        current_response = response
        conversation_steps += 1
        trajectory[f"step_{conversation_steps}"] = {"reasoning": response_str}

    self._log_trajectory(trajectory)
    result = {
        "response": response_str,
        "full_content": response_str,
        "usage": total_usage,
        "model": getattr(current_response, "model", None) or self.model_name,
        "tool_calls": None,
        "has_tool_calls": total_tools_executed > 0,
        "manual_tool_execution": True,
        "tools_executed": total_tools_executed,
        "conversation_steps": conversation_steps,
        "termination_reason": terminal_reason,
        "finish_reason": _finish_reason(current_response),
    }
    if self.current_phase == "execution" and not committed:
        result["protocol_error"] = "execution_without_committed_environment_action"
    return result


def install_colosseum_compat(upstream_root: str | None = None) -> dict[str, str]:
    """Install the adapter against the already imported pinned upstream modules."""
    import hashlib
    import inspect
    import sys
    from pathlib import Path

    root = str(Path(upstream_root).resolve()) if upstream_root else None
    if root and root not in sys.path:
        sys.path.insert(0, root)
    from llm_server.clients.together_client import TogetherClient
    from terrarium.agents.base import BaseAgent
    from experiments.common.local_protocol import LocalCommunicationProtocol

    if not hasattr(TogetherClient, "_colluscope_original_process_tool_calls"):
        TogetherClient._colluscope_original_process_tool_calls = TogetherClient.process_tool_calls
        async def wrapped_process(self, response, context, callback):
            return await strict_process_tool_calls(self, response, context, callback)
        TogetherClient.process_tool_calls = wrapped_process
    BaseAgent._multi_step_response_generation = compatible_multi_step_response_generation

    original_execution_turn = LocalCommunicationProtocol.agent_execution_turn
    if not getattr(original_execution_turn, "_colluscope_wrapped", False):
        async def checked_execution_turn(self, *args, **kwargs):
            result = await original_execution_turn(self, *args, **kwargs)
            return require_valid_turn(result)
        checked_execution_turn._colluscope_wrapped = True
        LocalCommunicationProtocol.agent_execution_turn = checked_execution_turn

    original_planning_turn = LocalCommunicationProtocol.agent_planning_turn
    if not getattr(original_planning_turn, "_colluscope_wrapped", False):
        async def checked_planning_turn(self, *args, **kwargs):
            result = await original_planning_turn(self, *args, **kwargs)
            return require_valid_turn(result)
        checked_planning_turn._colluscope_wrapped = True
        LocalCommunicationProtocol.agent_planning_turn = checked_planning_turn

    files = {
        "BaseAgent": inspect.getfile(BaseAgent),
        "TogetherClient": inspect.getfile(TogetherClient),
        "LocalCommunicationProtocol": inspect.getfile(LocalCommunicationProtocol),
    }
    return {name: hashlib.sha256(Path(path).read_bytes()).hexdigest().upper() for name, path in files.items()}
