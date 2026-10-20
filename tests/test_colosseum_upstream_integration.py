"""Offline integration tests against the pinned upstream call path."""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "reference" / "colosseum"
VENV_SITE = UPSTREAM / ".venv" / "Lib" / "site-packages"
if VENV_SITE.exists():
    sys.path.insert(0, str(VENV_SITE))
if str(UPSTREAM) not in sys.path:
    sys.path.insert(0, str(UPSTREAM))

COMPAT_PATH = ROOT / "reproductions" / "colosseum_local" / "runtime_compat.py"
spec = importlib.util.spec_from_file_location("colluscope_upstream_compat_integration", COMPAT_PATH)
compat = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = compat
assert spec.loader is not None
spec.loader.exec_module(compat)

from llm_server.clients.together_client import TogetherClient  # noqa: E402
from terrarium.agents.base import BaseAgent  # noqa: E402
from experiments.common.local_protocol import LocalCommunicationProtocol  # noqa: E402

compat.install_colosseum_compat(str(UPSTREAM))


def run_async(coroutine):
    import terrarium.async_utils as async_utils

    original = async_utils.run_blocking

    async def immediate(function, /, *args, **kwargs):
        return function(*args, **kwargs)

    async_utils.run_blocking = immediate
    try:
        while True:
            try:
                coroutine.send(None)
            except StopIteration as finished:
                return finished.value
            raise AssertionError("mock integration unexpectedly yielded; no scheduling/network is permitted")
    finally:
        async_utils.run_blocking = original


class Discovery:
    def __init__(self, phase: str):
        self.phase = phase

    def get_tools_for_environment(self, environment, phase):
        if phase == "execution":
            return [{"type": "function", "function": {"name": "assign_task"}}]
        return []

    def get_tools_for_blackboard(self, phase):
        return []

    def get_env_tool_names(self, environment):
        return {"assign_task"}

    def get_blackboard_tool_names(self):
        return {"post_message"}


class UpstreamCallPathTests(unittest.TestCase):
    def make_agent(self, phase: str, responses, environment_result=None):
        agent = object.__new__(BaseAgent)
        agent.current_phase = phase
        agent.current_agent_name = "Agent-A"
        agent.current_iteration = 1
        agent.current_round = 1
        agent.environment_name = "JiraTicketEnvironment"
        agent.toolset_discovery = Discovery(phase)
        agent.communication_protocol = SimpleNamespace()

        async def environment_handle(*args, **kwargs):
            return environment_result if environment_result is not None else {
                "status": "success", "result": {"state_updates": {"assigned": True}}
            }

        async def blackboard_handle(*args, **kwargs):
            return {"status": "success", "message_id": "mock-message"}

        agent.communication_protocol.environment_handle_tool_call = environment_handle
        agent.communication_protocol.blackboard_handle_tool_call = blackboard_handle
        agent._log_tool_call = lambda *args, **kwargs: None
        agent._log_trajectory = lambda *args, **kwargs: None
        agent._build_generation_params = lambda **kwargs: {}
        agent.model_name = "mock-only"
        agent.max_conversation_steps = 3
        agent._env_state_committed = False

        client = object.__new__(TogetherClient)
        client.generate_response = self.sequence(*responses)
        agent.client = client
        return agent

    @staticmethod
    def sequence(*responses):
        calls = iter(responses)

        def generate_response(*, input, params):
            item = next(calls)
            if isinstance(item, BaseException):
                raise item
            return item, item["choices"][0].get("message", {}).get("content", "")
        return generate_response

    @staticmethod
    def response(content="", *, finish="stop", tool_calls=None):
        message = {"role": "assistant", "content": content}
        if tool_calls is not None:
            message["tool_calls"] = tool_calls
        return {"choices": [{"finish_reason": finish, "message": message}]}

    @staticmethod
    def call(name="assign_task", arguments='{"task_id":"ISSUE-1"}', call_id="tc-1"):
        return {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}

    def test_actual_base_agent_and_together_client_accept_terminal_no_message(self):
        agent = self.make_agent("planning", [self.response("ordinary assistant text")])
        result = run_async(agent._multi_step_response_generation("system", "user"))
        self.assertEqual(result["termination_reason"], "no_tool_call")
        self.assertEqual(result["finish_reason"], "stop")
        self.assertEqual(result["conversation_steps"], 1)

    def test_actual_environment_callback_commit_is_required_for_execution_success(self):
        tool_response = self.response(finish="tool_calls", tool_calls=[self.call()])
        agent = self.make_agent("execution", [tool_response])
        result = run_async(agent._multi_step_response_generation("system", "user"))
        self.assertEqual(result["termination_reason"], "environment_action_committed")
        self.assertEqual(result["tools_executed"], 1)
        self.assertNotIn("protocol_error", result)

    def test_actual_environment_rejection_propagates_as_invalid_episode_path(self):
        rejected = {"status": "error", "result": {"error": "synthetic rejection"}}
        agent = self.make_agent(
            "execution", [self.response(finish="tool_calls", tool_calls=[self.call()])],
            environment_result=rejected,
        )
        with self.assertRaisesRegex(compat.CompatibilityProtocolError, "environment rejected"):
            run_async(agent._multi_step_response_generation("system", "user"))

    def test_late_malformed_call_has_no_earlier_tool_side_effect(self):
        client = object.__new__(TogetherClient)
        response = self.response(finish="tool_calls", tool_calls=[
            self.call(call_id="good"),
            self.call(arguments="{bad", call_id="bad"),
        ])
        side_effects = []

        async def callback(name, arguments):
            side_effects.append((name, arguments))
            return {"status": "success"}

        with self.assertRaisesRegex(compat.CompatibilityProtocolError, "not valid JSON"):
            run_async(client.process_tool_calls(response, [], callback))
        self.assertEqual(side_effects, [])

    def test_upstream_execution_without_commit_returns_protocol_error(self):
        agent = self.make_agent(
            "execution", [
                self.response(finish="tool_calls", tool_calls=[self.call()]),
                self.response("no action was actually applied"),
            ],
            environment_result={"status": "success", "result": {"message": "accepted but no update"}},
        )
        result = run_async(agent._multi_step_response_generation("system", "user"))
        self.assertEqual(result["protocol_error"], "execution_without_committed_environment_action")

    def test_actual_local_protocol_wrapper_rejects_protocol_error_even_if_returned(self):
        protocol = object.__new__(LocalCommunicationProtocol)

        async def empty_events(*args, **kwargs):
            return {}
        protocol._prefetch_blackboard_events = empty_events
        agent = SimpleNamespace(generate_response=self._invalid_turn)
        env = SimpleNamespace(prompts=object())
        with self.assertRaisesRegex(compat.CompatibilityProtocolError, "execution_without_committed"):
            run_async(LocalCommunicationProtocol.agent_execution_turn(
                protocol, agent, "Agent-A", {}, env, 1,
            ))

    @staticmethod
    async def _invalid_turn(**kwargs):
        return {"protocol_error": "execution_without_committed_environment_action"}

    def test_continuation_transport_exception_is_not_returned_as_success(self):
        first = self.response(finish="tool_calls", tool_calls=[self.call(
            name="post_message", arguments='{"message":"hello"}'
        )])
        agent = self.make_agent("planning", [first, TimeoutError("synthetic timeout")])
        with self.assertRaisesRegex(TimeoutError, "synthetic timeout"):
            run_async(agent._multi_step_response_generation("system", "user"))


if __name__ == "__main__":
    unittest.main()
