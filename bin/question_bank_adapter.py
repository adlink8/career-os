"""统一题库适配器：将外部项目导出的 JSON/CSV 映射到 mock_questions。"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

try:
    from career_os_store import get_db
except ModuleNotFoundError:
    from bin.career_os_store import get_db


class QuestionBankAdapter:
    capability = "question_bank"

    def provide(self, capability: str):
        return self if capability == self.capability else None

    def load(self, source: str | Path, *, source_plugin: str = "external", apply: bool = True) -> int:
        path = Path(source)
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                questions = list(csv.DictReader(handle))
        else:
            raw = json.loads(path.read_text(encoding="utf-8"))
            questions = raw.get("questions", raw) if isinstance(raw, dict) else raw
        if not isinstance(questions, list):
            raise ValueError("题库必须是数组，或包含 questions 数组的 JSON 对象")

        if not apply:
            # 仍然走完整格式校验，但不触碰 SQLite。
            for index, raw in enumerate(questions, 1):
                self._normalize(raw, index)
            return len(questions)

        conn = get_db()
        imported = 0
        for index, raw in enumerate(questions, 1):
            if not isinstance(raw, dict):
                raise ValueError(f"第 {index} 题不是对象")
            question = self._normalize(raw, index)
            existing = conn.execute(
                "SELECT id FROM mock_questions WHERE source_plugin = ? AND source_question_id = ?",
                (source_plugin, question["source_question_id"]),
            ).fetchone()
            values = (
                question["category"], question["difficulty"], question["company_tags"], question["question_type"],
                question["title"], question["options_json"], question["correct_answer"], question["test_cases_json"],
                question["starter_code"], question["explanation"], source_plugin, question["source_question_id"],
                question["assessment_kind"], question["dimension"], question["reverse_scored"],
                question["scale_min"], question["scale_max"],
            )
            if existing:
                conn.execute(
                    """
                    UPDATE mock_questions SET category=?, difficulty=?, company_tags=?, question_type=?, title=?,
                        options_json=?, correct_answer=?, test_cases_json=?, starter_code=?, explanation=?,
                        assessment_kind=?, dimension=?, reverse_scored=?, scale_min=?, scale_max=?
                    WHERE id=?
                    """,
                    (*values[:10], *values[12:], existing[0]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO mock_questions
                        (category, difficulty, company_tags, question_type, title, options_json,
                         correct_answer, test_cases_json, starter_code, explanation, source_plugin, source_question_id,
                         assessment_kind, dimension, reverse_scored, scale_min, scale_max)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            imported += 1
        conn.commit()
        conn.close()
        return imported

    @staticmethod
    def _normalize(raw: dict[str, Any], index: int) -> dict[str, Any]:
        qtype = str(raw.get("question_type", raw.get("type", "choice"))).lower()
        if qtype in {"single", "multiple", "mcq"}:
            qtype = "choice"
        if qtype in {"likert", "scale", "personality_test"}:
            qtype = "personality"
        # `interview` is an open-ended prompt used by the text interview
        # runtime.  It deliberately has no options/correct answer, so it must
        # remain distinct from OA choice questions.  Existing question types
        # keep their previous normalization and validation behavior.
        if qtype not in {"choice", "code", "personality", "interview"}:
            raise ValueError(f"第 {index} 题 question_type 只支持 choice/code/personality/interview")
        title = str(raw.get("title", raw.get("question", ""))).strip()
        if not title:
            raise ValueError(f"第 {index} 题缺少 title/question")
        options = raw.get("options", raw.get("options_json", []))
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except json.JSONDecodeError:
                options = [part.strip() for part in options.split("|") if part.strip()]
        tests = raw.get("test_cases", raw.get("test_cases_json", []))
        if isinstance(tests, str):
            try:
                tests = json.loads(tests)
            except json.JSONDecodeError:
                tests = []
        try:
            scale_min = int(raw.get("scale_min", 1))
            scale_max = int(raw.get("scale_max", 5))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"第 {index} 题量表范围必须是整数") from exc
        if scale_max <= scale_min:
            raise ValueError(f"第 {index} 题量表范围必须满足 scale_max > scale_min")
        reverse_raw = raw.get("reverse_scored", raw.get("reverse", False))
        if isinstance(reverse_raw, str):
            reverse_scored = int(reverse_raw.strip().lower() in {"1", "true", "yes", "y"})
        else:
            reverse_scored = int(bool(reverse_raw))
        if qtype == "personality" and len(options) < 2:
            options = [str(i) for i in range(scale_min, scale_max + 1)]
        source_id = str(raw.get("source_question_id", raw.get("id", index)))
        return {
            "source_question_id": source_id,
            "category": str(raw.get("category", "通用")),
            "difficulty": str(raw.get("difficulty", "中")),
            "company_tags": str(raw.get("company_tags", raw.get("tags", ""))),
            "question_type": qtype,
            "title": title,
            "options_json": json.dumps(options, ensure_ascii=False),
            "correct_answer": str(raw.get("correct_answer", raw.get("answer", ""))),
            "test_cases_json": json.dumps(tests, ensure_ascii=False),
            "starter_code": str(raw.get("starter_code", raw.get("code", ""))),
            "explanation": str(raw.get("explanation", "")),
            "assessment_kind": str(raw.get("assessment_kind", "general")),
            "dimension": str(raw.get("dimension", "")),
            "reverse_scored": reverse_scored,
            "scale_min": scale_min,
            "scale_max": scale_max,
        }


def create_plugin(manifest=None):
    return QuestionBankAdapter()
