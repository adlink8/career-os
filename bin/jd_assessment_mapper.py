"""根据 Career OS 岗位 JD 推导测评准备画像。

这是可解释的 JD 关键词映射，不声称代表雇主内部题库；企业实际测评仍以
当次邮件、岗位和地区为准。模块不修改数据库，便于 JD 更新后即时重算。
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


RULES: tuple[dict[str, Any], ...] = (
    {
        "track_id": "software-testing-ops",
        "label": "软件测试 / 运维 / SRE",
        "category_tokens": ("软件测试/运维",),
        "keywords": (
            "linux", "docker", "kubernetes", "k8s", "shell", "python", "sql", "tcp/ip",
            "http", "dns", "ci/cd", "sre", "测试", "自动化", "日志", "故障", "监控", "恢复", "容器",
        ),
        "question_families": (
            "Linux/网络/容器基础", "Shell/Python 自动化", "SQL/数据库运维", "测试设计与故障排查", "情景判断/SJT",
        ),
        "practice": ("技术客观题", "代码题", "情景判断", "工作风格测评"),
    },
    {
        "track_id": "technical-support-fae",
        "label": "技术支持 / FAE / 实施",
        "category_tokens": ("技术支持/FAE",),
        "keywords": (
            "fae", "sdk", "售前", "客户", "现场", "培训", "沟通", "排障", "工业", "协议", "硬件", "实施", "交付",
        ),
        "question_families": (
            "产品/协议/硬件基础", "现场故障定位", "客户沟通与冲突情景", "结构化行为面试", "英语沟通（岗位要求时）",
        ),
        "practice": ("技术客观题", "情景判断", "模拟面试", "工作风格测评"),
    },
    {
        "track_id": "iot-embedded",
        "label": "物联网 / 嵌入式",
        "category_tokens": ("物联网/嵌入式",),
        "keywords": (
            "c/c++", "c++", "freertos", "rtos", "uart", "can", "mqtt", "ble", "4g", "单片机", "嵌入式",
            "传感器", "ros2", "opencv", "mcu", "固件", "驱动",
        ),
        "question_families": (
            "C/C++ 与数据结构", "嵌入式 Linux/RTOS", "串口/CAN/MQTT 等协议", "硬件接口与调试", "编程题",
        ),
        "practice": ("技术客观题", "代码题", "项目深挖面试"),
    },
    {
        "track_id": "data-analysis",
        "label": "数据分析",
        "category_tokens": ("数据分析",),
        "keywords": (
            "sql", "python", "pandas", "numpy", "spark", "hadoop", "etl", "统计", "模型", "数据", "指标", "可视化",
        ),
        "question_families": (
            "SQL 查询与性能", "Python/pandas 数据处理", "统计与数据解读", "业务案例/资料分析", "编程题",
        ),
        "practice": ("技术客观题", "代码题", "资料分析", "结构化面试"),
    },
    {
        "track_id": "ai-rag",
        "label": "AI 应用 / RAG / Agent",
        "category_tokens": ("AI应用/RAG",),
        "keywords": (
            "rag", "llamaindex", "langchain", "embedding", "vector", "agent", "prompt", "api", "websocket",
            "grpc", "python", "c++", "检索", "知识库", "模型", "大模型",
        ),
        "question_families": (
            "Python/服务端接口", "RAG 检索链路与向量库", "Agent/Prompt 工程", "数据与评测", "编程题",
        ),
        "practice": ("技术客观题", "代码题", "项目深挖面试", "英文技术表达（岗位要求时）"),
    },
)


def _value(row: Mapping[str, Any], name: str) -> str:
    if hasattr(row, "keys") and name in row.keys():
        value = row[name]
    else:
        value = row.get(name, "")
    return "" if value is None else str(value)


def infer_assessment_profile(row: Mapping[str, Any]) -> dict[str, Any]:
    """从一条 jobs 行生成可解释的测评准备画像。"""

    searchable = " ".join(
        _value(row, field)
        for field in ("company_name", "job_title", "category", "responsibilities", "requirements", "english_req")
    ).casefold()
    category = _value(row, "category")
    matches: list[dict[str, Any]] = []
    category_rules = [
        rule for rule in RULES
        if any(token.casefold() in category.casefold() for token in rule["category_tokens"])
    ]
    # The curated jobs table already has canonical categories. Prefer them to
    # broad words such as Python/data/model that appear in many different JDs.
    candidate_rules = category_rules or list(RULES)
    for rule in candidate_rules:
        category_hit = rule in category_rules
        keyword_hits = [token for token in rule["keywords"] if token.casefold() in searchable]
        if category_hit or len(keyword_hits) >= 2:
            matches.append(
                {
                    "track_id": rule["track_id"],
                    "label": rule["label"],
                    "matched_signals": sorted(set(([f"category:{category}"] if category_hit else []) + keyword_hits)),
                    "question_families": list(rule["question_families"]),
                    "practice": list(rule["practice"]),
                }
            )

    if not matches:
        matches.append(
            {
                "track_id": "general-graduate",
                "label": "通用校招",
                "matched_signals": ["no-specialized-rule"],
                "question_families": ["言语/逻辑/数量", "工作风格", "结构化行为面试"],
                "practice": ["技术客观题", "工作风格测评", "模拟面试"],
            }
        )

    # Preserve rule order, while deduplicating families and practice actions.
    families: list[str] = []
    practice: list[str] = []
    signals: list[str] = []
    for match in matches:
        for field, target in (("question_families", families), ("practice", practice), ("matched_signals", signals)):
            for item in match[field]:
                if item not in target:
                    target.append(item)

    job_id = row["id"] if hasattr(row, "keys") and "id" in row.keys() else row.get("id")
    return {
        "job_id": job_id,
        "company_name": _value(row, "company_name"),
        "job_title": _value(row, "job_title"),
        "category": category,
        "inference_basis": "category/title/responsibilities/requirements keyword match; not employer-confirmed",
        "tracks": matches,
        "question_families": families,
        "practice": practice,
        "matched_signals": signals,
    }


def profiles_for_jobs(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [infer_assessment_profile(row) for row in rows]


def summarize_profiles(profiles: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for profile in profiles:
        for track in profile.get("tracks", []):
            counts[str(track["track_id"])] += 1
    return dict(counts)


__all__ = ["RULES", "infer_assessment_profile", "profiles_for_jobs", "summarize_profiles"]
