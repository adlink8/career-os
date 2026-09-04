"""Career OS 文本模拟面试 Agent。

问题来自企业指南与候选人画像，回答按 interview-master 的四维 rubric
评分，并将每一轮写入 SQLite。没有外部模型时使用可解释的本地评分器；
因此不会伪造“AI 已理解”或固定高分。
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone

try:
    from career_os_store import add_timeline_event, get_db
except ModuleNotFoundError:
    from bin.career_os_store import add_timeline_event, get_db

try:
    from jd_assessment_mapper import infer_assessment_profile
except ModuleNotFoundError:
    from bin.jd_assessment_mapper import infer_assessment_profile

try:
    from career_os_plugins import get_plugin_manager
except ModuleNotFoundError:
    from bin.career_os_plugins import get_plugin_manager


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RUBRIC_VERSION = "interview-v1"


def _clean(value: object) -> str:
    """替换历史数据库/控制台输入中的孤立 surrogate，保证 UTF-8 可持久化。"""
    return str(value or "").encode("utf-8", "replace").decode("utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _split_questions(raw: str | None) -> list[str]:
    if not raw:
        return []
    chunks: list[str] = []
    for line in raw.splitlines():
        line = re.sub(r"^\s*(?:[-*•●]|\d+[.、)])\s*", "", line).strip()
        if len(line) >= 8:
            chunks.append(line)
    if len(chunks) == 1:
        chunks = [piece.strip() for piece in re.split(r"[。！？；]", chunks[0]) if len(piece.strip()) >= 8]
    return chunks[:4]


def score_answer(question: str, answer: str, *, follow_up: bool = False) -> dict[str, int | str]:
    """可解释的离线评分器，维度与 career-interview-master 保持一致。"""

    text = answer.strip()
    length = len(text)
    technical_terms = ("Linux", "SQLite", "SQL", "MQTT", "HTTP", "TCP", "Docker", "Kubernetes", "Python", "日志", "事务", "索引", "并发", "监控", "故障")
    evidence_terms = ("我负责", "实现", "部署", "指标", "延迟", "吞吐", "数据", "线上", "复盘", "测试", "百分", "%", "秒", "条")
    structure_terms = ("首先", "然后", "最后", "因为", "所以", "但是", "取舍", "结论", "风险", "验证")
    tech_hits = sum(1 for term in technical_terms if term.lower() in text.lower())
    evidence_hits = sum(1 for term in evidence_terms if term in text)
    structure_hits = sum(1 for term in structure_terms if term in text)
    technical = min(100, 35 + tech_hits * 8 + evidence_hits * 4 + (10 if length >= 80 else 0))
    expression = min(100, 35 + (15 if 45 <= length <= 500 else 5 if length else 0) + structure_hits * 7 + (8 if re.search(r"[。！？]", text) else 0))
    project = min(100, 30 + evidence_hits * 9 + (12 if "项目" in text or "系统" in text else 0) + (8 if length >= 100 else 0))
    followup_score = min(100, 30 + structure_hits * 10 + (15 if any(x in text for x in ("为什么", "取舍", "边界", "回滚", "监控")) else 0) + (10 if length >= 80 else 0))
    overall = round(technical * 0.4 + expression * 0.3 + project * 0.2 + followup_score * 0.1)
    weakest = min((technical, expression, project, followup_score))
    focus = "技术细节" if weakest == technical else "表达结构" if weakest == expression else "项目证据" if weakest == project else "追问与取舍"
    return {
        "technical": technical,
        "expression": expression,
        "project": project,
        "follow_up": followup_score,
        "overall": overall,
        "focus": focus,
        "provider": "local-rubric",
        "follow_up_turn": "yes" if follow_up else "no",
    }


def _grade(score: int) -> str:
    if score >= 90:
        return "S"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def _find_company(conn, target: str):
    if str(target).isdigit():
        return conn.execute(
            """
            SELECT c.id, c.name, g.typical_questions, g.score_weights, g.avoid_pitfalls
            FROM companies c LEFT JOIN company_interview_guides g ON c.id = g.company_id
            WHERE c.id = ?
            """, (int(target),)
        ).fetchone()
    return conn.execute(
        """
        SELECT c.id, c.name, g.typical_questions, g.score_weights, g.avoid_pitfalls
        FROM companies c LEFT JOIN company_interview_guides g ON c.id = g.company_id
        WHERE c.name LIKE ? OR c.alias LIKE ?
        """, (f"%{target}%", f"%{target}%")
    ).fetchone()


# The question bank is an OA source, while the interview remains text based.
# These terms provide a deterministic bridge from the mapper's explainable
# families to existing question rows without inventing a new question bank.
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
    """Return matching terms for a mapper family, with a safe generic fallback."""

    if family in _FAMILY_TERMS:
        return _FAMILY_TERMS[family]
    return tuple(part.casefold() for part in re.split(r"[/、（）()\s]+", family) if len(part) >= 2)


def _interview_category_allowed(track: str, family: str, category: str) -> bool:
    """Apply an explainable domain guard to imported open-ended questions."""

    track_text = _clean(track).casefold()
    family_text = _clean(family).casefold()
    category_text = _clean(category).casefold()
    if track_text == "data-analysis":
        # Data roles may still consume a RAG/Agent item when the JD family
        # explicitly asks for it, but generic data tags must not pull one in.
        if any(token in category_text for token in ("rag", "agent")):
            return any(token in family_text for token in ("rag", "agent"))
    if track_text == "software-testing-ops":
        if any(token in category_text for token in ("c 语言", "c/c++", "c++", "freertos", "rtos", "串口", "嵌入式")):
            return False
    return True


def _row_question_text(row) -> str:
    return " ".join(_clean(row[key]) for key in ("category", "title", "explanation")).casefold()


def _select_jd_questions(conn, profile: dict) -> tuple[list[str], list[dict[str, str]]]:
    """Select existing guide/bank questions and retain their provenance."""

    families = [str(item) for item in profile.get("question_families", [])]
    tracks = [str(item.get("track_id")) for item in profile.get("tracks", [])]
    family_pairs = [
        (str(family), str(track.get("track_id")))
        for track in profile.get("tracks", [])
        for family in track.get("question_families", [])
    ] or [(family, tracks[0] if tracks else "") for family in families]
    guide_questions = _split_questions(profile.get("typical_questions"))
    guide_id_prefix = (
        f"career-os-company-guide/company-{profile.get('company_id')}-guide-"
        if profile.get("company_id") is not None
        else "career-os-company-guide/guide-"
    )
    candidates = conn.execute(
        """
        SELECT id, category, title, explanation, company_tags, question_type,
               source_plugin, source_question_id
        FROM mock_questions
        WHERE LOWER(question_type) IN ('interview', 'choice', 'code')
        ORDER BY CASE WHEN LOWER(question_type) = 'interview' THEN 0 ELSE 1 END, id
        """
    ).fetchall()

    bank: list[tuple[int, int, int, object, str, str]] = []
    for row in candidates:
        text = _row_question_text(row)
        if _clean(row["question_type"]).casefold() == "interview":
            # For open-ended imports, score the actual prompt/explanation;
            # category labels can be broad (e.g. "数据与评测") and otherwise
            # create false family hits for an unrelated RAG item.
            text = " ".join((_clean(row["title"]), _clean(row["explanation"]))).casefold()
        tags = {part.strip() for part in _clean(row["company_tags"]).split(",") if part.strip()}
        track_hits = sum(track in tags for track in tracks)
        if not track_hits:
            continue
        family_scores = []
        for family, track in family_pairs:
            if (
                _clean(row["question_type"]).casefold() == "interview"
                and not _interview_category_allowed(track, family, row["category"])
            ):
                continue
            family_scores.append((sum(term.casefold() in text for term in _question_terms(family)), family, track))
        score, family, _track = max(family_scores, default=(0, "", ""))
        # Open-ended interview imports must match an actual JD family.  A
        # broad track tag alone is insufficient (for example, a RAG item may
        # also be tagged data-analysis, or a volatile item software-testing).
        if _clean(row["question_type"]).casefold() == "interview" and score == 0:
            continue
        # A tagged row with no family hit remains a useful fallback, but rows
        # that explain the selected family always rank above it.
        if score or track_hits:
            open_priority = 1 if _clean(row["question_type"]).casefold() == "interview" else 0
            bank.append((open_priority, score, track_hits, row, family, text))
    bank.sort(key=lambda item: (-item[0], -item[1], -item[2], int(item[3]["id"])))

    selected: list[dict[str, str]] = []
    seen_families: set[str] = set()
    for _open_priority, score, _track_hits, row, family, _text in bank:
        if len(selected) >= 2:
            break
        if family and family in seen_families:
            continue
        family_label = family or (families[0] if families else "岗位基础")
        selected.append(
            {
                "source": "mock_questions",
                "question_id": str(row["id"]),
                "source_plugin": _clean(row["source_plugin"]) or "mock_questions",
                "source_question_id": _clean(row["source_question_id"]) or f"mock_questions-{row['id']}",
                "question_type": _clean(row["question_type"]) or "interview",
                "family": family_label,
                "category": _clean(row["category"]),
                "question": _clean(row["title"]),
                "match_score": str(score),
            }
        )
        seen_families.add(family_label)

    # Rank company-guide questions against the same families. Company guides
    # are the highest-signal source; the bank supplies an additional JD lens.
    guide_ranked = []
    for index, question in enumerate(guide_questions):
        text = question.casefold()
        score, family, _track = max(
            ((sum(term.casefold() in text for term in _question_terms(item)), item, "") for item in families),
            default=(0, "岗位基础", ""),
        )
        guide_ranked.append((-score, index, question, family))
    guide_ranked.sort()

    questions: list[str] = []
    provenance: list[dict[str, str]] = []
    if guide_ranked:
        _, guide_index, question, family = guide_ranked[0]
        questions.append(question)
        provenance.append(
            {
                "source": "company_interview_guide",
                "source_plugin": "career-os-company-guide",
                "source_question_id": f"{guide_id_prefix}{guide_index + 1}",
                "question_type": "interview",
                "family": family,
                "question": question,
            }
        )
    if selected:
        item = selected[0]
        questions.append(f"岗位专项追问（{item['family']}）：{item['question']}")
        provenance.append(item)
    if len(guide_ranked) > 1:
        _, guide_index, question, family = guide_ranked[1]
        questions.append(question)
        provenance.append(
            {
                "source": "company_interview_guide",
                "source_plugin": "career-os-company-guide",
                "source_question_id": f"{guide_id_prefix}{guide_index + 1}",
                "question_type": "interview",
                "family": family,
                "question": question,
            }
        )
    elif len(selected) > 1:
        item = selected[1]
        questions.append(f"岗位专项追问（{item['family']}）：{item['question']}")
        provenance.append(item)
    if not questions:
        questions.append("请结合该岗位 JD，说明你会如何拆解任务、验证结果并处理风险。")
        provenance.append(
            {
                "source": "fallback",
                "source_plugin": "career-os-core",
                "source_question_id": "career-os-core/jd-fallback",
                "question_type": "interview",
                "family": families[0] if families else "岗位基础",
                "question": questions[0],
            }
        )
    return questions[:3], provenance[:3]


def _try_interview_plugin(
    *,
    job: object,
    guide: dict[str, str],
    profile: dict | None,
) -> tuple[object | None, dict | None, list[dict], str | None]:
    """Resolve and prepare the active interview_agent capability.

    Plugin manifests are opt-in.  Preparation is isolated here so an invalid
    entrypoint or incompatible adapter falls back before any user input or DB
    write occurs.
    """

    try:
        agent = get_plugin_manager().capability("interview_agent")
        if agent is None:
            return None, None, [], None
        job_data = dict(job) if hasattr(job, "keys") else {}
        prepared = agent.prepare(job=job_data, guide=guide, profile=profile or {})
        raw_questions = agent.questions(prepared, limit=6)
        if not isinstance(raw_questions, list):
            raise TypeError("interview_agent.questions 必须返回 list")
        questions: list[dict] = []
        for item in raw_questions:
            if isinstance(item, str):
                question = _clean(item)
                questions.append({"question": question, "source": "plugin"})
            elif isinstance(item, dict) and _clean(item.get("question")):
                normalized = dict(item)
                normalized["question"] = _clean(normalized["question"])
                questions.append(normalized)
        if not questions:
            raise ValueError("interview_agent.questions 未返回可用问题")
        # Keep at least one company-guide question and one plugin-generated
        # track/family prompt when the adapter returned both kinds.  This makes
        # the active plugin visible in the actual interview, not only in the
        # persisted metadata.
        if len(questions) > 3:
            guide = [item for item in questions if _clean(item.get("source")) == "company-guide"]
            generated = [item for item in questions if _clean(item.get("source")) != "company-guide"]
            questions = (guide[:1] + generated[:2] + guide[1:])[:3]
        return agent, prepared, questions, None
    except Exception as exc:  # plugin isolation boundary; core must remain usable
        return None, None, [], f"{type(exc).__name__}: {exc}"


def run_mock_interview(company_target: str, job_id: int | None = None):
    conn = get_db()
    company = _find_company(conn, company_target)
    if not company:
        conn.close()
        print(f"❌ 未在数据库中找到企业: {company_target}")
        return False
    cid, cname, typical_questions, weights, pitfalls = company
    cname = _clean(cname)
    typical_questions = _clean(typical_questions)
    weights = _clean(weights)
    pitfalls = _clean(pitfalls)
    job = None
    profile = None
    if job_id:
        job = conn.execute(
            """
            SELECT id, company_id, company_name, job_title, category, responsibilities,
                   requirements, english_req
            FROM jobs WHERE id = ? AND company_id = ?
            """,
            (job_id, cid),
        ).fetchone()
        if job is not None:
            profile = infer_assessment_profile(job)
            profile["company_id"] = job["company_id"]
    if job is None:
        job = conn.execute("SELECT id, job_title FROM jobs WHERE company_id = ? ORDER BY priority, id LIMIT 1", (cid,)).fetchone()
    selected_job_id = job["id"] if job else None
    job_title = _clean(job["job_title"] if job else "校招技术岗位")

    # Resolve an explicitly enabled capability after the job/company lookup.
    # Preparation happens before user input, so a broken plugin can safely
    # fall back without leaving a partial interview report.
    plugin_agent = None
    plugin_prepared = None
    plugin_questions: list[dict] = []
    plugin_error = None
    if job is not None:
        plugin_job = job
        if "category" not in job.keys():
            plugin_job = conn.execute(
                """
                SELECT id, company_name, job_title, category, responsibilities,
                       requirements, english_req
                FROM jobs WHERE id = ?
                """,
                (selected_job_id,),
            ).fetchone()
        plugin_agent, plugin_prepared, plugin_questions, plugin_error = _try_interview_plugin(
            job=plugin_job,
            guide={
                "typical_questions": typical_questions,
                "score_weights": weights,
                "avoid_pitfalls": pitfalls,
            },
            profile=profile,
        )
        if plugin_error:
            print(f"[plugin-fallback] interview_agent: {plugin_error}; 使用 local-rubric")

    question_context: list[dict[str, str]] = []
    questions = ["请在 1 分钟内做自我介绍，并说明一个你亲自负责的项目。"]
    question_context.append(
        {
            "source": "fixed",
            "source_plugin": "career-os-core",
            "source_question_id": "career-os-core/fixed-self-intro",
            "question_type": "interview",
            "family": "结构化行为面试",
            "question": questions[0],
        }
    )
    if plugin_agent is not None:
        for item in plugin_questions:
            questions.append(_clean(item.get("question")))
            question_context.append(
                {
                    "source": _clean(item.get("source") or "interview_agent"),
                    "source_plugin": _clean(item.get("source_plugin") or "interview_agent"),
                    "source_question_id": _clean(
                        item.get("source_question_id")
                        or item.get("id")
                        or f"interview_agent-question-{len(question_context)}"
                    ),
                    "question_type": _clean(item.get("question_type") or "interview"),
                    "track": _clean(item.get("track") or ""),
                    "family": _clean(item.get("family") or item.get("track") or "插件问题"),
                    "question": _clean(item.get("question")),
                    "question_id": _clean(item.get("id")),
                }
            )
        questions = questions[:4]
        question_context = question_context[:4]
    elif profile is not None:
        selected, selected_context = _select_jd_questions(
            conn,
            {
                **profile,
                "typical_questions": typical_questions,
            },
        )
        questions.extend(selected)
        question_context.extend(selected_context)
        if len(questions) < 4:
            fallback = "如果生产系统出现高并发写入或突然断电，你会如何保证数据一致性、可观测性和可回滚？"
            questions.append(fallback)
            question_context.append(
                {
                    "source": "fixed-fallback",
                    "source_plugin": "career-os-core",
                    "source_question_id": "career-os-core/fixed-fallback",
                    "question_type": "interview",
                    "family": "测试设计与故障排查",
                    "question": fallback,
                }
            )
        questions = questions[:4]
        question_context = question_context[:4]
    else:
        # Preserve the legacy company-only flow exactly: two guide questions
        # followed by the generic production scenario.
        questions.extend(_split_questions(typical_questions)[:2])
        questions.append("如果生产系统出现高并发写入或突然断电，你会如何保证数据一致性、可观测性和可回滚？")
        questions = questions[:4]
        question_context.extend(
            {
                "source": "company_interview_guide",
                "source_plugin": "career-os-company-guide",
                "source_question_id": f"career-os-company-guide-{index + 1}",
                "question_type": "interview",
                "family": "公司指南",
                "question": item,
            }
            for index, item in enumerate(questions[1:])
        )

    interview_context = None
    active_provider = "local-rubric"
    active_rubric_version = RUBRIC_VERSION
    if plugin_prepared is not None:
        active_provider = _clean(plugin_prepared.get("provider")) or active_provider
        active_rubric_version = _clean(plugin_prepared.get("contract_version")) or active_rubric_version
    if profile is not None or plugin_prepared is not None:
        plugin_context = dict(plugin_prepared or {})
        interview_context = {
            "job_id": (profile or {}).get("job_id", selected_job_id),
            "company_name": _clean((profile or {}).get("company_name", cname)),
            "job_title": _clean((profile or {}).get("job_title", job_title)),
            "category": _clean((profile or {}).get("category")),
            "tracks": (profile or {}).get("tracks", plugin_context.get("tracks", [])),
            "matched_signals": (profile or {}).get("matched_signals", plugin_context.get("matched_signals", [])),
            "question_families": (profile or {}).get("question_families", plugin_context.get("question_families", [])),
            "selected_questions": question_context,
            "provider": active_provider,
            "rubric_version": active_rubric_version,
            "inference_basis": (profile or {}).get("inference_basis"),
        }
        if plugin_prepared is not None:
            interview_context["plugin_id"] = _clean(plugin_prepared.get("plugin_id"))
            interview_context["contract_version"] = _clean(plugin_prepared.get("contract_version"))
            interview_context["external_service"] = bool(plugin_prepared.get("external_service", False))
        if plugin_error:
            interview_context["plugin_fallback_reason"] = plugin_error

    print("\n" + "=" * 85)
    print("🎙️ 【Career OS 模拟面试 Agent · prep → live → report】")
    print(f"🏢 目标企业: 【{cname}】 | 岗位: {job_title}")
    print(f"⚖️ 评分契约: 技术 40% · 表达 30% · 项目 20% · 追问 10%（{active_rubric_version}）")
    print(f"🔌 当前引擎: {active_provider}（可由外部 interview_agent 插件替换）")
    print("=" * 85 + "\n")

    question_payloads: list[dict | str] = [questions[0]]
    if plugin_agent is not None:
        question_payloads.extend(plugin_questions[: len(questions) - 1])
    else:
        question_payloads.extend(questions[1:])

    def score_with_active_agent(
        question: str,
        answer: str,
        *,
        payload: dict | str | None = None,
        follow_up: bool = False,
    ) -> dict:
        nonlocal plugin_agent, plugin_error, active_provider, active_rubric_version
        if plugin_agent is not None and plugin_prepared is not None:
            try:
                result = plugin_agent.score(
                    plugin_prepared,
                    payload if payload is not None else question,
                    answer,
                    follow_up=follow_up,
                )
                if not isinstance(result, dict) or "overall" not in result:
                    raise TypeError("interview_agent.score 未返回有效 score")
                return result
            except Exception as exc:  # score failure is isolated per turn
                plugin_error = f"{type(exc).__name__}: {exc}"
                print(f"[plugin-fallback] interview_agent.score: {plugin_error}; 使用 local-rubric")
                plugin_agent = None
                active_provider = "local-rubric"
                active_rubric_version = RUBRIC_VERSION
                if interview_context is not None:
                    interview_context["provider"] = active_provider
                    interview_context["rubric_version"] = active_rubric_version
                    interview_context["plugin_fallback_reason"] = plugin_error
        return score_answer(question, answer, follow_up=follow_up)

    transcript: list[dict] = []
    for index, question in enumerate(questions, 1):
        print(f"👉 【第 {index} 题】{question}")
        try:
            answer = input("💬 你的回答（Q 退出）: ").strip()
        except (EOFError, KeyboardInterrupt):
            answer = "Q"
        if answer.upper() == "Q":
            conn.close()
            print("❌ 模拟面试已结束，未写入未完成报告。")
            return False
        answer = _clean(answer)
        question = _clean(question)
        scored = score_with_active_agent(
            question,
            answer,
            payload=question_payloads[index - 1] if index - 1 < len(question_payloads) else question,
        )
        transcript.append({"turn": index, "question": question, "answer": answer, "score": scored})
        print(f"📌 即时反馈：{scored['overall']} 分，优先补强 {scored['focus']}。")
        if scored["overall"] < 68 and index < len(questions):
            follow_question = f"追问：你刚才提到“{scored['focus']}”，请补充一个具体指标、取舍或验证方式。"
            print(f"🔎 {follow_question}")
            try:
                follow_answer = input("💬 追问回答: ").strip()
            except (EOFError, KeyboardInterrupt):
                follow_answer = "Q"
            if follow_answer.upper() == "Q":
                conn.close()
                print("❌ 模拟面试已结束，未写入未完成报告。")
                return False
            follow_question = _clean(follow_question)
            follow_answer = _clean(follow_answer)
            follow_scored = score_with_active_agent(
                follow_question,
                follow_answer,
                payload=follow_question,
                follow_up=True,
            )
            transcript.append({"turn": f"{index}.1", "question": follow_question, "answer": follow_answer, "score": follow_scored})
            print(f"📌 追问反馈：{follow_scored['overall']} 分。")
        print("-" * 85)

    base_scores = [item["score"] for item in transcript if isinstance(item["turn"], int)]
    if not base_scores:
        conn.close()
        return False
    avg = round(sum(int(item["overall"]) for item in base_scores) / len(base_scores))
    tech = round(sum(int(item["technical"]) for item in base_scores) / len(base_scores))
    expression = round(sum(int(item["expression"]) for item in base_scores) / len(base_scores))
    depth = round(sum(int(item["project"]) + int(item["follow_up"]) for item in base_scores) / (2 * len(base_scores)))
    grade = _grade(avg)
    summary = f"本次 {active_provider} 评分 {avg}/100（{grade}）。建议优先复盘：" + ", ".join(sorted({str(item["score"]["focus"]) for item in transcript}))
    if plugin_agent is not None and plugin_prepared is not None:
        try:
            plugin_report = plugin_agent.report(plugin_prepared, transcript)
            if not isinstance(plugin_report, dict):
                raise TypeError("interview_agent.report 未返回 dict")
            if interview_context is not None:
                interview_context["plugin_report"] = plugin_report
        except Exception as exc:  # report failure must not lose the core report
            plugin_error = f"{type(exc).__name__}: {exc}"
            print(f"[plugin-fallback] interview_agent.report: {plugin_error}; 使用 local-rubric 汇总")
            active_provider = "local-rubric"
            active_rubric_version = RUBRIC_VERSION
            if interview_context is not None:
                interview_context["provider"] = active_provider
                interview_context["rubric_version"] = active_rubric_version
                interview_context["plugin_fallback_reason"] = plugin_error
    if interview_context is not None:
        summary += " | JD上下文已写入 qa_transcript_json.context"
    transcript_payload = transcript if interview_context is None else {"context": interview_context, "turns": transcript}
    cur = conn.execute(
        """
        INSERT INTO mock_interview_reports
            (company_id, company_name, job_title, interview_type, score_tech,
             score_expression, score_depth, final_grade, summary_evaluation,
             qa_transcript_json, job_id, provider, rubric_version, started_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cid, cname, job_title, "技术一面模拟", tech, expression, depth, grade, summary,
         json.dumps(transcript_payload, ensure_ascii=False), selected_job_id, active_provider, active_rubric_version, _now(), _now()),
    )
    report_id = cur.lastrowid
    for item in transcript:
        conn.execute(
            "INSERT INTO interview_turns (report_id, turn_no, question, answer, score_json) VALUES (?, ?, ?, ?, ?)",
            (report_id, str(item["turn"]), item["question"], item["answer"], json.dumps(item["score"], ensure_ascii=False)),
        )
    if job:
        add_timeline_event(conn, job_id=selected_job_id, company_name=cname, job_title=job_title,
                           event_type="模拟面试完成", notes=f"{active_provider} {avg}/100，评级 {grade}")
    conn.commit()
    conn.close()

    print("\n" + "=" * 85)
    print("📊 【模拟面试结构化报告】")
    print(f"🎯 {cname} · {job_title} | 综合 {avg}/100 · 评级 {grade}")
    print(f"• 技术准确性: {tech} | 表达结构: {expression} | 深度/项目: {depth}")
    print(f"• 引擎: {active_provider} | 报告 ID: {report_id}")
    print(f"💡 避坑提醒: {pitfalls or '回答要给出结论、证据、取舍和验证。'}")
    print("=" * 85 + "\n")
    return True


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "36"
    job_arg = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
    raise SystemExit(0 if run_mock_interview(target, job_id=job_arg) else 1)
