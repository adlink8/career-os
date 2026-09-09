#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑 Career OS 单元 / 集成 / 回归测试。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Career OS pytest 入口")
    parser.add_argument(
        "--layer",
        choices=("all", "unit", "integration", "regression"),
        default="all",
    )
    parser.add_argument("-k", dest="keyword", default=None)
    args, rest = parser.parse_known_args()
    cmd = [sys.executable, "-m", "pytest", str(ROOT / "tests"), "--tb=short"]
    if args.layer != "all":
        cmd.extend(["-m", args.layer])
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    cmd.extend(rest)
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
