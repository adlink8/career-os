from __future__ import annotations

import os

from bin.code_runner import Judge0Runner


class Judge0Plugin:
    def __init__(self, manifest=None):
        self.manifest = manifest

    def provide(self, capability: str):
        if capability != "code_runner":
            return None
        base_url = os.environ.get("JUDGE0_URL")
        if not base_url:
            return None
        language_id = int(os.environ.get("JUDGE0_LANGUAGE_ID", "71"))
        return Judge0Runner(base_url, os.environ.get("JUDGE0_TOKEN"), language_id)


def create_plugin(manifest=None):
    return Judge0Plugin(manifest=manifest)

