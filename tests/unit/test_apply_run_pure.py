import pytest

from services.apply_run import (
    ApplyRunError,
    ATS_MIN_SCORE,
    REVIEW_PASS_EACH,
    REVIEW_PASS_TOTAL,
    WEIGHT_ATS,
    WEIGHT_HR,
    WEIGHT_TECH,
    _coverage_from_fields,
    _is_noise_label,
    _is_test_profile,
    _norm_mode,
    _norm_role,
    _open_key_for_label,
    _pick,
    _resolve_slot,
    _value_for_slot,
    _vetoes,
    _volume_knockout,
    build_autofill,
    pick_volume_track,
    suggest_gap_triage,
)

pytestmark = pytest.mark.unit


def test_norm_mode_aliases():
    assert _norm_mode("海投") == "volume"
    assert _norm_mode("专投") == "precision"
    assert _norm_mode("VOLUME") == "volume"
    with pytest.raises(ApplyRunError):
        _norm_mode("auto")


def test_norm_role_aliases():
    assert _norm_role("campus-hr") == "hr"
    assert _norm_role("ats-scanner") == "ats-llm"
    with pytest.raises(ApplyRunError):
        _norm_role("submitter")


def test_pick_volume_track_keywords():
    assert pick_volume_track("运维工程师", "Linux Docker")["track"] == "ops"
    assert pick_volume_track("大模型应用开发", "RAG LLM")["track"] == "ai"
    assert pick_volume_track("物联网工程师", "MQTT 嵌入式")["track"] == "iot"
    assert pick_volume_track("行政专员", "会议纪要")["track"] == "ops"


def test_volume_knockout_composite_title():
    reason = _volume_knockout({"title": "技术支持工程师 / 运维工程师"})
    assert "复合意向" in reason


def test_volume_knockout_single_role_ok():
    assert _volume_knockout({"title": "运维工程师（Linux与容器方向）"}) == ""


def test_test_profile_gate():
    assert _is_test_profile({"version": "3.0-test-fixture", "universal": {"personal": {"name": "甲"}}})
    assert _is_test_profile({"version": "3.0", "universal": {"personal": {"name": "测一填"}}})
    assert not _is_test_profile({"version": "3.0", "universal": {"personal": {"name": "正式姓名"}}})


def test_noise_and_open_keys():
    assert _is_noise_label("请选择")
    assert _is_noise_label("验证码")
    assert not _is_noise_label("求职意向")
    assert _open_key_for_label("为什么选择本公司") == "why_us"
    assert _open_key_for_label("职业规划") == "career_plan"


def test_review_weights_and_thresholds():
    assert (WEIGHT_ATS, WEIGHT_HR, WEIGHT_TECH) == (0.35, 0.30, 0.35)
    assert abs(WEIGHT_ATS + WEIGHT_HR + WEIGHT_TECH - 1.0) < 1e-9
    assert ATS_MIN_SCORE == 70
    assert REVIEW_PASS_TOTAL == 85
    assert REVIEW_PASS_EACH == 80


def test_vetoes_hr_mass_apply():
    vetoes = _vetoes(
        {"verdict": "PASS", "score": 90, "hr_impressions": {"mass_apply_risk_level": "HIGH"}},
        {"verdict": "PASS", "score": 90},
        {"verdict": "PASS", "score": 90, "knockout_check": {}},
    )
    assert any("HR" in v for v in vetoes)


def test_vetoes_ats_llm_score_is_not_a_veto():
    vetoes = _vetoes(
        {"verdict": "PASS", "score": 90, "hr_impressions": {"mass_apply_risk_level": "LOW"}},
        {"verdict": "PASS", "score": 88},
        {"verdict": "WARN", "score": 40, "knockout_check": {"has_composite_intent_violation": False}},
    )
    assert vetoes == []


def test_coverage_ready_requires_required_filled():
    fields = [
        {"label": "姓名", "required": True, "kind": "mapped", "empty": False},
        {"label": "手机号", "required": True, "kind": "mapped", "empty": True},
        {"label": "请选择", "required": False, "kind": "noise", "empty": True},
    ]
    cov = _coverage_from_fields(fields)
    assert cov["ready"] is False
    assert cov["required_empty"] == ["手机号"]


def test_build_autofill_uses_official_title(sample_context_payload, test_profile):
    payload = build_autofill(sample_context_payload, test_profile)
    assert payload["target_position"] == "运维工程师"
    assert payload["title"] == payload["target_position"]
    by_label = {f["label"]: f for f in payload["fields"]}
    assert by_label["求职意向"]["value"] == "运维工程师"
    assert by_label["请选择"]["kind"] == "noise"
    assert by_label["姓名"]["value"] == "测一填"


def test_value_for_slot_city_fallback():
    profile = {"application": {"target_cities": "苏州、上海"}}
    assert _value_for_slot("application.expected_city", profile) == "苏州"


def test_resolve_slot_from_rules():
    rules = _compile_safe()
    if not rules:
        pytest.skip("field-map-rules.json 缺失")
    assert _resolve_slot("姓名", rules) == "universal.personal.name"
    assert _resolve_slot("学校名称", rules) == "universal.education.undergraduate.school"


def _compile_safe():
    from services.apply_run import _compile_rules

    return _compile_rules()


def test_pick_nested():
    assert _pick({"a": {"b": 1}}, "a.b") == 1
    assert _pick({"a": {}}, "a.b.c") is None


def test_suggest_gap_triage_known_terms(tmp_path, monkeypatch):
    from services import apply_run as ar

    monkeypatch.setenv("CAREER_OS_APPLY_RUNS", str(tmp_path / "runs"))
    run_id = 99
    artifacts = tmp_path / "runs" / "99" / "artifacts"
    artifacts.mkdir(parents=True)
    bounce = {
        "ats": {"missing": ["LangChain", "Kafka", "微服务", "Milvus", "Redis", "多模态"]}
    }
    (artifacts / "bounce-iter1.json").write_text(
        __import__("json").dumps(bounce, ensure_ascii=False), encoding="utf-8"
    )
    (artifacts / "clause-map.json").write_text(
        __import__("json").dumps({"clauses": [{"jd": "多模态", "status": "corroborated"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(ar, "runs_root", lambda: tmp_path / "runs")
    out = suggest_gap_triage(run_id)
    by = {i["term"]: i["decision"] for i in out["items"]}
    assert by["LangChain"] == "skip"
    assert by["Kafka"] == "skip"
    assert by["微服务"] == "skip"
    assert by["Milvus"] == "skip"
    assert by["Redis"] == "branch"
    assert by["多模态"] == "rewrite"
