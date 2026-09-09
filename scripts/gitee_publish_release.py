#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a Gitee Release and attach the autofill zip. Token from GITEE_TOKEN only."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "li-shuoya"
REPO = "career-os-autofill"
TAG = "v1.8.0"
TITLE = "v1.8.0 网申填表助手"
BODY = """可单独使用，不必 Career OS / GitHub / Python。

下载本页附件 `career-os-autofill-1.8.0.zip`，解压后：

1. Edge 打开 edge://extensions
2. 打开开发人员模式
3. 加载解压缩的扩展（选中含 manifest.json 的文件夹）
4. 设置页填写或拖入 JSON，点「一键导入并启用」

不会自动点提交。
"""
ZIP_PATH = ROOT / "dist" / "career-os-autofill-1.8.0.zip"
API = "https://gitee.com/api/v5"


def token() -> str:
    t = (os.environ.get("GITEE_TOKEN") or os.environ.get("GITEE_ACCESS_TOKEN") or "").strip()
    if not t:
        raise SystemExit(
            "缺少 GITEE_TOKEN。请到 https://gitee.com/profile/personal_access_tokens 新建私人令牌（勾选 projects），然后：\n"
            "  $env:GITEE_TOKEN='你的令牌'\n"
            "再运行本脚本。"
        )
    return t


def api_json(method: str, url: str, data: dict | None = None, tok: str = "") -> dict:
    body = None
    headers = {"User-Agent": "career-os-autofill-release"}
    if data is not None:
        payload = dict(data)
        payload["access_token"] = tok
        body = urllib.parse.urlencode(payload).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif tok and "?" not in url:
        url = url + ("&" if "?" in url else "?") + "access_token=" + urllib.parse.quote(tok)
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Gitee API {exc.code} {url}: {err}") from exc


def multipart_upload(url: str, tok: str, file_path: Path) -> dict:
    boundary = "----CareerOsBoundary7MA4YWxkTrZu0gW"
    filename = file_path.name
    blob = file_path.read_bytes()
    parts = []
    def field(name: str, value: str) -> bytes:
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")
    parts.append(field("access_token", tok))
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/zip\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = b"".join(parts) + head + blob + tail
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "User-Agent": "career-os-autofill-release",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Gitee upload {exc.code}: {err}") from exc


def main() -> int:
    if not ZIP_PATH.is_file():
        raise SystemExit(f"找不到 zip: {ZIP_PATH}")
    tok = token()
    rel = None
    try:
        rel = api_json(
            "GET",
            f"{API}/repos/{OWNER}/{REPO}/releases/tags/{urllib.parse.quote(TAG)}",
            tok=tok,
        )
    except SystemExit:
        rel = None
    if not isinstance(rel, dict) or not rel.get("id"):
        rel = api_json(
            "POST",
            f"{API}/repos/{OWNER}/{REPO}/releases",
            data={
                "tag_name": TAG,
                "name": TITLE,
                "body": BODY,
                "target_commitish": "master",
            },
            tok=tok,
        )
    rid = rel.get("id")
    if not rid:
        raise SystemExit(f"创建发行版失败: {rel}")
    print(f"release_id={rid}")
    names = [a.get("name") for a in (rel.get("assets") or [])]
    if ZIP_PATH.name in names:
        print("zip already attached")
    else:
        uploaded = multipart_upload(
            f"{API}/repos/{OWNER}/{REPO}/releases/{rid}/attach_files",
            tok,
            ZIP_PATH,
        )
        print("attached", uploaded.get("name") or uploaded.get("browser_download_url") or uploaded)
    html = rel.get("html_url") or f"https://gitee.com/{OWNER}/{REPO}/releases"
    print(html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
