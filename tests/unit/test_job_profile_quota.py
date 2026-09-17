import pytest

from services.job_profile_quota import allocate_company_slots, background_fit

pytestmark = pytest.mark.unit

PROFILE = {
    "education": {"degree": "本科", "major": "计算机科学与技术", "graduation": "2027-06"},
    "career_target": {
        "primary": ["DevOps/运维实习", "IoT/Cloud 技术支持"],
        "secondary": ["技术销售", "现场应用"],
        "cities": ["南京", "苏州", "无锡", "上海"],
        "positioning": ["不走纯嵌入式驱动/底层固件路线"],
    },
    "skills": {"proficient": ["Linux", "Python", "Docker"], "familiar": ["SQL"]},
}


def test_fit_prefers_ops_support_over_ic_design():
    ops = background_fit(
        PROFILE,
        {
            "job_title": "技术支持实习生",
            "city": "南京",
            "education_req": "本科计算机",
            "responsibilities": "1、协助处理硬件故障。",
            "requirements": "本科计算机在校生，了解Linux。",
        },
    )
    ic = background_fit(
        PROFILE,
        {
            "job_title": "数字IC设计工程师（校招）",
            "city": "南京",
            "education_req": "微电子硕士",
            "responsibilities": "RTL 实现。",
            "requirements": "微电子专业，Verilog。",
        },
    )
    assert ops is not None and ops >= 55
    assert ic is None or ic < 45


def test_quota_is_count_of_fits_not_fixed_three():
    jobs = [
        {
            "id": 1,
            "job_title": "技术支持实习生",
            "city": "南京",
            "education_req": "本科计算机",
            "responsibilities": "协助排障。",
            "requirements": "本科，了解Linux。",
            "recommendation_weight": 90,
        },
        {
            "id": 2,
            "job_title": "运维工程师",
            "city": "无锡",
            "education_req": "本科计算机",
            "responsibilities": "协助 Linux 巡检。",
            "requirements": "本科计算机，Linux Docker。",
            "recommendation_weight": 70,
        },
        {
            "id": 3,
            "job_title": "数字IC设计工程师",
            "city": "南京",
            "education_req": "硕士微电子",
            "responsibilities": "RTL。",
            "requirements": "Verilog。",
            "recommendation_weight": 99,
        },
        {
            "id": 4,
            "job_title": "CET岗",
            "city": "南京",
            "education_req": "本科",
            "responsibilities": "运维。",
            "requirements": "CET-4或以上。",
            "recommendation_weight": 95,
        },
    ]
    picked = allocate_company_slots(jobs, PROFILE)
    assert [j["id"] for j in picked] == [1, 2]
    assert len(picked) != 3


def test_benshuobo_not_master_hard():
    fit = background_fit(
        PROFILE,
        {
            "job_title": "现场应用工程师",
            "city": "苏州",
            "education_req": "2027届本硕博",
            "responsibilities": "客户端技术支持。",
            "requirements": "2027届本硕博。",
        },
    )
    assert fit is not None and fit >= 50


def test_shenzhen_excluded_shanghai_allowed():
    sz = background_fit(
        PROFILE,
        {
            "job_title": "运维工程师",
            "city": "广东省·深圳市 (南山区)",
            "education_req": "本科",
            "responsibilities": "Linux。",
            "requirements": "本科 Linux。",
        },
    )
    sh = background_fit(
        PROFILE,
        {
            "job_title": "运维工程师",
            "city": "上海",
            "education_req": "本科计算机",
            "responsibilities": "协助 Linux。",
            "requirements": "本科计算机 Linux。",
        },
    )
    nj = background_fit(
        PROFILE,
        {
            "job_title": "运维工程师",
            "city": "南京",
            "education_req": "本科计算机",
            "responsibilities": "协助 Linux。",
            "requirements": "本科计算机 Linux。",
        },
    )
    assert sz is None
    assert sh is not None and nj is not None and nj > sh


def test_wrong_city_excluded():
    fit = background_fit(
        PROFILE,
        {
            "job_title": "运维工程师",
            "city": "北京市",
            "education_req": "本科",
            "responsibilities": "Linux。",
            "requirements": "本科 Linux。",
        },
    )
    assert fit is None


def test_quota_zero_when_nothing_fits():
    jobs = [
        {
            "id": 9,
            "job_title": "模拟IC设计工程师",
            "city": "北京",
            "education_req": "硕士",
            "responsibilities": "电路设计。",
            "requirements": "微电子硕士，CET-4。",
            "recommendation_weight": 80,
        }
    ]
    assert allocate_company_slots(jobs, PROFILE) == []


def test_band_keeps_near_best_fit_only():
    jobs = [
        {
            "id": 1,
            "job_title": "运维实习",
            "city": "南京",
            "education_req": "本科",
            "responsibilities": "Linux Docker。",
            "requirements": "本科计算机 Linux。",
            "recommendation_weight": 70,
        },
        {
            "id": 2,
            "job_title": "应用工程师",
            "city": "南京",
            "education_req": "本科计算机",
            "responsibilities": "协助客户支持。",
            "requirements": "本科计算机。",
            "recommendation_weight": 99,
        },
    ]
    picked = allocate_company_slots(jobs, PROFILE)
    assert [j["id"] for j in picked] == [1]


def test_sorts_by_weight_among_fits():
    jobs = [
        {
            "id": 1,
            "job_title": "运维实习",
            "city": "苏州",
            "education_req": "本科",
            "responsibilities": "Linux。",
            "requirements": "本科 Linux。",
            "recommendation_weight": 60,
        },
        {
            "id": 2,
            "job_title": "技术支持",
            "city": "南京",
            "education_req": "本科计算机",
            "responsibilities": "现场排障。",
            "requirements": "本科计算机。",
            "recommendation_weight": 85,
        },
    ]
    picked = allocate_company_slots(jobs, PROFILE)
    assert [j["id"] for j in picked] == [2, 1]
