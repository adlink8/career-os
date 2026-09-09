from __future__ import annotations

import json
from pathlib import Path

import pytest

from services import ats_engine
from services.apply_run import (
    ApplyRunError,
    arbitrate,
    ingest,
    lookup_fill_payload,
    mark_applied,
    next_action,
    release,
    run_ats,
    start_run,
)

from tests.helpers import fake_ats, review, write_json

pytestmark = pytest.mark.integration


def test_precision_pipeline_then_volume_lookup_prefers_released(
    isolated_db, tmp_path, sample_context_payload, monkeypatch
):
    conn = isolated_db
    ctx_path = write_json(tmp_path / "job-context.json", sample_context_payload)

    run = start_run(conn, context_path=str(ctx_path))
    run_id = int(run["id"])
    assert run["stage"] == "captured"
    assert run.get("apply_mode") in (None, "precision") or run["apply_mode"] == "precision"

    nxt = next_action(conn, run_id)
    assert nxt["action"] == "spawn" and nxt["role"] == "decompose"
    pack = json.loads(Path(nxt["packs"]["decompose"]).read_text(encoding="utf-8"))
    assert "Linux" in pack["jd_text"]
    assert set(pack) <= {
        "pack_role",
        "run_id",
        "iteration",
        "title",
        "company",
        "jd_text",
        "hard_filters",
    }

    with pytest.raises(ApplyRunError):
        run_ats(conn, run_id, str(ctx_path))

    breakdown = write_json(
        tmp_path / "breakdown.json",
        {
            "role": "decompose",
            "one_liner": "Linux 运维",
            "hard_gates": [{"item": "本科", "pass": True}],
            "must_keywords": ["Linux", "Docker"],
            "abandon": False,
        },
    )
    ingest(conn, run_id, "decompose", str(breakdown))
    ingest(
        conn,
        run_id,
        "map",
        str(
            write_json(
                tmp_path / "map.json",
                {"role": "map", "clauses": [{"jd": "Linux", "evidence": "项目A", "status": "corroborated"}]},
            )
        ),
    )
    resume_md = "# 求职意向 运维工程师\n\n## 教育\n本科 2027\n\n## 技能\nLinux\n\n## 项目\n负责 Linux Docker 排障，故障恢复 2 秒。\n"
    ingest(
        conn,
        run_id,
        "optimize",
        str(write_json(tmp_path / "opt.json", {"role": "optimize", "resume_md": resume_md})),
    )
    assert conn.execute("SELECT stage FROM job_apply_runs WHERE id=?", (run_id,)).fetchone()[0] == "resume_draft"

    resume_file = tmp_path / "resume.md"
    resume_file.write_text(resume_md, encoding="utf-8")
    monkeypatch.setattr(ats_engine, "ATSEngine", fake_ats(50, "FAIL"))
    ats_run = run_ats(conn, run_id, str(resume_file))
    assert ats_run["stage"] == "ats_failed"
    with pytest.raises(ApplyRunError) as exc:
        release(conn, run_id, allow_test_profile=True)
    assert "review_passed" in str(exc.value)

    nxt = next_action(conn, run_id)
    assert nxt["action"] == "spawn" and nxt["role"] == "gap-triage"
    ingest(conn, run_id, "gap-triage", str(write_json(tmp_path / "gap.json", nxt["suggested"])))
    nxt = next_action(conn, run_id)
    assert nxt["role"] == "optimize"
    opt_pack = json.loads(Path(nxt["packs"]["optimize"]).read_text(encoding="utf-8"))
    assert opt_pack.get("bounce_facts")
    assert "Kubernetes" in (opt_pack["bounce_facts"]["ats"]["missing"])
    assert "hr_impressions" not in opt_pack

    ingest(
        conn,
        run_id,
        "optimize",
        str(
            write_json(
                tmp_path / "opt2.json",
                {
                    "role": "optimize",
                    "resume_md": resume_md,
                    "open_answers": [{"key": "why_us", "value": "因为 Linux 运维与岗位职责对口。"}],
                },
            )
        ),
    )
    monkeypatch.setattr(ats_engine, "ATSEngine", fake_ats(88, "PASS"))
    assert run_ats(conn, run_id, str(resume_file))["stage"] == "ats_passed"

    nxt = next_action(conn, run_id)
    assert nxt["action"] == "spawn_review_parallel"
    hr_pack = json.loads(Path(nxt["packs"]["review-hr"]).read_text(encoding="utf-8"))
    ats_pack = json.loads(Path(nxt["packs"]["review-ats"]).read_text(encoding="utf-8"))
    leak = {"bounce_facts", "clause_map", "breakdown", "evidence_index", "hr_impressions"}
    assert not (leak & set(hr_pack))
    assert "matcher" in ats_pack and "matcher" not in hr_pack

    with pytest.raises(ApplyRunError):
        arbitrate(conn, run_id)

    ingest(
        conn,
        run_id,
        "hr",
        str(
            write_json(
                tmp_path / "hr.json",
                review("campus-hr", 90, "PASS", {"hr_impressions": {"mass_apply_risk_level": "LOW"}}),
            )
        ),
    )
    ingest(conn, run_id, "tech", str(write_json(tmp_path / "tech.json", review("tech-lead", 88, "PASS"))))
    ingest(
        conn,
        run_id,
        "ats-llm",
        str(
            write_json(
                tmp_path / "ats-llm.json",
                review("ats-scanner", 40, "WARN", {"knockout_check": {"has_composite_intent_violation": False}}),
            )
        ),
    )
    arb = arbitrate(conn, run_id)
    assert arb["arbitration"]["ats_matcher_score"] == 88
    assert arb["stage"] == "review_passed"

    released = release(conn, run_id, allow_test_profile=True)
    assert released["stage"] == "released"
    autofill = json.loads(Path(released["autofill_json_path"]).read_text(encoding="utf-8"))
    by_label = {str(f.get("label")): f for f in (autofill.get("fields") or [])}
    assert autofill["target_position"] == autofill["title"] == "运维工程师"
    assert by_label["求职意向"]["value"] == "运维工程师"
    assert "Linux" in by_label["为什么选择本公司"]["value"]

    looked = lookup_fill_payload(
        conn,
        url="https://example.zhiye.com/campus/detail?jobAdId=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    )
    assert looked["mode"] == "released" and looked["run_id"] == run_id

    with pytest.raises(ApplyRunError):
        mark_applied(conn, run_id, coverage={"required_empty": ["手机号"], "widget_fail": []})
    marked = mark_applied(conn, run_id, coverage={"required_empty": [], "widget_fail": []})
    assert marked["fill_coverage"]["ready"] is True

    run2 = start_run(conn, context_path=str(ctx_path))
    rid2 = int(run2["id"])
    ingest(conn, rid2, "decompose", str(breakdown))
    ingest(conn, rid2, "map", str(tmp_path / "map.json"))
    ingest(conn, rid2, "optimize", str(tmp_path / "opt.json"))
    monkeypatch.setattr(ats_engine, "ATSEngine", fake_ats(80, "WARN"))
    run_ats(conn, rid2, str(resume_file))
    ingest(
        conn,
        rid2,
        "hr",
        str(
            write_json(
                tmp_path / "hr-fail.json",
                review("campus-hr", 50, "FAIL", {"hr_impressions": {"mass_apply_risk_level": "HIGH"}}),
            )
        ),
    )
    ingest(conn, rid2, "tech", str(write_json(tmp_path / "tech2.json", review("tech-lead", 90, "PASS"))))
    ingest(
        conn,
        rid2,
        "ats-llm",
        str(
            write_json(
                tmp_path / "ats-llm2.json",
                review("ats-scanner", 90, "PASS", {"knockout_check": {"has_composite_intent_violation": False}}),
            )
        ),
    )
    arb2 = arbitrate(conn, rid2)
    assert arb2["stage"] == "review_failed"
    with pytest.raises(ApplyRunError):
        release(conn, rid2, allow_test_profile=True)

    vol = start_run(conn, context_path=str(ctx_path), mode="volume", allow_test_profile=True)
    assert vol["stage"] == "volume_ready"
    assert vol.get("apply_mode") == "volume"
    vol_af = json.loads(Path(vol["autofill_json_path"]).read_text(encoding="utf-8"))
    assert vol_af["target_position"] == vol_af["title"]
    assert vol_af.get("track") in {"ops", "ai", "iot"}
    nxt_vol = next_action(conn, int(vol["id"]))
    assert nxt_vol.get("done") is True

    looked_vol = lookup_fill_payload(
        conn,
        url="https://example.zhiye.com/campus/detail?jobAdId=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    )
    assert looked_vol["run_id"] == run_id and looked_vol["mode"] == "released"


def test_volume_composite_intent_abandons(isolated_db, tmp_path, sample_context_payload):
    payload = dict(sample_context_payload)
    payload["title"] = "技术支持工程师 / 运维工程师"
    ctx_path = write_json(tmp_path / "ctx.json", payload)
    with pytest.raises(ApplyRunError) as exc:
        start_run(isolated_db, context_path=str(ctx_path), mode="volume", allow_test_profile=True)
    assert "复合意向" in str(exc.value)


def test_test_profile_cannot_volume_without_flag(isolated_db, tmp_path, sample_context_payload, monkeypatch):
    from services import apply_run as ar

    monkeypatch.setattr(
        ar,
        "_load_profile",
        lambda allow_test=False: {
            "version": "3.0-test-fixture",
            "universal": {"personal": {"name": "测一填"}},
            "application": {},
        },
    )
    ctx_path = write_json(tmp_path / "ctx.json", sample_context_payload)
    with pytest.raises(ApplyRunError) as exc:
        start_run(isolated_db, context_path=str(ctx_path), mode="volume", allow_test_profile=False)
    assert "测试画像" in str(exc.value)
