"""独立验证简历登记的幂等性、查重和改名追踪。"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"[PASS] {label}")


def main() -> int:
    from bin import career_os_store
    from scripts import sync_resume_registry

    with tempfile.TemporaryDirectory(prefix="career-resume-smoke-") as temp_dir:
        temp = Path(temp_dir)
        db_path = temp / "career_jobs.sqlite"
        cv_path = temp / "cv"
        shutil.copy2(ROOT / "data" / "career_jobs.sqlite", db_path)
        shutil.copytree(ROOT / "data" / "cv", cv_path)
        career_os_store.DB_PATH = db_path
        sync_resume_registry.CV_ROOT = cv_path
        expected_file_count = len([path for path in cv_path.rglob("*") if path.is_file()])

        conn = career_os_store.get_db()
        with conn:
            first = sync_resume_registry.sync_registry(conn)
            first_newland_apps = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE submitted_artifact_id IN (SELECT id FROM resume_artifacts WHERE file_state='submitted' AND resume_version_id IN (SELECT id FROM resume_versions WHERE version_key='newland-data-analyst-v1.0'))"
            ).fetchone()[0]
        conn.close()
        check("initial scan sees all local CV files", first["files_scanned"] == expected_file_count)
        check("submitted Newland artifact links two applications", first_newland_apps == 2)

        conn = career_os_store.get_db()
        with conn:
            second = sync_resume_registry.sync_registry(conn)
        conn.close()
        check("second scan is idempotent", second["applications_linked_now"] == 0)

        submitted = cv_path / "final" / "cv-newland-photo-edition.pdf"
        renamed = cv_path / "final" / "20260903__newland__data-analyst__cv__v1.0__submitted.pdf"
        submitted.rename(renamed)
        conn = career_os_store.get_db()
        with conn:
            renamed_report = sync_resume_registry.sync_registry(conn)
            artifact = conn.execute(
                "SELECT id, sha256 FROM resume_artifacts WHERE file_state='submitted' AND resume_version_id=(SELECT id FROM resume_versions WHERE version_key='newland-data-analyst-v1.0')"
            ).fetchone()
            locations = conn.execute(
                "SELECT relative_path, is_current FROM resume_artifact_locations WHERE artifact_id=? ORDER BY relative_path",
                (artifact[0],),
            ).fetchall()
            app_count = conn.execute("SELECT COUNT(*) FROM applications WHERE submitted_artifact_id=?", (artifact[0],)).fetchone()[0]
        conn.close()
        check("rename scan keeps one content artifact", renamed_report["files_scanned"] == expected_file_count and artifact is not None)
        location_state = {row[0]: row[1] for row in locations}
        check(
            "rename preserves both old and new locations",
            len(locations) == 2
            and location_state.get("final/cv-newland-photo-edition.pdf") == 0
            and location_state.get("final/20260903__newland__data-analyst__cv__v1.0__submitted.pdf") == 1,
        )
        check("applications still point to renamed artifact", app_count == 2)
        check("schema remains current", career_os_store.SCHEMA_VERSION == 7)

    os.environ.pop("CAREER_OS_DB_PATH", None)
    print("Resume registry smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
