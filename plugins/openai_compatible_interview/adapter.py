"""Configurable OpenAI-compatible interview-agent adapter.

The adapter is opt-in and makes no network request until
``CAREER_OS_LLM_BASE_URL`` is configured.  It uses only Python's standard
library so local OpenAI-compatible gateways and hosted endpoints can be
plugged in without changing the Career OS interview runtime.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Mapping

from plugins.deepinterview.adapter import DeepInterviewAdapter, _text


PROVIDER = "openai-compatible"
DEFAULT_MODEL = "gpt-4o-mini"
CONTRACT_VERSION = "interview-agent-v1+openai-compatible"


def _configured_timeout() -> float:
    raw = os.environ.get("CAREER_OS_LLM_TIMEOUT_SECONDS", "30")
    try:
        return max(1.0, min(float(raw), 300.0))
    except ValueError:
        return 30.0


def _decode_score(content: Any, *, follow_up: bool, track: Any = None, plugin_id: str = "openai-compatible-interview") -> dict[str, Any]:
    """Validate the model's structured score and normalize it for the core."""

    if isinstance(content, Mapping):
        payload = dict(content)
    else:
        text = str(content or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        try:
            payload = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise ValueError("模型未返回 JSON 评分对象") from exc
    required = ("technical", "expression", "project", "follow_up", "overall")
    result: dict[str, Any] = {}
    for key in required:
        try:
            value = round(float(payload[key]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"模型评分缺少有效字段: {key}") from exc
        if not 0 <= value <= 100:
            raise ValueError(f"模型评分字段超出 0-100: {key}")
        result[key] = int(value)
    result["focus"] = _text(payload.get("focus")) or "项目证据"
    result.update(
        {
            "contract_version": CONTRACT_VERSION,
            "provider": PROVIDER,
            "plugin_id": plugin_id,
            "scoring_engine": PROVIDER,
            "external_service": True,
            "track": track,
            "follow_up_turn": "yes" if follow_up else "no",
        }
    )
    return result


class OpenAICompatibleInterviewAdapter(DeepInterviewAdapter):
    capability = "interview_agent"

    def __init__(self, manifest: Any = None):
        super().__init__(manifest=manifest)
        self.plugin_id = _text(getattr(manifest, "plugin_id", "openai-compatible-interview")) or "openai-compatible-interview"
        self.provider = PROVIDER

    def provide(self, capability: str):
        return self if capability == self.capability else None

    def prepare(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        base_url = _text(os.environ.get("CAREER_OS_LLM_BASE_URL"))
        if not base_url:
            raise RuntimeError("CAREER_OS_LLM_BASE_URL 未配置，openai-compatible 插件安全回退到 local-rubric")
        prepared = super().prepare(*args, **kwargs)
        prepared.update(
            {
                "contract_version": CONTRACT_VERSION,
                "provider": PROVIDER,
                "plugin_id": self.plugin_id,
                "external_service": True,
                "model": _text(os.environ.get("CAREER_OS_LLM_MODEL")) or DEFAULT_MODEL,
                "endpoint_configured": True,
            }
        )
        return prepared

    @staticmethod
    def _endpoint() -> str:
        base_url = _text(os.environ.get("CAREER_OS_LLM_BASE_URL"))
        if base_url.endswith("/chat/completions"):
            return base_url
        return base_url.rstrip("/") + "/chat/completions"

    def _chat(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": _text(os.environ.get("CAREER_OS_LLM_MODEL")) or DEFAULT_MODEL,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self._endpoint(),
            data=body,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {os.environ['CAREER_OS_LLM_API_KEY']}"} if os.environ.get("CAREER_OS_LLM_API_KEY") else {}),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=_configured_timeout()) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"OpenAI-compatible 请求失败: {type(exc).__name__}") from exc
        try:
            return decoded["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenAI-compatible 响应缺少 choices[0].message.content") from exc

    def score(
        self,
        prepared: Mapping[str, Any],
        question: Mapping[str, Any] | str,
        answer: str,
        *,
        follow_up: bool = False,
    ) -> dict[str, Any]:
        question_text = _text(question.get("question") if isinstance(question, Mapping) else question)
        track = question.get("track") if isinstance(question, Mapping) else None
        system = (
            "你是严格的校招面试评分器。只返回 JSON，不要 Markdown。"
            "字段必须是 technical、expression、project、follow_up、overall（0-100整数）和 focus（短中文）。"
            "评分依据：技术准确性40%、表达结构30%、项目证据20%、追问处理10%。"
        )
        user = json.dumps(
            {
                "job": prepared.get("job", {}),
                "tracks": prepared.get("tracks", []),
                "question": question_text,
                "answer": _text(answer),
                "follow_up": follow_up,
            },
            ensure_ascii=False,
        )
        content = self._chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
        return _decode_score(content, follow_up=follow_up, track=track, plugin_id=self.plugin_id)

    def report(self, prepared: Mapping[str, Any], turns: list[Mapping[str, Any]]) -> dict[str, Any]:
        report = super().report(prepared, turns)
        report.update(
            {
                "contract_version": CONTRACT_VERSION,
                "provider": PROVIDER,
                "plugin_id": self.plugin_id,
                "scoring_engine": PROVIDER,
                "external_service": True,
            }
        )
        return report


def create_plugin(manifest: Any = None) -> OpenAICompatibleInterviewAdapter:
    return OpenAICompatibleInterviewAdapter(manifest=manifest)
