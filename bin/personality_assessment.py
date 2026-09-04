"""职业性格/工作风格测评。

这是一个可替换的深模块：题库适配器只需提供统一的 Likert 题字段，
调用方只需要 ``score_personality`` 或 ``run_personality_assessment``。
结果描述职业行为倾向，不做临床诊断，也不把分数当作录用结论。
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from career_os_store import add_timeline_event, get_db
except ModuleNotFoundError:
    from bin.career_os_store import add_timeline_event, get_db


DEFAULT_ASSESSMENT_KIND = "career-personality-v1"
FULL_ASSESSMENT_KIND = "career-personality-ipip-neo-120"
DISCLAIMER = "本测评仅用于职业准备与自我复盘，不是心理疾病筛查、人格诊断或录用结论。"

_DIMENSION_NOTES = {
    "执行与可靠性": "偏好明确目标、可验收交付和持续复盘的工作方式。",
    "协作与沟通": "更关注信息同步、倾听反馈和让团队形成共识。",
    "学习与开放性": "面对新工具、新领域和不确定任务时，倾向于保持探索。",
    "稳定与抗压": "在变化或压力场景下，更重视拆解问题、保持节奏和及时求助。",
    "主动与责任": "倾向于主动澄清目标、承担结果并推动问题闭环。",
    "情绪反应性": "更容易受到压力和情绪波动影响，需结合真实工作场景理解调节方式。",
}


def _value(question: Mapping[str, Any] | Any, key: str, default: Any = None) -> Any:
    """支持 dict、sqlite3.Row 和其他 Mapping-like 题目。"""

    if isinstance(question, Mapping):
        return question.get(key, default)
    try:
        return question[key]
    except (KeyError, IndexError, TypeError):
        return default


def _normalise_response(raw: Any, minimum: int, maximum: int) -> int:
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"回答必须是 {minimum}-{maximum} 的整数") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"回答必须是 {minimum}-{maximum} 的整数")
    return value


def score_personality(
    questions: Iterable[Mapping[str, Any] | Any],
    responses: Iterable[Any],
) -> dict[str, Any]:
    """把 Likert 回答转换为可复盘的职业行为倾向画像。

    接口约定：每道题包含 ``dimension``、``scale_min``、``scale_max`` 和
    ``reverse_scored``；回答顺序与题目顺序一致。函数无 SQLite 或终端副作用，
    因此既是运行时评分 seam，也是最小测试 seam。
    """

    question_list = list(questions)
    response_list = list(responses)
    if len(question_list) != len(response_list):
        raise ValueError("题目数量与回答数量不一致")
    if not question_list:
        raise ValueError("至少需要一道性格测评题")

    dimension_values: dict[str, list[float]] = defaultdict(list)
    answer_rows: list[dict[str, Any]] = []
    for index, (question, raw) in enumerate(zip(question_list, response_list), 1):
        minimum = int(_value(question, "scale_min", 1))
        maximum = int(_value(question, "scale_max", 5))
        if maximum <= minimum:
            raise ValueError(f"第 {index} 题量表范围无效")
        selected = _normalise_response(raw, minimum, maximum)
        reverse = bool(int(_value(question, "reverse_scored", 0) or 0))
        adjusted = minimum + maximum - selected if reverse else selected
        normalized = round((adjusted - minimum) / (maximum - minimum) * 100, 1)
        dimension = str(_value(question, "dimension", "未分类") or "未分类")
        dimension_values[dimension].append(normalized)
        answer_rows.append(
            {
                "question_id": _value(question, "id"),
                "selected": selected,
                "adjusted": adjusted,
                "normalized": normalized,
                "dimension": dimension,
                "reverse_scored": reverse,
            }
        )

    dimensions: dict[str, dict[str, Any]] = {}
    for dimension, values in dimension_values.items():
        score = round(sum(values) / len(values))
        if score >= 70:
            band = "较高倾向"
        elif score >= 40:
            band = "中等倾向"
        else:
            band = "较低倾向"
        dimensions[dimension] = {
            "score": score,
            "band": band,
            "item_count": len(values),
            "note": _DIMENSION_NOTES.get(dimension, "需要结合具体岗位和实际经历解释。"),
        }

    overall = round(sum(item["score"] for item in dimensions.values()) / len(dimensions))
    return {
        "overall": overall,
        "dimensions": dimensions,
        "answers": answer_rows,
        "completion_rate": 1.0,
        "disclaimer": DISCLAIMER,
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_personality_assessment(
    job_id: int | None = None,
    *,
    assessment_kind: str = DEFAULT_ASSESSMENT_KIND,
    responses: Iterable[Any] | None = None,
    input_fn: Callable[[str], str] = input,
) -> bool:
    """交互式运行一次性格测评并写入统一报告表。"""

    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, category, difficulty, company_tags, question_type, title,
               options_json, explanation, assessment_kind, dimension,
               reverse_scored, scale_min, scale_max
        FROM mock_questions
        WHERE question_type = 'personality' AND assessment_kind = ?
        ORDER BY id
        """,
        (assessment_kind,),
    ).fetchall()
    if not rows:
        conn.close()
        print(f"❌ 当前没有 {assessment_kind} 性格测评题。")
        return False

    print("\n" + "=" * 80)
    print("🧭 【职业性格与工作风格测评】")
    mode_label = "快测" if assessment_kind == DEFAULT_ASSESSMENT_KIND else ("IPIP-NEO-120 完整测评" if assessment_kind == FULL_ASSESSMENT_KIND else assessment_kind)
    print(f"🎯 模式: {mode_label} | 本次 {len(rows)} 题 | 1-5 分量表 | 结果会写入 mock_exam_records")
    print(f"ℹ️ {DISCLAIMER}")
    print("=" * 80 + "\n")

    iterator = iter(responses) if responses is not None else None
    selected: list[int] = []
    response_times: list[int] = []
    started_at = _now()
    try:
        for index, row in enumerate(rows, 1):
            minimum, maximum = int(row["scale_min"] or 1), int(row["scale_max"] or 5)
            print(f"📌 第 {index}/{len(rows)} 题 [{row['dimension'] or '未分类'}]")
            print(f"  {row['title']}")
            for option in json.loads(row["options_json"] or "[]"):
                print(f"    {option}")
            started = time.perf_counter()
            raw = next(iterator) if iterator is not None else input_fn("👉 请输入 1-5，或 Q 退出: ")
            response_ms = round((time.perf_counter() - started) * 1000)
            if str(raw).strip().upper() == "Q":
                print("❌ 测评已终止，未写入未完成记录。")
                conn.close()
                return False
            selected.append(_normalise_response(raw, minimum, maximum))
            response_times.append(response_ms)
            print("✅ 已记录\n")
    except (EOFError, KeyboardInterrupt, StopIteration):
        print("❌ 测评未完成，未写入未完成记录。")
        conn.close()
        return False
    except ValueError as exc:
        print(f"❌ {exc}；测评未完成，未写入记录。")
        conn.close()
        return False

    report = score_personality(rows, selected)
    job = None
    if job_id:
        job = conn.execute("SELECT id, company_name, job_title FROM jobs WHERE id = ?", (job_id,)).fetchone()
    cur = conn.execute(
        """
        INSERT INTO mock_exam_records
            (exam_type, score, total_score, pass_rate, details_json, job_id,
             provider, rubric_version, started_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "personality",
            report["overall"],
            100,
            float(report["overall"]),
            json.dumps({"assessment_kind": assessment_kind, **report}, ensure_ascii=False),
            job_id,
            "local-rubric",
            "personality-v1",
            started_at,
            _now(),
        ),
    )
    record_id = cur.lastrowid
    for index, (question, answer) in enumerate(zip(rows, report["answers"])):
        conn.execute(
            """
            INSERT INTO mock_exam_answers
                (exam_record_id, question_id, selected_answer, correct, response_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            (record_id, question["id"], str(answer["selected"]), 0, response_times[index]),
        )
    if job:
        add_timeline_event(
            conn,
            job_id=job["id"],
            company_name=job["company_name"],
            job_title=job["job_title"],
            event_type="职业性格测评完成",
            notes=f"综合倾向指数 {report['overall']}/100；仅作职业准备参考",
        )
    conn.commit()
    conn.close()

    print(f"\n🎉 测评完成！综合倾向指数: 【{report['overall']} / 100】")
    for dimension, item in report["dimensions"].items():
        print(f"  • {dimension}: {item['score']}（{item['band']}）")
    print(f"ℹ️ {DISCLAIMER}")
    return True


__all__ = ["DEFAULT_ASSESSMENT_KIND", "FULL_ASSESSMENT_KIND", "DISCLAIMER", "run_personality_assessment", "score_personality"]
