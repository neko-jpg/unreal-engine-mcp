"""Input validation utilities for Unreal MCP server tools."""

import math
from typing import Any, Dict, List, Optional, Tuple


MAX_ACTORS_PER_BATCH = 500
MAX_WORLD_EXTENT = 1000000.0


class ValidationError(ValueError):
    """Raised when input validation fails."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def validate_vector3(
    value: Any,
    field_name: str,
    *,
    allow_none: bool = True,
    min_val: float = -MAX_WORLD_EXTENT,
    max_val: float = MAX_WORLD_EXTENT,
) -> Optional[List[float]]:
    if value is None:
        if allow_none:
            return None
        raise ValidationError(field_name, "must not be None")
    if not isinstance(value, (list, tuple)):
        raise ValidationError(field_name, f"must be a list of 3 floats, got {type(value).__name__}")
    if len(value) != 3:
        raise ValidationError(field_name, f"must have exactly 3 elements, got {len(value)}")
    result = []
    for i, v in enumerate(value):
        if not isinstance(v, (int, float)):
            raise ValidationError(field_name, f"element [{i}] must be a number, got {type(v).__name__}")
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            raise ValidationError(field_name, f"element [{i}] must be finite, got {v}")
        if v < min_val or v > max_val:
            raise ValidationError(field_name, f"element [{i}] must be between {min_val} and {max_val}, got {v}")
        result.append(float(v))
    return result


def validate_color(value: Any, field_name: str = "color") -> List[float]:
    if not isinstance(value, (list, tuple)):
        raise ValidationError(field_name, f"must be a list of 3 or 4 floats, got {type(value).__name__}")
    if len(value) not in (3, 4):
        raise ValidationError(field_name, f"must have 3 or 4 elements, got {len(value)}")
    result = []
    for i, v in enumerate(value):
        if not isinstance(v, (int, float)):
            raise ValidationError(field_name, f"element [{i}] must be a number, got {type(v).__name__}")
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            raise ValidationError(field_name, f"element [{i}] must be finite, got {v}")
        clamped = float(min(1.0, max(0.0, v)))
        result.append(clamped)
    if len(result) == 3:
        result.append(1.0)
    return result


def validate_string(
    value: Any,
    field_name: str,
    *,
    min_length: int = 1,
    max_length: int = 256,
    allow_none: bool = False,
) -> Optional[str]:
    if value is None:
        if allow_none:
            return None
        raise ValidationError(field_name, "must not be None")
    if not isinstance(value, str):
        raise ValidationError(field_name, f"must be a string, got {type(value).__name__}")
    if len(value) < min_length:
        raise ValidationError(field_name, f"must be at least {min_length} characters, got {len(value)}")
    if len(value) > max_length:
        raise ValidationError(field_name, f"must be at most {max_length} characters, got {len(value)}")
    return value


def validate_float(
    value: Any,
    field_name: str,
    *,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    allow_none: bool = False,
) -> Optional[float]:
    if value is None:
        if allow_none:
            return None
        raise ValidationError(field_name, "must not be None")
    if not isinstance(value, (int, float)):
        raise ValidationError(field_name, f"must be a number, got {type(value).__name__}")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValidationError(field_name, f"must be finite, got {value}")
    result = float(value)
    if min_val is not None and result < min_val:
        raise ValidationError(field_name, f"must be >= {min_val}, got {result}")
    if max_val is not None and result > max_val:
        raise ValidationError(field_name, f"must be <= {max_val}, got {result}")
    return result


def validate_int(
    value: Any,
    field_name: str,
    *,
    min_val: Optional[int] = None,
    max_val: Optional[int] = None,
    allow_none: bool = False,
) -> Optional[int]:
    if value is None:
        if allow_none:
            return None
        raise ValidationError(field_name, "must not be None")
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(field_name, f"must be an integer, got {type(value).__name__}")
    if min_val is not None and value < min_val:
        raise ValidationError(field_name, f"must be >= {min_val}, got {value}")
    if max_val is not None and value > max_val:
        raise ValidationError(field_name, f"must be <= {max_val}, got {value}")
    return value


def validate_positive_int(value: Any, field_name: str, *, max_val: Optional[int] = None) -> int:
    return validate_int(value, field_name, min_val=1, max_val=max_val)


def validate_nonneg_int(value: Any, field_name: str, *, max_val: Optional[int] = None) -> int:
    return validate_int(value, field_name, min_val=0, max_val=max_val)


def validate_unreal_path(value: Any, field_name: str) -> str:
    value = validate_string(value, field_name)
    if not value.startswith("/"):
        raise ValidationError(field_name, f"must start with '/', got '{value}'")
    return value


def make_validation_error_response(error: ValidationError) -> Dict[str, Any]:
    return {"success": False, "message": f"Validation error: {error.field}: {error.message}"}


def make_validation_error_response_from_exception(exc: Exception) -> Dict[str, Any]:
    if isinstance(exc, ValidationError):
        return make_validation_error_response(exc)
    return {"success": False, "message": str(exc)}