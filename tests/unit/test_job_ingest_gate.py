import pytest

from services.job_ingest_gate import (
    english_hard_block,
    ingest_gate_ok,
    ingest_gate_reasons,
    overspecified_no_train,
)

pytestmark = pytest.mark.unit


def test_cet4_hard_blocks():
    assert english_hard_block("1、本科。2、CET-4或以上。")
    assert english_hard_block("英语四级及以上，可阅读专业技术文献。")
    assert english_hard_block("雅思 6.5 分 / 六级 520 分 / 托福 90 分及以上")
    assert not english_hard_block("本科计算机。加分项：英语六级优先。")
    assert not english_hard_block("良好的英语阅读能力。")


def test_overspec_ai_app_blocks():
    duty = (
        "1. 调研访谈，输出场景清单。\n"
        "2. 拆解 Workflow、Skill、知识库。\n"
        "3. 完成 Agent 工作流搭建、提示词、知识库接入。\n"
        "4. 跟踪数据并沉淀模板。\n"
        "5. 跨部门协作推动从个人工具走向业务流程。\n"
        "6. 学习 RAG、MCP 等前沿并写竞品调研。"
    )
    req = "接触过 GPT/Claude 或 Dify/Coze/LangChain 等即可。"
    assert overspecified_no_train("AI应用工程师", duty, req)
    assert not ingest_gate_ok("AI应用工程师", duty, req)


def test_campus_hardware_ae_passes():
    duty = (
        "1. 负责电机应用方案的研发（电路原理、PCB Layout、单板调试）；\n"
        "2. 根据客户需求提出应用电路设计思路；\n"
        "3. 为销售及现场应用提供设计指导；\n"
        "4. 负责 MCU 芯片电气性能验证；\n"
        "5. 设计验证方法与测试流程；"
    )
    req = (
        "1. 本科计算机、电子、自动化相关；\n"
        "2. 熟练使用 Protel、Altium Designer、Cadence 绘制原理图及 PCB；\n"
        "3. 熟悉模电数电，有编程基础。"
    )
    assert ingest_gate_ok("应用工程师（硬件）（南京）", duty, req)


def test_short_support_intern_passes():
    duty = "1、协助技术支持工程师完成IT设备配置，常见硬件故障处理。"
    req = "1、本科计算机在校生；2、了解计算机软硬件维护知识。"
    assert ingest_gate_ok("技术支持实习生", duty, req)


def test_bonus_english_only_passes():
    req = "1、本科。2、沟通能力强。\n加分项：\n英语六级或雅思优先。"
    assert ingest_gate_ok("运维实习生", "1、协助巡检。", req)
