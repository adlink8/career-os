"""AI Mock Interviewer compatibility adapter.

The current implementation intentionally remains local and model-free.  It
reuses the stable DeepInterview contract while keeping a distinct plugin
entrypoint, so a future model-backed implementation can replace this adapter
without changing Career OS callers.
"""

from __future__ import annotations

from typing import Any

from plugins.deepinterview.adapter import DeepInterviewAdapter


class AIMockInterviewerAdapter(DeepInterviewAdapter):
    def __init__(self, manifest: Any = None):
        super().__init__(manifest=manifest)
        if not self.plugin_id or self.plugin_id == "deepinterview":
            self.plugin_id = "ai-mock-interviewer"
        self.provider = f"{self.plugin_id}-local-compat"

    def provide(self, capability: str):
        if capability == "question_bank":
            try:
                from bin.question_bank_adapter import QuestionBankAdapter

                return QuestionBankAdapter()
            except (ImportError, AttributeError):
                return None
        return super().provide(capability)


def create_plugin(manifest: Any = None) -> AIMockInterviewerAdapter:
    return AIMockInterviewerAdapter(manifest=manifest)
