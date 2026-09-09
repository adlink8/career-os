# -*- coding: utf-8 -*-
"""隐私内容扫描器（DATA-03 防线，2026-09-09）

用途：
  1. pre-commit 钩子：扫描暂存区文件，命中隐私规则则拒绝提交（exit 1）
  2. CI（GitHub Actions）：对比 base 分支的变更文件，命中则使 CI 失败
  3. --all：全量扫描 tracked 文件，用于基线审计

规则维度：
  - 内容正则：真实姓名、手机号、身份证、个人邮箱
  - 文件路径：简历/画像/投递库等 DATA-03 约定仅本地的文件被强行 add 时拦截

白名单：config/privacy-allowlist.yml
  - paths:    路径前缀放行（含理由），存量豁免
  - line_hash: 单行豁免（sha1 前 10 位，防止误伤测试画像）

用法：
  python bin/scan_privacy.py            # 扫描暂存区（pre-commit 模式）
  python bin/scan_privacy.py --ci       # 扫描与 base 的差异（CI 模式）
  python bin/scan_privacy.py --all      # 全量 tracked 文件
  python bin/scan_privacy.py <file...>  # 扫描指定文件
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST_PATH = REPO_ROOT / "config" / "privacy-allowlist.yml"

# ---------------------------------------------------------------------------
# 内容规则：name -> (正则, 说明)
# ---------------------------------------------------------------------------
# 标准测试假号（业内通用假数据，非真实号码），cn_mobile 规则排除
FAKE_PHONE_NUMBERS = {"13800138000", "13900139000", "13012345678", "13800000000", "13900000000"}

# 真实姓名（Unicode 转义书写，避免扫描器源码自命中）
_REAL_NAME = "\u674e\u7855\u7814"

CONTENT_RULES = {
    "real_name": (re.compile(_REAL_NAME), "真实姓名（DATA-03：仓库只进脱敏样本）"),
    "cn_mobile": (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "疑似手机号"),
    "cn_id_card": (
        re.compile(r"(?<![0-9A-Za-z/])\d{17}[0-9Xx](?![0-9A-Za-z])"),
        "疑似身份证号",
    ),
    "personal_email": (
        re.compile(r"[A-Za-z0-9._%+-]+@(?:qq|foxmail|163|126|gmail|outlook|hotmail)\.(?:com|cn|net)", re.I),
        "疑似个人邮箱",
    ),
}

# ---------------------------------------------------------------------------
# 路径规则：命中即拦截（防止 gitignore 被绕过强加）
# ---------------------------------------------------------------------------
PATH_RULES = [
    (re.compile(r"(?:^|/)config/profile\.yml$"), "真实求职画像（仅本地，提交用 profile.example.yml）"),
    (re.compile(r"(?:^|/)data/cv/"), "简历文件（DATA-03 仅本地）"),
    (re.compile("简历|resume_?李|" + _REAL_NAME + r".*\.(?:pdf|docx?)$", re.I), "疑似简历文件"),
    (re.compile(r"(?:^|/)data/(?:career_jobs\.(?:sqlite|db)|tracker\.tsv)"), "投递权威数据（仅本地）"),
    (re.compile(r"\.(?:sqlite|sqlite3|db|bak)$"), "数据库/备份文件"),
]

BINARY_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".zip", ".gz", ".7z", ".woff", ".woff2", ".ttf", ".hyb"}


def load_allowlist() -> dict:
    """解析白名单（最小 YAML 子集，避免引入 PyYAML 依赖）。"""
    allow = {"paths": [], "line_hash": set()}
    if not ALLOWLIST_PATH.exists():
        return allow
    section = None
    for raw in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.strip() == "paths:":
            section = "paths"
            continue
        if line.strip() == "line_hash:":
            section = "line_hash"
            continue
        if line.startswith((" ", "-")) and section == "paths" and line.strip().startswith("- "):
            allow["paths"].append(line.strip()[2:].strip())
        elif line.startswith((" ", "-")) and section == "line_hash":
            allow["line_hash"].add(line.strip()[2:].strip())
    return allow


def is_allowed_path(path: str, allow: dict) -> bool:
    return any(path.startswith(p) or path == p for p in allow["paths"])


def line_hash(line: str) -> str:
    return hashlib.sha1(line.strip().encode("utf-8")).hexdigest()[:10]


def list_staged() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [f for f in out.split("\0") if f]


def list_ci_changed() -> list[str]:
    base = os.environ.get("PRIVACY_SCAN_BASE", "origin/main")
    subprocess.run(["git", "fetch", "--quiet", "origin"], cwd=REPO_ROOT, capture_output=True)
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD", "-z"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [f for f in out.split("\0") if f]


def list_all_tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
    return [f for f in out.split("\0") if f]


def scan_file(path: str, allow: dict) -> list[dict]:
    findings: list[dict] = []
    full = REPO_ROOT / path
    if not full.is_file():
        return findings

    # 白名单整文件豁免
    if is_allowed_path(path, allow):
        return findings

    # 路径规则（命中直接拦截）

    for pattern, desc in PATH_RULES:
        if pattern.search(path.replace("\\", "/")):
            findings.append({"path": path, "line": 0, "rule": "path", "desc": desc, "snippet": path})
            break
    if full.suffix.lower() in BINARY_EXT:
        return findings
    try:
        text = full.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings
    for lineno, line in enumerate(text.splitlines(), 1):
        h = line_hash(line)
        if h in allow["line_hash"]:
            continue
        for rule, (pattern, desc) in CONTENT_RULES.items():
            m = pattern.search(line)
            if m and not (rule == "cn_mobile" and m.group() in FAKE_PHONE_NUMBERS):
                masked = line.strip()
                findings.append({"path": path, "line": lineno, "rule": rule, "desc": desc, "snippet": masked[:120]})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="隐私内容扫描器")
    parser.add_argument("files", nargs="*", help="显式指定文件（缺省按模式自动选择）")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ci", action="store_true", help="CI 模式：扫描与 base 分支差异")
    mode.add_argument("--all", action="store_true", help="全量扫描 tracked 文件")
    parser.add_argument("--base", default=None, help="CI 模式 base 分支（默认 origin/main）")
    args = parser.parse_args()

    allow = load_allowlist()

    if args.files:
        targets = args.files
    elif args.all:
        targets = list_all_tracked()
    elif args.ci:
        if args.base:
            os.environ["PRIVACY_SCAN_BASE"] = args.base
        targets = list_ci_changed()
    else:
        targets = list_staged()

    findings: list[dict] = []
    for path in targets:
        findings.extend(scan_file(path, allow))

    if not findings:
        print(f"[privacy-scan] OK — 扫描 {len(targets)} 个文件，无隐私命中")
        return 0

    print(f"[privacy-scan] FAIL — {len(targets)} 个文件中命中 {len(findings)} 处隐私内容：\n")
    for f in findings:
        loc = f"{f['path']}:{f['line']}" if f["line"] else f["path"]
        print(f"  [{f['rule']}] {loc}")
        print(f"    规则: {f['desc']}")
        print(f"    内容: {f['snippet']}\n")
    print("处理方式：删除隐私内容，或在 config/privacy-allowlist.yml 登记豁免（附理由）。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
