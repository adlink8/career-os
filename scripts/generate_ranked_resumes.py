"""按今日入选岗从三份母版生成细支 MD（只换求职意向）。"""

from __future__ import annotations

import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bin.services.apply_run import VOLUME_TRACKS, pick_volume_track

DB = ROOT / "data" / "career_jobs.sqlite"
MASTERS = {track: ROOT / path for track, path, _kws in VOLUME_TRACKS}


def _intent_title(raw: str, track: str) -> str:
    t = re.sub(r"[（(][^）)]*[)）]", "", raw or "")
    t = re.sub(r"【[^】]*】", "", t)
    t = re.sub(r"J\d+", "", t)
    parts = [p.strip(" -_") for p in re.split(r"[/／|]", t) if p.strip(" -_")]
    kws = []
    for name, _path, keys in VOLUME_TRACKS:
        if name == track:
            kws = list(keys)
            break
    chosen = parts[0] if parts else (raw or "工程师").strip()
    for part in parts:
        if any(k.lower() in part.lower() for k in kws):
            chosen = part
            break
    chosen = re.sub(r"\s+", "", chosen) if re.fullmatch(r"[\w\u4e00-\u9fa5 /－-]+", chosen) else chosen
    chosen = chosen.strip()
    return f"{chosen} | 2027届统招本科"


def _write_job_md(master: Path, intent: str, dest: Path) -> None:
    text = master.read_text(encoding="utf-8")
    text = re.sub(
        r"(> 求职意向：)[^\n]+",
        r"\1" + intent,
        text,
        count=1,
    )
    dest.write_text(text, encoding="utf-8")


def main() -> int:
    out_dir = ROOT / "data" / "cv" / "generated" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT j.id, c.alias, j.job_title, j.city, j.recommendation_rank,
               j.recommendation_weight, j.category
        FROM jobs j JOIN companies c ON c.id=j.company_id
        WHERE COALESCE(j.recommendation_rank,0) >= 1
          AND COALESCE(j.status,'') IN ('待投递','待沟通内推')
          AND COALESCE(c.pool,'sme_startup') IN ('sme_startup','applied')
        ORDER BY c.alias, j.recommendation_rank, j.id
        """
    ).fetchall()
    manifest = []
    for r in rows:
        picked = pick_volume_track(r["job_title"], "")
        track = picked["track"]
        master = MASTERS.get(track) or MASTERS["ops"]
        if not master.is_file():
            print("missing master", master)
            continue
        intent = _intent_title(r["job_title"], track)
        slug = re.sub(r"[^\w\u4e00-\u9fa5]+", "-", f"{r['id']}-{r['alias']}-{track}").strip("-")
        dest = out_dir / f"{slug}.md"
        _write_job_md(master, intent, dest)
        manifest.append(f"{r['id']}\t{r['alias']}\t{track}\t{intent}\t{dest.name}")
        print(f"{r['id']} {r['alias']} [{track}] {intent} -> {dest.name}")
    (out_dir / "manifest.tsv").write_text(
        "job_id\talias\ttrack\tintent\tfile\n" + "\n".join(manifest) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(manifest)} md -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
