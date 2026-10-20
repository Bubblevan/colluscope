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

    def test_decoded_python_object_is_rejected_before_upstream_json_loads(self):
        client = FakeClient()
        response = {"choices": [{"message": {"tool_calls": [
            {"function": {"name": "assign_task", "arguments": {"task_id": "x"}}}
        ]}}]}
        with self.assertRaisesRegex(compat.CompatibilityProtocolError, "must be a JSON string"):
            run_async(compat.strict_process_tool_calls(client, response, [], lambda *_: None))
        self.assertEqual(client.callback_count, 0)

    def test_tool_calls_with_stop_finish_reason_are_rejected_as_inconsistent(self):
        response = {"choices": [{"finish_reason": "stop", "message": {
            "tool_calls": [{"function": {"name": "post_message", "arguments": "{}"}}]
        }}]}
        self.assertEqual(
            compat._validate_finish_reason(response),
            "tool_calls_with_inconsistent_finish_reason:stop",
        )

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
    OUTPUTS = ROOT / "reference" / "colosseum" / "experiments" / "collusion" / "outputs"

    def test_capture_keeps_exact_bodies_and_finish_reason_without_auth_header(self):
        class Response:
            status_code = 200
            content = b'{"choices":[{"finish_reason":"tool_calls","message":{"role":"assistant","tool_calls":[{"function":{"name":"post_message","arguments":"{\\"message\\":\\"x\\"}"}}]}}]}'
            def json(self): return json.loads(self.content)
        with tempfile.TemporaryDirectory(dir=self.OUTPUTS) as temp:
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
            index_rows = [json.loads(line) for line in (directory / "index.jsonl").read_text().splitlines()]
            index = index_rows[0]
            self.assertEqual(request_bytes, b'{"messages":[{"role":"user","content":"private"}]}')
            self.assertEqual(response_bytes, Response.content)
            self.assertEqual(index["event"], "http_attempt_started")
            self.assertEqual(index_rows[1]["event"], "http_attempt_terminal")
            self.assertEqual(index_rows[1]["finish_reason"], "tool_calls")
            self.assertEqual(index_rows[1]["tool_names"], ["post_message"])
            saved = b"".join(path.read_bytes() for path in directory.iterdir() if path.is_file())
            self.assertNotIn(b"MUST_NOT_BE_CAPTURED", saved)
            self.assertTrue(pair.RawHttpCapture._assert_ignored_output(Path(temp)) is None)

    def test_unignored_or_nonlocal_raw_capture_is_blocked_before_transport(self):
        with self.assertRaises(pair.RawCapturePolicyError):
            pair.RawHttpCapture(ROOT / "tests" / "unignored-raw-capture")
        with tempfile.TemporaryDirectory(dir=self.OUTPUTS) as temp:
            recorder = pair.RawHttpCapture(Path(temp))
            called = []
            with self.assertRaises(pair.RawCapturePolicyError):
                recorder.request(
                    lambda *a, **k: called.append(True), object(), "POST",
                    "https://example.com/v1/chat/completions", data=b"private",
                )
            self.assertEqual(called, [])

    def test_pair_budget_is_exact_two_episode_call_graph(self):
        self.assertEqual(pair.PAIR_MAX_HTTP, 180)
        self.assertEqual(2 * 6 * (4 + 1) * 3, pair.PAIR_MAX_HTTP)

    def test_http_exception_keeps_exact_request_and_marks_no_response(self):
        with tempfile.TemporaryDirectory(dir=self.OUTPUTS) as temp:
            recorder = pair.RawHttpCapture(Path(temp))
            recorder.episode_id = "episode-error"
            def fail(*args, **kwargs):
                raise TimeoutError("synthetic timeout")
            with self.assertRaises(TimeoutError):
                recorder.request(fail, object(), "POST", "http://127.0.0.1:8081/v1/chat/completions", data=b"request-bytes")
            directory = Path(temp) / "raw" / "http" / "episode-error"
            self.assertEqual((directory / "attempt-0001.request.bin").read_bytes(), b"request-bytes")
            rows = [json.loads(line) for line in (directory / "index.jsonl").read_text().splitlines()]
            self.assertEqual(rows[0]["event"], "http_attempt_started")
            self.assertEqual(rows[1]["status"], "transport_or_capture_exception")
            self.assertEqual(rows[1]["exception_type"], "TimeoutError")

    def test_keyboard_interrupt_is_terminally_recorded_before_propagating(self):
        with tempfile.TemporaryDirectory(dir=self.OUTPUTS) as temp:
            recorder = pair.RawHttpCapture(Path(temp))
            with self.assertRaises(KeyboardInterrupt):
                recorder.request(
                    lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()),
                    object(), "POST", "http://127.0.0.1:8081/v1/chat/completions",
                    data=b"body",
                )
            path = Path(temp) / "raw" / "http" / "bootstrap" / "index.jsonl"
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual([row["event"] for row in rows], ["http_attempt_started", "http_attempt_terminal"])
            self.assertEqual(rows[-1]["exception_type"], "KeyboardInterrupt")

    def test_real_guard_capture_composition_records_both_starts_before_transport(self):
        import requests

        class Response:
            status_code = 200
            content = b'{"choices":[]}'
            def json(self): return json.loads(self.content)

        with tempfile.TemporaryDirectory(dir=self.OUTPUTS) as temp:
            root = Path(temp)
            capture = pair.RawHttpCapture(root)
            capture.episode_id = "precall-test"
            runner = pair.load_runner()
            ledger = root / "http_requests.jsonl"
            original_global = requests.Session.request
            transport_calls = []

            def transport(session, method, url, **kwargs):
                outer = [json.loads(line) for line in ledger.read_text().splitlines()]
                raw_path = root / "raw" / "http" / "precall-test" / "index.jsonl"
                raw = [json.loads(line) for line in raw_path.read_text().splitlines()]
                self.assertEqual(outer[-1]["event"], "http_attempt_started")
                self.assertEqual(raw[-1]["event"], "http_attempt_started")
                self.assertNotIn("headers", outer[-1])
                self.assertNotIn("Authorization", raw[-1])
                transport_calls.append(1)
                return Response()

            def capture_wrapper(session, method, url, **kwargs):
                return capture.request(transport, session, method, url, **kwargs)

            requests.Session.request = capture_wrapper
            guard = runner.RequestGuard(ledger, hard_cap=1)
            guard.install()
            guard.set_episode("precall-test")
            try:
                response = requests.Session().post(
                    pair.LOCAL_CHAT_COMPLETIONS,
                    data='{"messages":[]}',
                    headers={"Authorization": "Bearer HEADER_SENTINEL"},
                )
            finally:
                requests.Session.request = original_global
            self.assertEqual(response.status_code, 200)
            self.assertEqual(transport_calls, [1])
            self.assertEqual(guard.attempts, 1)
            self.assertNotIn("HEADER_SENTINEL", ledger.read_text())


if __name__ == "__main__":
    unittest.main()
