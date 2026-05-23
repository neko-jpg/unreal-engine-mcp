# UE 5.7 Build Environment

This document captures the build environment that the UnrealMCP plugin and the
`FlopperamUnrealMCP` sample project are validated against on Windows. Following
this matrix avoids the toolchain warnings emitted by `UnrealBuildTool` while
compiling against Unreal Engine 5.7.

## Recommended Windows toolchain

| Component              | Recommended version                           |
| ---------------------- | --------------------------------------------- |
| Visual Studio          | Visual Studio 2022 17.14 (Community / Pro / BuildTools) |
| MSVC compiler          | 14.44.35214 (`MSVC v143 - VS 2022 C++ x64/x86 build tools (14.44-17.14)`) |
| Windows 10 / 11 SDK    | 10.0.22621.0 or newer                         |
| .NET SDK               | .NET 8.0                                       |
| CMake (optional)       | 3.27 or newer (only required for Cesium)      |

These mirror the public UE 5.7 Visual Studio setup page: VS 2022 17.14
is the recommended default, MSVC 14.44.35214 is both the minimum and
recommended compiler, Windows SDK 10.0.22621.0+ is recommended, and
.NET 8.0 is required. Newer toolchains may work, but
`UnrealBuildTool` will warn (e.g. `Visual Studio 2026 compiler version
14.50.x is not a preferred version`). Some installed UE 5.7 builds may
print a nearby patch-level value such as `14.44.35207`; prefer the
exact patch version requested by your local UBT when it differs from
Epic documentation.

## Installing the preferred toolchain

1. Run the Visual Studio Installer.
2. Select **Visual Studio 2022 17.14** (Community / Professional / BuildTools).
3. Under **Workloads** enable:
   - *Game development with C++*
   - *Desktop development with C++*
4. Under **Individual components** make sure the following are checked:
   - `MSVC v143 - VS 2022 C++ x64/x86 build tools (14.44-17.14)`
   - `Windows 11 SDK (10.0.22621.0 or newer)`
   - `Visual Studio SDK` (required for "Editor integration")
   - `C++ profiling tools`
   - `C++ AddressSanitizer`
5. Reboot if prompted.

## Pinning `WindowsPlatform.CompilerVersion`

When more than one MSVC version is installed (typical when both VS 2022 17.14
and VS 2026 17.x are present), pin the preferred version so every contributor
hits the same toolchain. Drop the snippet below at:

```
%APPDATA%\Unreal Engine\UnrealBuildTool\BuildConfiguration.xml
```

```xml
<?xml version="1.0" encoding="utf-8"?>
<Configuration xmlns="https://www.unrealengine.com/BuildConfiguration">
    <WindowsPlatform>
        <!-- Force the UE 5.7 preferred MSVC version. -->
        <CompilerVersion>14.44.35214</CompilerVersion>
        <WindowsSdkVersion>10.0.22621.0</WindowsSdkVersion>
    </WindowsPlatform>
</Configuration>
```

After saving, regenerate Visual Studio project files for
`FlopperamUnrealMCP.uproject` (right-click the `.uproject`, *Generate Visual
Studio project files*) so the new pin is picked up by the IDE. A rebuild
should now be silent regarding compiler-version warnings.

## Sanity check

To confirm the toolchain is detected correctly, run:

```powershell
& "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" `
    UnrealEditor Win64 Development `
    -Project="$PWD\FlopperamUnrealMCP\FlopperamUnrealMCP.uproject" `
    -WaitMutex
```

A clean run should report:

- `Available x64 toolchains` selecting `14.44.35214` (or the local UBT-requested 14.44 patch)
- No `WARNING: Unable to find Visual Studio SDK`
- No `Plugin 'UnrealMCP' does not list plugin 'GeometryScripting'` or
  `'GeometryProcessing'` warnings (these are addressed in the plugin's
  `UnrealMCP.uplugin`).

## macOS / Linux notes

- macOS: see the *Extra steps for Mac* section in the project README. The
  recommended Xcode version is 16.x (Apple SDK 16.0). Newer Xcode releases
  require patching `Apple_SDK.json` per the README.
- Linux: UE 5.7 is validated against Clang 18.1.x with the bundled Linux
  toolchain Epic ships in `Engine/Extras/ThirdPartyNotUE/SDKs/HostLinux/`.

## Out of scope

- Forcing the toolchain at the project level. We deliberately allow newer
  toolchains for contributors who want to test them, even though they trigger
  a warning. This guide defaults to Epic's Visual Studio setup page values; if your installed UE 5.7 UBT reports the release-notes build-farm patch (`14.44.35207`), use that exact local value in your user-level `BuildConfiguration.xml`.

## References

- Epic UE 5.7 Visual Studio setup: https://dev.epicgames.com/documentation/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine?lang=en-US
- UE 5.7 release notes: https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-7-release-notes?lang=en-US
