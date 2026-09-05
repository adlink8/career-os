"""将 GitHub REST 搜索暴露为 Career OS 的 project_source 能力。"""

from __future__ import annotations

try:
    from bin.github_project_candidates import GitHubRestSource
except ModuleNotFoundError:
    from github_project_candidates import GitHubRestSource


class GitHubProjectSourceAdapter(GitHubRestSource):
    capability = "project_source"

    def provide(self, capability: str):
        return self if capability == self.capability else None


def create_plugin(manifest=None):
    return GitHubProjectSourceAdapter()
