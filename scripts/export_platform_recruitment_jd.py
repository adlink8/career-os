"""Export structured platform-lead JD fields to a readable Markdown report."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _clean(value: object) -> str:
    return "" if value is None else str(value).replace("\r\n", "\n").strip()


def export(output: Path) -> int:
    from bin.career_os_store import get_db

    conn = get_db()
    try:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, company_name, job_title, city, recruitment_type,
                       graduation_range, referral_code, status,
                       evidence_confidence, jd_summary, responsibilities,
                       requirements, education_requirement, major_requirement,
                       skill_requirement, experience_requirement,
                       jd_source_url, jd_evidence_confidence
                FROM platform_recruitment_leads
                ORDER BY id
                """
            )
        ]
    finally:
        conn.close()

    lines = [
        "# 江苏平台校招/实习岗位 JD 汇总",
        "",
        f"> 生成时间：{datetime.now(timezone.utc).isoformat(timespec='seconds')}；共 {len(rows)} 条。",
        "> 说明：内容为公开帖子或职位页的压缩摘录；“未披露/以具体职位为准”表示来源没有给出统一门槛，不是推测的硬性要求。",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['id']}. {_clean(row['company_name'])}｜{_clean(row['job_title'])}",
                "",
                f"- 城市：{_clean(row['city'])}",
                f"- 类型：{_clean(row['recruitment_type'])}；毕业范围：{_clean(row['graduation_range'])}",
                f"- 状态：{_clean(row['status'])}；JD证据置信度：{_clean(row['jd_evidence_confidence']) or '未填'}",
                f"- 内推码：{_clean(row['referral_code']) or '未公开'}",
                f"- JD来源：[{_clean(row['jd_source_url'])}]({_clean(row['jd_source_url'])})",
                "",
                f"**JD摘要**：{_clean(row['jd_summary'])}",
                "",
                f"**核心职责**：{_clean(row['responsibilities'])}",
                "",
                f"**任职要求**：{_clean(row['requirements'])}",
                "",
                f"- 学历/届别：{_clean(row['education_requirement'])}",
                f"- 专业：{_clean(row['major_requirement'])}",
                f"- 技能：{_clean(row['skill_requirement'])}",
                f"- 经验/实习：{_clean(row['experience_requirement'])}",
                "",
            ]
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"exported={len(rows)} output={output}")
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "platform_recruitment_jd.md",
    )
    args = parser.parse_args()
    export(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
