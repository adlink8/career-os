"""把本轮中小厂核验写回 job_targets，并把确认在招的微传写入 companies。"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db  # noqa: E402

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

# company_name -> (verification, application_status, url, notes)
CHECKS = {
    "常州程咬金人工智能科技有限公司": (
        "已核实-非技术岗",
        "不匹配",
        "https://www.zhipin.com/job_detail/fcf04505622c2a751XB63Ny_E1FX.html",
        "2026-09-09：无官网。BOSS 仅见短视频代运营（呼霸人工），不是技术/运维。",
    ),
    "常州德世物联网信息科技有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "常州惠研人工智能科技有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "常州数翼人工智能科技有限公司": (
        "已核实-无公开招聘",
        "搁置",
        "",
        "2026-09-09：常州数据集团2026-04新设全资公司，尚无对外招聘入口。",
    ),
    "常州常清人工智能科技有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网。勿把科教城常清BIO-AI载体当公司站。"),
    "常州玖焱智能化系统集成有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "无锡开悟人工智能科技有限责任公司": (
        "已核实-无公开在招",
        "待观察",
        "https://www.liepin.com/company/12573035",
        "2026-09-09：智联/猎聘有公司页，猎聘写暂无职位。官网 www.wxkwai.com 本次打不开。",
    ),
    "常州云校智能科技有限公司": (
        "已核实-招聘时效存疑",
        "待观察",
        "https://www.dazhi100.com/",
        "2026-09-09：官网大智云校在。猎聘挂嵌入式/Java 等，详情页更新时间见2023，需问HR是否仍招。https://www.liepin.com/company-jobs/9417174/",
    ),
    "常州浩瀚智能系统集成有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "无锡市荣诚软件开发科技有限公司": (
        "已核实-经营异常勿投",
        "搁置",
        "",
        "2026-09-09：公开信息含限制高消费/破产清算申请，无招聘。",
    ),
    "常州华奥智能系统集成有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "常州乐优学人工智能科技有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "常州卓远智能系统集成有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "常州旭高智能系统集成有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "常州杰易天智能系统集成有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "常州浦浩云计算信息技术有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "常州中湾智能科技有限公司": (
        "已核实-无公开在招",
        "待观察",
        "https://www.liepin.com/company/gs79664829/",
        "2026-09-09：猎聘公司页无自有职位。金坛真实地址，参保公开写0人。",
    ),
    "常州市宇元人工智能科技有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "常州云计算信息科技有限公司": (
        "已核实-非目标行业",
        "不匹配",
        "http://www.cloud518.com/",
        "2026-09-09：官网是建站/SEO公司，无招聘栏目，不是云计算/AI厂。",
    ),
    "常州市智领世纪物联网科技有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：仅过期黄页，无招聘。"),
    "常州市蓝涛物联网科技有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
    "常州辉途智能科技有限公司": (
        "已核实-无公开在招",
        "待观察",
        "https://wuitu.com/",
        "2026-09-09：官网在（牛轻松牧场物联网），无招聘栏。猎聘嵌入式等3岗已暂停。",
    ),
    "常州杰易天智能系统集成有限公司": ("已核实-疑似空壳", "搁置", "", "2026-09-09：无官网、无招聘页。"),
}


def _upsert_check(conn, target_id: int, url: str, notes: str, autumn: str) -> None:
    conn.execute(
        """
        INSERT INTO job_target_recruitment_checks (
            target_id, checked_at, search_engine, query, search_url,
            autumn_status, internship_status, confidence, result_count,
            autumn_evidence_url, autumn_evidence_title, autumn_evidence_snippet,
            autumn_evidence_date, internship_evidence_url, internship_evidence_title,
            internship_evidence_snippet, internship_evidence_date, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(target_id) DO UPDATE SET
            checked_at=excluded.checked_at,
            search_engine=excluded.search_engine,
            query=excluded.query,
            search_url=excluded.search_url,
            autumn_status=excluded.autumn_status,
            internship_status=excluded.internship_status,
            confidence=excluded.confidence,
            result_count=excluded.result_count,
            autumn_evidence_url=excluded.autumn_evidence_url,
            notes=excluded.notes
        """,
        (
            target_id,
            NOW,
            "web",
            "官网/招聘核验",
            url or "",
            autumn,
            "未发现公开实习证据" if autumn.startswith("未发现") or "空壳" in autumn else autumn,
            "中",
            1 if url else 0,
            url or None,
            "",
            notes,
            "2026-09-09",
            None,
            "",
            "",
            None,
            notes,
        ),
    )


def main() -> None:
    conn = get_db()
    updated_rows = 0
    companies = 0
    for name, (ver, app, url, notes) in CHECKS.items():
        rows = conn.execute("SELECT id FROM job_targets WHERE company_name=?", (name,)).fetchall()
        autumn = "未发现公开秋招/校招证据"
        if "在招" in ver or "社招" in ver:
            autumn = "明确社招（近期）"
        elif "空壳" in ver or "经营异常" in ver:
            autumn = "未发现公开秋招/校招证据"
        for row in rows:
            conn.execute(
                """
                UPDATE job_targets
                SET verification_status=?, application_status=?, application_url=?,
                    notes=?, updated_at=?
                WHERE id=?
                """,
                (ver, app, url, notes, NOW, row["id"]),
            )
            _upsert_check(conn, row["id"], url, notes, autumn)
            updated_rows += 1
        companies += 1 if rows else 0

    # 微传不在 top500，单独建档
    exist = conn.execute(
        "SELECT id FROM companies WHERE name=? OR alias=?",
        ("微传智能科技（常州）有限公司", "微传智能"),
    ).fetchone()
    if not exist:
        conn.execute(
            """
            INSERT INTO companies
                (name, alias, city, website, campus_url, industry, company_type,
                 campus_application_rules, pool)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "微传智能科技（常州）有限公司",
                "微传智能",
                "常州/上海",
                "https://www.vtrantech.com/",
                "https://www.vtrantech.com/rczp",
                "磁传感器芯片/FAE",
                "常州本土芯片设计",
                "官网招聘+猎聘。2026-09-09猎聘常州现场技术支持(FAE)在更新；偏社招，AE旧帖曾要求5年经验。",
                "sme_startup",
            ),
        )
        print("[INSERT company] 微传智能")
    else:
        conn.execute(
            """
            UPDATE companies
            SET website=?, campus_url=?, pool='sme_startup',
                campus_application_rules=?
            WHERE id=?
            """,
            (
                "https://www.vtrantech.com/",
                "https://www.vtrantech.com/rczp",
                "官网招聘+猎聘。2026-09-09猎聘常州现场技术支持(FAE)在更新。",
                exist["id"],
            ),
        )
        print("[UPDATE company] 微传智能")

    title = "现场技术支持工程师 (FAE)"
    dkey = hashlib.sha256(
        "微传智能科技（常州）有限公司|常州|现场技术支持工程师 (FAE)|vtrantech".encode()
    ).hexdigest()
    if not conn.execute("SELECT id FROM job_targets WHERE dedupe_key=?", (dkey,)).fetchone():
        conn.execute(
            """
            INSERT INTO job_targets (
                company_name, city, company_type, target_title, category,
                source_file, source_company_id, source_rank, total_score,
                verification_status, application_status, application_url, notes, dedupe_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "微传智能科技（常州）有限公司",
                "常州",
                "小型民企",
                title,
                "目标池/技术支持",
                "data/tianyancha/重点公司投递信息.csv",
                "vtrantech",
                14,
                305,
                "已核实-社招在招",
                "可联系",
                "https://www.vtrantech.com/rczp",
                "2026-09-09：官网 /rczp 可开。猎聘 https://www.liepin.com/company-jobs/9500840/ 常州FAE今日更新。非校招，经验岗。",
                dkey,
            ),
        )
        tid = conn.execute("SELECT id FROM job_targets WHERE dedupe_key=?", (dkey,)).fetchone()[0]
        _upsert_check(
            conn,
            tid,
            "https://www.vtrantech.com/rczp",
            "猎聘常州FAE在招；官网招聘页可开。",
            "明确社招（近期）",
        )
        print("[INSERT target] 微传 FAE")

    conn.commit()
    print("updated_job_target_rows", updated_rows, "companies_touched", companies)
    print("pool", list(conn.execute("SELECT pool, COUNT(*) FROM companies GROUP BY pool")))
    print("targets verification top")
    for r in conn.execute(
        "SELECT verification_status, COUNT(*) n FROM job_targets GROUP BY verification_status ORDER BY n DESC"
    ):
        print(tuple(r))
    print("companies", conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
