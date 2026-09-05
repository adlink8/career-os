"""GitHub 项目候选库的离线端到端冒烟测试。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"[PASS] {label}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="career-os-project-candidates-") as temp:
        temp_root = Path(temp)
        db_path = temp_root / "career_jobs.sqlite"
        shutil.copy2(ROOT / "data" / "career_jobs.sqlite", db_path)
        cv_root = temp_root / "cv"
        cv_root.mkdir()
        cv_path = cv_root / "cv-ops.md"
        cv_path.write_text((ROOT / "data" / "cv" / "cv-ops.md").read_text(encoding="utf-8"), encoding="utf-8")
        os.environ["CAREER_OS_DB_PATH"] = str(db_path)

        from bin.career_os_store import get_db
        from bin.career_os_plugins import get_plugin_manager
        from bin.github_project_candidates import (
            GitHubRestSource,
            StaticProjectSource,
            apply_proposal,
            build_search_queries,
            candidate_rows,
            confirm_candidate,
            get_job,
            save_candidates,
        )

        conn = get_db()
        # The real database may already contain a live-search sample.  The
        # copied test database is isolated, so clear only these new tables.
        conn.execute("DELETE FROM resume_project_proposals")
        conn.execute("DELETE FROM github_project_candidates")
        conn.commit()
        job = get_job(conn, 42)
        queries = build_search_queries(job)
        check("JD 生成 GitHub 查询", queries and all("category:" not in query for query in queries))

        source = StaticProjectSource(
            [
                {
                    "full_name": "demo/iot-gateway",
                    "html_url": "https://github.com/demo/iot-gateway",
                    "description": "Linux Docker Python MQTT gateway troubleshooting",
                    "language": "Python",
                    "topics": ["linux", "mqtt"],
                    "stargazers_count": 35,
                    "license": {"spdx_id": "MIT"},
                },
                {
                    "full_name": "demo/archived-no-license",
                    "html_url": "https://github.com/demo/archived-no-license",
                    "description": "unrelated sample",
                    "archived": True,
                },
            ]
        )
        rows = source.search(queries[0], limit=10)
        check("离线 Provider 不访问网络", len(rows) == 1)
        save_candidates(conn, job_id=42, query=queries[0], source=source, candidates=rows)
        save_candidates(conn, job_id=42, query=queries[0], source=source, candidates=rows)
        saved = candidate_rows(conn, job_id=42)
        check("候选写入 SQLite", len(saved) == 1)
        check("候选保留许可证和匹配词", saved[0]["license_spdx"] == "MIT" and saved[0]["matched_terms_json"] != "[]")
        check("候选写入幂等", conn.execute("select count(*) from github_project_candidates where job_id=42").fetchone()[0] == 1)
        check("默认 Provider 是只读 GitHub REST", GitHubRestSource.provider_name == "github-rest")
        from bin.github_project_candidates import normalise_github_item
        check(
            "GitHub NOASSERTION 不被当作有效许可证",
            normalise_github_item({"full_name": "demo/no-license", "license": {"spdx_id": "NOASSERTION"}}).license_status == "unknown",
        )

        try:
            confirm_candidate(conn, candidate_id=int(saved[0]["id"]), resume_key="cv-ops", evidence="local demo", cv_root=cv_root)
        except ValueError:
            pass
        else:
            raise AssertionError("missing --confirm must be rejected")
        before = cv_path.read_text(encoding="utf-8")
        proposal = confirm_candidate(
            conn,
            candidate_id=int(saved[0]["id"]),
            resume_key="cv-ops",
            evidence="本地 IoT 网关联调记录与可复现 demo",
            claim_level="adapted",
            confirm=True,
            cv_root=cv_root,
        )
        check("人工确认生成简历提案", proposal["status"] == "confirmed")
        check("确认阶段不改简历", cv_path.read_text(encoding="utf-8") == before)
        try:
            apply_proposal(conn, proposal_id=int(proposal["id"]), cv_root=cv_root)
        except ValueError:
            pass
        else:
            raise AssertionError("missing apply confirmation must be rejected")
        applied = apply_proposal(conn, proposal_id=int(proposal["id"]), confirm=True, cv_root=cv_root)
        after = cv_path.read_text(encoding="utf-8")
        check("显式确认后写入目标简历", applied == cv_path and after != before)
        apply_proposal(conn, proposal_id=int(proposal["id"]), confirm=True, cv_root=cv_root)
        check("重复 apply 不重复追加", cv_path.read_text(encoding="utf-8") == after)
        conn.close()

        old_plugins = os.environ.get("CAREER_OS_PLUGINS")
        os.environ["CAREER_OS_PLUGINS"] = "github-project-scout"
        try:
            provider = get_plugin_manager().capability("project_source")
            check("project_source 插件可拔插", provider is not None and provider.provider_name == "github-rest")
        finally:
            if old_plugins is None:
                os.environ.pop("CAREER_OS_PLUGINS", None)
            else:
                os.environ["CAREER_OS_PLUGINS"] = old_plugins
    print("GitHub project candidate smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
