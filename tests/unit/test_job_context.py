import pytest

from services.job_context import (
    context_from_job_row,
    extract_hard_filters,
    extract_job_ad_id,
    first_http_url,
    looks_like_form_page,
    looks_like_jd,
    merge_contexts,
    pick_jd_text,
    refine_title,
)

pytestmark = pytest.mark.unit


def test_extract_job_ad_id_beisen_and_moka():
    assert (
        extract_job_ad_id(
            "https://example.zhiye.com/campus/detail?jobAdId=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        )
        == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    assert extract_job_ad_id("https://app.mokahr.com/job/11111111-2222-3333-4444-555555555555") == (
        "11111111-2222-3333-4444-555555555555"
    )
    assert extract_job_ad_id(
        "https://app.mokahr.com/apply/focus/148405?sourceToken=abc#/job/f5bfbd62-fd05-476a-8807-f5bb6b114b53/apply"
    ) == "f5bfbd62-fd05-476a-8807-f5bb6b114b53"


def test_hard_filters():
    filters = extract_hard_filters(
        "运维工程师（苏州）2027届",
        "本科及以上，可实习6个月，英语四级，工作地点苏州、上海。熟悉 Linux Docker。",
    )
    assert "2027届" in filters["graduation_cohorts"]
    assert "本科" in filters["education"]
    assert "苏州" in filters["cities"]
    assert filters["internship_months_min"] == 6
    assert "CET-4" in filters["english"]


def test_refine_title_does_not_steal_duty_line():
    title = refine_title(
        {
            "title": "运维工程师",
            "jd_text": "岗位职责：负责 Linux Docker Kubernetes 运维。\n任职要求：本科。",
        }
    )
    assert title == "运维工程师"
    # 单行 JD 里带「运维」也不能覆盖官网标题
    title2 = refine_title(
        {
            "title": "运维工程师",
            "jd_text": "岗位职责：负责 Linux Docker Kubernetes 运维。任职要求：本科 2027届。",
        }
    )
    assert title2 == "运维工程师"


def test_refine_title_priority_marker():
    title = refine_title({"title": "校园招聘", "jd_text": "【优先】Linux运维工程师\n岗位职责：…"})
    assert "Linux运维工程师" in title


def test_pick_jd_prefers_duty_text_over_form():
    form = "你正在投递职位：运维工程师\n预览并提交"
    jd = "岗位职责：负责 Linux。任职要求：本科。"
    assert pick_jd_text(form, jd) == jd
    assert looks_like_jd(jd)
    assert looks_like_form_page(form)


def test_merge_contexts_keeps_detail_url_and_form_fields():
    detail = {
        "url": "https://example.zhiye.com/campus/detail?jobAdId=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "title": "运维工程师",
        "company": "示例公司",
        "jd_text": "岗位职责：负责 Linux。任职要求：本科。",
        "form_schema": [],
        "captured_at": "2026-09-01T00:00:00Z",
    }
    form = {
        "url": "https://example.zhiye.com/campus/form?jobAdId=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "title": "运维工程师",
        "jd_text": "你正在投递职位：运维工程师\n预览并提交",
        "form_schema": [{"label": "姓名", "required": True}],
        "captured_at": "2026-09-02T00:00:00Z",
        "host": "example.zhiye.com",
    }
    merged = merge_contexts(detail, form)
    assert "detail" in merged["url"]
    assert merged["form_schema"][0]["label"] == "姓名"
    assert "Linux" in merged["jd_text"]
    assert merged["job_ad_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_first_http_url_strips_trailing_note():
    assert (
        first_http_url("https://metaso.cn/ （简历直投：a@b.com）")
        == "https://metaso.cn/"
    )


def test_context_from_job_row_builds_jd():
    ctx = context_from_job_row(
        {
            "job_title": "运维工程师实习",
            "company_name": "微测科技",
            "responsibilities": "负责 Linux 监控与值班。",
            "requirements": "本科 2027届，熟悉 Docker。",
            "application_url": "https://micro.example/campus/detail?jobAdId=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        }
    )
    assert ctx["title"] == "运维工程师实习"
    assert ctx["company"] == "微测科技"
    assert "岗位职责" in ctx["jd_text"] and "Linux" in ctx["jd_text"]
    assert ctx["job_ad_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert ctx["stats"]["jd_chars"] >= 40
