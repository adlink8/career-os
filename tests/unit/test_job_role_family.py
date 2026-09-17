import pytest

from services.job_role_family import role_family

pytestmark = pytest.mark.unit


def test_merge_ops_and_it():
    assert role_family("Linux 集群运维与技术支持") == "运维/IT"
    assert role_family("【27届校招】IT工程师") == "运维/IT"
    assert role_family("SRE 云原生运维") == "运维/IT"


def test_merge_field_support_and_fae():
    assert role_family("技术支持实习生") == "现场支持/FAE"
    assert role_family("2027校招现场应用工程师(J11375)") == "现场支持/FAE"
    assert role_family("机器人系统调试与现场应用工程师 (FAE)") == "现场支持/FAE"


def test_app_and_sales_and_test():
    assert role_family("应用工程师（硬件）（南京）") == "应用工程"
    assert role_family("芯片应用工程师（2027校招）") == "应用工程"
    assert role_family("技术销售工程师（ACE计划）") == "技术销售"
    assert role_family("销售实习生") == "技术销售"
    assert role_family("芯片系统测试工程师") == "测试/验证"
    assert role_family("射频系统验证工程师") == "测试/验证"
