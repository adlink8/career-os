"""Build reproducible Career OS snapshots from cloned GitHub question sources.

The source checkouts live under ``tmp/github-question-sources`` and are never
read by the application at runtime.  This script only transforms verbatim
questions/answers into the project's traceable snapshot schema; it does not
author or paraphrase question content.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = ROOT / "tmp" / "github-question-sources"
DEFAULT_OUTPUT_ROOT = ROOT / "data"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_rapid_questions(path: Path) -> dict[int, str]:
    result: dict[int, str] = {}
    pattern = re.compile(r"^(\d+)\.\s+(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            result[int(match.group(1))] = match.group(2)
    if len(result) != 100:
        raise ValueError(f"rapid-fire question count mismatch: {len(result)}")
    return result


def _parse_rapid_answers(path: Path) -> dict[int, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    headings = list(enumerate(lines))
    found: list[tuple[int, int, str]] = []
    heading_re = re.compile(r"^\*\*(\d+)\.\s+(.+?)\*\*\s*$")
    for index, line in headings:
        match = heading_re.match(line.strip())
        if match:
            found.append((index, int(match.group(1)), match.group(2)))
    answers: dict[int, str] = {}
    for position, (start, number, _title) in enumerate(found):
        end = found[position + 1][0] if position + 1 < len(found) else len(lines)
        body = "\n".join(lines[start + 1 : end]).strip()
        body = re.sub(r"^---\s*$", "", body, flags=re.MULTILINE).strip()
        if body:
            answers[number] = body
    if len(answers) != 100:
        raise ValueError(f"rapid-fire answer count mismatch: {len(answers)}")
    return answers


def _parse_bug_hunts(path: Path) -> list[tuple[int, str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    found: list[tuple[int, int, str]] = []
    heading_re = re.compile(r"^##\s+Bug\s+(\d+)\s+[—-]\s+(.+?)\s*$")
    for index, line in enumerate(lines):
        match = heading_re.match(line.strip())
        if match:
            found.append((index, int(match.group(1)), match.group(2)))
    result: list[tuple[int, str, str]] = []
    for position, (start, number, title) in enumerate(found):
        end = found[position + 1][0] if position + 1 < len(found) else len(lines)
        body = "\n".join(lines[start + 1 : end]).strip()
        body = re.sub(r"^---\s*$", "", body, flags=re.MULTILINE).strip()
        if body:
            result.append((number, title, body))
    if len(result) != 20:
        raise ValueError(f"bug-hunt count mismatch: {len(result)}")
    return result


def _embedded_snapshot(source_root: Path) -> dict[str, Any]:
    repo = source_root / "embedded-interview-prep"
    rapid = repo / "13_Interview_QA" / "01_rapid_fire_100.md"
    answers = repo / "13_Interview_QA" / "answers" / "01_rapid_fire_100_answers.md"
    bugs = repo / "13_Interview_QA" / "02_bug_hunt_collection.md"
    questions = _parse_rapid_questions(rapid)
    answer_map = _parse_rapid_answers(answers)

    sections = (
        (1, 20, "嵌入式 C/C++ 与内存", "C Language"),
        (21, 35, "嵌入式中断与 ISR", "Interrupts and ISR"),
        (36, 50, "嵌入式内存与链接", "Memory"),
        (51, 70, "串口/CAN/MQTT/通信协议", "Peripherals and Protocols"),
        (71, 82, "嵌入式 Linux/FreeRTOS/RTOS", "RTOS"),
        (83, 91, "嵌入式 Linux/调试", "Linux Embedded"),
        (92, 100, "测试与嵌入式故障调试", "Testing and Debug"),
    )

    def section_for(number: int) -> tuple[str, str]:
        for start, end, category, module in sections:
            if start <= number <= end:
                return category, module
        raise AssertionError(number)

    items: list[dict[str, Any]] = []
    for number in range(1, 101):
        category, module = section_for(number)
        tags = "iot-embedded,technical-support-fae"
        if 92 <= number <= 100:
            tags += ",software-testing-ops"
        items.append(
            {
                "source_question_id": f"embedded-interview-prep-rapid-{number:03d}",
                "question_type": "interview",
                "assessment_kind": "technical-interview",
                "category": category,
                "difficulty": "中",
                "company_tags": tags,
                "title": questions[number],
                "source_text": questions[number],
                "explanation": answer_map[number],
                "source_file": "13_Interview_QA/01_rapid_fire_100.md",
                "source_module": module,
                "source_question_number": number,
            }
        )

    for number, title, body in _parse_bug_hunts(bugs):
        items.append(
            {
                "source_question_id": f"embedded-interview-prep-bug-{number:03d}",
                "question_type": "interview",
                "assessment_kind": "technical-interview",
                "category": "嵌入式故障排查与生产 Bug",
                "difficulty": "中",
                "company_tags": "iot-embedded,technical-support-fae",
                "title": f"Bug {number} — {title}",
                "source_text": f"Bug {number} — {title}",
                "explanation": body,
                "source_file": "13_Interview_QA/02_bug_hunt_collection.md",
                "source_module": "Bug Hunt Collection",
                "source_question_number": number,
            }
        )

    return {
        "name": "github-embedded-interview-prep",
        "schema": "interview_questions-v1",
        "description": "Embedded interview-prep rapid-fire and bug-hunt questions; verbatim snapshot, no generated prompts.",
        "source": {
            "repository": "https://github.com/Amir7698/embedded-interview-prep",
            "reference": "https://github.com/Amir7698/embedded-interview-prep/tree/main/13_Interview_QA",
            "license": "MIT",
            "license_evidence": "https://github.com/Amir7698/embedded-interview-prep#license",
            "retrieved_at": "2026-09-03",
            "content_note": "上游 README 声明 MIT；当前仓库快照未包含独立 LICENSE 文件，使用时保留该来源边界。",
        },
        "questions": items,
    }


def _exam_snapshot(source_root: Path) -> dict[str, Any]:
    repo = source_root / "exam-questions"
    files = (
        repo / "cuetmca" / "cuet_cs_mock1.json",
        repo / "nimcet" / "nimcet_mock1.json",
    )
    items: list[dict[str, Any]] = []
    answer_letters = "ABCD"
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for section in payload.get("sections", []):
            section_name = str(section.get("section_name", "通用能力"))
            for question in section.get("questions", []):
                options = question.get("options") or []
                option_texts = [str(item.get("text", "")) for item in options]
                correct_id = str(question.get("correct_opt_id", ""))
                try:
                    answer = answer_letters[int(correct_id) - 1]
                except (ValueError, IndexError) as exc:
                    raise ValueError(f"invalid answer in {path}: {question.get('q_id')}") from exc
                if len(option_texts) < 2 or not question.get("explanation"):
                    raise ValueError(f"incomplete question in {path}: {question.get('q_id')}")
                if section_name == "Computer Awareness":
                    category = "计算机基础与数字能力"
                elif section_name == "Mathematics":
                    category = "数量与数学推理"
                elif "Thinking" in section_name or "Reasoning" in section_name:
                    category = "逻辑推理与情景判断"
                else:
                    category = section_name
                items.append(
                    {
                        "source_question_id": f"exam-questions-{path.stem}-{question.get('q_id')}",
                        "question_type": "choice",
                        "assessment_kind": "online-aptitude",
                        "category": category,
                        "difficulty": str(question.get("difficulty") or payload.get("difficulty") or "中"),
                        "company_tags": "通用,software-testing-ops,data-analysis,technical-support-fae,iot-embedded,ai-rag",
                        "title": str(question.get("question_text", "")).strip(),
                        "source_text": str(question.get("question_text", "")).strip(),
                        "options": option_texts,
                        "answer": answer,
                        "explanation": str(question.get("explanation", "")).strip(),
                        "source_file": path.relative_to(repo).as_posix(),
                        "source_module": section_name,
                        "source_question_number": str(question.get("q_id", "")),
                    }
                )
    return {
        "name": "github-exam-questions-aptitude",
        "description": "MIT-licensed structured CUET MCA/NIMCET mock questions for generic online-assessment practice.",
        "source": {
            "repository": "https://github.com/AdithSuresh2004/exam-questions",
            "reference": "https://github.com/AdithSuresh2004/exam-questions/tree/main",
            "license": "MIT",
            "license_evidence": "https://github.com/AdithSuresh2004/exam-questions/blob/main/LICENCE",
            "retrieved_at": "2026-09-03",
            "content_note": "仅导入包含完整选项、答案和解释的 cuet_cs_mock1 与 nimcet_mock1；未导入缺少答案解释的 nimcet_mock2。",
        },
        "questions": items,
    }


def _bigfive_snapshot(source_root: Path) -> dict[str, Any]:
    repo = source_root / "bigfive-web"
    path = repo / "old-packages" / "questions" / "data" / "en" / "questions.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if len(raw) != 120:
        raise ValueError(f"IPIP-NEO question count mismatch: {len(raw)}")
    dimensions = {
        "O": "开放性",
        "C": "尽责性",
        "E": "外向性",
        "A": "宜人性",
        "N": "情绪反应性",
    }
    options = [
        "1. Very Inaccurate",
        "2. Moderately Inaccurate",
        "3. Neither Accurate Nor Inaccurate",
        "4. Moderately Accurate",
        "5. Very Accurate",
    ]
    items: list[dict[str, Any]] = []
    for index, question in enumerate(raw, 1):
        domain = str(question.get("domain", ""))
        items.append(
            {
                "source_question_id": f"bigfive-web-ipip-neo-120-{index:03d}",
                "question_type": "personality",
                "assessment_kind": "career-personality-ipip-neo-120",
                "category": "心理/性格测评 · IPIP-NEO-120",
                "difficulty": "不适用",
                "company_tags": "通用,技术岗,项目协作",
                "dimension": dimensions.get(domain, domain),
                "title": str(question.get("text", "")).strip(),
                "source_text": str(question.get("text", "")).strip(),
                "options": options,
                "reverse_scored": str(question.get("keyed", "plus")).lower() == "minus",
                "scale_min": 1,
                "scale_max": 5,
                "explanation": "IPIP-NEO-120 public-domain item; keyed direction preserved from upstream.",
                "source_file": "old-packages/questions/data/en/questions.json",
                "source_module": "IPIP-NEO-120",
                "source_question_number": index,
            }
        )
    return {
        "name": "github-bigfive-web-ipip-neo-120",
        "description": "IPIP-NEO-120 public-domain English personality items; kept as a separate traceable batch under the career-personality assessment kind.",
        "source": {
            "repository": "https://github.com/rubynor/bigfive-web",
            "reference": "https://github.com/rubynor/bigfive-web/tree/master/old-packages/questions/data/en",
            "license": "MIT",
            "license_evidence": "https://github.com/rubynor/bigfive-web/blob/master/LICENSE",
            "item_basis": "IPIP public-domain items; upstream README attributes the inventory to IPIP-NEO.",
            "item_basis_evidence": "https://ipip.ori.org/newPermission.htm",
            "retrieved_at": "2026-09-03",
        },
        "questions": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    outputs = (
        ("question-bank.github-embedded-interview-prep.json", _embedded_snapshot(args.source_root)),
        ("question-bank.github-exam-questions-aptitude.json", _exam_snapshot(args.source_root)),
        ("personality-bank.github-bigfive-web-ipip-neo-120.json", _bigfive_snapshot(args.source_root)),
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    for filename, payload in outputs:
        path = args.output_root / filename
        _write_json(path, payload)
        print(f"wrote {path}: {len(payload['questions'])} questions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
