"""
C++ Tools for Unreal Engine MCP Server.
Provides tools for analyzing, refactoring, and generating C++ code (like UPROPERTY/UFUNCTION macros).
"""
import os
import re
import logging
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
from server.core import mcp, make_error_response
from utils.responses import is_success_response

logger = logging.getLogger("UnrealMCP_CppTools")

@mcp.tool()
def read_cpp_file(file_path: str) -> Dict[str, Any]:
    """
    Reads the content of a C++ source or header file.

    Args:
        file_path: Absolute or relative path to the C++ file (.cpp, .h).

    Returns:
        Dict containing the file content or an error message.
    """
    if not os.path.exists(file_path):
        return make_error_response(f"File not found: {file_path}")

    if not (file_path.endswith('.cpp') or file_path.endswith('.h')):
        return make_error_response("File must be a .cpp or .h file")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "success": True,
            "file_path": file_path,
            "content": content
        }
    except Exception as e:
        logger.error(f"Error reading C++ file {file_path}: {e}")
        return make_error_response(f"Failed to read file: {str(e)}")

@mcp.tool()
def generate_uproperty_macro(
    file_path: str,
    variable_name: str,
    specifiers: List[str] = ["EditAnywhere", "BlueprintReadWrite", "Category=\"Default\""]
) -> Dict[str, Any]:
    """
    Analyzes a C++ header file and inserts a UPROPERTY macro above the specified variable.
    If a UPROPERTY already exists, it can optionally be updated (currently just adds if missing).

    Args:
        file_path: Path to the .h file.
        variable_name: The name of the variable to annotate.
        specifiers: List of UPROPERTY specifiers (e.g. ["EditAnywhere", "BlueprintReadWrite"]).

    Returns:
        Dict indicating success or failure, and the modified snippet or full content.
    """
    if not os.path.exists(file_path):
        return make_error_response(f"File not found: {file_path}")

    if not file_path.endswith('.h'):
        return make_error_response("UPROPERTY macros should be added to header (.h) files.")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        macro_string = f"UPROPERTY({', '.join(specifiers)})"

        # Simple regex to find the variable declaration
        # Matches type variable_name; or type variable_name = value;
        var_regex = re.compile(rf"\b{variable_name}\b\s*[;=]")

        modified_lines = []
        found = False
        already_has_macro = False

        for i, line in enumerate(lines):
            if var_regex.search(line):
                # Check if the previous non-empty line has a UPROPERTY
                prev_line_idx = i - 1
                while prev_line_idx >= 0 and lines[prev_line_idx].strip() == "":
                    prev_line_idx -= 1

                if prev_line_idx >= 0 and "UPROPERTY" in lines[prev_line_idx]:
                    already_has_macro = True
                    modified_lines.append(line)
                else:
                    found = True
                    # Preserve indentation
                    indent = len(line) - len(line.lstrip())
                    macro_line = " " * indent + macro_string + "\n"
                    modified_lines.append(macro_line)
                    modified_lines.append(line)
            else:
                modified_lines.append(line)

        if not found and not already_has_macro:
             return make_error_response(f"Variable '{variable_name}' not found in {file_path}")

        if already_has_macro:
             return {"success": True, "message": f"Variable '{variable_name}' already has a UPROPERTY macro.", "modified": False}

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)

        return {
            "success": True,
            "message": f"Successfully added UPROPERTY to {variable_name}.",
            "modified": True,
            "macro_added": macro_string
        }

    except Exception as e:
        logger.error(f"Error generating UPROPERTY in {file_path}: {e}")
        return make_error_response(f"Failed to generate UPROPERTY: {str(e)}")

@mcp.tool()
def generate_ufunction_macro(
    file_path: str,
    function_name: str,
    specifiers: List[str] = ["BlueprintCallable", "Category=\"Default\""]
) -> Dict[str, Any]:
    """
    Analyzes a C++ header file and inserts a UFUNCTION macro above the specified function declaration.

    Args:
        file_path: Path to the .h file.
        function_name: The name of the function to annotate.
        specifiers: List of UFUNCTION specifiers (e.g. ["BlueprintCallable", "BlueprintPure"]).

    Returns:
        Dict indicating success or failure.
    """
    if not os.path.exists(file_path):
        return make_error_response(f"File not found: {file_path}")

    if not file_path.endswith('.h'):
        return make_error_response("UFUNCTION macros should be added to header (.h) files.")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        macro_string = f"UFUNCTION({', '.join(specifiers)})"

        # Simple regex to find function declaration: ReturnType FunctionName(Args...);
        # This is a naive regex and might need refinement for complex signatures.
        func_regex = re.compile(rf"\b{function_name}\s*\(")

        modified_lines = []
        found = False
        already_has_macro = False

        for i, line in enumerate(lines):
            if func_regex.search(line):
                # Check previous line for UFUNCTION
                prev_line_idx = i - 1
                while prev_line_idx >= 0 and lines[prev_line_idx].strip() == "":
                    prev_line_idx -= 1

                if prev_line_idx >= 0 and "UFUNCTION" in lines[prev_line_idx]:
                    already_has_macro = True
                    modified_lines.append(line)
                else:
                    found = True
                    indent = len(line) - len(line.lstrip())
                    macro_line = " " * indent + macro_string + "\n"
                    modified_lines.append(macro_line)
                    modified_lines.append(line)
            else:
                modified_lines.append(line)

        if not found and not already_has_macro:
             return make_error_response(f"Function '{function_name}' not found in {file_path}")

        if already_has_macro:
             return {"success": True, "message": f"Function '{function_name}' already has a UFUNCTION macro.", "modified": False}

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)

        return {
            "success": True,
            "message": f"Successfully added UFUNCTION to {function_name}.",
            "modified": True,
            "macro_added": macro_string
        }

    except Exception as e:
        logger.error(f"Error generating UFUNCTION in {file_path}: {e}")
        return make_error_response(f"Failed to generate UFUNCTION: {str(e)}")

@mcp.tool()
def refactor_cpp_function(
    file_path: str,
    function_name: str,
    new_function_body: str
) -> Dict[str, Any]:
    """
    Replaces the body of a C++ function in a .cpp file with new code.
    Useful for refactoring bloated functions, replacing Tick with Timers, etc.

    Args:
        file_path: Path to the .cpp file.
        function_name: Name of the function to refactor (e.g. "AFireWeapon::Fire").
        new_function_body: The complete new C++ code for the function body (including braces).
                           Example: "{\n    // new code\n}"

    Returns:
        Dict indicating success or failure.
    """
    if not os.path.exists(file_path):
        return make_error_response(f"File not found: {file_path}")

    if not file_path.endswith('.cpp'):
        return make_error_response("Function refactoring is intended for .cpp files.")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try to locate the function definition.
        # This is a basic parser that looks for: ReturnType ClassName::FunctionName(...) {
        # It handles multiline signatures poorly, but works for standard simple formats.

        # We look for function_name followed by '(' and eventually a '{'
        # The regex looks for `function_name(` with anything up to the opening brace `{`
        pattern = re.compile(rf"\b{re.escape(function_name)}\s*\([^)]*\)\s*(const)?\s*\{{", re.MULTILINE)
        match = pattern.search(content)

        if not match:
            return make_error_response(f"Function definition for '{function_name}' not found or could not be parsed in {file_path}.")

        start_idx = match.end() - 1 # Index of the opening brace '{'

        # Find the matching closing brace
        brace_count = 0
        end_idx = -1

        for i in range(start_idx, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break

        if end_idx == -1:
            return make_error_response(f"Could not find matching closing brace for function '{function_name}'.")

        # Replace the function body
        # Ensure new_function_body starts and ends with braces if not provided
        if not new_function_body.strip().startswith('{'):
            new_function_body = '{\n' + new_function_body
        if not new_function_body.strip().endswith('}'):
            new_function_body = new_function_body + '\n}'

        modified_content = content[:start_idx] + new_function_body + content[end_idx + 1:]

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        return {
            "success": True,
            "message": f"Successfully refactored function '{function_name}'.",
            "modified": True
        }

    except Exception as e:
        logger.error(f"Error refactoring function in {file_path}: {e}")
        return make_error_response(f"Failed to refactor function: {str(e)}")
