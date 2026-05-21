// =====================================================================
// EpicUnrealMCPValidationCommands
//
// Phase 4 (Issue #31) split from EpicUnrealMCPProceduralCommands.cpp.
// Owns:
//   - compile_all_blueprints
//   - run_map_check
//   - find_broken_references
//
// Routed under id 23.
// =====================================================================

#include "Commands/EpicUnrealMCPValidationCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Editor.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"
#include "Engine/World.h"
#include "Engine/Blueprint.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "EditorAssetLibrary.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Logging/MessageLog.h"
#include "Misc/UObjectToken.h"
#include "Logging/TokenizedMessage.h"
#include "Misc/MessageDialog.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "Settings/EditorLoadingSavingSettings.h"
#include "EditorValidatorSubsystem.h"
#include "GenericPlatform/GenericPlatformMemory.h"
#include "Misc/App.h"
#include "AssetRegistry/AssetData.h"
#include "ProfilingDebugging/TraceAuxiliary.h"
#include "ISourceControlModule.h"
#include "ISourceControlProvider.h"

FEpicUnrealMCPValidationCommands::FEpicUnrealMCPValidationCommands()
{
}

UWorld* FEpicUnrealMCPValidationCommands::GetEditorWorld() const
{
    if (!GEditor)
    {
        return nullptr;
    }
    return GEditor->GetEditorWorldContext().World();
}

TSharedPtr<FJsonObject> FEpicUnrealMCPValidationCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPValidationCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("compile_all_blueprints"),  &FEpicUnrealMCPValidationCommands::HandleCompileAllBlueprints},
        {TEXT("run_map_check"),           &FEpicUnrealMCPValidationCommands::HandleRunMapCheck},
        {TEXT("find_broken_references"),  &FEpicUnrealMCPValidationCommands::HandleFindBrokenReferences},
        {TEXT("set_auto_save_settings"), &FEpicUnrealMCPValidationCommands::HandleSetAutoSaveSettings},  // W1-B
        {TEXT("get_editor_stats"), &FEpicUnrealMCPValidationCommands::HandleGetEditorStats},  // W1-B
        {TEXT("start_unreal_insights_trace"), &FEpicUnrealMCPValidationCommands::HandleStartUnrealInsightsTrace},  // W1-B
        {TEXT("stop_unreal_insights_trace"), &FEpicUnrealMCPValidationCommands::HandleStopUnrealInsightsTrace},  // W1-B
        {TEXT("validate_assets"), &FEpicUnrealMCPValidationCommands::HandleValidateAssets},  // W1-B
        {TEXT("get_source_control_status"), &FEpicUnrealMCPValidationCommands::HandleGetSourceControlStatus},  // W1-H
    };

    const Handler* H = Dispatch.Find(CommandType);
    if (H)
    {
        return (this->*(*H))(Params);
    }

    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown validation command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FEpicUnrealMCPValidationCommands::HandleCompileAllBlueprints(const TSharedPtr<FJsonObject>& Params)
{
    TArray<FAssetData> BlueprintAssets;
    FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
    FARFilter Filter;
    Filter.ClassPaths.Add(UBlueprint::StaticClass()->GetClassPathName());
    Filter.bRecursivePaths = true;
    AssetRegistryModule.Get().GetAssets(Filter, BlueprintAssets);

    int32 CompiledCount = 0;
    int32 ErrorCount = 0;
    TArray<TSharedPtr<FJsonValue>> ErrorList;

    for (const FAssetData& Asset : BlueprintAssets)
    {
        UBlueprint* Blueprint = Cast<UBlueprint>(UEditorAssetLibrary::LoadAsset(Asset.GetObjectPathString()));
        if (!Blueprint)
        {
            continue;
        }

        FCompilerResultsLog Results;
        Results.SetSourcePath(Asset.GetObjectPathString());
        FKismetEditorUtilities::CompileBlueprint(Blueprint, EBlueprintCompileOptions::None, &Results);
        CompiledCount++;

        if (Results.NumErrors > 0)
        {
            ErrorCount++;
            TSharedPtr<FJsonObject> ErrObj = MakeShared<FJsonObject>();
            ErrObj->SetStringField(TEXT("asset"), Asset.GetObjectPathString());
            ErrObj->SetNumberField(TEXT("errors"), Results.NumErrors);
            ErrObj->SetNumberField(TEXT("warnings"), Results.NumWarnings);
            ErrorList.Add(MakeShared<FJsonValueObject>(ErrObj));
        }
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetNumberField(TEXT("compiled_count"), CompiledCount);
    Result->SetNumberField(TEXT("error_count"), ErrorCount);
    Result->SetArrayField(TEXT("errors"), ErrorList);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPValidationCommands::HandleRunMapCheck(const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // Run the editor's map check
    FMessageLog MapCheckLog("MapCheck");
    MapCheckLog.NewPage(FText::FromString(TEXT("MCP Map Check")));

    int32 ErrorCount = 0;
    int32 WarningCount = 0;

    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!Actor)
        {
            continue;
        }

        // Check for actors without valid root component
        if (!Actor->GetRootComponent())
        {
            WarningCount++;
            MapCheckLog.Warning()
                ->AddToken(FTextToken::Create(FText::FromString(Actor->GetName())))
                ->AddToken(FTextToken::Create(FText::FromString(TEXT("has no root component"))));
        }

        // Check for overlapping static mesh actors (simplified)
        AStaticMeshActor* SMActor = Cast<AStaticMeshActor>(Actor);
        if (SMActor && SMActor->GetStaticMeshComponent())
        {
            if (!SMActor->GetStaticMeshComponent()->GetStaticMesh())
            {
                ErrorCount++;
                MapCheckLog.Error()
                    ->AddToken(FTextToken::Create(FText::FromString(Actor->GetName())))
                    ->AddToken(FTextToken::Create(FText::FromString(TEXT("has no static mesh assigned"))));
            }
        }
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetNumberField(TEXT("errors"), ErrorCount);
    Result->SetNumberField(TEXT("warnings"), WarningCount);
    Result->SetStringField(TEXT("message"), TEXT("Map check completed. See Unreal Editor's Map Check tab for details."));
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPValidationCommands::HandleFindBrokenReferences(const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    TArray<TSharedPtr<FJsonValue>> BrokenActors;
    int32 MissingMeshCount = 0;
    int32 MissingMaterialCount = 0;

    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!Actor)
        {
            continue;
        }

        TArray<TSharedPtr<FJsonValue>> Issues;

        AStaticMeshActor* SMActor = Cast<AStaticMeshActor>(Actor);
        if (SMActor && SMActor->GetStaticMeshComponent())
        {
            if (!SMActor->GetStaticMeshComponent()->GetStaticMesh())
            {
                MissingMeshCount++;
                TSharedPtr<FJsonObject> Issue = MakeShared<FJsonObject>();
                Issue->SetStringField(TEXT("type"), TEXT("missing_mesh"));
                Issue->SetStringField(TEXT("component"), TEXT("StaticMeshComponent"));
                Issues.Add(MakeShared<FJsonValueObject>(Issue));
            }

            UMaterialInterface* Mat = SMActor->GetStaticMeshComponent()->GetMaterial(0);
            if (!Mat)
            {
                MissingMaterialCount++;
                TSharedPtr<FJsonObject> Issue = MakeShared<FJsonObject>();
                Issue->SetStringField(TEXT("type"), TEXT("missing_material"));
                Issue->SetStringField(TEXT("component"), TEXT("StaticMeshComponent"));
                Issue->SetNumberField(TEXT("slot"), 0);
                Issues.Add(MakeShared<FJsonValueObject>(Issue));
            }
        }

        if (Issues.Num() > 0)
        {
            TSharedPtr<FJsonObject> ActorObj = MakeShared<FJsonObject>();
            ActorObj->SetStringField(TEXT("actor_name"), Actor->GetName());
            ActorObj->SetStringField(TEXT("actor_label"), Actor->GetActorLabel());
            ActorObj->SetArrayField(TEXT("issues"), Issues);
            BrokenActors.Add(MakeShared<FJsonValueObject>(ActorObj));
        }
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetNumberField(TEXT("broken_actor_count"), BrokenActors.Num());
    Result->SetNumberField(TEXT("missing_mesh_count"), MissingMeshCount);
    Result->SetNumberField(TEXT("missing_material_count"), MissingMaterialCount);
    Result->SetArrayField(TEXT("broken_actors"), BrokenActors);
    return Result;
}

// W1-B_VALIDATION_BEGIN
// W1-B Validation / Profiling residue (UE 5.7)

TSharedPtr<FJsonObject> FEpicUnrealMCPValidationCommands::HandleSetAutoSaveSettings(const TSharedPtr<FJsonObject>& Params)
{
    UEditorLoadingSavingSettings* Settings = GetMutableDefault<UEditorLoadingSavingSettings>();
    if (!Settings)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("UEditorLoadingSavingSettings unavailable"));

    bool bAnyChanged = false;
    bool bAutoSaveEnable = false;
    if (Params->TryGetBoolField(TEXT("auto_save_enable"), bAutoSaveEnable))
    {
        Settings->bAutoSaveEnable = bAutoSaveEnable;
        bAnyChanged = true;
    }
    int32 AutoSaveTimeMinutes = 0;
    if (Params->TryGetNumberField(TEXT("auto_save_time_minutes"), AutoSaveTimeMinutes))
    {
        if (AutoSaveTimeMinutes < 1) AutoSaveTimeMinutes = 1;
        Settings->AutoSaveTimeMinutes = AutoSaveTimeMinutes;
        bAnyChanged = true;
    }
    int32 AutoSaveWarningInSeconds = 0;
    if (Params->TryGetNumberField(TEXT("auto_save_warning_in_seconds"), AutoSaveWarningInSeconds))
    {
        if (AutoSaveWarningInSeconds < 0) AutoSaveWarningInSeconds = 0;
        Settings->AutoSaveWarningInSeconds = AutoSaveWarningInSeconds;
        bAnyChanged = true;
    }
    bool bAutoSaveContent = false;
    if (Params->TryGetBoolField(TEXT("auto_save_content"), bAutoSaveContent))
    {
        Settings->bAutoSaveContent = bAutoSaveContent;
        bAnyChanged = true;
    }
    bool bAutoSaveMaps = false;
    if (Params->TryGetBoolField(TEXT("auto_save_maps"), bAutoSaveMaps))
    {
        Settings->bAutoSaveMaps = bAutoSaveMaps;
        bAnyChanged = true;
    }

    bool bSaved = false;
    if (bAnyChanged)
    {
        // UE 5.7: prefer TryUpdateDefaultConfigFile() over deprecated UpdateDefaultConfigFile().
        bSaved = Settings->TryUpdateDefaultConfigFile();
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetBoolField(TEXT("auto_save_enable"), Settings->bAutoSaveEnable);
    Result->SetNumberField(TEXT("auto_save_time_minutes"), Settings->AutoSaveTimeMinutes);
    Result->SetNumberField(TEXT("auto_save_warning_in_seconds"), Settings->AutoSaveWarningInSeconds);
    Result->SetBoolField(TEXT("auto_save_content"), Settings->bAutoSaveContent);
    Result->SetBoolField(TEXT("auto_save_maps"), Settings->bAutoSaveMaps);
    Result->SetBoolField(TEXT("changed"), bAnyChanged);
    Result->SetBoolField(TEXT("saved_to_default_config"), bSaved);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPValidationCommands::HandleGetEditorStats(const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);

    // FPS / delta time
    const float DeltaSeconds = FApp::GetDeltaTime();
    const float FPS = DeltaSeconds > 0.0f ? 1.0f / DeltaSeconds : 0.0f;
    Result->SetNumberField(TEXT("delta_seconds"), DeltaSeconds);
    Result->SetNumberField(TEXT("fps"), FPS);

    // Memory stats
    FPlatformMemoryStats Memory = FPlatformMemory::GetStats();
    TSharedPtr<FJsonObject> MemObj = MakeShared<FJsonObject>();
    MemObj->SetNumberField(TEXT("used_physical_mb"), Memory.UsedPhysical / (1024.0 * 1024.0));
    MemObj->SetNumberField(TEXT("peak_used_physical_mb"), Memory.PeakUsedPhysical / (1024.0 * 1024.0));
    MemObj->SetNumberField(TEXT("available_physical_mb"), Memory.AvailablePhysical / (1024.0 * 1024.0));
    MemObj->SetNumberField(TEXT("used_virtual_mb"), Memory.UsedVirtual / (1024.0 * 1024.0));
    MemObj->SetNumberField(TEXT("peak_used_virtual_mb"), Memory.PeakUsedVirtual / (1024.0 * 1024.0));
    Result->SetObjectField(TEXT("memory"), MemObj);

    // Optional: execute a stat console command via the editor world.
    FString StatCommand;
    if (Params->TryGetStringField(TEXT("stat_command"), StatCommand) && !StatCommand.IsEmpty())
    {
        if (UWorld* World = GetEditorWorld())
        {
            if (GEngine)
            {
                GEngine->Exec(World, *StatCommand);
                Result->SetStringField(TEXT("stat_command"), StatCommand);
                Result->SetBoolField(TEXT("stat_command_executed"), true);
            }
        }
    }

    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPValidationCommands::HandleStartUnrealInsightsTrace(const TSharedPtr<FJsonObject>& Params)
{
    FString Channels;
    Params->TryGetStringField(TEXT("channels"), Channels);
    if (Channels.IsEmpty())
    {
        Channels = TEXT("default,cpu,gpu,frame,bookmark,log");
    }
    FString TraceFile;
    Params->TryGetStringField(TEXT("trace_file"), TraceFile);

    // UE 5.7: TraceAuxiliary is the supported channel-control facade.
    FTraceAuxiliary::FOptions Options;
    Options.bExcludeTail = false;
    Options.bNoWorkerThread = false;
    if (!TraceFile.IsEmpty())
    {
        FTraceAuxiliary::Start(FTraceAuxiliary::EConnectionType::File, *TraceFile, *Channels, &Options);
    }
    else
    {
        // No file: only enable the channels (assumes the listener is already attached).
        FTraceAuxiliary::EnableChannels(*Channels);
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("channels"), Channels);
    if (!TraceFile.IsEmpty())
    {
        Result->SetStringField(TEXT("trace_file"), TraceFile);
        Result->SetStringField(TEXT("mode"), TEXT("file"));
    }
    else
    {
        Result->SetStringField(TEXT("mode"), TEXT("channels_only"));
    }
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPValidationCommands::HandleStopUnrealInsightsTrace(const TSharedPtr<FJsonObject>& Params)
{
    const bool bStopped = FTraceAuxiliary::Stop();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetBoolField(TEXT("stopped"), bStopped);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPValidationCommands::HandleValidateAssets(const TSharedPtr<FJsonObject>& Params)
{
    UEditorValidatorSubsystem* Validator = GEditor ? GEditor->GetEditorSubsystem<UEditorValidatorSubsystem>() : nullptr;
    if (!Validator)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("UEditorValidatorSubsystem unavailable"));

    FString ContentPath = TEXT("/Game");
    Params->TryGetStringField(TEXT("content_path"), ContentPath);

    IAssetRegistry& AssetRegistry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();
    TArray<FAssetData> AllAssets;
    AssetRegistry.GetAssetsByPath(FName(*ContentPath), AllAssets, /*bRecursive=*/true);

    int32 RequestedLimit = 0;
    Params->TryGetNumberField(TEXT("max_assets"), RequestedLimit);
    if (RequestedLimit > 0 && AllAssets.Num() > RequestedLimit)
    {
        AllAssets.SetNum(RequestedLimit);
    }

    FValidateAssetsSettings VSettings;
    VSettings.bSkipExcludedDirectories = true;
    VSettings.bShowIfNoFailures = false;
    VSettings.ValidationUsecase = EDataValidationUsecase::Manual;

    FValidateAssetsResults VResults;
    Validator->ValidateAssetsWithSettings(AllAssets, VSettings, VResults);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("content_path"), ContentPath);
    Result->SetNumberField(TEXT("num_checked"), VResults.NumChecked);
    Result->SetNumberField(TEXT("num_valid"), VResults.NumValid);
    Result->SetNumberField(TEXT("num_invalid"), VResults.NumInvalid);
    Result->SetNumberField(TEXT("num_skipped"), VResults.NumSkipped);
    Result->SetNumberField(TEXT("num_warnings"), VResults.NumWarnings);
    Result->SetNumberField(TEXT("num_unable_to_validate"), VResults.NumUnableToValidate);
    return Result;
}

// W1-H_SCC_BEGIN
// W1-H Source Control status query (UE 5.7)
TSharedPtr<FJsonObject> FEpicUnrealMCPValidationCommands::HandleGetSourceControlStatus(const TSharedPtr<FJsonObject>& Params)
{
    ISourceControlModule& SCC = ISourceControlModule::Get();
    const bool bEnabled = SCC.IsEnabled();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetBoolField(TEXT("enabled"), bEnabled);

    if (bEnabled)
    {
        ISourceControlProvider& Provider = SCC.GetProvider();
        Result->SetStringField(TEXT("provider_name"), Provider.GetName().ToString());
        Result->SetStringField(TEXT("status_text"), Provider.GetStatusText().ToString());
        Result->SetBoolField(TEXT("available"), Provider.IsAvailable());
    }
    else
    {
        // Even when disabled, list the available providers so callers know
        // what to SetProvider() with.
        TArray<FName> ProviderNames;
        SCC.GetProviderNames(ProviderNames);
        TArray<TSharedPtr<FJsonValue>> ProvidersJson;
        for (const FName& Name : ProviderNames)
        {
            ProvidersJson.Add(MakeShared<FJsonValueString>(Name.ToString()));
        }
        Result->SetArrayField(TEXT("available_providers"), ProvidersJson);
    }
    return Result;
}
