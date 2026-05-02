import pytest
import os
import tempfile
from server.cpp_tools import read_cpp_file, generate_uproperty_macro, generate_ufunction_macro, refactor_cpp_function

def test_read_cpp_file():
    with tempfile.NamedTemporaryFile(suffix=".cpp", mode="w", delete=False) as f:
        f.write("int main() { return 0; }")
        temp_name = f.name

    try:
        res = read_cpp_file(temp_name)
        assert res.get("success") is True
        assert "int main" in res.get("content")
    finally:
        os.remove(temp_name)

def test_generate_uproperty_macro():
    with tempfile.NamedTemporaryFile(suffix=".h", mode="w", delete=False) as f:
        f.write("class ATest {\n    int32 MyVar;\n};\n")
        temp_name = f.name

    try:
        res = generate_uproperty_macro(temp_name, "MyVar")
        assert res.get("success") is True
        assert res.get("modified") is True
        with open(temp_name, "r") as f:
            content = f.read()
            assert "UPROPERTY(EditAnywhere" in content
            assert "int32 MyVar;" in content
    finally:
        os.remove(temp_name)

def test_generate_ufunction_macro():
    with tempfile.NamedTemporaryFile(suffix=".h", mode="w", delete=False) as f:
        f.write("class ATest {\n    void DoSomething();\n};\n")
        temp_name = f.name

    try:
        res = generate_ufunction_macro(temp_name, "DoSomething")
        assert res.get("success") is True
        assert res.get("modified") is True
        with open(temp_name, "r") as f:
            content = f.read()
            assert "UFUNCTION(BlueprintCallable" in content
            assert "void DoSomething();" in content
    finally:
        os.remove(temp_name)

def test_refactor_cpp_function():
    original = "void ATest::DoSomething() {\n    // Old code\n    int a = 1;\n}\n"
    with tempfile.NamedTemporaryFile(suffix=".cpp", mode="w", delete=False) as f:
        f.write(original)
        temp_name = f.name

    try:
        new_body = "{\n    // New code\n    int b = 2;\n}"
        res = refactor_cpp_function(temp_name, "ATest::DoSomething", new_body)
        assert res.get("success") is True
        with open(temp_name, "r") as f:
            content = f.read()
            assert "// New code" in content
            assert "int b = 2;" in content
            assert "Old code" not in content
    finally:
        os.remove(temp_name)
