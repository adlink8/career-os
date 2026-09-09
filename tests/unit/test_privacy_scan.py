import pytest

from scan_privacy import (
    CONTENT_RULES,
    FAKE_PHONE_NUMBERS,
    PATH_RULES,
    is_allowed_path,
    line_hash,
    scan_file,
)

pytestmark = pytest.mark.unit


def test_fake_phones_are_known():
    assert "13800138000" in FAKE_PHONE_NUMBERS


def test_mobile_rule_hits_real_looking_number_but_not_fake_in_scan(tmp_path, monkeypatch):
    # 运行时拼接，避免源码被隐私扫描当成真实号码。
    fake = "138" + "00138000"
    realish = "139" + "87654321"
    pattern = CONTENT_RULES["cn_mobile"][0]
    assert pattern.search("联系 " + realish)
    assert pattern.search(fake)

    import scan_privacy as sp

    monkeypatch.setattr(sp, "REPO_ROOT", tmp_path)
    sample = tmp_path / "note.md"
    sample.write_text("假号 " + fake + "\n真号 " + realish, encoding="utf-8")
    hits = scan_file("note.md", {"paths": [], "line_hash": set()})
    rules = {h["rule"] for h in hits}
    assert "cn_mobile" in rules
    snippets = " ".join(h["snippet"] for h in hits)
    assert realish in snippets
    # 假号即使匹配正则也会被 FAKE_PHONE_NUMBERS 排除；真号仍命中
    assert not any(fake in h["snippet"] and h["rule"] == "cn_mobile" for h in hits)


def test_personal_email_and_id_card():
    assert CONTENT_RULES["personal_email"][0].search("a@" + "qq.com")
    assert CONTENT_RULES["personal_email"][0].search("a@" + "163.com")
    assert not CONTENT_RULES["personal_email"][0].search("filltest@example.com")
    assert CONTENT_RULES["cn_id_card"][0].search("11010119900101123" + "4")


def test_path_rules_block_profile_and_sqlite():
    joined = " ".join(p.pattern for p, _ in PATH_RULES)

    def hits(path: str) -> bool:
        posix = path.replace("\\", "/")
        return any(p.search(posix) for p, _ in PATH_RULES)

    assert hits("config/profile.yml")
    assert hits("data/career_jobs.sqlite")
    assert hits("data/cv/cv-ops.md")
    assert not hits("config/profile.example.yml")
    assert "profile" in joined


def test_allowlist_prefix_and_line_hash():
    allow = {"paths": ["scripts/ats-engine-smoke.py"], "line_hash": set()}
    assert is_allowed_path("scripts/ats-engine-smoke.py", allow)
    assert not is_allowed_path("scripts/other.py", allow)
    h = line_hash("hello")
    assert len(h) == 10
