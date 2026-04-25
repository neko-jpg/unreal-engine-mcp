"""HTTP client for the scene-syncd Rust service."""

import os
import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("UnrealMCP_Advanced")

SCENE_SYNCD_URL = os.getenv("SCENE_SYNCD_URL", "http://127.0.0.1:8787")
SCENE_SYNCD_TIMEOUT = int(os.getenv("SCENE_SYNCD_TIMEOUT", "30"))


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