"""Interview-agent capability adapter for the DeepInterview plugin.

This is a local compatibility implementation, not a connection to an external
DeepInterview service.  It deliberately exposes a small, JSON-friendly
interface so the core can swap it in at the capability seam while retaining
``local-rubric`` as the fallback when the plugin is disabled or unavailable.
"""

from __future__ import annotations

import re
import json
import os
import sqlite3
from pathlib import Path
from collections.abc import Mapping, Sequence
from statistics import mean
from typing import Any


CONTRACT_VERSION = "interview-agent-v1"
PROVIDER = "deepinterview-local-compat"

# Keep this bridge identical to the core JD selector.  These are matching
# terms only; the adapter never turns them into a new question.
_FAMILY_TERMS: dict[str, tuple[str, ...]] = {
    "Linux/网络/容器基础": ("linux", "网络", "tcp", "http", "dns", "docker", "kubernetes", "容器"),
    "Shell/Python 自动化": ("shell", "python", "脚本", "自动化", "subprocess", "pytest"),
    "SQL/数据库运维": ("sql", "数据库", "mysql", "sqlite", "索引", "事务", "etl"),
    "测试设计与故障排查": ("测试", "pytest", "unittest", "mock", "故障", "排查", "监控"),
    "情景判断/SJT": ("情景", "客户", "冲突", "沟通", "协作", "现场"),
    "产品/协议/硬件基础": ("协议", "硬件", "sdk", "api", "串口", "传感器", "产品"),
    "现场故障定位": ("故障", "排障", "调试", "日志", "现场", "监控", "超时"),
    "客户沟通与冲突情景": ("客户", "沟通", "冲突", "投诉", "现场", "培训"),
    "结构化行为面试": ("项目", "团队", "协作", "沟通", "取舍", "压力"),
    "英语沟通（岗位要求时）": ("english", "英语", "technical", "communication"),
    "C/C++ 与数据结构": ("c/c++", "c++", "c语言", "数据结构", "指针", "内存", "算法"),
    "嵌入式 Linux/RTOS": ("嵌入式", "rtos", "freertos", "linux", "mcu", "固件", "驱动"),
    "串口/CAN/MQTT 等协议": ("uart", "串口", "can", "mqtt", "ble", "协议", "通信"),
    "硬件接口与调试": ("硬件", "调试", "传感器", "点云", "图像", "接口", "采集"),
    "SQL 查询与性能": ("sql", "查询", "索引", "数据库", "性能", "事务"),
    "Python/pandas 数据处理": ("python", "pandas", "numpy", "数据", "清洗", "etl"),
    "统计与数据解读": ("统计", "模型", "指标", "数据", "回归", "分类", "聚类"),
    "业务案例/资料分析": ("业务", "资料", "分析", "指标", "增长", "营收", "案例"),
    "Python/服务端接口": ("python", "api", "rest", "fastapi", "http", "服务端", "接口"),
    "RAG 检索链路与向量库": ("rag", "检索", "向量", "embedding", "chroma", "milvus", "知识库"),
    "Agent/Prompt 工程": ("agent", "prompt", "工具", "langchain", "llamaindex", "大模型"),
    "数据与评测": ("评测", "准确", "召回", "数据", "模型", "指标"),
    "编程题": ("代码", "算法", "编程", "python", "c++", "函数"),
}


def _question_terms(family: str) -> tuple[str, ...]:
    if family in _FAMILY_TERMS:
        return _FAMILY_TERMS[family]
    return tuple(part.casefold() for part in re.split(r"[/、（）()\s]+", family) if len(part) >= 2)


def _interview_category_allowed(track: str, family: str, category: str) -> bool:
    track_text = _text(track).casefold()
    family_text = _text(family).casefold()
    category_text = _text(category).casefold()
    if track_text == "data-analysis" and any(token in category_text for token in ("rag", "agent")):
        return any(token in family_text for token in ("rag", "agent"))
    if track_text == "software-testing-ops" and any(
        token in category_text for token in ("c 语言", "c/c++", "c++", "freertos", "rtos", "串口", "嵌入式")
    ):
        return False
    return True


def _question_database_path() -> Path:
    configured = os.environ.get("CAREER_OS_DB_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "data" / "career_jobs.sqlite"


def _read_question_rows() -> list[sqlite3.Row]:
    """Read the unified bank through a SQLite read-only connection."""

    path = _question_database_path()
    if not path.exists():
        return []
    try:
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            return connection.execute(
                """
                SELECT id, category, title, explanation, company_tags, question_type,
                       source_plugin, source_question_id
                FROM mock_questions
                WHERE LOWER(question_type) IN ('interview', 'choice', 'code')
                  AND source_plugin IS NOT NULL AND TRIM(source_plugin) <> ''
                ORDER BY CASE WHEN LOWER(question_type) = 'interview' THEN 0 ELSE 1 END, id
                """
            ).fetchall()
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [_text(item) for item in value if _text(item)]
    return []


def _split_questions(raw: Any) -> list[str]:
    """Parse guide questions without assuming one particular export format."""

    values = _as_list(raw)
    if values:
        lines: list[str] = []
        for value in values:
            lines.extend(value.splitlines())
    else:
        lines = _text(raw).splitlines()
    result: list[str] = []
    for line in lines:
        cleaned = re.sub(r"^\s*(?:[-*•●]|\d+[.、)])\s*", "", line).strip()
        if len(cleaned) >= 8:
            result.append(cleaned)
    if len(result) == 1:
        result = [piece.strip() for piece in re.split(r"[。！？；]", result[0]) if len(piece.strip()) >= 8]
    return result[:8]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalise_tracks(value: Any) -> list[dict[str, str]]:
    """Keep mapper track IDs and labels while accepting string shorthand."""

    if isinstance(value, Mapping):
        value = [value]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        value = [value] if value else []
    tracks: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, Mapping):
            track_id = _text(item.get("track_id", item.get("id", item.get("value"))))
            label = _text(item.get("label", track_id))
            track = {"track_id": track_id, "label": label or track_id}
            for key in ("question_families", "matched_signals", "practice"):
                values = _as_list(item.get(key))
                if values:
                    track[key] = values
        else:
            track_id = _text(item)
            label = track_id
        if track_id:
            tracks.append(track if isinstance(item, Mapping) else {"track_id": track_id, "label": label or track_id})
    return tracks


def _fallback_score(question: str, answer: str, *, follow_up: bool) -> dict[str, Any]:
    """Small offline fallback used only if the core rubric cannot be imported."""

    text = _text(answer)
    length = len(text)
    evidence = sum(term in text for term in ("指标", "测试", "验证", "复盘", "日志", "数据", "我负责"))
    structure = sum(term in text for term in ("首先", "然后", "最后", "取舍", "风险"))
    technical = min(100, 35 + evidence * 7 + (15 if length >= 80 else 0))
    expression = min(100, 35 + structure * 8 + (15 if 45 <= length <= 500 else 0))
    project = min(100, 30 + evidence * 9 + (12 if "项目" in text or "系统" in text else 0))
    follow_up_score = min(100, 30 + structure * 10 + (15 if follow_up and length >= 80 else 0))
    overall = round(technical * 0.4 + expression * 0.3 + project * 0.2 + follow_up_score * 0.1)
    return {
        "technical": technical,
        "expression": expression,
        "project": project,
        "follow_up": follow_up_score,
        "overall": overall,
        "focus": "技术细节" if technical == min(technical, expression, project, follow_up_score) else "项目证据",
        "provider": "local-rubric-fallback",
        "follow_up_turn": "yes" if follow_up else "no",
    }


class DeepInterviewAdapter:
    """A deep module behind the four-method interview-agent interface."""

    capability = "interview_agent"

    def __init__(self, manifest: Any = None):
        self.manifest = manifest
        self.plugin_id = _text(getattr(manifest, "plugin_id", "deepinterview")) or "deepinterview"
        self.provider = f"{self.plugin_id}-local-compat"

    def provide(self, capability: str) -> "DeepInterviewAdapter | None":
        return self if capability == self.capability else None

    def prepare(
        self,
        context: Mapping[str, Any] | None = None,
        *,
        job: Mapping[str, Any] | None = None,
        guide: Mapping[str, Any] | None = None,
        profile: Mapping[str, Any] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """Normalize JD, company guide and assessment profile into a session."""

        source = dict(_mapping(context))
        source.update(extra)
        job_data = dict(_mapping(job or source.get("job")))
        guide_data = dict(_mapping(guide or source.get("guide") or source.get("interview_guide")))
        profile_data = dict(_mapping(profile or source.get("assessment_profile") or source.get("profile")))
        guide_questions = _split_questions(
            guide_data.get("typical_questions", source.get("typical_questions"))
        )
        track_items = _normalise_tracks(profile_data.get("tracks", source.get("tracks")))
        families = _as_list(
            profile_data.get("question_families", source.get("question_families"))
        )
        if not families:
            for track in track_items:
                families.extend(_as_list(track.get("question_families")))
            families = list(dict.fromkeys(families))
        matched_signals = _as_list(profile_data.get("matched_signals", source.get("matched_signals")))
        if not matched_signals:
            for track in track_items:
                matched_signals.extend(_as_list(track.get("matched_signals")))
            matched_signals = list(dict.fromkeys(matched_signals))
        return {
            "contract_version": CONTRACT_VERSION,
            "provider": self.provider,
            "plugin_id": self.plugin_id,
            "external_service": False,
            "job": {
                "id": job_data.get("id"),
                "company_name": _text(job_data.get("company_name", source.get("company_name"))),
                "job_title": _text(job_data.get("job_title", source.get("job_title"))),
                "category": _text(job_data.get("category", source.get("category"))),
            },
            "tracks": track_items,
            "matched_signals": matched_signals,
            "question_families": families,
            "guide_questions": guide_questions,
            "guide_source": _text(guide_data.get("authentic_sources", source.get("authentic_sources"))),
        }

    def questions(self, prepared: Mapping[str, Any], *, limit: int = 4) -> list[dict[str, Any]]:
        """Select traceable guide/bank rows; never synthesize a question."""

        if limit <= 0:
            return []
        tracks = _normalise_tracks(prepared.get("tracks"))
        track_ids = [track["track_id"] for track in tracks]
        families = _as_list(prepared.get("question_families"))
        family_pairs: list[tuple[str, str]] = []
        for track in tracks:
            for family in _as_list(track.get("question_families")):
                family_pairs.append((family, track["track_id"]))
        if not family_pairs:
            family_pairs = [(family, track_ids[0] if track_ids else "") for family in families]

        def match_row(row: sqlite3.Row) -> tuple[int, int, str, str] | None:
            qtype = _text(row["question_type"]).casefold()
            tags = {_text(part).casefold() for part in _text(row["company_tags"]).split(",") if _text(part)}
            track_hits = sum(track.casefold() in tags for track in track_ids)
            if not track_hits:
                return None
            row_text = " ".join((_text(row["title"]), _text(row["explanation"])))
            if qtype != "interview":
                row_text = " ".join((_text(row["category"]), row_text))
            family_scores: list[tuple[int, str, str]] = []
            for family, track in family_pairs:
                if qtype == "interview" and not _interview_category_allowed(track, family, row["category"]):
                    continue
                score = sum(term.casefold() in row_text.casefold() for term in _question_terms(family))
                family_scores.append((score, family, track))
            score, family, track = max(family_scores, default=(0, "", ""))
            # An imported open-ended item must match a real family, not just a
            # broad tag (e.g. a volatile embedded item tagged with ops).
            if qtype == "interview" and score == 0:
                return None
            return score, track_hits, family, track

        bank: list[tuple[int, int, int, sqlite3.Row, str, str]] = []
        for row in _read_question_rows():
            match = match_row(row)
            if match is None:
                continue
            score, track_hits, family, track = match
            open_priority = 1 if _text(row["question_type"]).casefold() == "interview" else 0
            bank.append((open_priority, score, track_hits, row, family, track))
        bank.sort(key=lambda item: (-item[0], -item[1], -item[2], int(item[3]["id"])))

        selected: list[dict[str, Any]] = []
        seen_families: set[str] = set()
        for pass_no in (0, 1):
            for _open_priority, score, _track_hits, row, family, track in bank:
                if len(selected) >= limit:
                    break
                if pass_no == 0 and family and family in seen_families:
                    continue
                question_id = str(row["id"])
                source_plugin = _text(row["source_plugin"])
                source_question_id = _text(row["source_question_id"]) or f"mock_questions-{question_id}"
                selected.append({
                    "id": question_id,
                    "question_id": question_id,
                    "source": "mock_questions",
                    "source_plugin": source_plugin,
                    "source_question_id": source_question_id,
                    "question_type": _text(row["question_type"]) or "interview",
                    "category": _text(row["category"]),
                    "family": family or (families[0] if families else "岗位基础"),
                    "track": track or (track_ids[0] if track_ids else None),
                    "question": _text(row["title"]),
                    "match_score": str(score),
                })
                if family:
                    seen_families.add(family)
            if len(selected) >= limit:
                break

        # Company-guide entries remain supported, but are never fabricated and
        # carry an explicit synthetic source ID because they are not bank rows.
        guide_questions = _as_list(prepared.get("guide_questions"))
        for index, question in enumerate(guide_questions[:2]):
            if len(selected) >= limit:
                break
            guide_text = question.casefold()
            _score, family, _track = max(
                ((sum(term.casefold() in guide_text for term in _question_terms(item)), item, "") for item in families),
                default=(0, families[0] if families else "岗位基础", ""),
            )
            selected.insert(0, {
                "id": f"guide-{index + 1}",
                "question_id": f"guide-{index + 1}",
                "source": "company-guide",
                "source_plugin": "career-os-company-guide",
                "source_question_id": f"guide-{index + 1}",
                "question_type": "interview",
                "category": "公司面试指南",
                "family": family,
                "track": None,
                "question": question,
            })
            if len(selected) > limit:
                selected.pop()
        return selected[:limit]

    def score(
        self,
        prepared: Mapping[str, Any],
        question: Mapping[str, Any] | str,
        answer: str,
        *,
        follow_up: bool = False,
    ) -> dict[str, Any]:
        """Score one turn using Career OS local-rubric when available."""

        question_text = _text(question.get("question") if isinstance(question, Mapping) else question)
        answer_text = _text(answer)
        try:
            from bin.mock_interview_agent import score_answer

            result = dict(score_answer(question_text, answer_text, follow_up=follow_up))
        except (ImportError, AttributeError, TypeError):
            result = _fallback_score(question_text, answer_text, follow_up=follow_up)
        result.update({
            "contract_version": CONTRACT_VERSION,
            "provider": self.provider,
            "plugin_id": self.plugin_id,
            "scoring_engine": "local-rubric",
            "external_service": False,
            "track": (question.get("track") if isinstance(question, Mapping) else None),
        })
        return result

    def report(
        self,
        prepared: Mapping[str, Any],
        turns: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Aggregate turn scores without persisting or mutating caller data."""

        scores = [
            turn.get("score") if isinstance(turn.get("score"), Mapping) else turn.get("score_json")
            for turn in turns
        ]
        score_maps = []
        for score in scores:
            if isinstance(score, Mapping):
                score_maps.append(score)
            elif isinstance(score, str):
                try:
                    decoded = json.loads(score)
                except (TypeError, ValueError):
                    decoded = None
                if isinstance(decoded, Mapping):
                    score_maps.append(decoded)
        overall_values = [float(score["overall"]) for score in score_maps if isinstance(score.get("overall"), (int, float))]
        dimensions = {
            name: round(mean(float(score[name]) for score in score_maps if isinstance(score.get(name), (int, float))))
            if any(isinstance(score.get(name), (int, float)) for score in score_maps)
            else None
            for name in ("technical", "expression", "project", "follow_up")
        }
        average = round(mean(overall_values)) if overall_values else None
        return {
            "contract_version": CONTRACT_VERSION,
            "provider": self.provider,
            "plugin_id": self.plugin_id,
            "scoring_engine": "local-rubric",
            "external_service": False,
            "job": dict(_mapping(prepared.get("job"))),
            "tracks": _normalise_tracks(prepared.get("tracks")),
            "question_families": _as_list(prepared.get("question_families")),
            "turn_count": len(turns),
            "average_score": average,
            "dimensions": dimensions,
            "status": "completed" if turns else "empty",
        }


def create_plugin(manifest: Any = None) -> DeepInterviewAdapter:
    return DeepInterviewAdapter(manifest=manifest)
