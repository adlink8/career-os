"""命令行导入外部题库：python bin/import_question_bank.py export.json --source exameow"""

from __future__ import annotations

import argparse
import sys

from question_bank_adapter import QuestionBankAdapter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="导入 Career OS 统一题库格式 JSON/CSV")
    parser.add_argument("source", help="题库文件路径")
    parser.add_argument("--source", default="external", dest="source_plugin", help="来源插件 ID，用于幂等去重")
    parser.add_argument("--apply", action="store_true", help="确认写入本地题库")
    args = parser.parse_args()
    count = QuestionBankAdapter().load(args.source, source_plugin=args.source_plugin, apply=args.apply)
    if args.apply:
        print(f"✅ 已导入/更新 {count} 道题，来源插件: {args.source_plugin}")
    else:
        print(f"👀 题库预览: {count} 道题；加 --apply 才写入")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
