"""把 companies.pool 标成 applied / sme_startup / archive_big。不删行。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db  # noqa: E402

APPLIED = {
    "新大陆科技集团",
    "思必驰 (AISpeech)",
    "九号公司 (Ninebot)",
    "先导智能 (LEAD)",
    "合合信息 (INTSIG)",
    "浩鲸科技 (Whale Cloud)",
}

# 已投之外，仍主动跟的中小/创业/本地专精特新
KEEP_IF_NOT_APPLIED_TYPES = (
    "明星科创",
    "明星独角兽",
    "独角兽",
    "专精特新",
    "常州本土",
    "南京本土",
    "微型",
    "民营上市公司",
    "科创板上市",
    "北交所",
    "无锡本土上市",
    "AI落地",
    "顶流具身",
    "全球机器人",
    "明星芯片",
)

ARCHIVE_TYPE_HINTS = (
    "千亿",
    "上市巨头",
    "上市大厂",
    "上市龙头",
    "上市老牌",
    "央企",
    "国有大型",
    "全球巨头",
    "德企",
    "法国",
    "海康旗下",
    "阿里与中兴",
    "网易旗下",
    "港股上市IT",
    "港股上市AI",
    "纽交所",
    "名企研发",
)


def classify(name: str, ctype: str) -> str:
    if name in APPLIED:
        return "applied"
    ctype = ctype or ""
    if any(h in ctype for h in ARCHIVE_TYPE_HINTS):
        return "archive_big"
    if ctype in {"外企", "外企规范"} and name != "松下信息系统 (Panasonic IS)":
        return "archive_big"
    if any(h in ctype for h in KEEP_IF_NOT_APPLIED_TYPES):
        return "sme_startup"
    if not ctype:
        return "sme_startup"
    return "sme_startup"


def main() -> None:
    conn = get_db()
    counts = {"applied": 0, "sme_startup": 0, "archive_big": 0}
    for row in conn.execute("SELECT id, name, company_type FROM companies"):
        pool = classify(row["name"], row["company_type"] or "")
        conn.execute("UPDATE companies SET pool=? WHERE id=?", (pool, row["id"]))
        counts[pool] += 1
    conn.commit()
    print("pool counts", counts)
    print("--- archive_big ---")
    for r in conn.execute(
        "SELECT name, company_type FROM companies WHERE pool='archive_big' ORDER BY name"
    ):
        print(f"{r['name']}\t{r['company_type']}")
    print("--- sme_startup ---")
    for r in conn.execute(
        "SELECT name, company_type, city FROM companies WHERE pool='sme_startup' ORDER BY name"
    ):
        print(f"{r['name']}\t{r['company_type']}\t{r['city']}")
    print("--- applied ---")
    for r in conn.execute("SELECT name FROM companies WHERE pool='applied'"):
        print(r["name"])
    conn.close()


if __name__ == "__main__":
    main()
