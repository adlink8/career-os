"""入库/海投门禁：硬门槛未满足则不可进可投队列。

当前硬规则（个人约束）：
1. 任职要求写死 CET-4 / 四级 / 六级 / 雅思 / 托福（加分项除外）
2. JD 条目又多又细、堆现成工具栈，像招熟手不像校招培养
"""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple

# 加分段之后的英语证书不当硬门槛
_BONUS_SPLIT = re.compile(r"(加分项|优先条件|加分：)")
_ENG_HARD = re.compile(
    r"(CET-?\s*[46]|英语[四六]级|[四六]级(?:及以上|或以上|以上)?|"
    r"雅思\s*\d|托福\s*\d|IELTS|TOEFL)",
    re.I,
)
_DUTY_ITEM = re.compile(r"(?m)^\s*(?:\d+[\.、．\)]|（\d+）|\(\d+\))")
_MASTER_VERB = re.compile(r"(熟练掌握|精通|必须掌握|须掌握)")

# 产品/框架堆砌（岗位本职工器具如 Altium/示波器不在此列）
_STACK = (
    "gpt", "claude", "qwen", "deepseek", "kimi", "豆包",
    "dify", "coze", "扣子", "fastgpt", "langchain", "huggingface",
    "springboot", "spring boot", "spring cloud", "mybatis",
    "vue", "layui", "nginx", "tomcat",
    "hadoop", "spark", "clickhouse", "elasticsearch",
    "milvus", "pinecone", "embedding", "onnx", "lora",
    "kubernetes", "k8s", "kafka", "redis",
    "mcp", "rag", "agent",
    "向量数据库", "工作流", "workflow",
)


def _blob(duty: str, req: str) -> str:
    return f"{duty or ''}\n{req or ''}"


def _hard_req_text(req: str) -> str:
    return _BONUS_SPLIT.split(req or "", maxsplit=1)[0]


def english_hard_block(req: str, duty: str = "") -> bool:
    """任职硬性段出现四六级/雅思/托福分数线。"""
    hard = _hard_req_text(req)
    if _ENG_HARD.search(hard):
        return True
    # 有的 JD 把任职写进职责栏
    if not (req or "").strip() and _ENG_HARD.search(_hard_req_text(duty)):
        return True
    return False


def _stack_hits(text: str) -> int:
    low = (text or "").lower()
    n = 0
    for tok in _STACK:
        if tok.lower() in low:
            n += 1
    return n


def _duty_items(duty: str) -> int:
    return len(_DUTY_ITEM.findall(duty or ""))


def overspecified_no_train(title: str, duty: str, req: str) -> bool:
    """条目多、工具栈细，像不培养应届。"""
    text = _blob(duty, req)
    stack = _stack_hits(text)
    items = _duty_items(duty)
    masters = len(_MASTER_VERB.findall(_hard_req_text(req) or duty))
    if stack >= 4:
        return True
    if items >= 6 and stack >= 2:
        return True
    if masters >= 3 and stack >= 2:
        return True
    return False


def ingest_gate_reasons(title: str, duty: str, req: str) -> List[str]:
    reasons: List[str] = []
    if english_hard_block(req, duty):
        reasons.append("无CET4：任职写死四级/六级/雅思/托福")
    if overspecified_no_train(title, duty, req):
        reasons.append("JD过细：工具栈/条目像招熟手不像培养")
    return reasons


def ingest_gate_ok(title: str, duty: str, req: str) -> bool:
    return not ingest_gate_reasons(title, duty, req)


def gate_job_row(row: dict) -> Tuple[bool, List[str]]:
    title = str(row.get("job_title") or row.get("title") or "")
    duty = str(row.get("responsibilities") or row.get("duty") or "")
    req = str(row.get("requirements") or row.get("req") or "")
    reasons = ingest_gate_reasons(title, duty, req)
    return (not reasons, reasons)
