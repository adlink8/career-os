#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Career OS — Technical Lexicon & NLP Service (技术词库与分词公共服务层)
提供高精度的中英混合边界正则匹配、技术字典与 TF-IDF 分词器。
"""

import re
from typing import Dict, List, Set

TECH_DICTIONARY = {
    "ai_llm": [
        "RAG", "Agent", "FastAPI", "LangChain", "LlamaIndex", "Prompt", "大模型", "向量检索", 
        "Embedding", "PyTorch", "ONNX", "Transformer", "微调", "Fine-tuning", "NLP", "多模态",
        "Milvus", "Chroma", "Qdrant", "BM25", "LLM", "vLLM", "Ollama"
    ],
    "data_eng": [
        "SQL", "ETL", "Hive", "Spark", "Flink", "Kafka", "数据清洗", "数据仓库", "血缘分析",
        "数据治理", "MySQL", "PostgreSQL", "ClickHouse", "数据建模", "爬虫", "Scrapy", "反爬",
        "逆向", "Selenium", "Pandas", "NumPy", "数据湖", "Hadoop", "数仓", "数据分析"
    ],
    "devops_sys": [
        "Linux", "Docker", "Kubernetes", "K8s", "CI/CD", "Shell", "Bash", "Nginx", "Git",
        "TCP/IP", "Wireshark", "Prometheus", "Grafana", "自动化测试", "系统监控", "运维",
        "抓包", "路由交换", "网络协议", "负载均衡", "微服务", "Ansible", "DevOps", "排障"
    ],
    "iot_embed": [
        "ESP32", "MQTT", "Modbus", "单片机", "嵌入式", "传感器", "串口", "网关", "FreeRTOS",
        "STM32", "C语言", "C++", "上位机", "工业物联网", "物联网", "硬件调试", "局域网", "PLC",
        "树莓派", "RTOS", "边缘计算", "PyQt5", "CAN总线", "I2C", "SPI"
    ],
    "soft_eng": [
        "Java", "SpringBoot", "Python", "Go", "Golang", "Vue", "React", "RESTful", "API",
        "Redis", "消息队列", "面向对象", "设计模式", "单元测试", "GitFlow", "软件工程", "UML"
    ]
}

ALL_TECH_KEYWORDS = {}
for cat, words in TECH_DICTIONARY.items():
    for w in words:
        ALL_TECH_KEYWORDS[w.lower()] = w

def match_keyword_in_text(kw: str, text: str) -> bool:
    """Accurately match English words (with ASCII lookaround) or Chinese substrings in mixed text."""
    if re.search(r'[\u4e00-\u9fa5]', kw):
        return kw in text
    else:
        pattern = r'(?i)(?<![a-zA-Z0-9])' + re.escape(kw) + r'(?![a-zA-Z0-9])'
        return bool(re.search(pattern, text))

def extract_keywords_from_jd(jd_text: str) -> Set[str]:
    """Extract required tech keywords from JD using technical dictionary & lookaround."""
    found_keywords = set()
    for kw_lower, original_case in ALL_TECH_KEYWORDS.items():
        if match_keyword_in_text(kw_lower, jd_text):
            found_keywords.add(original_case)
    return found_keywords

def hybrid_tokenizer(text: str) -> List[str]:
    """Tokenize mixed Chinese and English text for TF-IDF without external segmenter."""
    tokens = re.findall(r'[a-zA-Z0-9+#]{2,}', text.lower())
    cn_chars = re.sub(r'[^\u4e00-\u9fa5]', '', text)
    for i in range(len(cn_chars) - 1):
        tokens.append(cn_chars[i:i+2])
        if i < len(cn_chars) - 2:
            tokens.append(cn_chars[i:i+3])
    return tokens
