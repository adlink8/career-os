"""测试共用假引擎与 JSON 写入。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def fake_ats(score: int, verdict: str):
    class FakeEngine:
        def __init__(self, *args, **kwargs):
            pass

        def run_full_diagnosis(self):
            return {
                "total_score": score,
                "verdict": verdict,
                "status_text": verdict,
                "sub_scores": {
                    "knockout": {"score": 5, "max": 5, "warnings": [], "critical": []},
                    "keywords_grounding": {
                        "score": 10,
                        "missing": ["Kubernetes"],
                        "grounded": ["Linux"],
                        "skill_only": [],
                    },
                    "project_alignment": {"score": 10, "notes": ["第一项目错位"]},
                    "star_and_evidence": {"score": 5, "notes": []},
                    "parsability": {"score": 8, "notes": []},
                },
            }

    return FakeEngine


def review(role: str, score: int, verdict: str, extra=None) -> dict:
    payload = {"agent_role": role, "score": score, "verdict": verdict}
    if extra:
        payload.update(extra)
    return payload
