"""JD 驱动的 GitHub 开源项目候选库。

该模块只把外部仓库作为“候选参考”保存到本地，绝不自动把仓库作者的工作写成
个人经历。候选确认和简历写入是两个显式动作，便于保留许可证、来源和个人证据。
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol

try:
    from career_os_store import get_db, ROOT
except ModuleNotFoundError:
    from bin.career_os_store import get_db, ROOT

try:
    from services.job_service import JobService
except ImportError:
    from bin.services.job_service import JobService

try:
    from jd_assessment_mapper import infer_assessment_profile
except ModuleNotFoundError:
    from bin.jd_assessment_mapper import infer_assessment_profile


CV_ROOT = ROOT / "data" / "cv"
PROPOSAL_ROOT = ROOT / "data" / "resume-project-proposals"
ALLOWED_CLAIM_LEVELS = {"reference", "adapted", "implemented"}
CORE_TERMS = (
    "linux", "docker", "kubernetes", "k8s", "python", "shell", "sql", "mqtt", "iot",
    "aws", "azure", "tcp", "udp", "network", "pytest", "testing", "fastapi", "api",
    "prometheus", "grafana", "kafka", "flink", "hadoop", "rag", "agent", "embedding",
    "opencv", "esp32", "freertos", "rtos", "can", "modbus", "observability", "devops",
)
TRACK_TERMS = {
    "software-testing-ops": ("devops", "testing", "pytest", "linux", "docker", "python", "network", "observability"),
    "technical-support-fae": ("iot", "network", "mqtt", "sdk", "linux", "support"),
    "iot-embedded": ("iot", "mqtt", "esp32", "embedded", "freertos", "rtos", "gateway"),
    "data-analysis": ("python", "sql", "pandas", "data-analysis", "etl", "spark"),
    "ai-rag": ("rag", "agent", "embedding", "llm", "python", "vector", "fastapi"),
    "general-graduate": ("python", "linux", "docker"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _json(value: Any, default: Any) -> str:
    return json.dumps(value if value is not None else default, ensure_ascii=False, sort_keys=True)


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = value.strip().casefold()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _candidate_is_relevant(candidate: "ProjectCandidate", terms: Iterable[str]) -> bool:
    """过滤明显的聚合页/无关大仓库，同时保留描述型项目。"""

    terms = tuple(term.casefold() for term in terms if term)
    name_text = candidate.repo_full_name.casefold()
    topic_text = " ".join(candidate.topics).casefold()
    return any(term in name_text or term in topic_text for term in terms) or candidate.relevance_score >= 65


def _job_text(job: Any) -> str:
    fields = ("company_name", "job_title", "category", "responsibilities", "requirements", "english_req")
    if hasattr(job, "keys"):
        return " ".join(_text(job[field]) for field in fields if field in job.keys()).casefold()
    return " ".join(_text(job.get(field, "")) for field in fields).casefold()


def build_search_queries(job: Any, *, max_queries: int = 3) -> list[str]:
    """根据数据库 JD 生成可解释、短而稳定的 GitHub 查询。"""

    profile = infer_assessment_profile(job)
    text = _job_text(job)
    track_ids = [str(item.get("track_id", "")) for item in profile.get("tracks", [])]
    terms: list[str] = []
    for term in CORE_TERMS:
        if term in text:
            terms.append(term)
    for track_id in track_ids:
        track_terms = TRACK_TERMS.get(track_id, ())
        # Keep the first two terms as track anchors (e.g. devops/testing or
        # iot/mqtt); add the remaining terms only when the JD contains them.
        terms.extend(term for index, term in enumerate(track_terms) if index < 2 or term in text)
    # Preserve a few Chinese JD signals as searchable terms, but avoid passing
    # the entire sentence to GitHub search where it produces noisy results.
    for raw_signal in profile.get("matched_signals", []):
        # The canonical category is already represented by track terms; do not
        # send strings such as ``category:软件测试/运维`` to GitHub search.
        if _text(raw_signal).startswith("category:"):
            continue
        signal = _text(raw_signal)
        if signal and len(signal) >= 2 and not signal.isascii() and "/" not in signal:
            terms.append(signal)
    terms = _unique(terms)
    if not terms:
        terms = list(TRACK_TERMS.get(track_ids[0] if track_ids else "general-graduate", TRACK_TERMS["general-graduate"]))
    primary = " ".join(terms[:6])
    queries = [f"{primary} in:name,description"]
    if len(terms) >= 3:
        queries.append(" ".join(terms[:3]) + " in:name,description")
    category = _text(job["category"] if hasattr(job, "keys") and "category" in job.keys() else job.get("category", ""))
    category_terms = " ".join(part for part in re.split(r"[/、\s]+", category) if len(part) >= 2)
    if category_terms and category_terms.casefold() not in primary.casefold():
        queries.append(f"{category_terms} {' '.join(terms[:3])}".strip() + " in:name,description")
    return _unique(queries)[:max_queries]


@dataclass(frozen=True)
class ProjectCandidate:
    repo_full_name: str
    repo_url: str
    name: str
    description: str
    language: str
    topics: tuple[str, ...]
    stars: int
    forks: int
    open_issues: int
    license_spdx: str
    license_status: str
    archived: bool
    pushed_at: str
    updated_at: str
    matched_terms: tuple[str, ...]
    relevance_score: float
    source_url: str


class ProjectSource(Protocol):
    provider_name: str

    def search(self, query: str, *, limit: int = 10) -> list[ProjectCandidate]:
        ...


class StaticProjectSource:
    """测试和离线演示用 Provider，不访问网络。"""

    provider_name = "static-test"

    def __init__(self, rows: Iterable[dict[str, Any]]):
        self.rows = list(rows)

    def search(self, query: str, *, limit: int = 10) -> list[ProjectCandidate]:
        terms = tuple(item for item in re.findall(r"[a-z0-9+#.-]+", query.casefold()) if item not in {"in", "name", "description", "readme"})
        result = [normalise_github_item(row, terms=terms) for row in self.rows]
        result = [item for item in result if _candidate_is_relevant(item, terms)]
        return sorted(result, key=lambda item: (-item.relevance_score, item.repo_full_name))[:limit]


class GitHubRestSource:
    """GitHub REST search Provider；只读，不 clone、fork 或写入 GitHub。"""

    provider_name = "github-rest"

    def __init__(self, *, token: str | None = None, timeout: float = 15.0):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.timeout = timeout

    def search(self, query: str, *, limit: int = 10) -> list[ProjectCandidate]:
        limit = max(1, min(int(limit), 30))
        params = urllib.parse.urlencode({"q": query, "per_page": limit, "sort": "stars", "order": "desc"})
        url = f"https://api.github.com/search/repositories?{params}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "career-os-project-scout/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read(300).decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub 搜索失败 HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"GitHub 搜索不可用: {exc}") from exc
        terms = tuple(item for item in re.findall(r"[a-z0-9+#.-]+", query.casefold()) if item not in {"in", "name", "description", "readme"})
        candidates = [normalise_github_item(item, terms=terms) for item in payload.get("items", [])]
        return [item for item in candidates if _candidate_is_relevant(item, terms)]


def normalise_github_item(item: dict[str, Any], *, terms: Iterable[str] = ()) -> ProjectCandidate:
    full_name = _text(item.get("full_name", item.get("repo_full_name", item.get("name", ""))))
    name = _text(item.get("name", full_name.rsplit("/", 1)[-1]))
    description = _text(item.get("description", ""))
    topics_raw = item.get("topics", [])
    if isinstance(topics_raw, str):
        topics = tuple(_unique(re.split(r"[,\s]+", topics_raw)))
    else:
        topics = tuple(_unique(_text(value) for value in topics_raw or []))
    license_raw = item.get("license")
    if isinstance(license_raw, dict):
        license_spdx = _text(license_raw.get("spdx_id", license_raw.get("key", "")))
    else:
        license_spdx = _text(item.get("license_spdx", license_raw))
    license_status = "declared" if license_spdx and license_spdx.casefold() not in {"none", "other", "noassertion"} else "unknown"
    name_searchable = " ".join((full_name, name, *topics)).casefold()
    description_searchable = " ".join((description, _text(item.get("language")))).casefold()
    matched = tuple(_unique(term for term in terms if term.casefold() in (name_searchable + " " + description_searchable)))
    name_matches = sum(1 for term in terms if term.casefold() in name_searchable)
    description_matches = sum(1 for term in terms if term.casefold() in description_searchable)
    score = round(
        min(
            100.0,
            name_matches * 24
            + description_matches * 10
            + min(int(item.get("stargazers_count", item.get("stars", 0)) or 0), 1000) / 200
            + (10 if license_status == "declared" else 0),
        ),
        2,
    )
    return ProjectCandidate(
        repo_full_name=full_name,
        repo_url=_text(item.get("html_url", item.get("repo_url", ""))) or (f"https://github.com/{full_name}" if full_name else ""),
        name=name,
        description=description,
        language=_text(item.get("language", "")),
        topics=topics,
        stars=int(item.get("stargazers_count", item.get("stars", 0)) or 0),
        forks=int(item.get("forks_count", item.get("forks", 0)) or 0),
        open_issues=int(item.get("open_issues_count", item.get("open_issues", 0)) or 0),
        license_spdx=license_spdx,
        license_status=license_status,
        archived=bool(item.get("archived", False)),
        pushed_at=_text(item.get("pushed_at", "")),
        updated_at=_text(item.get("updated_at", "")),
        matched_terms=matched,
        relevance_score=score,
        source_url=_text(item.get("html_url", item.get("repo_url", ""))) or (f"https://github.com/{full_name}" if full_name else ""),
    )


def save_candidates(conn: Any, *, job_id: int, query: str, source: ProjectSource, candidates: Iterable[ProjectCandidate]) -> int:
    now = utc_now()
    count = 0
    for candidate in candidates:
        if not candidate.repo_full_name:
            continue
        conn.execute(
            """
            INSERT INTO github_project_candidates
                (job_id, provider, repo_full_name, repo_url, name, description, language,
                 topics_json, stars, forks, open_issues, license_spdx, license_status,
                archived, pushed_at, repo_updated_at, matched_terms_json, relevance_score,
                 search_query, source_url, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate', ?, ?)
            ON CONFLICT(job_id, provider, repo_full_name) DO UPDATE SET
                repo_url=excluded.repo_url, name=excluded.name, description=excluded.description,
                language=excluded.language, topics_json=excluded.topics_json, stars=excluded.stars,
                forks=excluded.forks, open_issues=excluded.open_issues, license_spdx=excluded.license_spdx,
                license_status=excluded.license_status, archived=excluded.archived,
                pushed_at=excluded.pushed_at, repo_updated_at=excluded.repo_updated_at,
                matched_terms_json=excluded.matched_terms_json, relevance_score=excluded.relevance_score,
                search_query=excluded.search_query, source_url=excluded.source_url,
                status=CASE WHEN github_project_candidates.status IN ('approved', 'rejected')
                            THEN github_project_candidates.status ELSE 'candidate' END
            """,
            (
                job_id, source.provider_name, candidate.repo_full_name, candidate.repo_url, candidate.name,
                candidate.description, candidate.language, _json(candidate.topics, []), candidate.stars,
                candidate.forks, candidate.open_issues, candidate.license_spdx, candidate.license_status,
                int(candidate.archived), candidate.pushed_at, candidate.updated_at, _json(candidate.matched_terms, []),
                candidate.relevance_score, query, candidate.source_url, now, now,
            ),
        )
        count += 1
    conn.commit()
    return count


def candidate_rows(conn: Any, *, job_id: int | None = None, status: str | None = None) -> list[Any]:
    clauses: list[str] = []
    args: list[Any] = []
    if job_id is not None:
        clauses.append("job_id=?")
        args.append(job_id)
    if status:
        clauses.append("status=?")
        args.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return conn.execute(
        f"SELECT * FROM github_project_candidates {where} ORDER BY relevance_score DESC, id DESC", args
    ).fetchall()


def resolve_resume_path(resume_key: str, *, cv_root: Path = CV_ROOT) -> Path:
    raw = Path(resume_key)
    if raw.suffix.lower() == ".md" or raw.parent != Path("."):
        path = raw if raw.is_absolute() else (ROOT / raw)
    else:
        path = cv_root / f"{resume_key}.md"
    path = path.resolve()
    root = cv_root.resolve()
    if root not in path.parents or path == root:
        raise ValueError(f"简历路径必须位于 {root} 内: {path}")
    if not path.exists():
        raise FileNotFoundError(f"未找到目标简历: {path}")
    return path


def confirm_candidate(
    conn: Any,
    *,
    candidate_id: int,
    resume_key: str,
    evidence: str,
    claim_level: str = "reference",
    confirm: bool = False,
    cv_root: Path = CV_ROOT,
) -> Any:
    if not confirm:
        raise ValueError("必须显式传入 --confirm，才会把候选标记为人工确认")
    if claim_level not in ALLOWED_CLAIM_LEVELS:
        raise ValueError(f"claim_level 只能是: {', '.join(sorted(ALLOWED_CLAIM_LEVELS))}")
    evidence = evidence.strip()
    if not evidence:
        raise ValueError("--evidence 不能为空；请填写个人可验证证据或明确的参考说明")
    row = conn.execute("SELECT * FROM github_project_candidates WHERE id=?", (candidate_id,)).fetchone()
    if not row:
        raise ValueError(f"候选项目不存在: {candidate_id}")
    resume_path = resolve_resume_path(resume_key, cv_root=cv_root)
    now = utc_now()
    title = f"{row['name'] or row['repo_full_name']}（{claim_level}）"
    disclaimer = {
        "reference": "外部开源参考，未声称个人贡献；需自行完成后再升级口径。",
        "adapted": "仅在证据对应的个人改造已完成并可复现时使用。",
        "implemented": "仅在个人已独立实现、可演示并能回答细节时使用。",
    }[claim_level]
    proposal = (
        f"### {title}\n\n"
        f"- 项目链接：{row['repo_url']}\n"
        f"- 与 JD 匹配：{', '.join(json.loads(row['matched_terms_json'] or '[]')) or '待人工复核'}\n"
        f"- 许可证：{row['license_spdx'] or '未声明（需人工核验）'}\n"
        f"- 个人证据：{evidence}\n"
        f"- 边界说明：{disclaimer}\n"
        f"- 来源记录：GitHub 候选库 ID {candidate_id}，抓取查询 `{row['search_query']}`\n"
    )
    conn.execute(
        """
        INSERT INTO resume_project_proposals
            (candidate_id, resume_key, resume_path, claim_level, evidence_text,
             proposal_markdown, status, confirmed_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?, ?, ?)
        ON CONFLICT(candidate_id, resume_key) DO UPDATE SET
            claim_level=excluded.claim_level, evidence_text=excluded.evidence_text,
            proposal_markdown=excluded.proposal_markdown, status='confirmed',
            confirmed_at=excluded.confirmed_at, updated_at=excluded.updated_at
        """,
        (candidate_id, resume_key, str(resume_path), claim_level, evidence, proposal, now, now, now),
    )
    conn.execute("UPDATE github_project_candidates SET status='approved', updated_at=? WHERE id=?", (now, candidate_id))
    conn.commit()
    return conn.execute(
        "SELECT * FROM resume_project_proposals WHERE candidate_id=? AND resume_key=?", (candidate_id, resume_key)
    ).fetchone()


def apply_proposal(conn: Any, *, proposal_id: int, confirm: bool = False, cv_root: Path = CV_ROOT) -> Path:
    if not confirm:
        raise ValueError("必须显式传入 --confirm，才会写入简历文件")
    proposal = conn.execute("SELECT * FROM resume_project_proposals WHERE id=?", (proposal_id,)).fetchone()
    if not proposal:
        raise ValueError(f"简历提案不存在: {proposal_id}")
    if proposal["status"] == "applied":
        return Path(proposal["resume_path"])
    if proposal["status"] != "confirmed":
        raise ValueError(f"提案状态不是 confirmed: {proposal['status']}")
    path = resolve_resume_path(proposal["resume_key"], cv_root=cv_root)
    marker = f"<!-- career-os-project-proposal:{proposal_id} -->"
    content = path.read_text(encoding="utf-8")
    if marker not in content:
        heading = "## 开源项目补强（人工确认）"
        section_prefix = "" if heading in content else f"\n\n{heading}\n\n"
        block = f"{section_prefix}{marker}\n{proposal['proposal_markdown']}\n"
        path.write_text(content.rstrip() + block, encoding="utf-8")
    now = utc_now()
    conn.execute("UPDATE resume_project_proposals SET status='applied', applied_at=?, updated_at=? WHERE id=?", (now, now, proposal_id))
    conn.commit()
    return path


def get_job(conn: Any, job_id: int) -> Any:
    row = JobService.get_job(int(job_id), conn=conn)
    if not row:
        raise ValueError(f"岗位不存在: {job_id}")
    return row


__all__ = [
    "ALLOWED_CLAIM_LEVELS", "GitHubRestSource", "ProjectCandidate", "ProjectSource", "StaticProjectSource",
    "apply_proposal", "build_search_queries", "candidate_rows", "confirm_candidate", "get_db", "get_job",
    "normalise_github_item", "save_candidates",
]
