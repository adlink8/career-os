import json
from pathlib import Path

import pytest

from services.apply_run import _compile_rules, _resolve_slot, _value_for_slot

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def test_field_map_rules_compile():
    rules = _compile_rules()
    assert len(rules) >= 10
    slots = {r["slot"] for r in rules}
    assert "universal.personal.name" in slots
    assert "application.target_position" in slots


def test_common_beisen_labels():
    rules = _compile_rules()
    cases = {
        "姓名": "universal.personal.name",
        "手机号码": "universal.personal.phone",
        "电子邮箱": "universal.personal.email",
        "学校名称": "universal.education.undergraduate.school",
        "学习形式": "universal.education.undergraduate.education_type",
        "期望工作城市": "application.expected_city",
        "求职意向": "application.target_position",
    }
    for label, slot in cases.items():
        assert _resolve_slot(label, rules) == slot, label


def test_id_card_empty_in_test_profile():
    profile = json.loads(
        (ROOT / "extensions" / "ats-autofill" / "profile.test.json").read_text(encoding="utf-8")
    )
    assert profile["universal"]["personal"]["name"] == "测一填"
    assert not profile["universal"]["personal"].get("id_card")
    assert profile["universal"]["personal"]["phone"] == "13800138000"


def test_list_slot_uses_first_project():
    profile = {
        "application": {
            "projects": [
                {"name": "网关", "full_text": "MQTT 排障超过二十个字符的描述。"},
                {"name": "其他"},
            ]
        }
    }
    assert _value_for_slot("application.projects.name", profile) == "网关"
    assert "MQTT" in _value_for_slot("application.projects.full_text", profile)
