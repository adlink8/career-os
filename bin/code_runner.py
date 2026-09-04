"""代码题执行后端。

默认使用可选的 Judge0 自托管服务；Windows 本地后端明确标记为
trusted-local，只适合本人编写的题目代码，不把它宣传成安全沙箱。
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request


@dataclass
class RunResult:
    status: str
    cases: list[dict]
    stdout: str = ""
    stderr: str = ""
    elapsed_ms: int = 0
    error: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "ACCEPTED" and bool(self.cases) and all(c.get("passed") for c in self.cases)


def _function_name(source_code: str) -> str:
    tree = ast.parse(source_code)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
    raise ValueError("题目代码中没有可调用的函数")


def build_harness(source_code: str, test_cases: list[dict]) -> str:
    """生成只负责测试输出的脚本，不在主进程中 exec 用户代码。"""

    func_name = _function_name(source_code)
    cases_literal = repr(test_cases)
    return f"""{source_code}

import json as __career_json
__career_cases = {cases_literal}
__career_results = []
for __career_index, __career_case in enumerate(__career_cases, 1):
    try:
        __career_input = __career_case.get('input')
        if isinstance(__career_input, list):
            __career_actual = {func_name}(*__career_input)
        else:
            __career_actual = {func_name}(__career_input)
        __career_expected = __career_case.get('expected')
        __career_results.append({{
            'index': __career_index,
            'passed': __career_actual == __career_expected,
            'actual': __career_actual,
            'expected': __career_expected,
        }})
    except Exception as __career_exc:
        __career_results.append({{
            'index': __career_index,
            'passed': False,
            'expected': __career_case.get('expected'),
            'error': f'{{type(__career_exc).__name__}}: {{__career_exc}}',
        }})
print(__career_json.dumps(__career_results, ensure_ascii=False, default=str))
"""


class TrustedLocalRunner:
    name = "trusted-local"

    def __init__(self, timeout_seconds: float = 3.0):
        self.timeout_seconds = timeout_seconds

    def run(self, source_code: str, test_cases: list[dict]) -> RunResult:
        started = time.perf_counter()
        try:
            harness = build_harness(source_code, test_cases)
        except (SyntaxError, ValueError) as exc:
            return RunResult("COMPILE_ERROR", [], elapsed_ms=0, error=str(exc))

        with tempfile.TemporaryDirectory(prefix="career-os-code-") as tmp:
            path = Path(tmp) / "solution.py"
            path.write_text(harness, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", "-S", str(path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=self.timeout_seconds,
                    cwd=tmp,
                )
            except subprocess.TimeoutExpired:
                return RunResult("TIME_LIMIT_EXCEEDED", [], elapsed_ms=_elapsed(started), error="超过本地执行时间限制")
            except OSError as exc:
                return RunResult("RUNTIME_ERROR", [], elapsed_ms=_elapsed(started), error=str(exc))

        if proc.returncode != 0:
            return RunResult("RUNTIME_ERROR", [], proc.stdout, proc.stderr, _elapsed(started), "本地进程退出码非 0")
        try:
            cases = json.loads(proc.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError) as exc:
            return RunResult("RUNTIME_ERROR", [], proc.stdout, proc.stderr, _elapsed(started), f"无法解析判题输出: {exc}")
        status = "ACCEPTED" if cases and all(item.get("passed") for item in cases) else "WRONG_ANSWER"
        return RunResult(status, cases, proc.stdout, proc.stderr, _elapsed(started))


class Judge0Runner:
    name = "judge0"

    def __init__(self, base_url: str, token: str | None = None, language_id: int = 71, timeout_seconds: float = 12.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.language_id = language_id
        self.timeout_seconds = timeout_seconds

    def run(self, source_code: str, test_cases: list[dict]) -> RunResult:
        started = time.perf_counter()
        try:
            harness = build_harness(source_code, test_cases)
            payload = json.dumps({"language_id": self.language_id, "source_code": harness, "stdin": ""}).encode()
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["X-Auth-Token"] = self.token
            req = request.Request(
                f"{self.base_url}/submissions?wait=true&base64_encoded=false",
                data=payload,
                headers=headers,
                method="POST",
            )
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (ValueError, SyntaxError, error.URLError, error.HTTPError, TimeoutError, OSError) as exc:
            return RunResult("UNAVAILABLE", [], elapsed_ms=_elapsed(started), error=f"Judge0 请求失败: {exc}")

        stdout = body.get("stdout") or ""
        stderr = body.get("stderr") or ""
        status_text = (body.get("status") or {}).get("description", "")
        try:
            cases = json.loads(stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            cases = []
        if cases:
            status = "ACCEPTED" if all(item.get("passed") for item in cases) else "WRONG_ANSWER"
        elif status_text:
            status = status_text.upper().replace(" ", "_")
        else:
            status = "RUNTIME_ERROR"
        return RunResult(status, cases, stdout, stderr, _elapsed(started), body.get("message", ""))


def _elapsed(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def configured_runner(*, trusted_local: bool = False):
    # 外部实现优先走统一插件接口；插件不可用时再使用内置 Judge0 配置。
    try:
        try:
            from career_os_plugins import get_plugin_manager
        except ModuleNotFoundError:
            from bin.career_os_plugins import get_plugin_manager

        plugin_runner = get_plugin_manager().capability(
            "code_runner", preferred=os.environ.get("CAREER_OS_CODE_PLUGIN")
        )
        if plugin_runner is not None:
            return plugin_runner
    except (ImportError, ValueError):
        pass
    base_url = os.environ.get("JUDGE0_URL")
    if base_url:
        language_id = int(os.environ.get("JUDGE0_LANGUAGE_ID", "71"))
        return Judge0Runner(base_url, os.environ.get("JUDGE0_TOKEN"), language_id)
    if trusted_local:
        return TrustedLocalRunner()
    return None
