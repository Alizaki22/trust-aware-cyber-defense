"""Model invocation layer. Agents depend only on ``LLMClient.generate``.

- ``OpenAICompatibleClient``: any OpenAI-compatible server (vLLM, Ollama,
  llama.cpp server) serving Qwen/Qwen3-4B-Instruct-2507 (Phase 1) or the
  fine-tuned Detection model (Phase 2). Uses the OpenAI SDK (D-007).
- ``StubLLMClient``: deterministic offline stand-in for tests / CI / demos.
  Its outputs are NOT model results and are labelled ``stub:`` everywhere.
"""
from __future__ import annotations

import json
import re
from typing import Callable, Optional


class LLMError(RuntimeError):
    """Transport/server failure (distinct from an unparseable answer)."""


class LLMClient:
    model_id: str = "unknown"

    def generate(self, system_prompt: str, user_prompt: str) -> str:  # pragma: no cover
        raise NotImplementedError


class OpenAICompatibleClient(LLMClient):
    def __init__(self, base_url: str, model: str, api_key: str = "EMPTY",
                 temperature: float = 0.0, max_tokens: int = 512,
                 timeout_s: float = 120.0, seed: Optional[int] = 42, max_retries: int = 2):
        from openai import OpenAI

        self.model_id = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.seed = seed
        self._client = OpenAI(base_url=base_url, api_key=api_key,
                              timeout=timeout_s, max_retries=max_retries)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from openai import OpenAIError

        kwargs = dict(model=self.model_id, temperature=self.temperature, max_tokens=self.max_tokens,
                      messages=[{"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}])
        if self.seed is not None:
            kwargs["seed"] = self.seed
        try:
            response = self._client.chat.completions.create(**kwargs)
        except OpenAIError as error:
            raise LLMError(f"{type(error).__name__}: {error}") from error
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMError("empty response from model server")
        return content


class StubLLMClient(LLMClient):
    """Deterministic offline client.

    ``responder`` maps (system_prompt, user_prompt) -> text. The default
    responder always answers "benign / Normal" citing the first three input
    features: a trivial, clearly-labelled baseline used only to exercise the
    pipeline end-to-end without a model server.
    """

    def __init__(self, responder: Optional[Callable[[str, str], str]] = None,
                 model_id: str = "stub:always-normal"):
        self.model_id = model_id
        self.responder = responder or _always_normal
        self.calls = 0

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        return self.responder(system_prompt, user_prompt)


def _always_normal(system_prompt: str, user_prompt: str) -> str:
    body = user_prompt.split("\n", 1)[-1]
    evidence = ", ".join(body.split(", ")[1:4])
    return json.dumps({"verdict": "benign", "classification": "Normal", "evidence": evidence,
                       "confidence": "low", "reasoning": "Stub response (not a model output)."})


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)
_THINK = re.compile(r"<think>.*?</think>", re.S)


def extract_json_object(text: str) -> dict:
    """Return the first JSON object in a model response.

    Tolerates code fences and <think> blocks (Qwen3-Instruct-2507 should not
    emit them, but other servers/templates may). Raises ValueError if none.
    """
    text = _THINK.sub("", text).strip()
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    while start != -1:
        depth, in_str, escape = 0, False, False
        for index in range(start, len(text)):
            char = text[index]
            if in_str:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_str = False
            elif char == '"':
                in_str = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(text[start:index + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(value, dict):
                        return value
                    break
        start = text.find("{", start + 1)
    raise ValueError("no JSON object found in model response")


def build_llm_client(config, agent: str = "detection") -> LLMClient:
    if config.llm_backend == "stub":
        return StubLLMClient()
    return OpenAICompatibleClient(base_url=config.llm_base_url, model=config.model_for(agent),
                                  api_key=config.llm_api_key, temperature=config.llm_temperature,
                                  max_tokens=config.llm_max_tokens, timeout_s=config.llm_timeout_s,
                                  seed=config.llm_seed)
