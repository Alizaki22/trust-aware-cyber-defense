"""E3: evaluations never silently fall back to default trust; stale calibration is refused.

A local fake OpenAI-compatible server stands in for the Qwen server so the real
(non-stub) code path -- OpenAI SDK -> HTTP -> parse -> pipeline -> metrics -- runs
end to end. Its answers are canned, NOT model output.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from src.cli import main
from src.data.unsw_nb15 import prepare
from src.evaluation.runner import (CalibrationMismatchError, CalibrationMissingError, run_calibration,
                                   run_evaluation)


class _FakeQwen(BaseHTTPRequestHandler):
    """Answers every chat request with a schema-valid, grounded 'Normal' finding."""

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        features = dict(p.split("=", 1) for p in body["messages"][-1]["content"].split("\n", 1)[1].split(", "))
        answer = {"verdict": "benign", "classification": "Normal",
                  "evidence": ", ".join(f"{k}={features[k]}" for k in ("proto", "service", "state")),
                  "confidence": "low", "reasoning": "canned test answer"}
        payload = {"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                   "choices": [{"index": 0, "finish_reason": "stop",
                                "message": {"role": "assistant", "content": json.dumps(answer)}}]}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_qwen():
    server = HTTPServer(("127.0.0.1", 0), _FakeQwen)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


@pytest.fixture
def real_config(stub_config, fake_qwen):
    prepare(stub_config.data_dir, log=lambda *_: None)
    return stub_config.model_copy(update={"llm_backend": "openai", "llm_base_url": fake_qwen, "llm_timeout_s": 10})


quiet = dict(log=lambda *_: None)


def test_real_evaluation_without_calibration_fails_loudly(real_config):
    with pytest.raises(CalibrationMissingError, match="python -m src.cli calibrate"):
        run_evaluation(real_config, **quiet)
    assert not real_config.runs_dir.exists() or not any(real_config.runs_dir.iterdir())  # nothing written


def test_cli_reports_missing_calibration_and_exits_1(real_config, monkeypatch, capsys):
    for key, value in {"LLM_BACKEND": "openai", "LLM_BASE_URL": real_config.llm_base_url,
                       "DATA_DIR": str(real_config.data_dir), "RUNS_DIR": str(real_config.runs_dir)}.items():
        monkeypatch.setenv(key, value)
    assert main(["evaluate"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("ERROR: No calibration file") and "calibrate" in out


def test_real_path_calibrate_then_evaluate_through_the_openai_sdk(real_config):
    run_calibration(real_config, **quiet)
    run_dir = run_evaluation(real_config, run_id="real-path", **quiet)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    config = json.loads((run_dir / "config.json").read_text())
    assert metrics["is_mock"] is False and metrics["calibrated"] is True and metrics["valid_for_reporting"] is True
    assert metrics["schema_valid_rate"]["outcomes"]["valid"] == metrics["n_events"] > 0
    assert config["agent_models_effective"]["detection"] == "Qwen/Qwen3-4B-Instruct-2507"
    # Detection answered every calibration event, so its trust comes from measurement, not a default
    assert "detection" not in config["trust_history_defaults"]
    assert config["trust_history"]["detection"] == json.loads(real_config.calibration_path.read_text())["agents"]["detection"]["accuracy"]
    assert "llm_api_key" not in config


@pytest.mark.parametrize("change", ["reference data", "detection model"])
def test_stale_calibration_is_refused(real_config, change):
    run_calibration(real_config, **quiet)
    if change == "reference data":
        path = real_config.data_dir / "processed" / "intel_signatures.json"
        data = json.loads(path.read_text())
        data["signatures"]["tcp|-|FIN|1|1"] = {"reputation": "benign", "support": 99, "attack_share": 0.0}
        path.write_text(json.dumps(data))
        config = real_config
    else:  # same calibration file name, different engine behind it
        from src.utils.llm_client import StubLLMClient
        with pytest.raises(CalibrationMismatchError, match="agent_models"):
            run_evaluation(real_config, detection_llm=StubLLMClient(model_id="other-model"), **quiet)
        return
    with pytest.raises(CalibrationMismatchError, match="intel_signatures|signatures"):
        run_evaluation(config, **quiet)


def test_allow_uncalibrated_is_explicit_and_marked_invalid(real_config):
    run_dir = run_evaluation(real_config, allow_uncalibrated=True, **quiet)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    config = json.loads((run_dir / "config.json").read_text())
    assert run_dir.name.endswith("-UNCALIBRATED")
    assert metrics["calibrated"] is False and metrics["valid_for_reporting"] is False
    assert config["trust_history_defaults"] == ["detection", "intelligence", "behavioral"]
