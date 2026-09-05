#!/usr/bin/env python3
"""把 adlink8 的 GitHub 全量数据同步进 career_jobs.sqlite（v9 GitHub 数据域）。

数据流：gh CLI（已认证）→ GitHub REST → github_profile / github_repositories / github_commits。
幂等：仓库按 full_name upsert，提交按 (repo_full_name, sha) INSERT OR IGNORE，profile 单行覆盖。
fork 仓库只存元数据与精确提交数（per_page=1 + Link 头反推），不逐条入库。

用法：python scripts/sync_github_data.py [--owner adlink8]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db  # noqa: E402

UTC_NOW = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds")


def gh_api(path: str, *, paginate: bool = False, include_headers: bool = False):
    cmd = ["gh", "api", path]
    if paginate:
        cmd += ["--paginate", "--slurp"]
    if include_headers:
        cmd.append("-i")
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh api {path} 失败: {result.stderr.strip()[:300]}")
    if include_headers:
        head, _, body = result.stdout.partition("\n\n")
        return head, json.loads(body)
    return json.loads(result.stdout)


def exact_commit_count(full_name: str, default_branch: str) -> int | None:
    """per_page=1 + Link(rel=last) 反推默认分支的精确提交数，一次请求完成。"""
    try:
        head, body = gh_api(
            f"repos/{full_name}/commits?per_page=1" + (f"&sha={default_branch}" if default_branch else ""),
            include_headers=True,
        )
    except RuntimeError as exc:
        if "409" in str(exc) or "404" in str(exc):
            return 0  # 空仓库 / 无默认分支提交
        raise
    if isinstance(body, dict) and body.get("message"):
        return 0
    match = re.search(r'<[^>]*[?&]page=(\d+)[^>]*>; rel="last"', head)
    if match:
        return int(match.group(1))
    return 1  # 无分页头说明恰好 1 条


def fetch_all_commits(full_name: str, default_branch: str) -> list[dict]:
    path = f"repos/{full_name}/commits?per_page=100"
    if default_branch:
        path += f"&sha={default_branch}"
    pages = gh_api(path, paginate=True)
    return [commit for page in pages for commit in page]


def upsert_profile(conn, owner: str) -> None:
    user = gh_api(f"users/{owner}")
    search = gh_api(f"search/commits?q=author:{owner}&per_page=1")
    conn.execute(
        """
        INSERT OR REPLACE INTO github_profile
            (id, login, name, bio, company, location, public_repos, followers,
             total_authored_commits, account_created_at, fetched_at, raw_json)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user["login"],
            user.get("name") or "",
            user.get("bio") or "",
            user.get("company") or "",
            user.get("location") or "",
            user.get("public_repos") or 0,
            user.get("followers") or 0,
            search.get("total_count"),
            user.get("created_at") or "",
            UTC_NOW,
            json.dumps(user, ensure_ascii=False),
        ),
    )


def upsert_repository(conn, repo: dict) -> None:
    detail = gh_api(f"repos/{repo['full_name']}")
    languages = gh_api(f"repos/{repo['full_name']}/languages")
    license_spdx = ((detail.get("license") or {}).get("spdx_id")) or ""
    conn.execute(
        """
        INSERT INTO github_repositories
            (full_name, name, owner, description, homepage, html_url, primary_language,
             languages_json, topics_json, license_spdx, default_branch, stars, forks,
             open_issues, size_kb, is_private, is_fork, is_archived, commit_count,
             commits_imported, repo_created_at, repo_updated_at, repo_pushed_at, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
        ON CONFLICT(full_name) DO UPDATE SET
            description=excluded.description, homepage=excluded.homepage,
            primary_language=excluded.primary_language,
            languages_json=excluded.languages_json, topics_json=excluded.topics_json,
            license_spdx=excluded.license_spdx, default_branch=excluded.default_branch,
            stars=excluded.stars, forks=excluded.forks, open_issues=excluded.open_issues,
            size_kb=excluded.size_kb, is_private=excluded.is_private,
            is_fork=excluded.is_fork, is_archived=excluded.is_archived,
            repo_updated_at=excluded.repo_updated_at, repo_pushed_at=excluded.repo_pushed_at,
            fetched_at=excluded.fetched_at
        """,
        (
            detail["full_name"],
            detail.get("name") or "",
            (detail.get("owner") or {}).get("login") or "",
            detail.get("description") or "",
            detail.get("homepage") or "",
            detail.get("html_url") or "",
            detail.get("language") or "",
            json.dumps(languages, ensure_ascii=False),
            json.dumps(detail.get("topics") or [], ensure_ascii=False),
            "" if license_spdx == "NOASSERTION" else license_spdx,
            detail.get("default_branch") or "",
            detail.get("stargazers_count") or 0,
            detail.get("forks_count") or 0,
            detail.get("open_issues_count") or 0,
            detail.get("size") or 0,
            1 if detail.get("private") else 0,
            1 if detail.get("fork") else 0,
            1 if detail.get("archived") else 0,
            None,
            detail.get("created_at") or "",
            detail.get("updated_at") or "",
            detail.get("pushed_at") or "",
            UTC_NOW,
        ),
    )
    return detail


def import_commits(conn, full_name: str, default_branch: str, owner: str) -> int:
    commits = fetch_all_commits(full_name, default_branch)
    rows = []
    for c in commits:
        git_author = c.get("commit", {}).get("author") or {}
        gh_author = c.get("author") or {}
        rows.append(
            (
                full_name,
                c.get("sha") or "",
                gh_author.get("login") or "",
                git_author.get("name") or "",
                git_author.get("email") or "",
                git_author.get("date") or "",
                c.get("commit", {}).get("message") or "",
                c.get("html_url") or "",
            )
        )
    conn.executemany(
        """
        INSERT OR IGNORE INTO github_commits
            (repo_full_name, sha, author_login, author_name, author_email,
             committed_at, message, html_url, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [row + (UTC_NOW,) for row in rows],
    )
    conn.execute(
        "UPDATE github_repositories SET commits_imported = 1, commit_count = ? WHERE full_name = ?",
        (len(rows), full_name),
    )
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="同步 GitHub 全量数据进 Career OS 库")
    parser.add_argument("--owner", default="adlink8")
    args = parser.parse_args()

    conn = get_db()
    conn.execute("PRAGMA foreign_keys = ON")

    print(f"[1/3] 档案快照: {args.owner}")
    upsert_profile(conn, args.owner)

    print("[2/3] 全量仓库（含私有，affiliation=owner）")
    repos = gh_api(f"user/repos?per_page=100&affiliation=owner&sort=full_name")
    repos = [r for r in repos if (r.get("owner") or {}).get("login") == args.owner]
    print(f"      共 {len(repos)} 个仓库")

    stats = {"fork": 0, "imported": []}
    for i, repo in enumerate(repos, 1):
        name = repo["full_name"]
        detail = upsert_repository(conn, repo)
        is_fork = bool(detail.get("fork"))
        if is_fork:
            detail["__count"] = exact_commit_count(name, detail.get("default_branch") or "")
            conn.execute(
                "UPDATE github_repositories SET commit_count = ? WHERE full_name = ?",
                (detail["__count"], name),
            )
            stats["fork"] += 1
            print(f"      [{i}/{len(repos)}] {name} (fork, commits={detail['__count']})")
        else:
            n = import_commits(conn, name, detail.get("default_branch") or "", args.owner)
            stats["imported"].append((name, n))
            print(f"      [{i}/{len(repos)}] {name} commits={n} (逐条入库)")

    conn.commit()
    print("[3/3] 提交完成")
    total_commits = conn.execute("SELECT COUNT(*) FROM github_commits").fetchone()[0]
    total_repos = conn.execute("SELECT COUNT(*) FROM github_repositories").fetchone()[0]
    print(f"汇总: 仓库 {total_repos}（fork {stats['fork']} 个只存计数）, 提交明细 {total_commits} 条")
    for name, n in stats["imported"]:
        if n:
            print(f"  - {name}: {n}")
    conn.close()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
