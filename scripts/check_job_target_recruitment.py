"""Check public recruiting evidence for the target-company pool.

This is an evidence collector, not an application submitter.  It searches
Sogou's public web results for each company and stores only company-relevant
titles/snippets.  Generic "internship" or "campus recruiting" portals are not
counted unless the target company's name is present in the result itself.
"""

from __future__ import annotations

import argparse
import csv
import html as html_lib
import re
import sys
import time
import urllib.parse
import urllib.request
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_FILE = ROOT / "data" / "job_target_recruitment_report.json"
SEARCH_ENGINE = "Sogou"
FALLBACK_SEARCH_ENGINE = "360"
CUTOFF_DATE = date.today() - timedelta(days=365)
AUTUMN_TERMS = (
    "秋招",
    "秋季校园招聘",
    "校招",
    "校园招聘",
    "校园招募",
    "应届生招聘",
    "2026届",
    "2027届",
    "2028届",
)
INTERNSHIP_TERMS = ("实习", "实习生", "暑期实习", "日常实习")


def compact(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", "", text).casefold()


def text_only(value: str) -> str:
    value = html_lib.unescape(value)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def date_from_text(value: str) -> date | None:
    match = re.search(
        r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", value
    )
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def parse_results(payload: bytes) -> list[dict[str, str]]:
    # lxml is already part of the workspace runtime and handles the nested
    # result-card markup more reliably than regex/HTMLParser heuristics.
    from lxml import html as lxml_html

    doc = lxml_html.fromstring(payload)
    cards: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    nodes = doc.xpath(
        '//div[(contains(concat(" ", normalize-space(@class), " "), " vrwrap ") '
        'or contains(concat(" ", normalize-space(@class), " "), " reactResult ")) '
        'and .//h3[contains(concat(" ", normalize-space(@class), " "), " vr-title ")] ]'
    )
    for node in nodes:
        title = text_only(" ".join(node.xpath('.//h3[contains(@class,"vr-title")]//text()')))
        if not title:
            continue
        summary_nodes = node.xpath(
            './/*[contains(concat(" ", normalize-space(@class), " "), " fz-mid ") '
            'or contains(@id, "summary")]//text()'
        )
        snippet = text_only(" ".join(summary_nodes))
        cite_nodes = node.xpath('.//*[contains(@class,"citeLinkClass")]')
        cite = cite_nodes[0] if cite_nodes else None
        url_candidates = node.xpath('.//*[@data-url]/@data-url')
        if cite is not None:
            url_candidates += cite.xpath('./@href')
        url = next((u for u in url_candidates if u and u.startswith("http")), "")
        cite_text = text_only(" ".join(cite.xpath('.//text()'))) if cite is not None else ""
        observed_date = ""
        observed = date_from_text(cite_text)
        if observed:
            observed_date = observed.isoformat()
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        cards.append(
            {"title": title, "snippet": snippet, "url": url, "date": observed_date}
        )
    return cards


def parse_360_results(payload: bytes) -> list[dict[str, str]]:
    """Parse 360's server-rendered ``li.res-list`` cards."""
    from lxml import html as lxml_html

    doc = lxml_html.fromstring(payload)
    cards: list[dict[str, str]] = []
    for node in doc.xpath('//li[contains(concat(" ", normalize-space(@class), " "), " res-list ")]'):
        title = text_only(" ".join(node.xpath('.//h3[contains(@class,"res-title")]//text()')))
        snippet = text_only(" ".join(node.xpath('.//*[contains(@class,"res-desc")]//text()')))
        if not title:
            continue
        hrefs = node.xpath('.//h3//a/@data-mdurl') or node.xpath('.//h3//a/@href')
        cite = text_only(" ".join(node.xpath('.//*[contains(@class,"g-linkinfo")]//text()')))
        observed = date_from_text(cite + " " + snippet)
        cards.append(
            {
                "title": title,
                "snippet": snippet,
                "url": next((u for u in hrefs if u.startswith("http")), ""),
                "date": observed.isoformat() if observed else "",
            }
        )
    return cards


def search_company(company_name: str) -> dict[str, object]:
    query = f'"{company_name}" 招聘 秋招 校招 实习 2026'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
    }
    attempts = [
        (
            SEARCH_ENGINE,
            "https://www.sogou.com/web?query=" + urllib.parse.quote(query),
            parse_results,
        ),
        (
            FALLBACK_SEARCH_ENGINE,
            "https://so.com/s?q=" + urllib.parse.quote(query),
            parse_360_results,
        ),
    ]
    last_error: Exception | None = None
    results: list[dict[str, str]] = []
    used_engine = SEARCH_ENGINE
    used_url = attempts[0][1]
    for engine, search_url, parser in attempts:
        try:
            request = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(request, timeout=25) as response:
                payload = response.read()
            results = parser(payload)
            used_engine = engine
            used_url = search_url
            break
        except Exception as exc:
            last_error = exc
    else:
        return {
            "company_name": company_name,
            "query": query,
            "search_url": used_url,
            "search_engine": FALLBACK_SEARCH_ENGINE,
            "result_count": 0,
            "autumn_status": "查询失败",
            "internship_status": "查询失败",
            "confidence": "低",
            "notes": f"{type(last_error).__name__}: {last_error}",
            "autumn": None,
            "internship": None,
        }

    company_key = compact(company_name)
    relevant: list[dict[str, str]] = []
    for result in results:
        searchable = compact(result["title"] + result["snippet"])
        if company_key and company_key in searchable:
            result["relevant"] = "1"
            relevant.append(result)

    def term_near_company(result: dict[str, str], terms: tuple[str, ...]) -> bool:
        """Avoid generic portal lists where the company is only one item."""
        title_key = compact(result["title"])
        snippet_key = compact(result["snippet"])
        if any(compact(term) in title_key for term in terms):
            return True
        if any(marker in snippet_key for marker in ("搜索职位", "相关搜索", "招聘酷", "公司排行榜", "首页")):
            return False
        start = snippet_key.find(company_key)
        while start >= 0:
            for term in terms:
                term_key = compact(term)
                term_start = snippet_key.find(term_key)
                if term_start >= 0 and abs(term_start - start) <= 100:
                    return True
            start = snippet_key.find(company_key, start + len(company_key))
        return False

    def pick(terms: tuple[str, ...]) -> dict[str, object] | None:
        candidates: list[tuple[int, dict[str, str]]] = []
        for result in relevant:
            searchable = compact(result["title"] + result["snippet"])
            if not term_near_company(result, terms):
                continue
            score = 0
            score += 4 if company_key in searchable else 0
            score += 3 if any(compact(term) in compact(result["title"]) for term in terms) else 0
            score += 2 if result["date"] and (date_from_text(result["date"]) or date.min) >= CUTOFF_DATE else 0
            score += 1 if "招聘" in searchable else 0
            candidates.append((score, result))
        if not candidates:
            return None
        _, best = max(candidates, key=lambda item: (item[0], item[1].get("date", "")))
        observed = date_from_text(best["date"])
        if observed and observed >= CUTOFF_DATE:
            recency = "近期"
        elif observed:
            recency = "过往"
        elif any(year in compact(best["title"] + best["snippet"]) for year in ("2026", "2027", "2028")):
            recency = "近期"
        else:
            recency = "日期未知"
        return {
            "url": best["url"],
            "title": best["title"],
            "snippet": best["snippet"],
            "date": best["date"],
            "recency": recency,
        }

    autumn = pick(AUTUMN_TERMS)
    internship = pick(INTERNSHIP_TERMS)

    def status(hit: dict[str, object] | None, kind: str) -> str:
        if hit is None:
            return f"未发现公开{kind}证据"
        label = kind
        if kind == "秋招/校招":
            raw = compact(str(hit["title"]) + " " + str(hit["snippet"]))
            label = "秋招" if ("秋招" in raw or "秋季" in raw) else "校招"
        return f"明确{label}（{hit['recency']}）"

    confidence = "高" if relevant and (autumn or internship) else ("中" if relevant else "低")
    return {
        "company_name": company_name,
        "query": query,
        "search_url": used_url,
        "search_engine": used_engine,
        "result_count": len(results),
        "autumn_status": status(autumn, "秋招/校招"),
        "internship_status": status(internship, "实习"),
        "confidence": confidence,
        "notes": (
            "仅统计标题/摘要含企业全称的结果；未命中不等于企业没有岗位。"
            if relevant
            else "检索结果未出现企业全称，不能据此认定有/无岗位。"
        ),
        "autumn": autumn,
        "internship": internship,
    }


def load_companies(retry_failures: bool = False) -> list[tuple[int, str]]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from bin.career_os_store import get_db

    conn = get_db()
    try:
        if retry_failures:
            rows = conn.execute(
                """
                SELECT MIN(j.id) AS target_id, j.company_name
                FROM job_targets j
                LEFT JOIN job_target_recruitment_checks c ON c.target_id = j.id
                GROUP BY j.company_name
                HAVING MAX(CASE WHEN c.autumn_status = '查询失败'
                                OR c.internship_status = '查询失败' THEN 1 ELSE 0 END) = 1
                ORDER BY MIN(j.id)
                """
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT MIN(id) AS target_id, company_name FROM job_targets GROUP BY company_name ORDER BY MIN(id)"
            ).fetchall()
    finally:
        conn.close()
    return [(int(row["target_id"]), str(row["company_name"])) for row in rows]


def save_checks(companies: list[tuple[int, str]], checks: dict[str, dict[str, object]]) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from bin.career_os_store import get_db

    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_db()
    try:
        with conn:
            for target_id, company_name in companies:
                check = checks[company_name]
                autumn = check.get("autumn") or {}
                internship = check.get("internship") or {}
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
                        autumn_evidence_title=excluded.autumn_evidence_title,
                        autumn_evidence_snippet=excluded.autumn_evidence_snippet,
                        autumn_evidence_date=excluded.autumn_evidence_date,
                        internship_evidence_url=excluded.internship_evidence_url,
                        internship_evidence_title=excluded.internship_evidence_title,
                        internship_evidence_snippet=excluded.internship_evidence_snippet,
                        internship_evidence_date=excluded.internship_evidence_date,
                        notes=excluded.notes
                    """,
                    (
                        target_id,
                        checked_at,
                        check["search_engine"],
                        check["query"],
                        check["search_url"],
                        check["autumn_status"],
                        check["internship_status"],
                        check["confidence"],
                        check["result_count"],
                        autumn.get("url"),
                        autumn.get("title"),
                        autumn.get("snippet"),
                        autumn.get("date"),
                        internship.get("url"),
                        internship.get("title"),
                        internship.get("snippet"),
                        internship.get("date"),
                        check["notes"],
                    ),
                )
    finally:
        conn.close()


def reclassify_saved_checks() -> tuple[int, int]:
    """Tighten already-collected evidence without issuing new web requests."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from bin.career_os_store import get_db

    def classify(
        company_name: str,
        kind: str,
        title: str | None,
        snippet: str | None,
        evidence_date: str | None,
    ) -> str:
        title = title or ""
        snippet = snippet or ""
        if not title and not snippet:
            return f"未发现公开{kind}证据"
        terms = AUTUMN_TERMS if kind == "秋招/校招" else INTERNSHIP_TERMS
        title_key = compact(title)
        snippet_key = compact(snippet)
        if not any(compact(term) in title_key for term in terms):
            if any(marker in snippet_key for marker in ("搜索职位", "相关搜索", "招聘酷", "公司排行榜", "首页")):
                return f"未发现公开{kind}证据"
            company_key = compact(company_name)
            company_pos = snippet_key.find(company_key)
            if company_pos < 0 or not any(
                0 <= snippet_key.find(compact(term)) - company_pos <= 100
                for term in terms
            ):
                return f"未发现公开{kind}证据"
        observed = date_from_text(" ".join(part for part in (evidence_date, title, snippet) if part))
        if observed:
            recency = "近期" if observed >= CUTOFF_DATE else "过往"
        else:
            years = [int(year) for year in re.findall(r"20\d{2}", title + " " + snippet)]
            recency = "近期" if any(year >= date.today().year for year in years) else "日期未知"
        label = kind
        if kind == "秋招/校招":
            raw = compact(title + " " + snippet)
            label = "秋招" if ("秋招" in raw or "秋季" in raw) else "校招"
        return f"明确{label}（{recency}）"

    conn = get_db()
    updated = 0
    autumn_hits = 0
    internship_hits = 0
    try:
        rows = conn.execute(
            """
            SELECT c.id, j.company_name, c.autumn_status, c.internship_status,
                   c.autumn_evidence_title, c.autumn_evidence_snippet, c.autumn_evidence_date,
                   c.internship_evidence_title, c.internship_evidence_snippet, c.internship_evidence_date,
                   c.autumn_evidence_url, c.internship_evidence_url
            FROM job_target_recruitment_checks c
            JOIN job_targets j ON j.id = c.target_id
            """
        ).fetchall()
        with conn:
            for row in rows:
                autumn_status = classify(
                    row["company_name"], "秋招/校招", row["autumn_evidence_title"],
                    row["autumn_evidence_snippet"], row["autumn_evidence_date"]
                )
                internship_status = classify(
                    row["company_name"], "实习", row["internship_evidence_title"],
                    row["internship_evidence_snippet"], row["internship_evidence_date"]
                )
                autumn_date = row["autumn_evidence_date"] or ""
                autumn_observed = date_from_text(
                    " ".join(
                        part
                        for part in (
                            row["autumn_evidence_date"],
                            row["autumn_evidence_title"],
                            row["autumn_evidence_snippet"],
                        )
                        if part
                    )
                )
                if autumn_observed:
                    autumn_date = autumn_observed.isoformat()
                internship_date = row["internship_evidence_date"] or ""
                internship_observed = date_from_text(
                    " ".join(
                        part
                        for part in (
                            row["internship_evidence_date"],
                            row["internship_evidence_title"],
                            row["internship_evidence_snippet"],
                        )
                        if part
                    )
                )
                if internship_observed:
                    internship_date = internship_observed.isoformat()
                confidence = "高" if autumn_status.startswith("明确") or internship_status.startswith("明确") else "低"
                conn.execute(
                    """
                    UPDATE job_target_recruitment_checks
                    SET autumn_status=?, internship_status=?, confidence=?,
                        autumn_evidence_date=?, internship_evidence_date=?
                    WHERE id=?
                    """,
                    (autumn_status, internship_status, confidence, autumn_date, internship_date, row["id"]),
                )
                updated += 1
                autumn_hits += autumn_status.startswith("明确")
                internship_hits += internship_status.startswith("明确")
    finally:
        conn.close()
    return autumn_hits, internship_hits


def write_summary_report() -> None:
    """Write a compact, user-readable snapshot from the evidence table."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from bin.career_os_store import get_db

    conn = get_db()
    try:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT j.company_name, j.city, c.autumn_status, c.internship_status,
                       c.checked_at, c.search_engine, c.autumn_evidence_url,
                       c.autumn_evidence_title, c.autumn_evidence_date,
                       c.internship_evidence_url, c.internship_evidence_title,
                       c.internship_evidence_date
                FROM job_targets j
                JOIN job_target_recruitment_checks c ON c.target_id = j.id
                ORDER BY j.id
                """
            )
        ]
    finally:
        conn.close()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "search_engine": "Sogou with 360 fallback",
        "cutoff_date": CUTOFF_DATE.isoformat(),
        "checked_companies": len(rows),
        "autumn_status_counts": dict(Counter(row["autumn_status"] for row in rows)),
        "internship_status_counts": dict(Counter(row["internship_status"] for row in rows)),
        "autumn_evidence": [
            {
                "company_name": row["company_name"],
                "city": row["city"],
                "status": row["autumn_status"],
                "title": row["autumn_evidence_title"],
                "url": row["autumn_evidence_url"],
                "date": row["autumn_evidence_date"],
            }
            for row in rows
            if row["autumn_status"].startswith("明确")
        ],
        "internship_evidence": [
            {
                "company_name": row["company_name"],
                "city": row["city"],
                "status": row["internship_status"],
                "title": row["internship_evidence_title"],
                "url": row["internship_evidence_url"],
                "date": row["internship_evidence_date"],
            }
            for row in rows
            if row["internship_status"].startswith("明确")
        ],
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report={REPORT_FILE}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="只检查前 N 家，便于先试跑")
    parser.add_argument("--workers", type=int, default=3, help="并发检索数（默认 3）")
    parser.add_argument("--sleep", type=float, default=0.2, help="提交任务间隔秒数")
    parser.add_argument("--retry-failures", action="store_true", help="只重查上次网络失败的企业")
    parser.add_argument("--reclassify-only", action="store_true", help="只按已保存证据重新判定，不联网")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers 必须 >= 1")

    if args.reclassify_only:
        autumn_hits, internship_hits = reclassify_saved_checks()
        write_summary_report()
        print(f"reclassified=true autumn_hits={autumn_hits} internship_hits={internship_hits}")
        return 0

    companies = load_companies(args.retry_failures)
    if args.limit:
        companies = companies[: args.limit]
    print(f"checking_companies={len(companies)} engine={SEARCH_ENGINE} cutoff={CUTOFF_DATE}")

    checks: dict[str, dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        for _, company_name in companies:
            futures[pool.submit(search_company, company_name)] = company_name
            if args.sleep:
                time.sleep(args.sleep)
        for index, future in enumerate(as_completed(futures), start=1):
            company_name = futures[future]
            checks[company_name] = future.result()
            if index % 10 == 0 or index == len(companies):
                print(f"completed={index}/{len(companies)}")

    save_checks(companies, checks)
    write_summary_report()
    autumn = sum("明确" in item["autumn_status"] for item in checks.values())
    internship = sum("明确" in item["internship_status"] for item in checks.values())
    failures = sum(item["autumn_status"] == "查询失败" for item in checks.values())
    print(f"saved={len(checks)} autumn_hits={autumn} internship_hits={internship} failures={failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
