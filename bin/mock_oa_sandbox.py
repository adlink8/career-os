"""线上笔试/代码题运行器。

客观题和代码题都写入 Career OS 的本地报告表。代码执行默认要求配置
Judge0 插件/服务；只有显式 ``--trusted-local`` 才允许本机受信代码进程。
"""

from __future__ import annotations

import json
import random
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

try:
    from career_os_store import add_timeline_event, get_db
    from code_runner import configured_runner
    from jd_assessment_mapper import infer_assessment_profile
    from services.job_service import JobService
except ModuleNotFoundError:
    from bin.career_os_store import add_timeline_event, get_db
    from bin.code_runner import configured_runner
    from bin.jd_assessment_mapper import infer_assessment_profile
    from bin.services.job_service import JobService


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _job_context(conn, job_id: int | None):
    if not job_id:
        return None
    return JobService.get_job(int(job_id), conn=conn)


def _job_question_tracks(conn, job_id: int | None) -> list[str]:
    """Return specialized JD tracks for a job; an unknown job keeps the global pool."""

    if not job_id:
        return []
    row = JobService.get_job(int(job_id), conn=conn)
    if not row:
        return []
    profile = infer_assessment_profile(row)
    return [track["track_id"] for track in profile["tracks"] if track["track_id"] != "general-graduate"]


def select_choice_questions(rows, *, limit: int | None = 30, seed: int | None = None):
    """Select a realistic, reproducible exam slice from the matching pool.

    The pool is stratified by category and sampled round-robin so a large
    single source/category cannot crowd out the rest of a JD-targeted exam.
    ``limit=None`` explicitly requests the complete pool for audit/research.
    """

    pool = list(rows)
    if limit is None:
        return pool
    if limit <= 0:
        raise ValueError("limit 必须是正整数，或使用 None 表示全量题池")
    if limit >= len(pool):
        return pool

    rng = random.Random(seed)
    groups = defaultdict(list)
    for row in pool:
        category = str(row["category"] if hasattr(row, "keys") else row[1] or "未分类")
        groups[category].append(row)
    categories = list(groups)
    rng.shuffle(categories)
    for category in categories:
        rng.shuffle(groups[category])

    selected = []
    while len(selected) < limit:
        progressed = False
        for category in categories:
            if groups[category] and len(selected) < limit:
                selected.append(groups[category].pop())
                progressed = True
        if not progressed:
            break
    return selected


def run_choice_quiz(
    job_id: int | None = None,
    *,
    limit: int | None = 30,
    duration_minutes: int | None = 30,
    seed: int | None = None,
):
    """运行客观题模拟，并持久化答题明细/错题。"""

    conn = get_db()
    tracks = _job_question_tracks(conn, job_id)
    where = "question_type = 'choice'"
    params: list[str] = []
    if tracks:
        where += " AND (" + " OR ".join("company_tags LIKE ?" for _ in tracks) + ")"
        params.extend(f"%{track}%" for track in tracks)
    rows = conn.execute(
        f"""
        SELECT id, category, difficulty, company_tags, source_plugin, title, options_json,
               correct_answer, explanation
        FROM mock_questions WHERE {where} ORDER BY id
        """,
        params,
    ).fetchall()
    started_at = _now()
    job = _job_context(conn, job_id)
    if not rows:
        conn.close()
        print("❌ 当前没有可用客观题。")
        return False

    print("\n" + "=" * 80)
    print("📝 【校招线上笔试模拟 · 客观题】")
    scope = "；JD 定向: " + "/".join(tracks) if tracks else "；全量题池"
    try:
        selected_rows = select_choice_questions(rows, limit=limit, seed=seed)
    except ValueError as exc:
        conn.close()
        print(f"❌ {exc}")
        return False
    deadline = None
    if duration_minutes is not None:
        if duration_minutes <= 0:
            conn.close()
            print("❌ duration_minutes 必须是正整数，或使用 None 表示不限时。")
            return False
        deadline = time.monotonic() + duration_minutes * 60
    limit_label = "全量题池" if limit is None else f"抽取 {len(selected_rows)} 题"
    timer_label = "不限时" if duration_minutes is None else f"建议限时 {duration_minutes} 分钟"
    print(f"🎯 题池 {len(rows)} 题 | 本次 {limit_label} | 每题 20 分 | {timer_label} | 结果会写入 mock_exam_records{scope}")
    if seed is not None:
        print(f"🎲 抽题种子: {seed}")
    print("=" * 80 + "\n")

    score = 0
    answers: list[dict] = []
    for idx, row in enumerate(selected_rows, 1):
        if deadline is not None and time.monotonic() >= deadline:
            conn.close()
            print("⏰ 已超过模拟笔试时限，未写入未完成记录。")
            return False
        qid, cat, diff, tags, source_plugin, title, opt_json, correct, explanation = row
        print(f"📌 第 {idx}/{len(selected_rows)} 题 [{cat} · {diff}] (标签: {tags})")
        print(f"  {title}")
        for opt in json.loads(opt_json or "[]"):
            print(f"    {opt}")
        question_started = time.perf_counter()
        try:
            selected = input("\n👉 请输入 A/B/C/D，或 Q 退出: ").strip().upper()
        except (EOFError, KeyboardInterrupt, StopIteration):
            selected = "Q"
        response_ms = round((time.perf_counter() - question_started) * 1000)
        if deadline is not None and time.monotonic() >= deadline:
            conn.close()
            print("⏰ 已超过模拟笔试时限，未写入未完成记录。")
            return False
        if selected == "Q":
            conn.close()
            print("❌ 模拟笔试已终止，未写入未完成记录。")
            return False
        is_correct = selected == str(correct).upper()
        if is_correct:
            score += 20
            print(f"✅ 回答正确！(+20 分)\n💡 {explanation}\n")
        else:
            print(f"❌ 回答错误，正确答案: 【{correct}】\n💡 {explanation}\n")
        answers.append({"question_id": qid, "selected_answer": selected, "correct": is_correct, "response_ms": response_ms})
        print("-" * 80)

    total = len(selected_rows) * 20
    pass_rate = round(score / total * 100, 1) if total else 0.0
    details = {
        "answers": answers,
        "question_count": len(selected_rows),
        "pool_question_count": len(rows),
        "question_ids": [row["id"] for row in selected_rows],
        "question_sources": sorted({str(row["source_plugin"] or "unknown") for row in selected_rows}),
        "limit": limit,
        "duration_minutes": duration_minutes,
        "seed": seed,
        "job_id": job_id,
    }
    cur = conn.execute(
        """
        INSERT INTO mock_exam_records
            (exam_type, score, total_score, pass_rate, details_json, job_id,
             provider, rubric_version, started_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("choice", score, total, pass_rate, json.dumps(details, ensure_ascii=False), job_id,
         "local-rubric", "oa-v1", started_at, _now()),
    )
    record_id = cur.lastrowid
    for item in answers:
        conn.execute(
            """
            INSERT INTO mock_exam_answers
                (exam_record_id, question_id, selected_answer, correct, response_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            (record_id, item["question_id"], item["selected_answer"], int(item["correct"]), item["response_ms"]),
        )
    if job:
        add_timeline_event(conn, job_id=job["id"], company_name=job["company_name"], job_title=job["job_title"],
                           event_type="模拟笔试完成", notes=f"得分 {score}/{total}，得分率 {pass_rate}%")
    conn.commit()
    conn.close()

    print(f"\n🎉 笔试结束！最终得分: 【{score} / {total}】（得分率: {pass_rate}%）")
    print("🌟 结果已保存，可通过查询 mock_exam_records/mock_exam_answers 复盘错题。" if pass_rate >= 60 else "⚠️ 结果已保存，请优先复盘错题。")
    return True


def run_code_sandbox(question_id: int = 5, trusted_local: bool = False, job_id: int | None = None):
    """运行代码题。无 Judge0 时必须显式传 trusted_local。"""

    conn = get_db()
    row = conn.execute(
        "SELECT title, starter_code, test_cases_json, explanation FROM mock_questions WHERE id = ? AND question_type = 'code'",
        (question_id,),
    ).fetchone()
    job = _job_context(conn, job_id)
    if not row:
        conn.close()
        print("❌ 未找到指定的编程题！")
        return False

    runner = configured_runner(trusted_local=trusted_local)
    if runner is None:
        conn.close()
        print("🛡️ 未执行：当前没有启用 code_runner 插件。请配置 JUDGE0_URL 并启用 judge0，或显式使用 --trusted-local。")
        return False

    title, starter, tc_json, explanation = row
    test_cases = json.loads(tc_json or "[]")
    print("\n" + "=" * 80)
    print(f"💻 【代码题判题】: {title}")
    print(f"🔌 执行后端: {runner.name}")
    print("=" * 80)
    result = runner.run(starter or "", test_cases)
    for case in result.cases:
        mark = "✅ PASS" if case.get("passed") else "❌ FAIL"
        print(f"  {mark} Test Case #{case.get('index')}: 期望={case.get('expected')} 实际={case.get('actual', case.get('error'))}")
    print("-" * 80)
    print(f"判题结果: 【{result.status}】 | 耗时 {result.elapsed_ms} ms")
    if result.error:
        print(f"错误: {result.error}")
    print(f"💡 {explanation}")

    details = {"question_id": question_id, "cases": result.cases, "error": result.error}
    cur = conn.execute(
        """
        INSERT INTO mock_exam_records
            (exam_type, score, total_score, pass_rate, details_json, job_id,
             provider, rubric_version, started_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("code", 100 if result.passed else 0, 100, 100.0 if result.passed else 0.0,
         json.dumps(details, ensure_ascii=False), job_id, runner.name, "code-v1", _now(), _now()),
    )
    conn.execute(
        "INSERT INTO mock_exam_answers (exam_record_id, question_id, selected_answer, correct) VALUES (?, ?, ?, ?)",
        (cur.lastrowid, question_id, result.status, int(result.passed)),
    )
    if job:
        add_timeline_event(conn, job_id=job["id"], company_name=job["company_name"], job_title=job["job_title"],
                           event_type="模拟代码题完成", notes=f"{result.status}，后端 {runner.name}")
    conn.commit()
    conn.close()
    return result.passed


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "code":
        qid = int(sys.argv[2]) if len(sys.argv) > 2 else 11
        trusted = "--trusted-local" in sys.argv[3:]
        raise SystemExit(0 if run_code_sandbox(qid, trusted_local=trusted) else 1)
    raise SystemExit(0 if run_choice_quiz() else 1)
