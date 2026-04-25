"""
Standalone response-format helpers for the Unreal MCP project.

This module has zero imports from ``server`` or ``helpers`` and therefore
breaks the circular-import chain that would occur if these functions lived
inside ``server.validation`` (which itself is imported by ``server.__init__``,
which imports every tool module, which imports helpers, which import these
functions back).

All modules that need to construct or inspect responses should import from
here rather than defining their own inline copies.

Canonical response envelope after normalization
-------------------------------------------------
Success::

    {"success": True, ...data fields...}

Error::

    {"success": False, "error": "<human-readable message>", ...optional extra fields...}

The C++ bridge sends ``{"status": "success", "result": {…}}`` or
``{"status": "error", "error": "…"}``, which ``core.send_command`` normalises
into the shapes above before any Python tool sees them.
"""

from typing import Any, Dict


def make_error_response(error: str, **extra: Any) -> Dict[str, Any]:
    """Create a standardised error response.

    All error responses use ``{"success": False, "error": "<msg>"}`` plus
    any extra key-value pairs supplied via *extra*.
    """
    result: Dict[str, Any] = {"success": False, "error": error}
    result.update(extra)
    return result


def is_success_response(result: Dict[str, Any]) -> bool:
    """Return True if *result* represents a successful operation.

    Accepts both ``{"success": True}`` and ``{"status": "success"}``
    envelopes, since the C++ bridge uses the latter.
    """
    if result.get("success") is True:
        return True
    if result.get("status") == "success":
        return True
    return False


def is_error_response(result: Dict[str, Any]) -> bool:
    """Return True if *result* represents a failed operation.

    Accepts ``{"success": False}``, ``{"status": "error"}``, or any dict
    that ``is_success_response`` does not consider successful.
    """
    if not isinstance(result, dict):
        return True
    if result.get("success") is False or result.get("status") == "error":
        return True
    return not is_success_response(result)