"""HTTP client for the scene-syncd Rust service."""

import json
import os
import logging
from typing import Any, Dict, Iterator, Optional

import requests

logger = logging.getLogger("UnrealMCP_Advanced")

SCENE_SYNCD_URL = os.getenv("SCENE_SYNCD_URL", "http://127.0.0.1:8787")
SCENE_SYNCD_TIMEOUT = int(os.getenv("SCENE_SYNCD_TIMEOUT", "30"))
SCENE_SYNCD_STREAM_TIMEOUT = int(os.getenv("SCENE_SYNCD_STREAM_TIMEOUT", "600"))


def call_scene_syncd_stream(
    path: str, payload: Dict[str, Any]
) -> Iterator[Dict[str, Any]]:
    """Send a POST request expecting an `application/x-ndjson` stream and yield parsed JSON events.

    Used by the streaming sync endpoints (中長期-3). Each yielded value is the
    decoded JSON object for one NDJSON line. The iterator terminates when the
    server closes the stream. Network errors are converted to a single
    `{"event": "error", "message": ...}` event before termination.
    """
    url = f"{SCENE_SYNCD_URL}{path}"
    try:
        with requests.post(
            url, json=payload, stream=True, timeout=SCENE_SYNCD_STREAM_TIMEOUT
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                try:
                    yield json.loads(raw_line)
                except json.JSONDecodeError as e:
                    yield {
                        "event": "error",
                        "message": f"Failed to decode NDJSON line: {e}; raw={raw_line!r}",
                    }
    except requests.exceptions.ConnectionError:
        yield {
            "event": "error",
            "message": f"Could not connect to scene-syncd at {url}.",
        }
    except requests.exceptions.Timeout:
        yield {
            "event": "error",
            "message": f"Request to scene-syncd at {url} timed out after {SCENE_SYNCD_STREAM_TIMEOUT}s.",
        }
    except requests.exceptions.HTTPError as e:
        yield {
            "event": "error",
            "message": f"HTTP error from scene-syncd: {e}",
        }
    except Exception as e:  # noqa: BLE001
        yield {
            "event": "error",
            "message": f"Unexpected error calling scene-syncd: {e}",
        }


def call_scene_syncd(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a POST request to the scene-syncd service and return the JSON response."""
    url = f"{SCENE_SYNCD_URL}{path}"
    try:
        response = requests.post(url, json=payload, timeout=SCENE_SYNCD_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to scene-syncd at {url}")
        return {
            "success": False,
            "data": None,
            "warnings": [],
            "error": {
                "code": "scene_syncd_unavailable",
                "message": f"Could not connect to scene-syncd at {url}. Is the service running?",
            },
        }
    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling scene-syncd at {url}")
        return {
            "success": False,
            "data": None,
            "warnings": [],
            "error": {
                "code": "scene_syncd_timeout",
                "message": f"Request to scene-syncd at {url} timed out after {SCENE_SYNCD_TIMEOUT}s",
            },
        }
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error from scene-syncd: {e}")
        try:
            return response.json()
        except Exception:
            return {
                "success": False,
                "data": None,
                "warnings": [],
                "error": {
                    "code": "scene_syncd_http_error",
                    "message": str(e),
                },
            }
    except Exception as e:
        logger.error(f"Unexpected error calling scene-syncd: {e}")
        return {
            "success": False,
            "data": None,
            "warnings": [],
            "error": {
                "code": "scene_syncd_error",
                "message": str(e),
            },
        }


def call_scene_syncd_get(path: str) -> Dict[str, Any]:
    """Send a GET request to the scene-syncd service and return the JSON response."""
    url = f"{SCENE_SYNCD_URL}{path}"
    try:
        response = requests.get(url, timeout=SCENE_SYNCD_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to scene-syncd at {url}")
        return {
            "success": False,
            "data": None,
            "warnings": [],
            "error": {
                "code": "scene_syncd_unavailable",
                "message": f"Could not connect to scene-syncd at {url}",
            },
        }
    except Exception as e:
        logger.error(f"Unexpected error calling scene-syncd GET: {e}")
        return {
            "success": False,
            "data": None,
            "warnings": [],
            "error": {
                "code": "scene_syncd_error",
                "message": str(e),
            },
        }