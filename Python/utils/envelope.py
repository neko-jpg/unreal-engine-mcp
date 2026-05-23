"""234-stubs Wave 0 (#72): executed-envelope assertion helpers.

Spec: docs/implementation-plan-234-stubs.md sec. 11.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class EnvelopeAssertionError(AssertionError):
    """Raised when the executed-envelope contract is violated."""

    def __init__(self, command, message, payload=None):
        self.command = command
        self.payload = payload
        super().__init__(f"[envelope:{command}] {message}")


def _is_dict(x):
    return isinstance(x, dict)


def _success_flag(envelope):
    if envelope.get("success") is True:
        return True
    if envelope.get("status") == "success":
        return True
    return False


def _data_block(envelope):
    data = envelope.get("data")
    return data if _is_dict(data) else None


def is_executed_envelope(result):
    if not _is_dict(result):
        return False
    if not _success_flag(result):
        return False
    data = _data_block(result)
    if data is None:
        return False
    if data.get("queued") is True:
        return False
    return data.get("executed") is True


def is_queued_envelope(result):
    if not _is_dict(result):
        return False
    if not _success_flag(result):
        return False
    data = _data_block(result)
    if data is None:
        return result.get("queued") is True
    if data.get("executed") is True:
        return False
    return data.get("queued") is True


def assert_executed(result, command, *, allow_legacy=False):
    """Assert result is fully-executed; return inner data dict on success."""
    if not _is_dict(result):
        raise EnvelopeAssertionError(command, f"expected dict envelope, got {type(result).__name__}", None)
    if not _success_flag(result):
        err = result.get("error") or result.get("message") or "<no error message>"
        hint = result.get("hint")
        if hint:
            err = f"{err} (hint: {hint})"
        raise EnvelopeAssertionError(command, f"envelope reports failure: {err}", result)
    if is_queued_envelope(result):
        raise EnvelopeAssertionError(command, "handler is still queued-only; promote it to executed=true", result)
    data = _data_block(result)
    if data is None:
        if allow_legacy:
            return {k: v for k, v in result.items() if k not in {"success", "status"}}
        raise EnvelopeAssertionError(
            command,
            "envelope is in the legacy flat shape; migrate the handler to MakeExecutedEnvelope() or pass allow_legacy=True",
            result,
        )
    if data.get("executed") is True:
        return data
    raise EnvelopeAssertionError(command, "data.executed is not True", result)


def assert_no_queued(result, command):
    if is_queued_envelope(result):
        raise EnvelopeAssertionError(command, "handler emitted queued=true; this regression is banned by issue #77", result)


def assert_error(result, command, expected_substring=None):
    if not _is_dict(result):
        raise EnvelopeAssertionError(command, f"expected dict envelope, got {type(result).__name__}", None)
    if _success_flag(result):
        raise EnvelopeAssertionError(command, "envelope reports success but an error was expected", result)
    if expected_substring is not None:
        msg = result.get("error") or ""
        if expected_substring not in msg:
            raise EnvelopeAssertionError(
                command,
                f"error message does not contain {expected_substring!r}, got: {msg!r}",
                result,
            )
    return result
