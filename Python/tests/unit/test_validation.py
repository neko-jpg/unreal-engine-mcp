"""Unit tests for input validation utilities."""
import math
import pytest
from server.validation import (
    validate_vector3,
    validate_color,
    validate_string,
    validate_float,
    validate_int,
    validate_positive_int,
    validate_nonneg_int,
    validate_unreal_path,
    ValidationError,
    MAX_ACTORS_PER_BATCH,
    MAX_WORLD_EXTENT,
)


class TestValidateVector3:
    def test_valid_list(self):
        result = validate_vector3([1.0, 2.0, 3.0], "pos")
        assert result == [1.0, 2.0, 3.0]

    def test_valid_tuple(self):
        result = validate_vector3((0.0, -1.0, 0.5), "pos")
        assert result == [0.0, -1.0, 0.5]

    def test_none_allowed(self):
        result = validate_vector3(None, "pos", allow_none=True)
        assert result is None

    def test_none_not_allowed(self):
        with pytest.raises(ValidationError, match="must not be None"):
            validate_vector3(None, "pos", allow_none=False)

    def test_wrong_type(self):
        with pytest.raises(ValidationError, match="must be a list"):
            validate_vector3("not_a_list", "pos")

    def test_wrong_length(self):
        with pytest.raises(ValidationError, match="exactly 3 elements"):
            validate_vector3([1.0, 2.0], "pos")

    def test_non_numeric_element(self):
        with pytest.raises(ValidationError, match="must be a number"):
            validate_vector3([1.0, "two", 3.0], "pos")

    def test_nan_rejected(self):
        with pytest.raises(ValidationError, match="must be finite"):
            validate_vector3([1.0, math.nan, 3.0], "pos")

    def test_inf_rejected(self):
        with pytest.raises(ValidationError, match="must be finite"):
            validate_vector3([1.0, math.inf, 3.0], "pos")

    def test_out_of_bounds(self):
        with pytest.raises(ValidationError, match="must be between"):
            validate_vector3([0.0, MAX_WORLD_EXTENT + 1, 0.0], "pos")


class TestValidateColor:
    def test_valid_rgb(self):
        result = validate_color([0.5, 0.3, 0.1])
        assert result == [0.5, 0.3, 0.1, 1.0]

    def test_valid_rgba(self):
        result = validate_color([1.0, 0.0, 0.0, 0.5])
        assert result == [1.0, 0.0, 0.0, 0.5]

    def test_clamped_to_zero(self):
        result = validate_color([-0.5, 0.5, 0.5])
        assert result == [0.0, 0.5, 0.5, 1.0]

    def test_clamped_to_one(self):
        result = validate_color([1.5, 0.5, 0.5])
        assert result == [1.0, 0.5, 0.5, 1.0]

    def test_wrong_type(self):
        with pytest.raises(ValidationError, match="must be a list"):
            validate_color("red")


class TestValidateString:
    def test_valid_string(self):
        result = validate_string("hello", "name")
        assert result == "hello"

    def test_too_short(self):
        with pytest.raises(ValidationError, match="at least"):
            validate_string("", "name", min_length=1)

    def test_too_long(self):
        with pytest.raises(ValidationError, match="at most"):
            validate_string("x" * 300, "name", max_length=256)

    def test_none_not_allowed(self):
        with pytest.raises(ValidationError, match="must not be None"):
            validate_string(None, "name")

    def test_wrong_type(self):
        with pytest.raises(ValidationError, match="must be a string"):
            validate_string(42, "name")


class TestValidateInt:
    def test_valid_int(self):
        result = validate_int(42, "count")
        assert result == 42

    def test_bool_rejected(self):
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_int(True, "flag")

    def test_float_rejected(self):
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_int(3.14, "count")

    def test_below_min(self):
        with pytest.raises(ValidationError, match="must be >="):
            validate_int(0, "count", min_val=1)

    def test_above_max(self):
        with pytest.raises(ValidationError, match="must be <="):
            validate_int(MAX_ACTORS_PER_BATCH + 1, "count", max_val=MAX_ACTORS_PER_BATCH)


class TestValidateUnrealPath:
    def test_valid_path(self):
        result = validate_unreal_path("/Engine/BasicShapes/Cube.Cube", "mesh")
        assert result == "/Engine/BasicShapes/Cube.Cube"

    def test_no_slash_prefix(self):
        with pytest.raises(ValidationError, match="must start with"):
            validate_unreal_path("Engine/Cube", "mesh")

    def test_path_traversal_rejected(self):
        with pytest.raises(ValidationError, match="path traversal not allowed"):
            validate_unreal_path("/Engine/../secret", "mesh")

    def test_null_byte_rejected(self):
        with pytest.raises(ValidationError, match="control characters"):
            validate_unreal_path("/Engine/\x00Cube", "mesh")

    def test_newline_rejected(self):
        with pytest.raises(ValidationError, match="control characters"):
            validate_unreal_path("/Engine/\nCube", "mesh")


class TestValidateNonNeg:
    def test_positive(self):
        result = validate_nonneg_int(5, "count")
        assert result == 5

    def test_zero(self):
        result = validate_nonneg_int(0, "count")
        assert result == 0

    def test_negative_rejected(self):
        with pytest.raises(ValidationError, match="must be >="):
            validate_nonneg_int(-1, "count")