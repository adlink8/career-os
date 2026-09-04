"""Build a source-traceable Jiangsu SME target pool for job outreach.

The input is a company ranking, not a live vacancy feed.  Rows written here
therefore land in ``job_targets`` with ``待核实``/``待准备`` states and never
overwrite the confirmed-JD/application ``jobs`` table.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "data" / "tianyancha" / "投递清单_top500.csv"
SOURCE_LABEL = "data/tianyancha/投递清单_top500.csv"
EXPECTED_COUNT = 500
SME_TYPES = {"小型民企", "中型民企", "中小集团", "微型/初创"}
CITY_TOKENS = (
    "连云港",
    "南京",
    "苏州",
    "无锡",
    "常州",
    "南通",
    "徐州",
    "扬州",
    "镇江",
    "泰州",
    "盐城",
    "淮安",
    "宿迁",
)
ROLE_FAMILIES = (
    ("技术支持工程师（IoT/云平台）", "目标池/技术支持"),
    ("项目实施/交付工程师（物联网）", "目标池/项目实施"),
    ("云平台/DevOps运维工程师", "目标池/运维"),
)
TARGET_NOTE = (
    "企业名录目标池；公开来源未确认当前在招 JD，需到官网/招聘平台二次核验。"
    "匹配依据：江苏中小/微型企业 + IoT/云/AI/系统集成关键词评分。"
)


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _number(value: object) -> float | None:
    raw = _text(value)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _normalise(value: object) -> str:
    return re.sub(r"\s+", "", _text(value)).casefold()


def _city(company_name: str) -> str:
    for token in CITY_TOKENS:
        if token in company_name:
            return token
    return "江苏（城市待核实）"


def _dedupe_key(company_name: str, city: str, title: str, source_company_id: str) -> str:
    payload = "|".join(
        _normalise(part) for part in (company_name, city, title, source_company_id)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_targets() -> list[dict[str, object]]:
    with SOURCE_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    ranked: list[tuple[int, dict[str, str]]] = []
    for source_rank, row in enumerate(rows, start=1):
        if _text(row.get("base")) != "江苏":
            continue
        if _text(row.get("company_type")) not in SME_TYPES:
            continue
        ranked.append((source_rank, row))

    ranked.sort(
        key=lambda item: (
            -(_number(item[1].get("total_score")) or 0),
            -(_number(item[1].get("entry_friendliness")) or 0),
            item[0],
        )
    )
    if len(ranked) != 214:
        raise RuntimeError(f"江苏中小/微型企业数量变化：期望 214，实际 {len(ranked)}")

    targets: list[dict[str, object]] = []
    for company_position, (source_rank, row) in enumerate(ranked):
        company_name = _text(row.get("name"))
        city = _city(company_name)
        source_company_id = _text(row.get("id")) or f"rank-{source_rank:03d}"
        role_count = 3 if company_position < 72 else 2
        for title, category in ROLE_FAMILIES[:role_count]:
            targets.append(
                {
                    "company_name": company_name,
                    "city": city,
                    "company_type": _text(row.get("company_type")),
                    "target_title": title,
                    "category": category,
                    "source_file": SOURCE_LABEL,
                    "source_company_id": source_company_id,
                    "source_rank": source_rank,
                    "total_score": _number(row.get("total_score")),
                    "entry_friendliness": _number(row.get("entry_friendliness")),
                    "registration_capital": _text(row.get("regCapital")),
                    "establishment_date": _text(row.get("estiblishTime")),
                    "reg_status": _text(row.get("regStatus")),
                    "verification_status": "待核实",
                    "application_status": "待准备",
                    "application_url": "",
                    "notes": TARGET_NOTE,
                    "dedupe_key": _dedupe_key(
                        company_name, city, title, source_company_id
                    ),
                }
            )

    if len(targets) != EXPECTED_COUNT:
        raise RuntimeError(f"目标岗位数量变化：期望 {EXPECTED_COUNT}，实际 {len(targets)}")
    return targets


def apply_targets(targets: list[dict[str, object]]) -> tuple[int, int, int]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from bin.career_os_store import get_db

    conn = get_db()
    inserted = 0
    updated = 0
    try:
        with conn:
            for target in targets:
                existing = conn.execute(
                    "SELECT id FROM job_targets WHERE dedupe_key = ?",
                    (target["dedupe_key"],),
                ).fetchone()
                values = (
                    target["company_name"],
                    target["city"],
                    target["company_type"],
                    target["target_title"],
                    target["category"],
                    target["source_file"],
                    target["source_company_id"],
                    target["source_rank"],
                    target["total_score"],
                    target["entry_friendliness"],
                    target["registration_capital"],
                    target["establishment_date"],
                    target["reg_status"],
                    target["application_url"],
                    target["notes"],
                    target["dedupe_key"],
                )
                if existing is None:
                    conn.execute(
                        """
                        INSERT INTO job_targets (
                            company_name, city, company_type, target_title, category,
                            source_file, source_company_id, source_rank, total_score,
                            entry_friendliness, registration_capital, establishment_date,
                            reg_status, application_url, notes, dedupe_key
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                    inserted += 1
                else:
                    conn.execute(
                        """
                        UPDATE job_targets
                        SET company_name = ?, city = ?, company_type = ?,
                            target_title = ?, category = ?, source_file = ?,
                            source_company_id = ?, source_rank = ?, total_score = ?,
                            entry_friendliness = ?, registration_capital = ?,
                            establishment_date = ?, reg_status = ?, application_url = ?,
                            notes = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE dedupe_key = ?
                        """,
                        values,
                    )
                    updated += 1
        total = int(conn.execute("SELECT COUNT(*) FROM job_targets").fetchone()[0])
    finally:
        conn.close()
    return inserted, updated, total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="写入 job_targets；默认只预览"
    )
    args = parser.parse_args()

    targets = load_targets()
    companies = len({target["company_name"] for target in targets})
    cities = len({target["city"] for target in targets})
    print(
        f"generated={len(targets)} companies={companies} cities={cities} "
        f"source={SOURCE_LABEL}"
    )
    if not args.apply:
        print("dry_run=true (未写入数据库；使用 --apply 执行导入)")
        return 0

    inserted, updated, total = apply_targets(targets)
    print(f"inserted={inserted} updated={updated} target_total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
