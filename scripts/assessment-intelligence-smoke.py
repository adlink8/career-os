"""测评情报数据契约冒烟：只验证来源、证据等级和版权边界。"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "data" / "assessment-intelligence.json"


def main() -> int:
    data = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    records = data["records"]
    assert len(records) >= 8, len(records)
    assert data["policy"]["raw_company_questions"] is False
    assert {item["source_type"] for item in records} >= {"official", "community"}
    assert {item["evidence_level"] for item in records} >= {"confirmed", "reported"}
    assert all(item.get("source_url", "").startswith(("https://", "http://")) for item in records)
    assert all(item.get("raw_questions_included") is False for item in records)
    assert all(item.get("company") and item.get("question_families") for item in records)
    print(f"Assessment intelligence smoke: PASS ({len(records)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
