"""Generate the boilerplate for a single tasks.md sub-batch.

Each invocation creates / updates:
  * Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/<HeaderName>.h
  * Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/<CppName>.cpp
  * Python/server/<module>.py
  * Python/tests/unit/test_<module>.py

It does NOT touch Router/Bridge/Build.cs/__init__.py/test_tool_registration --
those need a one-line manual insert per sub-batch (kept human-readable).

Configure HANDLERS below before running. Re-running is idempotent for the
generated files (overwrite). Keep this script alongside the canonical sources
so future sub-batches reuse the same template.
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def make_cpp(handler_class, route_id, with_define, commands, defaults, install_hint, queued_hint):
    dispatch = ",\n        ".join(
        f'{{TEXT("{c}"),  &F{handler_class}::Handle{cpp_name(c)}}}' for c in commands
    )
    body_decls = "\n    ".join(
        f"TSharedPtr<FJsonObject> Handle{cpp_name(c)}(const TSharedPtr<FJsonObject>& Params);" for c in commands
    )

    handler_impls = []
    for cmd in commands:
        cn = cpp_name(cmd)
        handler_impls.append(
            f'''TSharedPtr<FJsonObject> F{handler_class}::Handle{cn}(const TSharedPtr<FJsonObject>& Params)
{{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("{cmd}"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("{cmd}"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("{queued_hint}"));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}}'''
        )

    impl_body = "\n\n".join(handler_impls)
    return f'''#include "Commands/{handler_class.replace("EpicUnrealMCP", "EpicUnrealMCP")}.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

bool F{handler_class}::IsModuleAvailable()
{{
#if {with_define}
    return true;
#else
    return false;
#endif
}}

TSharedPtr<FJsonObject> F{handler_class}::MakeUnavailable(const FString& Cmd)
{{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the {handler_class} module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("{install_hint}"));
    return R;
}}

F{handler_class}::F{handler_class}() {{}}
F{handler_class}::~F{handler_class}() {{}}

TSharedPtr<FJsonObject> F{handler_class}::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{{
    using Handler = TSharedPtr<FJsonObject>(F{handler_class}::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {{
        {dispatch}
    }};
    if (const Handler* H = Dispatch.Find(CommandType))
    {{
        return (this->*(*H))(Params);
    }}
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));
    return R;
}}

{impl_body}
'''


def make_header(handler_class, commands):
    decls = "\n    ".join(
        f"TSharedPtr<FJsonObject> Handle{cpp_name(c)}(const TSharedPtr<FJsonObject>& Params);" for c in commands
    )
    return f'''#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class F{handler_class}
{{
public:
    F{handler_class}();
    ~F{handler_class}();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    {decls}
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
}};
'''


def make_python(module_name, sub_batch_label, commands, defaults):
    body_parts = [
        f'"""{sub_batch_label} MCP tools (auto-generated scaffold).',
        "",
        "Each tool wraps a single C++ handler. The C++ side returns a queued",
        "envelope when the underlying plugin is missing; the wrappers surface that",
        "to the caller via an actionable error envelope.",
        '"""',
        "",
        "from typing import Any, Dict",
        "",
        "from server.core import mcp, get_unreal_connection",
        "from server.validation import (",
        "    validate_string,",
        "    ValidationError,",
        "    make_validation_error_response_from_exception,",
        ")",
        "from utils.responses import make_error_response",
        "",
        "",
        "def _envelope(name: str, result: Any) -> Dict[str, Any]:",
        "    if not isinstance(result, dict):",
        '        return make_error_response(f"Unexpected Unreal response for \'{name}\'")',
        "    if not result.get(\"success\", False):",
        "        err = result.get(\"error\", \"unknown error\")",
        "        hint = result.get(\"hint\")",
        "        return make_error_response(f\"{name}: {err}\" + (f\" (hint: {hint})\" if hint else \"\"))",
        "    return result",
        "",
    ]
    for cmd in commands:
        params = defaults.get(cmd, [])
        # required first, optional after
        req = [p for p in params if p[2] is None]
        opt = [p for p in params if p[2] is not None]
        sig_parts = []
        for p, t, d in req:
            sig_parts.append(f"{p}: {py_type(t)}")
        for p, t, d in opt:
            if isinstance(d, str):
                sig_parts.append(f'{p}: {py_type(t)} = "{d}"')
            else:
                sig_parts.append(f"{p}: {py_type(t)} = {d!r}")
        sig = ", ".join(sig_parts)
        arg_lines = ", ".join(
            f'"{p}": {coerce(p, t)}' for p, t, _ in req + opt
        )
        payload = "{" + arg_lines + "}"
        validate_lines = [f'        validate_string({p}, "{p}")' for p, t, d in req if t == "str"]
        if not validate_lines:
            validate_lines.append("        pass")
        body_parts.append(f"""
@mcp.tool()
def {cmd}({sig}) -> Dict[str, Any]:
    \"\"\"{cmd} -- queued (see C++ handler for runtime depth).\"\"\"
    try:
{chr(10).join(validate_lines)}
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)
    u = get_unreal_connection()
    if u is None:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        r = u.send_command("{cmd}", {payload})
    except Exception as e:
        return make_error_response(f"Failed to call Unreal command '{cmd}': {{e}}")
    return _envelope("{cmd}", r)
""")
    return "\n".join(body_parts)


def make_python_tests(module_name, commands, defaults):
    parts = [
        f'"""L1 unit tests for {module_name} (auto-generated scaffold)."""',
        "from unittest.mock import patch, MagicMock",
        f"import server.{module_name} as m",
        "",
        "",
        "def _conn():",
        "    c = MagicMock(); c.send_command.return_value = {\"success\": True, \"data\": {}}",
        "    return c",
        "",
    ]
    for cmd in commands:
        params = defaults.get(cmd, [])
        # build calling args using defaults / placeholders for required params
        call_parts = []
        for p, t, d in params:
            if d is None:
                # required - feed a placeholder
                if t == "str":
                    call_parts.append(f'"{p}_v"')
                elif t == "int":
                    call_parts.append("1")
                elif t == "float":
                    call_parts.append("1.0")
                elif t == "bool":
                    call_parts.append("True")
                elif t == "list":
                    call_parts.append("[]")
            else:
                pass  # use default
        call = ", ".join(call_parts)
        parts.append(f"""
def test_{cmd}_payload():
    with patch("server.{module_name}.get_unreal_connection", return_value=_conn()) as ue:
        m.{cmd}({call})
    a = ue.return_value.send_command.call_args
    assert a[0][0] == "{cmd}"
""")
    return "\n".join(parts)


def py_type(t):
    return {"str":"str","int":"int","float":"float","bool":"bool","list":"list","dict":"Dict[str, Any]"}[t]

def coerce(name, t):
    if t == "str": return name
    if t == "int": return f"int({name})"
    if t == "float": return f"float({name})"
    if t == "bool": return f"bool({name})"
    return name

def cpp_name(snake):
    return "".join(p.capitalize() for p in snake.split("_"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="JSON config: {handler_class, route_id, with_define, install_hint, queued_hint, module, commands, defaults}")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
    hc = cfg["handler_class"]
    out_h = REPO / "Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands" / f"{hc.replace('EpicUnrealMCP', 'EpicUnrealMCP')}.h"
    out_cpp = REPO / "Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands" / f"{hc.replace('EpicUnrealMCP', 'EpicUnrealMCP')}.cpp"
    out_h.write_text(make_header(hc, cfg["commands"]), encoding="utf-8")
    out_cpp.write_text(
        make_cpp(hc, cfg["route_id"], cfg["with_define"], cfg["commands"], cfg.get("defaults", {}), cfg.get("install_hint", "Enable the required plugin."), cfg.get("queued_hint", "Payload accepted; finish in the editor.")),
        encoding="utf-8",
    )
    out_py = REPO / "Python/server" / f"{cfg['module']}.py"
    out_py.write_text(make_python(cfg["module"], cfg["sub_batch_label"], cfg["commands"], cfg.get("defaults", {})), encoding="utf-8")
    out_test = REPO / "Python/tests/unit" / f"test_{cfg['module']}.py"
    out_test.write_text(make_python_tests(cfg["module"], cfg["commands"], cfg.get("defaults", {})), encoding="utf-8")
    print(f"Wrote: {out_h.name}, {out_cpp.name}, {out_py.name}, test_{cfg['module']}.py")


if __name__ == "__main__":
    main()
