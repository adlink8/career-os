"""Career OS 统一插件适配层。

核心流程只认识 capability（如 ``code_runner``、``question_bank``、
``interview_agent``、``job_source``），不直接依赖某一个开源项目。插件以
``plugins/<id>/plugin.json`` 声明元数据，启用后再按 entrypoint 延迟加载。
插件默认关闭；启用列表由 ``CAREER_OS_PLUGINS`` 控制，便于随时拔出。
"""

from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from career_os_store import ROOT
except ModuleNotFoundError:  # 允许从仓库根目录以 bin.career_os_plugins 导入
    from bin.career_os_store import ROOT


PLUGIN_ROOT = ROOT / "plugins"


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    capabilities: tuple[str, ...]
    entrypoint: str | None
    enabled_by_default: bool = False
    description: str = ""
    license: str = ""


class PluginError(RuntimeError):
    pass


class PluginManager:
    def __init__(self, root: Path = PLUGIN_ROOT):
        self.root = root
        self._instances: dict[str, Any] = {}

    def discover(self) -> list[PluginManifest]:
        manifests: list[PluginManifest] = []
        if not self.root.exists():
            return manifests
        for path in sorted(self.root.glob("*/plugin.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                manifests.append(
                    PluginManifest(
                        plugin_id=str(raw["id"]),
                        name=str(raw.get("name", raw["id"])),
                        version=str(raw.get("version", "0.0.0")),
                        capabilities=tuple(raw.get("capabilities", [])),
                        entrypoint=raw.get("entrypoint"),
                        enabled_by_default=bool(raw.get("enabled_by_default", False)),
                        description=str(raw.get("description", "")),
                        license=str(raw.get("license", "")),
                    )
                )
            except (OSError, ValueError, KeyError) as exc:
                raise PluginError(f"插件 manifest 无法读取: {path}: {exc}") from exc
        return manifests

    def enabled_ids(self) -> set[str]:
        raw = os.environ.get("CAREER_OS_PLUGINS", "")
        if raw.strip():
            return {item.strip() for item in raw.split(",") if item.strip()}
        return {m.plugin_id for m in self.discover() if m.enabled_by_default}

    def manifests_for(self, capability: str | None = None, *, enabled_only: bool = False) -> list[PluginManifest]:
        manifests = self.discover()
        if capability:
            manifests = [m for m in manifests if capability in m.capabilities]
        if enabled_only:
            active = self.enabled_ids()
            manifests = [m for m in manifests if m.plugin_id in active]
        return manifests

    def load(self, manifest: PluginManifest) -> Any:
        if not manifest.entrypoint:
            raise PluginError(f"插件 {manifest.plugin_id} 未声明 entrypoint")
        if manifest.plugin_id in self._instances:
            return self._instances[manifest.plugin_id]
        module_name, separator, factory_name = manifest.entrypoint.partition(":")
        if not separator:
            factory_name = "create_plugin"
        module = importlib.import_module(module_name)
        factory = getattr(module, factory_name)
        instance = factory(manifest=manifest)
        self._instances[manifest.plugin_id] = instance
        return instance

    def capability(self, capability: str, preferred: str | None = None) -> Any | None:
        candidates = self.manifests_for(capability, enabled_only=True)
        if preferred:
            candidates = [m for m in candidates if m.plugin_id == preferred]
        for manifest in candidates:
            try:
                plugin = self.load(manifest)
                if hasattr(plugin, "provide"):
                    provided = plugin.provide(capability)
                    if provided is not None:
                        return provided
            except (ImportError, AttributeError, PluginError) as exc:
                # 插件故障不应拖垮 Career OS；调用方可回退到核心能力。
                print(f"[plugin-skip] {manifest.plugin_id}: {exc}")
        return None


def get_plugin_manager() -> PluginManager:
    return PluginManager()
