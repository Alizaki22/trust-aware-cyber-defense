import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from src.utils.llm_client import LLMError, OpenAICompatibleClient, StubLLMClient, extract_json_object


@pytest.mark.parametrize("text", [
    '{"a": 1}', 'Sure! {"a": 1} hope that helps', '```json\n{"a": 1}\n```',
    '<think>x {"no": 0}</think>{"a": 1}', 'noise {not json} then {"a": 1}'])
def test_extract_json_object(text):
    assert extract_json_object(text) == {"a": 1}


def test_extract_json_handles_braces_in_strings():
    assert extract_json_object('{"e": "a={b}, c=}"}') == {"e": "a={b}, c=}"}


@pytest.mark.parametrize("text", ["", "no json here", "[1, 2]", "{broken"])
def test_extract_json_rejects(text):
    with pytest.raises(ValueError):
        extract_json_object(text)


class _FakeChatServer(BaseHTTPRequestHandler):
    requests: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _FakeChatServer.requests.append(body)
        payload = {"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                   "choices": [{"index": 0, "finish_reason": "stop",
                                "message": {"role": "assistant", "content": '{"ok": true}'}}]}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def test_openai_compatible_client_speaks_the_protocol():
    server = HTTPServer(("127.0.0.1", 0), _FakeChatServer)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = OpenAICompatibleClient(f"http://127.0.0.1:{server.server_port}/v1",
                                        "Qwen/Qwen3-4B-Instruct-2507", timeout_s=5, max_retries=0)
        assert client.generate("SYS", "USER") == '{"ok": true}'
        sent = _FakeChatServer.requests[-1]
        assert sent["model"] == "Qwen/Qwen3-4B-Instruct-2507"
        assert sent["temperature"] == 0.0 and sent["seed"] == 42
        assert sent["messages"] == [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USER"}]
    finally:
        server.shutdown()


def test_unreachable_server_raises_llm_error():
    client = OpenAICompatibleClient("http://127.0.0.1:9/v1", "m", timeout_s=2, max_retries=0)
    with pytest.raises(LLMError):
        client.generate("s", "u")


def test_stub_is_labelled_and_deterministic():
    stub = StubLLMClient()
    assert stub.model_id.startswith("stub:")
    assert stub.generate("s", "h\na=1, b=2, c=3, d=4") == stub.generate("s", "h\na=1, b=2, c=3, d=4")
