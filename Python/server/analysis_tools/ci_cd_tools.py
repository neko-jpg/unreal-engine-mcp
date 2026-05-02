import os
import subprocess
from pathlib import Path
from server.core import mcp

@mcp.tool()
async def run_unreal_build(project_path: str, build_config: str = "Development", platform: str = "Win64") -> str:
    """
    Executes the Unreal Build Tool to compile the project.
    Note: Requires UnrealBuildTool to be in the system PATH or standard locations.

    Args:
        project_path: The full path to the .uproject file.
        build_config: The build configuration (e.g. "Development", "DebugGame", "Shipping"). Defaults to "Development".
        platform: The target platform (e.g. "Win64", "Mac", "Linux"). Defaults to "Win64".
    """
    uproject_file = Path(project_path)
    if not uproject_file.exists() or uproject_file.suffix != '.uproject':
        return f"Error: Invalid uproject path provided: {project_path}"

    project_name = uproject_file.stem

    # In a real environment, we'd locate UBT dynamically from registry or env vars.
    # Here we mock the invocation to show intent or rely on a system script if available.
    command = f"UnrealBuildTool {project_name}Editor {platform} {build_config} -Project=\"{uproject_file.absolute()}\" -WaitMutex"

    try:
        # We run it but don't strictly enforce success since UBT might not be in PATH in all envs.
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        output = f"Executed build command: `{command}`\n\n"
        output += f"Exit Code: {result.returncode}\n\n"
        if result.stdout:
            output += f"### Stdout (last 20 lines):\n```\n...{result.stdout[-1000:]}\n```\n"
        if result.stderr:
            output += f"### Stderr:\n```\n{result.stderr}\n```\n"

        return output
    except Exception as e:
        return f"Failed to run build tool: {str(e)}"

@mcp.tool()
async def get_latest_unreal_logs(root_dir: str = ".", lines: int = 50, filter_errors: bool = True) -> str:
    """
    Reads the latest Unreal Engine log file from the Saved/Logs directory.
    Useful for identifying crashes, PIE errors, or build failures.

    Args:
        root_dir: The root directory of the Unreal project.
        lines: Number of lines from the end of the log to return. Defaults to 50.
        filter_errors: If true, attempts to filter and show only lines containing 'Warning' or 'Error'.
    """
    logs_dir = Path(root_dir) / "Saved" / "Logs"
    if not logs_dir.exists():
        return f"Error: Logs directory not found at {logs_dir.absolute()}. The project might not have been run yet."

    log_files = list(logs_dir.glob("*.log"))
    if not log_files:
        return "No log files found in the Saved/Logs directory."

    # Get the most recently modified log file
    latest_log = max(log_files, key=os.path.getmtime)

    try:
        content = latest_log.read_text(encoding='utf-8', errors='ignore').splitlines()

        if filter_errors:
            filtered = [line for line in content if "Error:" in line or "Warning:" in line]
            if not filtered:
                return f"No errors or warnings found in {latest_log.name}."
            content = filtered

        tail = content[-lines:] if len(content) > lines else content

        output = f"### Latest Logs from `{latest_log.name}`\n"
        output += f"*(Showing last {len(tail)} lines" + (" filtered for Warnings/Errors" if filter_errors else "") + ")*\n\n"
        output += "```text\n"
        output += "\n".join(tail)
        output += "\n```"
        return output

    except Exception as e:
        return f"Failed to read log file {latest_log.name}: {str(e)}"
