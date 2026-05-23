// EpicUnrealMCPPackagingExtensionCommands.h
//
// Sub-batch AA: Packaging / Build / Deployment extensions (issue #56).
// Adds five MCP commands that map to UE 5.7 packaging-related settings
// surfaces that are absent from the existing base packaging tools:
//
//   set_live_coding_mode             - dynamic Live Coding (Windows) toggle + compile
//   set_pak_iostore_settings         - UProjectPackagingSettings Pak / IoStore / compression flags
//   set_chunk_settings               - UProjectPackagingSettings chunk-generation flags
//   set_localization_cook_settings   - UProjectPackagingSettings culture / cook-all / loc-targets
//   set_crash_reporter_settings      - [CrashReportClient] ini knobs (DefaultEngine.ini)
//
// All settings persist through TryUpdateDefaultConfigFile() per AGENTS.md
// (UE 5.7 deprecates UpdateDefaultConfigFile()).  The Crash Reporter case
// writes [CrashReportClient] directly through GConfig because there is no
// UCLASS for client-side crash settings in UE 5.7.
//
// Live Coding handler is Editor + Windows only.  On other targets it
// returns a graceful {"success": true, "available": false, "hint": ...}
// envelope instead of failing.
//
// Owned by route id 42 (see EpicUnrealMCPRouter.cpp and EpicUnrealMCPBridge.cpp).
#pragma once

#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPPackagingExtensionCommands
{
public:
    FEpicUnrealMCPPackagingExtensionCommands();
    ~FEpicUnrealMCPPackagingExtensionCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleSetLiveCodingMode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetPakIoStoreSettings(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetChunkSettings(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetLocalizationCookSettings(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetCrashReporterSettings(const TSharedPtr<FJsonObject>& Params);
};