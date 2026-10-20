import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
COMPAT_PATH = ROOT / "reproductions" / "colosseum_local" / "runtime_compat.py"
PAIR_PATH = ROOT / "reproductions" / "colosseum_local" / "run_pair.py"
VENV_SITE = ROOT / "reference" / "colosseum" / ".venv" / "Lib" / "site-packages"
if VENV_SITE.exists():
    sys.path.insert(0, str(VENV_SITE))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


compat = load_module("colluscope_runtime_compat_tests", COMPAT_PATH)
pair = load_module("colluscope_pair_runner_tests", PAIR_PATH)


def run_async(coroutine):
    """Drive immediate mock coroutines without opening a Windows socketpair."""
    import terrarium.async_utils as async_utils

    original_run_blocking = async_utils.run_blocking

    async def run_blocking_immediately(function, /, *args, **kwargs):
        return function(*args, **kwargs)

    async_utils.run_blocking = run_blocking_immediately
    try:
        while True:
            try:
                yielded = coroutine.send(None)
            except StopIteration as completed:
                return completed.value
            if yielded is not None:
                raise AssertionError(
                    "offline mock coroutine unexpectedly yielded an external awaitable"
                )
    finally:
        async_utils.run_blocking = original_run_blocking


class FakeClient:
    def __init__(self):
        self.callback_count = 0

    async def _colluscope_original_process_tool_calls(self, response, context, callback):
        self.callback_count += 1
        context.append({"role": "assistant", "tool_calls": response["choices"][0]["message"]["tool_calls"]})
        return 1, context, ["post_message -- {}"]


class ToolSchemaValidationTests(unittest.TestCase):
    def test_malformed_arguments_fail_before_callback(self):
        for bad in ("{not-json", "", "null", "[]"):
            client = FakeClient()
            with self.subTest(arguments=bad):
                with self.assertRaises(compat.CompatibilityProtocolError):
                    run_async(compat.strict_process_tool_calls(
                        client,
                        {"choices": [{"message": {"tool_calls": [{"function": {"name": "post_message", "arguments": bad}}]}}]},
                        [],
                        lambda *_: None,
                    ))
                self.assertEqual(client.callback_count, 0)

    def test_missing_arguments_do_not_default_to_empty_object(self):
        client = FakeClient()
        response = {"choices": [{"message": {"tool_calls": [{"function": {"name": "post_message"}}]}}]}
        with self.assertRaisesRegex(compat.CompatibilityProtocolError, "no arguments field"):
            run_async(compat.strict_process_tool_calls(client, response, [], lambda *_: None))
        self.assertEqual(client.callback_count, 0)

    def test_json_scalar_is_not_accepted_as_tool_argument_object(self):
        for value in ("null", "7", "true", '"text"'):
            with self.subTest(value=value), self.assertRaises(compat.CompatibilityProtocolError):
                compat._tool_calls({"choices": [{"message": {"tool_calls": [
                    {"function": {"name": "assign_task", "arguments": value}}
                ]}}]})

    def test_environment_tool_error_is_not_treated_as_success(self):
        class ErrorClient(FakeClient):
            async def _colluscope_original_process_tool_calls(self, response, context, callback):
                context.extend([
                    {"role": "assistant", "tool_calls": response["choices"][0]["message"]["tool_calls"]},
                    {"role": "tool", "content": json.dumps({"error": "invalid task"})},
                ])
                return 1, context, ["assign_task -- {}"]
        client = ErrorClient()
        good_syntax = {"choices": [{"message": {"tool_calls": [{"function": {"name": "assign_task", "arguments": "{}"}}]}}]}
        with self.assertRaisesRegex(compat.CompatibilityProtocolError, "environment rejected"):
            run_async(compat.strict_process_tool_calls(client, good_syntax, [], lambda *_: None))


class ContinuationStateTests(unittest.TestCase):
    def _fake_agent(self, phase="planning", tool_steps=None):
        tool_steps = tool_steps or []
        class Discovery:
            def get_tools_for_environment(self, *_): return []
            def get_tools_for_blackboard(self, *_): return []
        class Client:
            def __init__(self): self.generated = 0
            def init_context(self, system, user): return [{"role": "system", "content": system}, {"role": "user", "content": user}]
            def generate_response(inner, *, input, params):
                inner.generated += 1
                return {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "ordinary assistant text"}}]}, "ordinary assistant text"
            def get_usage(self, response, total): return total
            async def process_tool_calls(inner, response, context, callback):
                context.append(response["choices"][0]["message"])
                return 0, context, []
        client = Client()
        return SimpleNamespace(
            current_phase=phase,
            toolset_discovery=Discovery(),
            environment_name="JiraTicketEnvironment",
            _build_generation_params=lambda **_: {},
            client=client,
            max_conversation_steps=3,
            _execute_tool_call=lambda *_: None,
            _log_trajectory=lambda _: None,
            model_name="mock",
        ), client

    def test_plain_assistant_response_is_terminal_not_a_second_http_request(self):
        agent, client = self._fake_agent("planning")
        result = run_async(compat.compatible_multi_step_response_generation(agent, "system", "user"))
        self.assertEqual(client.generated, 1)
        self.assertEqual(result["termination_reason"], "no_tool_call")
        self.assertEqual(result["finish_reason"], "stop")
        self.assertNotIn("protocol_error", result)

    def test_execution_without_committed_action_is_explicit_failure(self):
        agent, client = self._fake_agent("execution")
        result = run_async(compat.compatible_multi_step_response_generation(agent, "system", "user"))
        self.assertEqual(client.generated, 1)
        self.assertEqual(result["protocol_error"], "execution_without_committed_environment_action")
        with self.assertRaises(compat.CompatibilityProtocolError):
            compat.require_valid_turn(result)

    def test_truncated_generation_is_not_silently_validated_as_no_message(self):
        agent, _ = self._fake_agent("planning")
        original = agent.client.generate_response
        def truncated(**kwargs):
            response, text = original(**kwargs)
            response["choices"][0]["finish_reason"] = "length"
            return response, text
        agent.client.generate_response = truncated
        with self.assertRaisesRegex(compat.CompatibilityProtocolError, "nonterminal_finish_reason"):
            run_async(compat.compatible_multi_step_response_generation(agent, "system", "user"))

    def test_missing_finish_reason_is_explicit_protocol_failure(self):
        agent, _ = self._fake_agent("planning")
        original = agent.client.generate_response
        def missing(**kwargs):
            response, text = original(**kwargs)
            response["choices"][0].pop("finish_reason")
            return response, text
        agent.client.generate_response = missing
        with self.assertRaisesRegex(compat.CompatibilityProtocolError, "missing_finish_reason"):
            run_async(compat.compatible_multi_step_response_generation(agent, "system", "user"))

    def test_tool_calls_finish_reason_without_tool_calls_is_rejected(self):
        agent, _ = self._fake_agent("planning")
        original = agent.client.generate_response
        def inconsistent(**kwargs):
            response, text = original(**kwargs)
            response["choices"][0]["finish_reason"] = "tool_calls"
            return response, text
        agent.client.generate_response = inconsistent
        with self.assertRaisesRegex(compat.CompatibilityProtocolError, "without_tool_calls"):
            run_async(compat.compatible_multi_step_response_generation(agent, "system", "user"))


class RawCaptureTests(unittest.TestCase):
    def test_capture_keeps_exact_bodies_and_finish_reason_without_auth_header(self):
        class Response:
            status_code = 200
            content = b'{"choices":[{"finish_reason":"tool_calls","message":{"role":"assistant","tool_calls":[{"function":{"name":"post_message","arguments":"{\\"message\\":\\"x\\"}"}}]}}]}'
            def json(self): return json.loads(self.content)
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            recorder = pair.RawHttpCapture(Path(temp))
            recorder.episode_id = "seed1-local"
            response = recorder.request(
                lambda session, method, url, **kwargs: Response(),
                object(), "POST", "http://127.0.0.1:8081/v1/chat/completions",
                data='{"messages":[{"role":"user","content":"private"}]}',
                headers={"Authorization": "Bearer MUST_NOT_BE_CAPTURED"},
            )
            self.assertEqual(response.status_code, 200)
            directory = Path(temp) / "raw" / "http" / "seed1-local"
            request_bytes = (directory / "attempt-0001.request.bin").read_bytes()
            response_bytes = (directory / "attempt-0001.response.bin").read_bytes()
            index = json.loads((directory / "index.jsonl").read_text().splitlines()[0])
            self.assertEqual(request_bytes, b'{"messages":[{"role":"user","content":"private"}]}')
            self.assertEqual(response_bytes, Response.content)
            self.assertEqual(index["finish_reason"], "tool_calls")
            self.assertEqual(index["tool_names"], ["post_message"])
            self.assertNotIn("MUST_NOT_BE_CAPTURED", (directory / "index.jsonl").read_text())

    def test_pair_budget_is_exact_two_episode_call_graph(self):
        self.assertEqual(pair.PAIR_MAX_HTTP, 180)
        self.assertEqual(2 * 6 * (4 + 1) * 3, pair.PAIR_MAX_HTTP)

    def test_http_exception_keeps_exact_request_and_marks_no_response(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            recorder = pair.RawHttpCapture(Path(temp))
            recorder.episode_id = "episode-error"
            def fail(*args, **kwargs):
                raise TimeoutError("synthetic timeout")
            with self.assertRaises(TimeoutError):
                recorder.request(fail, object(), "POST", "http://127.0.0.1:8081/v1/chat/completions", data=b"request-bytes")
            directory = Path(temp) / "raw" / "http" / "episode-error"
            self.assertEqual((directory / "attempt-0001.request.bin").read_bytes(), b"request-bytes")
            row = json.loads((directory / "index.jsonl").read_text().splitlines()[0])
            self.assertEqual(row["status"], "transport_exception")
            self.assertEqual(row["exception_type"], "TimeoutError")


if __name__ == "__main__":
    unittest.main()
