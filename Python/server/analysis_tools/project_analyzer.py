import re
from pathlib import Path
from server.core import mcp

@mcp.tool()
async def analyze_project_structure(root_dir: str = ".") -> str:
    """
    Scans the Unreal Engine project root directory and generates a Markdown
    representation (including Mermaid.js graphs) of the project structure,
    dependencies, and class inheritance.

    Args:
        root_dir: The root directory of the Unreal project to scan. Defaults to current directory.
    """
    root_path = Path(root_dir)
    if not root_path.exists() or not root_path.is_dir():
        return f"Error: Directory {root_dir} does not exist or is not a directory."

    output = []
    output.append(f"# Project Structure Analysis: {root_path.absolute()}")

    # 1. Directory Tree (simplified)
    output.append("## Directory Structure")
    output.append("```text")
    def build_tree(dir_path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0):
        if current_depth > max_depth:
            return ""

        tree_str = ""
        try:
            items = sorted([p for p in dir_path.iterdir() if p.is_dir() and not p.name.startswith('.') and p.name not in ('Binaries', 'Intermediate', 'Saved')])
            for i, item in enumerate(items):
                is_last = (i == len(items) - 1)
                marker = "└── " if is_last else "├── "
                tree_str += f"{prefix}{marker}{item.name}/\n"

                next_prefix = prefix + ("    " if is_last else "│   ")
                tree_str += build_tree(item, next_prefix, max_depth, current_depth + 1)
        except PermissionError:
            pass
        return tree_str

    output.append(f"{root_path.name}/")
    output.append(build_tree(root_path))
    output.append("```")

    # 2. C++ Class Inheritance Graph (Basic regex-based parsing)
    output.append("\n## C++ Class Inheritance Graph")
    output.append("```mermaid")
    output.append("classDiagram")

    class_pattern = re.compile(r"class\s+[A-Z_]+_API\s+([A-Za-z0-9_]+)\s*:\s*public\s+([A-Za-z0-9_]+)")

    source_dir = root_path / "Source"
    plugins_dir = root_path / "Plugins"

    files_to_scan = []
    if source_dir.exists():
        files_to_scan.extend(source_dir.rglob("*.h"))
    if plugins_dir.exists():
        files_to_scan.extend(plugins_dir.rglob("*.h"))

    classes_found = False
    for h_file in files_to_scan:
        try:
            content = h_file.read_text(encoding='utf-8', errors='ignore')
            for match in class_pattern.finditer(content):
                child_class = match.group(1)
                parent_class = match.group(2)
                output.append(f"    {parent_class} <|-- {child_class}")
                classes_found = True
        except Exception:
            continue

    if not classes_found:
        output.append("    note \"No C++ class inheritance found matching pattern.\"")

    output.append("```")

    return "\n".join(output)
