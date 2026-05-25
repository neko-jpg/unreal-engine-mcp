"""Fake UnrealConnection used by integration tests.

Records every send_command call and returns programmable responses. Used so
PatchExecutor / dialog_tools.scene_edit(apply_safe) can be exercised without a
running editor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class _Call:
    command: str
    params: Dict[str, Any]


class FakeUnrealConnection:
    def __init__(self, responder: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None) -> None:
        self.calls: List[_Call] = []
        self._responder = responder
        # Auto-success default behaviour
        self.default_response = {"success": True}
        # Programmable per-command overrides
        self.responses: Dict[str, Any] = {}

    def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        self.calls.append(_Call(command, dict(params)))
        if self._responder is not None:
            return self._responder(command, params)
        if command in self.responses:
            value = self.responses[command]
            return value(params) if callable(value) else dict(value)
        return dict(self.default_response)

    # Helpers ----------------------------------------------------------------
    def commands(self) -> List[str]:
        return [c.command for c in self.calls]

    def calls_for(self, command: str) -> List[_Call]:
        return [c for c in self.calls if c.command == command]
