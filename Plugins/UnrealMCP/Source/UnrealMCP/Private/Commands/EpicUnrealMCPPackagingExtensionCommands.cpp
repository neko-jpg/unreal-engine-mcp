// EpicUnrealMCPPackagingExtensionCommands.cpp
//
// Sub-batch AA: Packaging / Build / Deployment extensions (issue #56).
// See header for the full handler contract.
//
// AGENTS.md compliance:
//   - All UObject settings classes are persisted with TryUpdateDefaultConfigFile()
//     (UpdateDefaultConfigFile() is deprecated in UE 5.7).
//   - The Crash Reporter case writes to [CrashReportClient] via GConfig and
//     then flushes through GConfig->Flush(false, GEngineIni).
//   - Live Coding is only available on Editor + Windows targets; on every
//     other configuration we return a graceful "available=false" envelope.

#include "Commands/EpicUnrealMCPPackagingExtensionCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Containers/UnrealString.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformProcess.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/CoreMiscDefines.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "Settings/ProjectPackagingSettings.h"
#include "UObject/Class.h"

#if PLATFORM_WINDOWS && WITH_LIVE_CODING
#include "ILiveCodingModule.h"
#endif

namespace
{
    constexpr const TCHAR* CrashReporterIniSection = TEXT("CrashReportClient");

    void AddBoolIfChanged(const TSharedRef<FJsonObject>& Out, const TCHAR* Key, bool bBefore, bool bAfter)
    {
        Out->SetBoolField(Key, bAfter);
        if (bBefore != bAfter)
        {
            FString ChangedField = FString::Printf(TEXT("%s_changed"), Key);
            Out->SetBoolField(ChangedField, true);
        }
    }
}

FEpicUnrealMCPPackagingExtensionCommands::FEpicUnrealMCPPackagingExtensionCommands() {}
FEpicUnrealMCPPackagingExtensionCommands::~FEpicUnrealMCPPackagingExtensionCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPPackagingExtensionCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPPackagingExtensionCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("set_live_coding_mode"),           &FEpicUnrealMCPPackagingExtensionCommands::HandleSetLiveCodingMode},
        {TEXT("set_pak_iostore_settings"),       &FEpicUnrealMCPPackagingExtensionCommands::HandleSetPakIoStoreSettings},
        {TEXT("set_chunk_settings"),             &FEpicUnrealMCPPackagingExtensionCommands::HandleSetChunkSettings},
        {TEXT("set_localization_cook_settings"), &FEpicUnrealMCPPackagingExtensionCommands::HandleSetLocalizationCookSettings},
        {TEXT("set_crash_reporter_settings"),    &FEpicUnrealMCPPackagingExtensionCommands::HandleSetCrashReporterSettings},
    };
    if (const Handler* Found = Dispatch.Find(CommandType))
    {
        return (this->*(*Found))(Params);
    }
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));
    return R;
}

// ---------------------------------------------------------------------------
// set_live_coding_mode
//
// Wraps the Windows-only ILiveCodingModule.  The plan calls for a dynamic
// toggle plus an optional immediate-compile trigger.  Non-Windows / non-Editor
// builds return a graceful "available=false" envelope rather than failing,
// so the bridge still answers the command on Linux / Mac / Server builds.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPPackagingExtensionCommands::HandleSetLiveCodingMode(const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();

#if WITH_EDITOR && PLATFORM_WINDOWS && WITH_LIVE_CODING
    ILiveCodingModule* Module = FModuleManager::Get().GetModulePtr<ILiveCodingModule>(LIVE_CODING_MODULE_NAME);
    if (!Module)
    {
        Module = FModuleManager::Get().LoadModulePtr<ILiveCodingModule>(LIVE_CODING_MODULE_NAME);
    }
    if (!Module)
    {
        Out->SetBoolField(TEXT("success"), true);
        Data->SetBoolField(TEXT("available"), false);
        Data->SetStringField(TEXT("hint"), TEXT("Live Coding module is not loaded; build the editor with LiveCoding support to enable this command."));
        Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
        return Out;
    }

    bool bRequestEnable = false;
    bool bHasEnable = Params.IsValid() && Params->TryGetBoolField(TEXT("enable"), bRequestEnable);
    bool bCompileNow = false;
    if (Params.IsValid())
    {
        Params->TryGetBoolField(TEXT("compile_now"), bCompileNow);
    }

    const bool bWasEnabled = Module->IsEnabledForSession();
    if (bHasEnable)
    {
        Module->EnableForSession(bRequestEnable);
    }
    const bool bNowEnabled = Module->IsEnabledForSession();

    bool bCompileTriggered = false;
    if (bCompileNow && bNowEnabled && Module->CanEnableForSession())
    {
        Module->Compile();
        bCompileTriggered = true;
    }

    Out->SetBoolField(TEXT("success"), true);
    Data->SetBoolField(TEXT("available"), true);
    Data->SetBoolField(TEXT("was_enabled"), bWasEnabled);
    Data->SetBoolField(TEXT("enabled"), bNowEnabled);
    Data->SetBoolField(TEXT("started"), Module->HasStarted());
    Data->SetBoolField(TEXT("compile_triggered"), bCompileTriggered);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
#else
    Out->SetBoolField(TEXT("success"), true);
    Data->SetBoolField(TEXT("available"), false);
    Data->SetStringField(TEXT("hint"), TEXT("Live Coding is only available on Editor + Windows builds in UE 5.7."));
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
#endif
}

// ---------------------------------------------------------------------------
// set_pak_iostore_settings
//
// Mutates UProjectPackagingSettings { UsePakFile, bUseIoStore, bCompressed,
// bGenerateNoChunks } and persists with TryUpdateDefaultConfigFile().
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPPackagingExtensionCommands::HandleSetPakIoStoreSettings(const TSharedPtr<FJsonObject>& Params)
{
    UProjectPackagingSettings* Settings = GetMutableDefault<UProjectPackagingSettings>();
    if (!Settings)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("UProjectPackagingSettings unavailable"));
    }

    const bool bWasUsePak       = Settings->UsePakFile;
    const bool bWasUseIoStore   = Settings->bUseIoStore;
    const bool bWasCompressed   = Settings->bCompressed;
    const bool bWasNoChunks     = Settings->bGenerateNoChunks;

    bool bAnyChanged = false;
    bool bUsePak = false;
    if (Params.IsValid() && Params->TryGetBoolField(TEXT("use_pak"), bUsePak))
    {
        if (Settings->UsePakFile != bUsePak) { Settings->UsePakFile = bUsePak; bAnyChanged = true; }
    }
    bool bUseIoStore = false;
    if (Params.IsValid() && Params->TryGetBoolField(TEXT("use_iostore"), bUseIoStore))
    {
        if (Settings->bUseIoStore != bUseIoStore) { Settings->bUseIoStore = bUseIoStore; bAnyChanged = true; }
    }
    bool bCompressed = false;
    if (Params.IsValid() && Params->TryGetBoolField(TEXT("compressed"), bCompressed))
    {
        if (Settings->bCompressed != bCompressed) { Settings->bCompressed = bCompressed; bAnyChanged = true; }
    }
    bool bGenerateNoChunks = false;
    if (Params.IsValid() && Params->TryGetBoolField(TEXT("generate_no_chunks"), bGenerateNoChunks))
    {
        if (Settings->bGenerateNoChunks != bGenerateNoChunks) { Settings->bGenerateNoChunks = bGenerateNoChunks; bAnyChanged = true; }
    }

    bool bSaved = false;
    if (bAnyChanged)
    {
        // UE 5.7: prefer TryUpdateDefaultConfigFile() over deprecated UpdateDefaultConfigFile().
        bSaved = Settings->TryUpdateDefaultConfigFile();
    }

    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Data->SetBoolField(TEXT("any_changed"), bAnyChanged);
    Data->SetBoolField(TEXT("config_saved"), bSaved);
    AddBoolIfChanged(Data.ToSharedRef(), TEXT("use_pak"),            bWasUsePak,     Settings->UsePakFile);
    AddBoolIfChanged(Data.ToSharedRef(), TEXT("use_iostore"),        bWasUseIoStore, Settings->bUseIoStore);
    AddBoolIfChanged(Data.ToSharedRef(), TEXT("compressed"),         bWasCompressed, Settings->bCompressed);
    AddBoolIfChanged(Data.ToSharedRef(), TEXT("generate_no_chunks"), bWasNoChunks,   Settings->bGenerateNoChunks);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

// ---------------------------------------------------------------------------
// set_chunk_settings
//
// Toggles UProjectPackagingSettings { bGenerateChunks, bChunkHardReferencesOnly }
// plus an optional has_chunk_assignment_rules acknowledgement that is recorded
// in the response (UAssetManager's chunk-assignment policy lives on
// PrimaryAssetType rules so we surface the intent without mutating other
// settings objects in this entry point).
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPPackagingExtensionCommands::HandleSetChunkSettings(const TSharedPtr<FJsonObject>& Params)
{
    UProjectPackagingSettings* Settings = GetMutableDefault<UProjectPackagingSettings>();
    if (!Settings)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("UProjectPackagingSettings unavailable"));
    }

    const bool bWasGenerate     = Settings->bGenerateChunks;
    const bool bWasHardOnly     = Settings->bChunkHardReferencesOnly;

    bool bAnyChanged = false;
    bool bGenerateChunks = false;
    if (Params.IsValid() && Params->TryGetBoolField(TEXT("generate_chunks"), bGenerateChunks))
    {
        if (Settings->bGenerateChunks != bGenerateChunks) { Settings->bGenerateChunks = bGenerateChunks; bAnyChanged = true; }
    }
    bool bHardRefsOnly = false;
    if (Params.IsValid() && Params->TryGetBoolField(TEXT("chunk_hard_references_only"), bHardRefsOnly))
    {
        if (Settings->bChunkHardReferencesOnly != bHardRefsOnly) { Settings->bChunkHardReferencesOnly = bHardRefsOnly; bAnyChanged = true; }
    }
    bool bHasChunkAssignment = false;
    bool bHasChunkAssignmentProvided = Params.IsValid() && Params->TryGetBoolField(TEXT("has_chunk_assignment_rules"), bHasChunkAssignment);

    bool bSaved = false;
    if (bAnyChanged)
    {
        // UE 5.7: prefer TryUpdateDefaultConfigFile() over deprecated UpdateDefaultConfigFile().
        bSaved = Settings->TryUpdateDefaultConfigFile();
    }

    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Data->SetBoolField(TEXT("any_changed"), bAnyChanged);
    Data->SetBoolField(TEXT("config_saved"), bSaved);
    AddBoolIfChanged(Data.ToSharedRef(), TEXT("generate_chunks"),            bWasGenerate, Settings->bGenerateChunks);
    AddBoolIfChanged(Data.ToSharedRef(), TEXT("chunk_hard_references_only"), bWasHardOnly, Settings->bChunkHardReferencesOnly);
    if (bHasChunkAssignmentProvided)
    {
        Data->SetBoolField(TEXT("has_chunk_assignment_rules"), bHasChunkAssignment);
        Data->SetStringField(TEXT("has_chunk_assignment_rules_hint"),
            TEXT("Chunk assignment rules live on UAssetManager PrimaryAssetType entries; configure them via the Asset Manager UI or DefaultGame.ini PrimaryAssetTypesToScan."));
    }
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

// ---------------------------------------------------------------------------
// set_localization_cook_settings
//
// Mutates CulturesToStage / bCookAll / LocalizationTargetsToChunk on
// UProjectPackagingSettings and persists with TryUpdateDefaultConfigFile().
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPPackagingExtensionCommands::HandleSetLocalizationCookSettings(const TSharedPtr<FJsonObject>& Params)
{
    UProjectPackagingSettings* Settings = GetMutableDefault<UProjectPackagingSettings>();
    if (!Settings)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("UProjectPackagingSettings unavailable"));
    }

    bool bAnyChanged = false;

    auto ReadStringArray = [&Params](const TCHAR* Field, TArray<FString>& OutValue, bool& OutProvided)
    {
        OutProvided = false;
        if (!Params.IsValid()) return;
        const TArray<TSharedPtr<FJsonValue>>* JsonArray = nullptr;
        if (Params->TryGetArrayField(Field, JsonArray) && JsonArray)
        {
            OutProvided = true;
            OutValue.Reset(JsonArray->Num());
            for (const TSharedPtr<FJsonValue>& V : *JsonArray)
            {
                if (V.IsValid() && V->Type == EJson::String)
                {
                    OutValue.Add(V->AsString());
                }
            }
        }
    };

    TArray<FString> NewCultures;
    bool bCulturesProvided = false;
    ReadStringArray(TEXT("cultures_to_stage"), NewCultures, bCulturesProvided);
    if (bCulturesProvided && Settings->CulturesToStage != NewCultures)
    {
        Settings->CulturesToStage = MoveTemp(NewCultures);
        bAnyChanged = true;
    }

    bool bCookAll = false;
    if (Params.IsValid() && Params->TryGetBoolField(TEXT("cook_all"), bCookAll))
    {
        if (Settings->bCookAll != bCookAll) { Settings->bCookAll = bCookAll; bAnyChanged = true; }
    }

    TArray<FString> NewLocTargets;
    bool bLocTargetsProvided = false;
    ReadStringArray(TEXT("localization_targets_to_chunk"), NewLocTargets, bLocTargetsProvided);
    if (bLocTargetsProvided && Settings->LocalizationTargetsToChunk != NewLocTargets)
    {
        Settings->LocalizationTargetsToChunk = MoveTemp(NewLocTargets);
        bAnyChanged = true;
    }

    bool bSaved = false;
    if (bAnyChanged)
    {
        // UE 5.7: prefer TryUpdateDefaultConfigFile() over deprecated UpdateDefaultConfigFile().
        bSaved = Settings->TryUpdateDefaultConfigFile();
    }

    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Data->SetBoolField(TEXT("any_changed"), bAnyChanged);
    Data->SetBoolField(TEXT("config_saved"), bSaved);
    Data->SetBoolField(TEXT("cook_all"), Settings->bCookAll);

    TArray<TSharedPtr<FJsonValue>> CulturesJson;
    for (const FString& C : Settings->CulturesToStage)
    {
        CulturesJson.Add(MakeShared<FJsonValueString>(C));
    }
    Data->SetArrayField(TEXT("cultures_to_stage"), CulturesJson);

    TArray<TSharedPtr<FJsonValue>> LocJson;
    for (const FString& T : Settings->LocalizationTargetsToChunk)
    {
        LocJson.Add(MakeShared<FJsonValueString>(T));
    }
    Data->SetArrayField(TEXT("localization_targets_to_chunk"), LocJson);

    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

// ---------------------------------------------------------------------------
// set_crash_reporter_settings
//
// UE 5.7 does not expose a UCLASS for client-side crash settings; the
// CrashReportClient reads its config from [CrashReportClient] in
// DefaultEngine.ini.  We write the keys via GConfig and flush to the
// DefaultEngine.ini path so the change persists across editor restarts.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPPackagingExtensionCommands::HandleSetCrashReporterSettings(const TSharedPtr<FJsonObject>& Params)
{
    if (!GConfig)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("GConfig unavailable"));
    }
    const FString ConfigPath = FPaths::SourceConfigDir() / TEXT("DefaultEngine.ini");

    bool bAnyChanged = false;

    FString CrashReportClientEmail;
    bool bEmailProvided = Params.IsValid() && Params->TryGetStringField(TEXT("crash_report_client_email"), CrashReportClientEmail);
    if (bEmailProvided)
    {
        FString Existing;
        GConfig->GetString(CrashReporterIniSection, TEXT("CrashReportClientEmail"), Existing, ConfigPath);
        if (Existing != CrashReportClientEmail)
        {
            GConfig->SetString(CrashReporterIniSection, TEXT("CrashReportClientEmail"), *CrashReportClientEmail, ConfigPath);
            bAnyChanged = true;
        }
    }

    bool bSendUnattended = false;
    bool bUnattendedProvided = Params.IsValid() && Params->TryGetBoolField(TEXT("send_unattended_bug_reports"), bSendUnattended);
    if (bUnattendedProvided)
    {
        bool bExisting = false;
        GConfig->GetBool(CrashReporterIniSection, TEXT("bSendUnattendedBugReports"), bExisting, ConfigPath);
        if (bExisting != bSendUnattended)
        {
            GConfig->SetBool(CrashReporterIniSection, TEXT("bSendUnattendedBugReports"), bSendUnattended, ConfigPath);
            bAnyChanged = true;
        }
    }

    bool bSendUsageData = false;
    bool bUsageProvided = Params.IsValid() && Params->TryGetBoolField(TEXT("send_usage_data"), bSendUsageData);
    if (bUsageProvided)
    {
        bool bExisting = false;
        GConfig->GetBool(CrashReporterIniSection, TEXT("bSendUsageData"), bExisting, ConfigPath);
        if (bExisting != bSendUsageData)
        {
            GConfig->SetBool(CrashReporterIniSection, TEXT("bSendUsageData"), bSendUsageData, ConfigPath);
            bAnyChanged = true;
        }
    }

    bool bSaved = false;
    if (bAnyChanged)
    {
        GConfig->Flush(false, ConfigPath);
        // Reload so subsequent reads see the value we just wrote.
        GConfig->LoadFile(ConfigPath);
        bSaved = true;
    }

    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Data->SetBoolField(TEXT("any_changed"), bAnyChanged);
    Data->SetBoolField(TEXT("config_saved"), bSaved);
    Data->SetStringField(TEXT("config_path"), ConfigPath);

    // Echo back the resulting values so callers can verify the write.
    FString ResolvedEmail;
    GConfig->GetString(CrashReporterIniSection, TEXT("CrashReportClientEmail"), ResolvedEmail, ConfigPath);
    Data->SetStringField(TEXT("crash_report_client_email"), ResolvedEmail);

    bool bResolvedUnattended = false;
    GConfig->GetBool(CrashReporterIniSection, TEXT("bSendUnattendedBugReports"), bResolvedUnattended, ConfigPath);
    Data->SetBoolField(TEXT("send_unattended_bug_reports"), bResolvedUnattended);

    bool bResolvedUsage = false;
    GConfig->GetBool(CrashReporterIniSection, TEXT("bSendUsageData"), bResolvedUsage, ConfigPath);
    Data->SetBoolField(TEXT("send_usage_data"), bResolvedUsage);

    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}