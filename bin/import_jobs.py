"""导入外部岗位导出；默认预览，--apply 才写库。"""

from __future__ import annotations

import argparse
import sys

from job_source_adapter import JobSourceAdapter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="导入 Career OS 统一岗位格式 JSON/CSV")
    parser.add_argument("source", help="岗位导出文件路径")
    parser.add_argument("--source", default="external", dest="source_plugin", help="来源插件 ID")
    parser.add_argument("--apply", action="store_true", help="确认写入本地岗位库")
    args = parser.parse_args()
    result = JobSourceAdapter().load(args.source, source_plugin=args.source_plugin, apply=args.apply)
    if args.apply:
        print(f"✅ 岗位导入完成: 新增 {result['inserted']}，更新 {result['updated']}，企业 {result['companies']} 家")
    else:
        print(f"👀 预览: {result['preview']} 条岗位 / {result['companies']} 家企业；加 --apply 才写入")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
