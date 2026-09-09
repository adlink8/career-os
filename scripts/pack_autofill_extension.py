#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包可单独分发的网申填表插件 zip（不含个人 profile.json）。"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "extensions" / "ats-autofill"
DIST = ROOT / "dist"
SKIP_NAMES = {
    "profile.json",
    "profile.test.json",
}
SKIP_DIRS = {"native", "__pycache__"}

INSTALL_TXT = """网申自动填表助手 — 安装说明（国内、无需 GitHub / 无需 Career OS）

1. 解压本 zip，得到一个文件夹（里面有 manifest.json）。
2. 打开 Edge（推荐）或 Chrome：
   Edge:  edge://extensions
   Chrome: chrome://extensions
3. 打开右上角「开发人员模式」。
4. 点「加载解压缩的扩展」→ 选中刚才那个文件夹。
5. 首次会弹出设置页：填写底稿，或把 JSON 拖进去，点「一键导入并启用」。
6. 打开企业北森 / Moka 报名页即可填表。不会自动点提交。

不要把解压后的文件夹删掉或挪走，否则扩展会失效。
升级：再下新 zip，解压覆盖同一文件夹，到扩展页点「重新加载」。
"""


def main() -> int:
    manifest = json.loads((SRC / "manifest.json").read_text(encoding="utf-8"))
    version = str(manifest.get("version") or "0")
    name = "career-os-autofill-" + version
    dist_dir = DIST / name
    if DIST.exists():
        for old in DIST.glob("career-os-autofill-*"):
            if old.is_dir():
                shutil.rmtree(old)
            elif old.suffix == ".zip":
                old.unlink()
    dist_dir.mkdir(parents=True, exist_ok=True)

    for path in SRC.rglob("*"):
        rel = path.relative_to(SRC)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name in SKIP_NAMES:
            continue
        dest = dist_dir / rel
        if path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)

    (dist_dir / "安装说明.txt").write_text(INSTALL_TXT, encoding="utf-8")
    zip_path = DIST / (name + ".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in dist_dir.rglob("*"):
            if path.is_file():
                zf.write(path, Path(name) / path.relative_to(dist_dir))
    print(zip_path)
    print("bytes", zip_path.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
