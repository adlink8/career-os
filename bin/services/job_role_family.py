"""把岗位标题收成少数方向，避免「校园招聘 / 软件测试/运维 / FAE」混用。"""

from __future__ import annotations

FAMILIES = (
    "运维/IT",
    "现场支持/FAE",
    "应用工程",
    "技术销售",
    "测试/验证",
    "其他",
)


def role_family(title: str) -> str:
    t = title or ""
    low = t.lower()
    if any(k in t for k in ("技术销售", "销售实习", "销售管培")):
        return "技术销售"
    if any(k in t for k in ("运维", "SRE", "灾备", "IT工程师", "IT 工程师")) or "sre" in low:
        return "运维/IT"
    if any(k in t for k in ("FAE", "现场应用", "现场交付", "技术支持", "现场实施", "系统调试")):
        return "现场支持/FAE"
    if any(k in t for k in ("系统应用", "芯片应用", "应用工程师")):
        return "应用工程"
    if any(k in t for k in ("测试", "验证")):
        return "测试/验证"
    return "其他"
