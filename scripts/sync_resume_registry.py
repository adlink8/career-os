"""扫描简历文件并同步到 Career OS 的简历登记表。

原始 PDF/DOCX/Markdown 文件保留在 ``data/cv``；SQLite 只登记元数据、内容哈希
和投递关系。文件名不是身份标识，SHA-256 才是内容身份标识，因此改名或移动
文件不会破坏已投递记录。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CV_ROOT = ROOT / "data" / "cv"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.career_os_store import get_db


STATE_PRIORITY = {
    "auxiliary": 0,
    "source": 1,
    "draft": 2,
    "ready": 3,
    "submitted": 4,
    "audit": 5,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slug(value: str) -> str:
    value = value.casefold().replace("_", "-")
    value = re.sub(r"[^a-z0-9-]+", "-", value).strip("-")
    return value or "file"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def version_spec(path: Path) -> dict[str, str] | None:
    """Return the logical resume version represented by a file, if any."""

    name = path.name.casefold()
    stem = path.stem.casefold()

    if name == "cv-style-index.md" or name.startswith("audit-"):
        return None
    if name in {"portfolio.docx", "portfolio.html", "portfolio.pdf", "portrait.jpg"}:
        return None
    if name.startswith("test") or name in {"cv-template-replica.html", "cv_page1.png"}:
        return None

    if name.endswith("简历_最终版.pdf") or name == "sample-resume.pdf":
        return {
            "version_key": "process-engineer-v1.0",
            "role_slug": "process-engineer",
            "company_slug": "",
            "job_slug": "full-time",
            "version_label": "v1.0",
            "state": "ready",
        }

    if stem == "cv-material":
        return {
            "version_key": "source-material-v1.0",
            "role_slug": "source-material",
            "company_slug": "",
            "job_slug": "",
            "version_label": "v1.0",
            "state": "source",
        }
    if stem == "cv-real":
        return {
            "version_key": "baseline-v1.0",
            "role_slug": "baseline",
            "company_slug": "",
            "job_slug": "",
            "version_label": "v1.0",
            "state": "source",
        }

    draft = re.fullmatch(r"cv-(ops|iot|ai-infra)-v2-draft", stem)
    if draft:
        role = draft.group(1)
        return {
            "version_key": f"{role}-v2.0",
            "role_slug": role,
            "company_slug": "",
            "job_slug": "",
            "version_label": "v2.0",
            "state": "draft",
        }

    role_files = {
        "cv-ops": "ops",
        "cv-iot": "iot",
        "cv-ai-infra": "ai-infra",
        "cv-network": "network",
        "cv-compact": "compact",
        "cv-aispeech-devops": "aispeech-devops",
        "cv-aispeech-opensource": "aispeech-opensource",
        "cv-aispeech-agent": "aispeech-agent",
    }

    # Generated photo-style artifacts are alternate renderings of an existing
    # logical version. Keep them attached to that version instead of creating
    # unclassified logical versions during a registry scan.
    photo_style = re.fullmatch(r"cv-(ops|iot|ai-infra|network|compact|aispeech-devops|aispeech-opensource|aispeech-agent)-photo-style", stem)
    if photo_style:
        role = photo_style.group(1)
        version_label = "v2.0" if role in {"ops", "iot", "ai-infra"} else "v1.0"
        return {
            "version_key": f"{role}-{version_label}",
            "role_slug": role,
            "company_slug": "",
            "job_slug": "",
            "version_label": version_label,
            "state": "ready",
        }

    if stem == "cv-newland-customized-photo-style":
        return {
            "version_key": "newland-data-analyst-v1.0",
            "role_slug": "data-analyst",
            "company_slug": "newland",
            "job_slug": "data-analyst-2027-campus",
            "version_label": "v1.0",
            "state": "ready",
        }

    if "研发效能" in stem or stem in {"cv-aispeech-devops", "cv-aispeech-devops-photo-style"}:
        return {
            "version_key": "aispeech-devops-v1.0",
            "role_slug": "aispeech-devops",
            "company_slug": "aispeech",
            "job_slug": "rd-quality-2027",
            "version_label": "v1.0",
            "state": "submitted",
        }

    if "开源技术" in stem or stem in {"cv-aispeech-opensource", "cv-aispeech-opensource-photo-style"}:
        return {
            "version_key": "aispeech-opensource-v1.0",
            "role_slug": "aispeech-opensource",
            "company_slug": "aispeech",
            "job_slug": "opensource-2027",
            "version_label": "v1.0",
            "state": "submitted",
        }

    if "先导智能" in stem or stem.startswith("cv-leadchina-"):
        return {
            "version_key": "leadchina-ai-dev-v1.0",
            "role_slug": "leadchina-ai-dev",
            "company_slug": "leadchina",
            "job_slug": "leadchina-ai-2027",
            "version_label": "v1.0",
            "state": "submitted",
        }

    if "合合信息" in stem or stem.startswith("cv-intsig-"):
        return {
            "version_key": "intsig-data-crawler-v1.0",
            "role_slug": "intsig-data-crawler",
            "company_slug": "intsig",
            "job_slug": "intsig-data-2027",
            "version_label": "v1.0",
            "state": "submitted",
        }

    if "浩鲸科技" in stem or stem.startswith("cv-whalecloud-"):
        return {
            "version_key": "whalecloud-ai-delivery-v1.0",
            "role_slug": "whalecloud-ai-delivery",
            "company_slug": "whalecloud",
            "job_slug": "whalecloud-ai-2027",
            "version_label": "v1.0",
            "state": "submitted",
        }

    if stem in role_files:
        role = role_files[stem]
        return {
            "version_key": f"{role}-v1.0",
            "role_slug": role,
            "company_slug": "",
            "job_slug": "",
            "version_label": "v1.0",
            "state": "ready",
        }

    if stem.startswith("cv-newland-"):
        return {
            "version_key": "newland-data-analyst-v1.0",
            "role_slug": "data-analyst",
            "company_slug": "newland",
            "job_slug": "data-analyst-2027-campus",
            "version_label": "v1.0",
            "state": "ready",
        }

    # Unknown cv-* files are registered as source material instead of being
    # silently ignored; this makes later manual classification visible.
    if stem.startswith("cv-"):
        role = slug(stem.removeprefix("cv-"))
        return {
            "version_key": f"{role}-unclassified-v1.0",
            "role_slug": role,
            "company_slug": "",
            "job_slug": "",
            "version_label": "v1.0",
            "state": "source",
        }
    return None


def classify(path: Path, relative_path: str) -> tuple[str, dict[str, str] | None]:
    name = path.name.casefold()
    if name.startswith("audit-"):
        return "audit", None
    if name == "cv-style-index.md":
        return "source", None
    if name in {"portfolio.docx", "portfolio.html", "portfolio.pdf", "portrait.jpg"}:
        return "auxiliary", None
    if name.startswith("test") or name in {"cv-template-replica.html", "cv_page1.png"}:
        return "auxiliary", None

    spec = version_spec(path)
    if spec is None:
        return "auxiliary", None

    stem = path.stem.casefold()
    if path.suffix.casefold() == ".md":
        return "source", spec
    if (stem in {"cv-newland-photo-edition", "cv-aispeech-devops", "cv-aispeech-opensource"}
        or any(k in stem for k in ["研发效能", "开源技术", "先导智能", "合合信息", "浩鲸科技"])):
        if path.suffix.casefold() == ".pdf":
            return "submitted", spec
    if path.suffix.casefold() in {".docx", ".pdf"}:
        return "ready", spec
    if path.suffix.casefold() in {".png", ".jpg", ".jpeg", ".html"}:
        return "auxiliary", spec
    return "source", spec


def canonical_filename(path: Path, state: str, spec: dict[str, str] | None) -> str:
    suffix = path.suffix.casefold()
    if spec is None:
        if state == "audit":
            return f"audit__{slug(path.stem)}{suffix}"
        if path.name.casefold() == "cv-style-index.md":
            return "catalog__resume-style-index.md"
        return f"aux__{slug(path.stem)}{suffix}"

    company = spec["company_slug"]
    role = spec["role_slug"]
    label = spec["version_label"]
    stem = f"{company}__{role}__cv__{label}" if company else f"cv__{role}__{label}"
    if state == "submitted":
        if path.stem.casefold() == "cv-newland-photo-edition":
            submitted_date = "20260903"
        elif "aispeech" in (spec["role_slug"] if spec else "") or "研发效能" in path.stem or "开源技术" in path.stem:
            submitted_date = "20260906"
        elif any(k in path.stem for k in ["先导智能", "合合信息", "浩鲸科技"]):
            submitted_date = "20260908"
        else:
            submitted_date = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d")
        return f"{submitted_date}__{company or role}__{role}__cv__{label}__submitted{suffix}"
    if suffix == ".md":
        return f"{stem}__source.md"
    if suffix == ".docx":
        return f"{stem}__editable.docx"
    if suffix in {".png", ".jpg", ".jpeg"}:
        return f"{stem}__preview{suffix}"
    return f"{stem}__ready{suffix}"


def upsert_version(conn: sqlite3.Connection, spec: dict[str, str], relative_path: str) -> int:
    source_path = relative_path if relative_path.casefold().endswith(".md") else ""
    conn.execute(
        """
        INSERT INTO resume_versions
            (version_key, role_slug, target_company_slug, target_job_slug,
             version_label, state, source_relative_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(version_key) DO UPDATE SET
            role_slug=excluded.role_slug,
            target_company_slug=excluded.target_company_slug,
            target_job_slug=excluded.target_job_slug,
            version_label=excluded.version_label,
            source_relative_path=CASE
                WHEN excluded.source_relative_path <> '' THEN excluded.source_relative_path
                ELSE resume_versions.source_relative_path
            END,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            spec["version_key"],
            spec["role_slug"],
            spec["company_slug"],
            spec["job_slug"],
            spec["version_label"],
            spec["state"],
            source_path,
        ),
    )
    return int(conn.execute("SELECT id FROM resume_versions WHERE version_key=?", (spec["version_key"],)).fetchone()[0])


def upsert_artifact(
    conn: sqlite3.Connection,
    *,
    relative_path: str,
    original_filename: str,
    state: str,
    canonical: str,
    digest: str,
    size_bytes: int,
    version_id: int | None,
    now: str,
) -> int:
    existing = conn.execute(
        "SELECT id, file_state, resume_version_id FROM resume_artifacts WHERE sha256=?",
        (digest,),
    ).fetchone()
    if existing:
        artifact_id = int(existing[0])
        old_state = str(existing[1])
        chosen_state = state if STATE_PRIORITY.get(state, 0) >= STATE_PRIORITY.get(old_state, 0) else old_state
        chosen_version_id = existing[2]
        if version_id and existing[2]:
            old_version = conn.execute(
                "SELECT version_key FROM resume_versions WHERE id=?",
                (int(existing[2]),),
            ).fetchone()
            if old_version and str(old_version[0]).endswith("-unclassified-v1.0"):
                chosen_version_id = version_id
        elif version_id:
            chosen_version_id = version_id
        conn.execute(
            """
            UPDATE resume_artifacts
            SET resume_version_id=?,
                file_state=?, canonical_filename=?, size_bytes=?,
                last_seen_at=?, missing_at=NULL
            WHERE id=?
            """,
            (chosen_version_id, chosen_state, canonical, size_bytes, now, artifact_id),
        )
    else:
        conn.execute(
            """
            INSERT INTO resume_artifacts
                (resume_version_id, file_state, format, canonical_filename,
                 sha256, size_bytes, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (version_id, state, Path(original_filename).suffix.casefold().lstrip("."), canonical, digest, size_bytes, now, now),
        )
        artifact_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

    # A path is unique in the registry. If its content hash changed since the
    # previous scan (for example, an edited catalog), retarget that path row to
    # the new artifact instead of attempting a second row and violating the
    # path uniqueness invariant.
    location = conn.execute(
        "SELECT id, artifact_id FROM resume_artifact_locations WHERE relative_path=? ORDER BY id DESC LIMIT 1",
        (relative_path,),
    ).fetchone()
    if location:
        conn.execute(
            "UPDATE resume_artifact_locations SET artifact_id=?, original_filename=?, is_current=1, last_seen_at=?, missing_at=NULL WHERE id=?",
            (artifact_id, original_filename, now, int(location[0])),
        )
    else:
        conn.execute(
            """
            INSERT INTO resume_artifact_locations
                (artifact_id, relative_path, original_filename, is_current,
                 first_seen_at, last_seen_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (artifact_id, relative_path, original_filename, now, now),
        )
    return artifact_id


def sync_registry(conn: sqlite3.Connection) -> dict[str, object]:
    if not CV_ROOT.exists():
        raise FileNotFoundError(f"简历目录不存在: {CV_ROOT}")

    now = utc_now()
    conn.execute(
        "UPDATE resume_artifact_locations SET is_current=0, missing_at=COALESCE(missing_at, ?)",
        (now,),
    )
    files = sorted(path for path in CV_ROOT.rglob("*") if path.is_file())
    state_counts: dict[str, int] = {}
    version_ids: dict[str, int] = {}
    artifact_ids: dict[str, int] = {}
    for path in files:
        relative_path = path.relative_to(CV_ROOT).as_posix()
        state, spec = classify(path, relative_path)
        version_id = upsert_version(conn, spec, relative_path) if spec else None
        digest = sha256_file(path)
        artifact_id = upsert_artifact(
            conn,
            relative_path=relative_path,
            original_filename=path.name,
            state=state,
            canonical=canonical_filename(path, state, spec),
            digest=digest,
            size_bytes=path.stat().st_size,
            version_id=version_id,
            now=now,
        )
        state_counts[state] = state_counts.get(state, 0) + 1
        artifact_ids[path.name] = artifact_id
        if spec:
            version_ids[spec["version_key"]] = version_id

    # The user confirmed this exact artifact was used for the existing Newland
    # submissions. Link it by content hash so a later rename is harmless.
    submitted_artifact = conn.execute(
        """
        SELECT a.id, a.resume_version_id
        FROM resume_artifacts a
        JOIN resume_versions v ON v.id=a.resume_version_id
        WHERE a.file_state='submitted' AND v.version_key='newland-data-analyst-v1.0'
        ORDER BY a.id
        LIMIT 1
        """
    ).fetchone()
    linked_applications = 0
    if submitted_artifact:
        newland_jobs = conn.execute(
            """
            SELECT id, job_title
            FROM jobs
            WHERE company_name='新大陆科技集团' AND status='已投递'
            ORDER BY id
            """
        ).fetchall()
        for job_id, job_title in newland_jobs:
            existing = conn.execute(
                "SELECT id FROM applications WHERE job_id=? AND submitted_artifact_id=?",
                (int(job_id), int(submitted_artifact[0])),
            ).fetchone()
            if existing:
                application_id = int(existing[0])
                conn.execute(
                    "UPDATE applications SET resume_version_id=?, submitted_at=COALESCE(submitted_at, '2026-09-03'), status='已投递', updated_at=? WHERE id=?",
                    (submitted_artifact[1], now, application_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO applications
                        (job_id, resume_version_id, submitted_artifact_id,
                         submitted_at, channel, status, notes)
                    VALUES (?, ?, ?, '2026-09-03', '官网校招', '已投递', ?)
                    """,
                    (int(job_id), submitted_artifact[1], int(submitted_artifact[0]), "用户确认使用 cv-newland-photo-edition.pdf"),
                )
                application_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
                linked_applications += 1
            conn.execute(
                "UPDATE application_timeline SET application_id=? WHERE job_id=? AND event_type='已投递' AND application_id IS NULL",
                (application_id, int(job_id)),
            )

    # AISpeech 投递关联 (研发效能与质量平台工程师 job_id=62, 开源技术研发工程师 job_id=63)
    aispeech_configs = [
        ("aispeech-devops-v1.0", 62, "思必驰科技股份有限公司", "研发效能与质量平台工程师-2027届", "官网校招网申，投递简历：研发效能与质量平台工程师-常州大学-2027届.pdf", "官网提交申请，等待简历初筛；对位 CI/CD、自动化测试门禁与质量自检"),
        ("aispeech-opensource-v1.0", 63, "思必驰科技股份有限公司", "开源技术研发工程师-2027届", "官网校招网申，投递简历：开源技术研发工程师-常州大学-2027届.pdf", "官网提交申请，等待简历初筛；对位 开源架构、MCP协议、FastAPI与工程规范"),
    ]
    for ver_key, job_id, comp_name, job_title, app_notes, tl_notes in aispeech_configs:
        sub_art = conn.execute(
            """
            SELECT a.id, a.resume_version_id
            FROM resume_artifacts a
            JOIN resume_versions v ON v.id=a.resume_version_id
            WHERE a.file_state='submitted' AND v.version_key=?
            ORDER BY a.id DESC
            LIMIT 1
            """,
            (ver_key,),
        ).fetchone()
        if sub_art:
            conn.execute("UPDATE jobs SET status='已投递', updated_at=? WHERE id=?", (now, job_id))
            existing = conn.execute(
                "SELECT id FROM applications WHERE job_id=? AND submitted_artifact_id=?",
                (job_id, int(sub_art[0])),
            ).fetchone()
            if existing:
                application_id = int(existing[0])
                conn.execute(
                    "UPDATE applications SET resume_version_id=?, submitted_at=COALESCE(submitted_at, '2026-09-06'), status='已投递', updated_at=? WHERE id=?",
                    (sub_art[1], now, application_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO applications
                        (job_id, resume_version_id, submitted_artifact_id,
                         submitted_at, channel, status, notes)
                    VALUES (?, ?, ?, '2026-09-06', '思必驰校招官网', '已投递', ?)
                    """,
                    (job_id, sub_art[1], int(sub_art[0]), app_notes),
                )
                application_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
                linked_applications += 1

            tl_exists = conn.execute(
                "SELECT id FROM application_timeline WHERE job_id=? AND event_type='已投递'",
                (job_id,),
            ).fetchone()
            if not tl_exists:
                conn.execute(
                    """
                    INSERT INTO application_timeline
                        (job_id, company_name, job_title, event_date, event_type, notes, application_id)
                    VALUES (?, ?, ?, '2026-09-06', '已投递', ?, ?)
                    """,
                    (job_id, comp_name, job_title, tl_notes, application_id),
                )
            else:
                conn.execute(
                    "UPDATE application_timeline SET application_id=?, notes=? WHERE id=?",
                    (application_id, tl_notes, int(tl_exists[0])),
                )

    # 2026-09-08 批量校招网申投递关联 (先导智能 3个, 合合信息 3个, 浩鲸科技 2个)
    batch_20260908_configs = [
        # 先导智能 (LEAD)
        ("leadchina-ai-dev-v1.0", 266, "先导智能 (LEAD)", "AI应用开发工程师（2027届校招）(J17813)", "先导智能校招官网", "官网校招网申已完成，投递定制简历《先导智能-AI应用开发工程师-常州大学-2027届.pdf》", "官网提交网申，等待初筛；对位NovelMind长文本分层检索系统（L0~L4多粒度向量建模+RAG+FastAPI）"),
        ("leadchina-ai-dev-v1.0", 267, "先导智能 (LEAD)", "软件开发（2027届校招）(J17840)", "先导智能校招官网", "官网校招网申已完成，投递定制简历《先导智能-AI应用开发工程师-常州大学-2027届.pdf》", "官网提交网申，等待初筛；对位物联网竞赛与上位机开发经历（PyQt5上位机+串口网口通信调试+Modbus排障）"),
        ("leadchina-ai-dev-v1.0", 268, "先导智能 (LEAD)", "信息安全工程师（2027届校招）(J17810)", "先导智能校招官网", "官网校招网申已完成，投递定制简历《先导智能-AI应用开发工程师-常州大学-2027届.pdf》", "官网提交网申，等待初筛；对位计科本科功底与网络安全基础（PKS接口自动化测试+Preflight安全门禁）"),
        # 合合信息 (INTSIG)
        ("intsig-data-crawler-v1.0", 269, "合合信息 (INTSIG)", "27届校招-数据开发工程师(J14428)", "合合信息校招官网", "官网校招网申已完成，投递定制简历《合合信息-数据开发工程师-常州大学-2027届.pdf》", "官网提交网申，等待初筛；对标PKS数据挖掘管道（28GB清洗、14,031条SQL血缘映射、数据防篡改门禁）"),
        ("intsig-data-crawler-v1.0", 270, "合合信息 (INTSIG)", "27届校招-爬虫工程师(J14414)", "合合信息校招官网", "官网校招网申已完成，投递定制简历《合合信息-数据开发工程师-常州大学-2027届.pdf》", "官网提交网申，等待初筛；命中官方加分项（Codex/Claude Code），对位Wireshark抓包排障与Python网络协议"),
        ("intsig-data-crawler-v1.0", 271, "合合信息 (INTSIG)", "27届校招-数据产品经理（质检方向）(J14410)", "合合信息校招官网", "官网校招网申已完成，投递定制简历《合合信息-数据开发工程师-常州大学-2027届.pdf》", "官网提交网申，等待初筛；纯技术底子降维竞聘数据质检产品，SQL数据一致性排查与数据治理经验"),
        # 浩鲸科技 (Whale Cloud)
        ("whalecloud-ai-delivery-v1.0", 272, "浩鲸科技 (Whale Cloud)", "AI应用开发—南京—2027届校招(J18169)", "浩鲸科技校招官网", "官网校招网申已完成，投递定制简历《浩鲸科技-AI应用与交付工程师-常州大学-2027届.pdf》", "官网提交网申，等待初筛；主力志愿，对位NovelMind分层长文本向量检索与AI Agent工程落地"),
        ("whalecloud-ai-delivery-v1.0", 273, "浩鲸科技 (Whale Cloud)", "交付工程师—南京—2027届校招(J18084)", "浩鲸科技校招官网", "官网校招网申已完成，投递定制简历《浩鲸科技-AI应用与交付工程师-常州大学-2027届.pdf》", "官网提交网申，等待初筛；稳妥保底志愿，对位网络通信协议（TCP/IP、路由交换）与现场排障交付能力"),
    ]
    for ver_key, job_id, comp_name, job_title, channel, app_notes, tl_notes in batch_20260908_configs:
        sub_art = conn.execute(
            """
            SELECT a.id, a.resume_version_id
            FROM resume_artifacts a
            JOIN resume_versions v ON v.id=a.resume_version_id
            WHERE a.file_state='submitted' AND v.version_key=?
            ORDER BY a.id DESC
            LIMIT 1
            """,
            (ver_key,),
        ).fetchone()
        if sub_art:
            conn.execute("UPDATE jobs SET status='已投递', updated_at=? WHERE id=?", (now, job_id))
            existing = conn.execute(
                "SELECT id FROM applications WHERE job_id=? AND submitted_artifact_id=?",
                (job_id, int(sub_art[0])),
            ).fetchone()
            if existing:
                application_id = int(existing[0])
                conn.execute(
                    "UPDATE applications SET resume_version_id=?, submitted_at=COALESCE(submitted_at, '2026-09-08'), channel=?, status='已投递', notes=?, updated_at=? WHERE id=?",
                    (sub_art[1], channel, app_notes, now, application_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO applications
                        (job_id, resume_version_id, submitted_artifact_id,
                         submitted_at, channel, status, notes)
                    VALUES (?, ?, ?, '2026-09-08', ?, '已投递', ?)
                    """,
                    (job_id, sub_art[1], int(sub_art[0]), channel, app_notes),
                )
                application_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
                linked_applications += 1

            tl_exists = conn.execute(
                "SELECT id FROM application_timeline WHERE job_id=? AND event_type='已投递'",
                (job_id,),
            ).fetchone()
            if not tl_exists:
                conn.execute(
                    """
                    INSERT INTO application_timeline
                        (job_id, company_name, job_title, event_date, event_type, notes, application_id)
                    VALUES (?, ?, ?, '2026-09-08', '已投递', ?, ?)
                    """,
                    (job_id, comp_name, job_title, tl_notes, application_id),
                )
            else:
                conn.execute(
                    "UPDATE application_timeline SET application_id=?, notes=? WHERE id=?",
                    (application_id, tl_notes, int(tl_exists[0])),
                )

    duplicate_hashes = [
        {"sha256": row[0], "locations": int(row[1])}
        for row in conn.execute(
            """
            SELECT a.sha256, COUNT(l.id)
            FROM resume_artifacts a
            JOIN resume_artifact_locations l ON l.artifact_id=a.id
            WHERE l.is_current=1
            GROUP BY a.sha256
            HAVING COUNT(l.id)>1
            ORDER BY COUNT(l.id) DESC, a.sha256
            """
        )
    ]
    return {
        "files_scanned": len(files),
        "state_counts": state_counts,
        "versions": len(version_ids),
        "applications_linked_now": linked_applications,
        "duplicate_hash_groups": duplicate_hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="同步 data/cv 到 Career OS 简历登记表")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args()
    conn = get_db()
    try:
        with conn:
            report = sync_registry(conn)
    finally:
        conn.close()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"简历登记同步完成：扫描 {report['files_scanned']} 个文件，登记 {report['versions']} 个逻辑版本")
        print(f"分类：{report['state_counts']}")
        print(f"本次新增投递关联：{report['applications_linked_now']} 条")
        print(f"当前重复哈希组：{len(report['duplicate_hash_groups'])} 组")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
