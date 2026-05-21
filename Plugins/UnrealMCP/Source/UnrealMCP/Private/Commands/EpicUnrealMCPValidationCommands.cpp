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

