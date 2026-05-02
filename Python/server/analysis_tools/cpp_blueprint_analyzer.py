import re
from pathlib import Path
from server.core import mcp

@mcp.tool()
async def analyze_execution_flow(target_class_or_func: str, root_dir: str = ".") -> str:
    """
    Attempts to analyze and trace the execution flow involving the given C++ class
    or function name, especially across UFUNCTION / BlueprintCallable boundaries.
    Outputs a Mermaid Sequence Diagram representing potential calls.

    Args:
        target_class_or_func: The C++ class or function name to search for (e.g. "TakeDamage" or "AMyActor").
        root_dir: The project root directory. Defaults to ".".
    """
    root_path = Path(root_dir)
    source_dir = root_path / "Source"

    if not source_dir.exists():
        return f"Error: Source directory not found at {source_dir.absolute()}"

    output = []
    output.append(f"## Execution Flow Analysis for: {target_class_or_func}")
    output.append("```mermaid")
    output.append("sequenceDiagram")
    output.append("    participant BP as Blueprint")
    output.append("    participant CPP as C++ Source")

    # 1. Search headers for UFUNCTIONs exposing this to Blueprints
    ufunc_pattern = re.compile(r"UFUNCTION\s*\((.*?)\)\s*\n\s*(?:virtual\s+)?(?:\w+\s+)?(\w+)\s*\(", re.MULTILINE)

    found_any = False

    for h_file in source_dir.rglob("*.h"):
        try:
            content = h_file.read_text(encoding='utf-8', errors='ignore')
            for match in ufunc_pattern.finditer(content):
                macros = match.group(1).lower()
                func_name = match.group(2)

                # If target matches the function name or class name (broad search)
                if target_class_or_func.lower() in func_name.lower() or target_class_or_func.lower() in h_file.stem.lower():
                    found_any = True
                    class_name = h_file.stem

                    if "blueprintcallable" in macros or "blueprintpure" in macros:
                        output.append(f"    BP->>CPP: Call {class_name}::{func_name}()")
                    elif "blueprintimplementableevent" in macros or "blueprintnativeevent" in macros:
                        output.append(f"    CPP->>BP: Trigger Event {func_name}()")
                    else:
                        output.append(f"    CPP->>CPP: Internal Call {class_name}::{func_name}()")
        except Exception:
            continue

    if not found_any:
        output.append(f"    note over BP,CPP: No direct UFUNCTION links found for '{target_class_or_func}'")
        output.append("    note over BP,CPP: (Ensure the name is correct and it is exposed via UFUNCTION)")

    output.append("```")
    return "\n".join(output)
