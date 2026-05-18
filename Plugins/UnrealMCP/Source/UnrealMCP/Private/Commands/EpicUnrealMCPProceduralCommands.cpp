// =====================================================================
// EpicUnrealMCPProceduralCommands
//
// Phase 4 (Issue #31) trimmed this file to host only the procedural
// generation surface and the single request_cognitive_processing
// command.  Physics / Validation / Instance handlers were extracted into
// dedicated classes:
//   - FEpicUnrealMCPPhysicsCommands     (route 22)
//   - FEpicUnrealMCPValidationCommands  (route 23)
//   - FEpicUnrealMCPInstanceCommands    (route 24)
//
// Adding a new procedural command that fits the existing surface should
// stay here; otherwise spin up a new FEpicUnrealMCPXxxCommands so this
// file does not regrow back to the pre-Phase-4 size.
// =====================================================================

#include "Commands/EpicUnrealMCPProceduralCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"
#include "EpicUnrealMCPBridge.h"

#include "Editor.h"
#include "EditorViewportClient.h"
#include "LevelEditorViewport.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "EditorAssetLibrary.h"
#include "ScopedTransaction.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"

// =====================================================================
// Class members
// =====================================================================

FEpicUnrealMCPProceduralCommands::FEpicUnrealMCPProceduralCommands()
{
}

UWorld* FEpicUnrealMCPProceduralCommands::GetEditorWorld() const
{
    if (!GEditor)
    {
        return nullptr;
    }
    return GEditor->GetEditorWorldContext().World();
}

TSharedPtr<FJsonObject> FEpicUnrealMCPProceduralCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPProceduralCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        // Procedural generation
        {TEXT("spawn_tile_grid"),                  &FEpicUnrealMCPProceduralCommands::HandleSpawnTileGrid},
        {TEXT("spawn_procedural_actor_batch"),     &FEpicUnrealMCPProceduralCommands::HandleSpawnProceduralActorBatch},
        {TEXT("create_spline_mesh_from_segments"), &FEpicUnrealMCPProceduralCommands::HandleCreateSplineMeshFromSegments},
        {TEXT("create_data_layer_for_generation"), &FEpicUnrealMCPProceduralCommands::HandleCreateDataLayerForGeneration},
        {TEXT("clear_generated_group"),            &FEpicUnrealMCPProceduralCommands::HandleClearGeneratedGroup},

        // Cognitive processing (single-command surface kept here for now)
        {TEXT("request_cognitive_processing"),     &FEpicUnrealMCPProceduralCommands::HandleRequestCognitiveProcessing},
    };

    const Handler* H = Dispatch.Find(CommandType);
    if (H)
    {
        return (this->*(*H))(Params);
    }

    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown procedural command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FEpicUnrealMCPProceduralCommands::HandleRequestCognitiveProcessing(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing required parameter: actor_name"));
    }

    FString Context;
    Params->TryGetStringField(TEXT("context"), Context);

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // Find the actor (can be an AI Controller or any actor with the function)
    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName || It->GetActorLabel() == ActorName)
        {
            TargetActor = *It;
            break;
        }
    }

    if (!TargetActor)
    {
        // Try mcp_id lookup via the shared ActorIndex first, then fall back to tag scan.
        TargetActor = FEpicUnrealMCPCommonUtils::GetActorIndex().FindByMcpId(ActorName);
        if (!TargetActor)
        {
            TargetActor = FEpicUnrealMCPCommonUtils::FindActorByMcpIdTag(World, ActorName);
        }
    }

    if (!TargetActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    // Use reflection to call RequestCognitiveProcessing(EnvironmentalContext)
    UFunction* Func = TargetActor->FindFunction(FName(TEXT("RequestCognitiveProcessing")));
    if (!Func)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Actor '%s' does not have a RequestCognitiveProcessing function"), *ActorName));
    }

    // Set up parameters for the function call
    struct FRequestCognitiveProcessingParams
    {
        FString EnvironmentalContext;
    };

    FRequestCognitiveProcessingParams FuncParams;
    FuncParams.EnvironmentalContext = Context;

    TargetActor->ProcessEvent(Func, &FuncParams);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("actor_name"), TargetActor->GetName());
    ResultObj->SetStringField(TEXT("message"), TEXT("Cognitive processing requested asynchronously"));
    return ResultObj;
}



// ===================================================================
// HandleSpawnTileGrid (WFC realization)
// ===================================================================
// Spawns one HISM actor per unique tile_id from a WFC grid result.
// Inputs:
//   set_id_prefix (string, default "wfc"): prefix for actor names + mcp_id tag
//   tiles (array, required): [{x:int, y:int, tile_id:string, rotation_degrees:float}]
//   tile_asset_map (object, required): { tile_id : "/Game/.../SM_Asset" }
//   default_mesh_path (string, optional): fallback mesh when a tile is missing in tile_asset_map
//   material_map (object, optional): { tile_id : "/Game/.../M_Asset" }
//   default_material_path (string, optional)
//   cell_size (object, optional): { x: 100.0, y: 100.0 } default 100 cm
//   origin (object, optional): { x, y, z } default zero
//   replace_existing (bool, optional, default true): if true delete actors with the same set_id_prefix before spawning
//   focus_viewport (bool, optional, default false)
// Returns:
//   success, total_instance_count, per_tile: [ { tile_id, mesh_path, instance_count, actor_name, actor_path } ],
//   skipped_tile_ids: [ tile_ids missing from map and no default ]
TSharedPtr<FJsonObject> FEpicUnrealMCPProceduralCommands::HandleSpawnTileGrid(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString SetPrefix = TEXT("wfc");
    Params->TryGetStringField(TEXT("set_id_prefix"), SetPrefix);
    if (SetPrefix.IsEmpty())
    {
        SetPrefix = TEXT("wfc");
    }

    const TArray<TSharedPtr<FJsonValue>>* TilesArray = nullptr;
    if (!Params->TryGetArrayField(TEXT("tiles"), TilesArray) || !TilesArray)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'tiles' array is required"));
    }

    const TSharedPtr<FJsonObject>* TileAssetMapPtr = nullptr;
    if (!Params->TryGetObjectField(TEXT("tile_asset_map"), TileAssetMapPtr) || !TileAssetMapPtr)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'tile_asset_map' object is required (e.g. {\"grass\":\"/Game/Tiles/SM_Grass\"})"));
    }

    FString DefaultMeshPath;
    Params->TryGetStringField(TEXT("default_mesh_path"), DefaultMeshPath);

    const TSharedPtr<FJsonObject>* MaterialMapPtr = nullptr;
    Params->TryGetObjectField(TEXT("material_map"), MaterialMapPtr);

    FString DefaultMaterialPath;
    Params->TryGetStringField(TEXT("default_material_path"), DefaultMaterialPath);

    double CellSizeX = 100.0;
    double CellSizeY = 100.0;
    const TSharedPtr<FJsonObject>* CellSizePtr = nullptr;
    if (Params->TryGetObjectField(TEXT("cell_size"), CellSizePtr) && CellSizePtr)
    {
        (*CellSizePtr)->TryGetNumberField(TEXT("x"), CellSizeX);
        (*CellSizePtr)->TryGetNumberField(TEXT("y"), CellSizeY);
    }

    FVector OriginVec = FVector::ZeroVector;
    const TSharedPtr<FJsonObject>* OriginPtr = nullptr;
    if (Params->TryGetObjectField(TEXT("origin"), OriginPtr) && OriginPtr)
    {
        double Ox = 0.0, Oy = 0.0, Oz = 0.0;
        (*OriginPtr)->TryGetNumberField(TEXT("x"), Ox);
        (*OriginPtr)->TryGetNumberField(TEXT("y"), Oy);
        (*OriginPtr)->TryGetNumberField(TEXT("z"), Oz);
        OriginVec = FVector(Ox, Oy, Oz);
    }

    bool bReplaceExisting = true;
    Params->TryGetBoolField(TEXT("replace_existing"), bReplaceExisting);

    bool bFocusViewport = false;
    Params->TryGetBoolField(TEXT("focus_viewport"), bFocusViewport);

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // 1) Group tiles by tile_id and resolve transforms.
    struct FGroupedTile
    {
        FString TileId;
        TArray<FTransform> Transforms;
    };
    TMap<FString, FGroupedTile> Grouped;

    for (const TSharedPtr<FJsonValue>& Value : *TilesArray)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) continue;
        TSharedPtr<FJsonObject> Tile = Value->AsObject();
        if (!Tile.IsValid()) continue;

        double Xd = 0.0, Yd = 0.0, RotDeg = 0.0;
        Tile->TryGetNumberField(TEXT("x"), Xd);
        Tile->TryGetNumberField(TEXT("y"), Yd);
        Tile->TryGetNumberField(TEXT("rotation_degrees"), RotDeg);

        FString TileId;
        if (!Tile->TryGetStringField(TEXT("tile_id"), TileId) || TileId.IsEmpty())
        {
            continue;
        }

        FVector Loc = OriginVec + FVector(Xd * CellSizeX, Yd * CellSizeY, 0.0);
        FRotator Rot(0.0, RotDeg, 0.0);
        FTransform T(Rot, Loc, FVector::OneVector);

        FGroupedTile& G = Grouped.FindOrAdd(TileId);
        G.TileId = TileId;
        G.Transforms.Add(T);
    }

    // 2) Optionally replace existing actors that share the same prefix.
    if (bReplaceExisting)
    {
        const FString PrefixTag = FString::Printf(TEXT("mcp_id:tile_grid_%s_"), *SetPrefix);
        TArray<AActor*> ToDestroy;
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            AActor* A = *It;
            if (!A) continue;
            for (const FName& Tag : A->Tags)
            {
                if (Tag.ToString().StartsWith(PrefixTag))
                {
                    ToDestroy.Add(A);
                    break;
                }
            }
        }
        for (AActor* A : ToDestroy)
        {
            A->Destroy();
        }
    }

    FScopedTransaction Transaction(FText::FromString(FString::Printf(TEXT("UnrealMCP: Spawn Tile Grid %s"), *SetPrefix)));

    TArray<TSharedPtr<FJsonValue>> PerTileResults;
    TArray<TSharedPtr<FJsonValue>> Skipped;
    int32 TotalInstances = 0;

    for (const TPair<FString, FGroupedTile>& Pair : Grouped)
    {
        const FString& TileId = Pair.Key;
        const FGroupedTile& Group = Pair.Value;

        // Resolve mesh path
        FString MeshPath;
        if (TileAssetMapPtr && (*TileAssetMapPtr)->HasField(TileId))
        {
            (*TileAssetMapPtr)->TryGetStringField(TileId, MeshPath);
        }
        if (MeshPath.IsEmpty())
        {
            MeshPath = DefaultMeshPath;
        }

        if (MeshPath.IsEmpty())
        {
            TSharedPtr<FJsonObject> SkipObj = MakeShared<FJsonObject>();
            SkipObj->SetStringField(TEXT("tile_id"), TileId);
            SkipObj->SetStringField(TEXT("reason"), TEXT("no mesh path in tile_asset_map and no default_mesh_path"));
            SkipObj->SetNumberField(TEXT("instance_count"), Group.Transforms.Num());
            Skipped.Add(MakeShared<FJsonValueObject>(SkipObj));
            continue;
        }

        UStaticMesh* Mesh = Cast<UStaticMesh>(UEditorAssetLibrary::LoadAsset(MeshPath));
        if (!Mesh)
        {
            TSharedPtr<FJsonObject> SkipObj = MakeShared<FJsonObject>();
            SkipObj->SetStringField(TEXT("tile_id"), TileId);
            SkipObj->SetStringField(TEXT("reason"), FString::Printf(TEXT("Failed to load mesh: %s"), *MeshPath));
            SkipObj->SetNumberField(TEXT("instance_count"), Group.Transforms.Num());
            Skipped.Add(MakeShared<FJsonValueObject>(SkipObj));
            continue;
        }

        // Resolve material
        FString MatPath;
        if (MaterialMapPtr && (*MaterialMapPtr)->HasField(TileId))
        {
            (*MaterialMapPtr)->TryGetStringField(TileId, MatPath);
        }
        if (MatPath.IsEmpty())
        {
            MatPath = DefaultMaterialPath;
        }

        const FString ActorLabel = FString::Printf(TEXT("TileGrid_%s_%s"), *SetPrefix, *TileId);
        const FString McpIdTag = FString::Printf(TEXT("mcp_id:tile_grid_%s_%s"), *SetPrefix, *TileId);

        FActorSpawnParameters SpawnParams;
        SpawnParams.Name = *ActorLabel;
        SpawnParams.NameMode = FActorSpawnParameters::ESpawnActorNameMode::Requested;

        AActor* TileActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
        if (!TileActor)
        {
            TSharedPtr<FJsonObject> SkipObj = MakeShared<FJsonObject>();
            SkipObj->SetStringField(TEXT("tile_id"), TileId);
            SkipObj->SetStringField(TEXT("reason"), TEXT("Failed to spawn actor"));
            SkipObj->SetNumberField(TEXT("instance_count"), Group.Transforms.Num());
            Skipped.Add(MakeShared<FJsonValueObject>(SkipObj));
            continue;
        }

        TileActor->SetActorLabel(*ActorLabel);
        TileActor->Tags.AddUnique(FName(TEXT("managed_by_mcp")));
        TileActor->Tags.AddUnique(FName(TEXT("wfc_generated")));
        TileActor->Tags.AddUnique(FName(*McpIdTag));
        TileActor->Tags.AddUnique(FName(*FString::Printf(TEXT("wfc_tile_id:%s"), *TileId)));

        UHierarchicalInstancedStaticMeshComponent* HISM = NewObject<UHierarchicalInstancedStaticMeshComponent>(
            TileActor, UHierarchicalInstancedStaticMeshComponent::StaticClass(), TEXT("TileGridHISM"));
        HISM->RegisterComponent();
        TileActor->SetRootComponent(HISM);
        HISM->SetStaticMesh(Mesh);
        HISM->SetCollisionEnabled(ECollisionEnabled::NoCollision);

        if (!MatPath.IsEmpty())
        {
            UMaterialInterface* Material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(MatPath));
            if (Material)
            {
                HISM->SetMaterial(0, Material);
            }
        }

        for (const FTransform& T : Group.Transforms)
        {
            HISM->AddInstance(T);
        }
        HISM->MarkRenderStateDirty();

        TileActor->Modify();
        TileActor->MarkPackageDirty();

        FEpicUnrealMCPCommonUtils::GetActorIndex().AddActor(TileActor);

        TotalInstances += Group.Transforms.Num();

        TSharedPtr<FJsonObject> Entry = MakeShared<FJsonObject>();
        Entry->SetStringField(TEXT("tile_id"), TileId);
        Entry->SetStringField(TEXT("mesh_path"), MeshPath);
        Entry->SetStringField(TEXT("actor_name"), TileActor->GetName());
        Entry->SetStringField(TEXT("actor_path"), TileActor->GetPathName());
        Entry->SetNumberField(TEXT("instance_count"), Group.Transforms.Num());
        if (!MatPath.IsEmpty())
        {
            Entry->SetStringField(TEXT("material_path"), MatPath);
        }
        PerTileResults.Add(MakeShared<FJsonValueObject>(Entry));
    }

    if (bFocusViewport && PerTileResults.Num() > 0 && GEditor)
    {
        TArray<AActor*> Focus;
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            for (const FName& Tag : It->Tags)
            {
                if (Tag.ToString().StartsWith(FString::Printf(TEXT("mcp_id:tile_grid_%s_"), *SetPrefix)))
                {
                    Focus.Add(*It);
                    break;
                }
            }
        }
        if (Focus.Num() > 0)
        {
            GEditor->MoveViewportCamerasToActor(Focus, true);
        }
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("set_id_prefix"), SetPrefix);
    ResultObj->SetNumberField(TEXT("total_instance_count"), TotalInstances);
    ResultObj->SetNumberField(TEXT("tile_kind_count"), PerTileResults.Num());
    ResultObj->SetArrayField(TEXT("per_tile"), PerTileResults);
    ResultObj->SetArrayField(TEXT("skipped"), Skipped);
    return ResultObj;
}



// ===================================================================
// Issue #26: Remaining procedural realization commands
// ===================================================================
// All four handlers run on the GameThread (the bridge dispatches editor
// commands via AsyncTask). They follow the existing conventions:
//   - structured envelope: { success, data | error, hint? }
//   - tag every spawned actor with `managed_by_mcp` and (when provided)
//     `mcp_id:<id>` and the caller's custom tags
//   - Modify() + MarkPackageDirty() before returning so World Partition
//     captures the change and saves it on the next Save All
//   - guardrails: per-call max counts to keep accidental large requests safe


// Shared tag / lookup helpers are implemented in FEpicUnrealMCPCommonUtils.


// -------------------------------------------------------------------
// HandleSpawnProceduralActorBatch
// -------------------------------------------------------------------
// Bulk spawn N actors in a single GameThread pass.
// Inputs:
//   group_id (string, optional)         - tag added as `procedural_group:<id>`
//   max_actors (int, default 5000)      - safety cap on number of placements
//   focus_viewport (bool, default false)
//   placements (array, required) of:
//       mcp_id (string, optional)
//       actor_class (string, default "StaticMeshActor")
//       static_mesh (string, optional, only for StaticMeshActor)
//       location (array[3] or {x,y,z})
//       rotation (array[3] or {pitch,yaw,roll})
//       scale (array[3] or {x,y,z})
//       tags (array<string>, optional)
//       desired_name (string, optional) - if absent, use mcp_id, else auto.
TSharedPtr<FJsonObject> FEpicUnrealMCPProceduralCommands::HandleSpawnProceduralActorBatch(
    const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    const TArray<TSharedPtr<FJsonValue>>* PlacementsArray = nullptr;
    if (!Params->TryGetArrayField(TEXT("placements"), PlacementsArray) || !PlacementsArray)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'placements' array is required"));
    }

    FString GroupId;
    Params->TryGetStringField(TEXT("group_id"), GroupId);

    int32 MaxActors = 5000;
    int32 MaxFromJson = 0;
    if (Params->TryGetNumberField(TEXT("max_actors"), MaxFromJson) && MaxFromJson > 0)
    {
        MaxActors = MaxFromJson;
    }

    bool bFocusViewport = false;
    Params->TryGetBoolField(TEXT("focus_viewport"), bFocusViewport);

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    const int32 Requested = PlacementsArray->Num();
    const int32 Effective = FMath::Min(Requested, MaxActors);
    TArray<TSharedPtr<FJsonValue>> Warnings;
    if (Effective < Requested)
    {
        TSharedPtr<FJsonObject> W = MakeShared<FJsonObject>();
        W->SetStringField(TEXT("type"), TEXT("ActorCountCapped"));
        W->SetNumberField(TEXT("requested"), Requested);
        W->SetNumberField(TEXT("applied"), Effective);
        Warnings.Add(MakeShared<FJsonValueObject>(W));
    }

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Spawn Procedural Batch")));

    int32 SpawnedCount = 0;
    int32 SkippedCount = 0;
    TArray<TSharedPtr<FJsonValue>> ActorPaths;
    TArray<AActor*> SpawnedForFocus;

    for (int32 i = 0; i < Effective; ++i)
    {
        const TSharedPtr<FJsonValue>& V = (*PlacementsArray)[i];
        if (!V.IsValid() || V->Type != EJson::Object)
        {
            ++SkippedCount;
            continue;
        }
        const TSharedPtr<FJsonObject>& Item = V->AsObject();
        if (!Item.IsValid())
        {
            ++SkippedCount;
            continue;
        }

        FString ActorClass = TEXT("StaticMeshActor");
        Item->TryGetStringField(TEXT("actor_class"), ActorClass);

        FString McpId;
        Item->TryGetStringField(TEXT("mcp_id"), McpId);

        FString DesiredName;
        if (!Item->TryGetStringField(TEXT("desired_name"), DesiredName) || DesiredName.IsEmpty())
        {
            DesiredName = !McpId.IsEmpty()
                ? FString::Printf(TEXT("ProcBatch_%s"), *McpId)
                : FString::Printf(TEXT("ProcBatch_%d"), i);
        }

        FVector Location = FVector::ZeroVector;
        FRotator Rotation = FRotator::ZeroRotator;
        FVector Scale = FVector::OneVector;
        FString ParamError;
        if (Item->HasField(TEXT("location")))
        {
            FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Item, TEXT("location"), Location, ParamError);
        }
        if (Item->HasField(TEXT("rotation")))
        {
            FEpicUnrealMCPCommonUtils::TryGetRotatorFromJson(Item, TEXT("rotation"), Rotation, ParamError);
        }
        if (Item->HasField(TEXT("scale")))
        {
            FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Item, TEXT("scale"), Scale, ParamError);
        }

        FActorSpawnParameters SpawnParams;
        SpawnParams.Name = *DesiredName;
        SpawnParams.NameMode = FActorSpawnParameters::ESpawnActorNameMode::Requested;
        SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

        AActor* NewActor = nullptr;
        if (ActorClass == TEXT("StaticMeshActor"))
        {
            AStaticMeshActor* SMActor = World->SpawnActor<AStaticMeshActor>(
                AStaticMeshActor::StaticClass(), Location, Rotation, SpawnParams);
            if (SMActor)
            {
                FString MeshPath;
                if (Item->TryGetStringField(TEXT("static_mesh"), MeshPath) && !MeshPath.IsEmpty())
                {
                    UStaticMesh* Mesh = Cast<UStaticMesh>(UEditorAssetLibrary::LoadAsset(MeshPath));
                    if (Mesh)
                    {
                        SMActor->GetStaticMeshComponent()->SetStaticMesh(Mesh);
                    }
                }
            }
            NewActor = SMActor;
        }
        else
        {
            // Generic resolution by class name (Engine module).
            UClass* FoundClass = LoadClass<AActor>(nullptr,
                *FString::Printf(TEXT("/Script/Engine.%s"), *ActorClass));
            if (!FoundClass)
            {
                FoundClass = LoadClass<AActor>(nullptr,
                    *FString::Printf(TEXT("/Script/FlopperamUnrealMCP.%s"), *ActorClass));
            }
            if (FoundClass)
            {
                NewActor = World->SpawnActor<AActor>(FoundClass, Location, Rotation, SpawnParams);
            }
        }

        if (!NewActor)
        {
            ++SkippedCount;
            continue;
        }

        // Apply scale (SpawnActor takes only loc+rot).
        FTransform T = NewActor->GetTransform();
        T.SetScale3D(Scale);
        NewActor->SetActorTransform(T);

        TArray<FString> ExtraTags = FEpicUnrealMCPCommonUtils::ReadStringArrayField(Item, TEXT("tags"));
        if (!GroupId.IsEmpty())
        {
            ExtraTags.Add(FString::Printf(TEXT("procedural_group:%s"), *GroupId));
        }
        FEpicUnrealMCPCommonUtils::ApplyMcpIdAndTags(NewActor, McpId, ExtraTags);

        NewActor->Modify();
        NewActor->MarkPackageDirty();
        FEpicUnrealMCPCommonUtils::GetActorIndex().AddActor(NewActor);

        ++SpawnedCount;
        SpawnedForFocus.Add(NewActor);
        ActorPaths.Add(MakeShared<FJsonValueString>(NewActor->GetPathName()));
    }

    if (bFocusViewport && SpawnedForFocus.Num() > 0 && GEditor)
    {
        GEditor->MoveViewportCamerasToActor(SpawnedForFocus, true);
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetNumberField(TEXT("requested_count"), Requested);
    Data->SetNumberField(TEXT("spawned_count"), SpawnedCount);
    Data->SetNumberField(TEXT("skipped_count"), SkippedCount);
    Data->SetNumberField(TEXT("max_actors_cap"), MaxActors);
    Data->SetArrayField(TEXT("actor_paths"), ActorPaths);
    Data->SetArrayField(TEXT("warnings"), Warnings);
    if (!GroupId.IsEmpty())
    {
        Data->SetStringField(TEXT("group_id"), GroupId);
    }

    TSharedPtr<FJsonObject> Resp = MakeShared<FJsonObject>();
    Resp->SetBoolField(TEXT("success"), true);
    Resp->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Resp;
}

// -------------------------------------------------------------------
// HandleCreateSplineMeshFromSegments
// -------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPProceduralCommands::HandleCreateSplineMeshFromSegments(
    const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));
    }
    FString MeshPath;
    if (!Params->TryGetStringField(TEXT("mesh_path"), MeshPath) || MeshPath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'mesh_path' parameter"));
    }

    const TArray<TSharedPtr<FJsonValue>>* SegArray = nullptr;
    if (!Params->TryGetArrayField(TEXT("segments"), SegArray) || !SegArray)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'segments' array is required"));
    }

    FString McpId;
    Params->TryGetStringField(TEXT("mcp_id"), McpId);

    FString MaterialPath;
    Params->TryGetStringField(TEXT("material_path"), MaterialPath);

    FString ForwardAxisStr = TEXT("X");
    Params->TryGetStringField(TEXT("forward_axis"), ForwardAxisStr);
    ESplineMeshAxis::Type ForwardAxis = ESplineMeshAxis::X;
    if (ForwardAxisStr.Equals(TEXT("Y"), ESearchCase::IgnoreCase)) ForwardAxis = ESplineMeshAxis::Y;
    else if (ForwardAxisStr.Equals(TEXT("Z"), ESearchCase::IgnoreCase)) ForwardAxis = ESplineMeshAxis::Z;

    int32 MaxSegments = 10000;
    int32 MaxFromJson = 0;
    if (Params->TryGetNumberField(TEXT("max_segments"), MaxFromJson) && MaxFromJson > 0)
    {
        MaxSegments = MaxFromJson;
    }

    UStaticMesh* Mesh = Cast<UStaticMesh>(UEditorAssetLibrary::LoadAsset(MeshPath));
    if (!Mesh)
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"), FString::Printf(TEXT("Failed to load mesh: %s"), *MeshPath));
        Err->SetStringField(TEXT("hint"), TEXT("Verify the path under /Game/... is correct and the asset exists."));
        return Err;
    }
    UMaterialInterface* Material = nullptr;
    if (!MaterialPath.IsEmpty())
    {
        Material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(MaterialPath));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    const int32 RequestedSegments = SegArray->Num();
    const int32 EffectiveSegments = FMath::Min(RequestedSegments, MaxSegments);
    TArray<TSharedPtr<FJsonValue>> Warnings;
    if (EffectiveSegments < RequestedSegments)
    {
        TSharedPtr<FJsonObject> W = MakeShared<FJsonObject>();
        W->SetStringField(TEXT("type"), TEXT("SegmentCountCapped"));
        W->SetNumberField(TEXT("requested"), RequestedSegments);
        W->SetNumberField(TEXT("applied"), EffectiveSegments);
        Warnings.Add(MakeShared<FJsonValueObject>(W));
    }

    AActor* Parent = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetFName() == FName(*ActorName))
        {
            Parent = *It;
            break;
        }
    }
    bool bCreated = false;
    if (!Parent)
    {
        FActorSpawnParameters SpawnParams;
        SpawnParams.Name = *ActorName;
        SpawnParams.NameMode = FActorSpawnParameters::ESpawnActorNameMode::Requested;
        Parent = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
        if (!Parent)
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn parent actor for spline meshes"));
        }
        Parent->SetActorLabel(*ActorName);
        USceneComponent* Root = NewObject<USceneComponent>(Parent, USceneComponent::StaticClass(), TEXT("SplineMeshRoot"));
        Root->RegisterComponent();
        Parent->SetRootComponent(Root);
        bCreated = true;
    }

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Create Spline Mesh from Segments")));

    TArray<FString> ExtraTags = FEpicUnrealMCPCommonUtils::ReadStringArrayField(Params, TEXT("tags"));
    ExtraTags.Add(TEXT("procedural_spline_mesh"));
    FEpicUnrealMCPCommonUtils::ApplyMcpIdAndTags(Parent, McpId, ExtraTags);

    int32 ComponentCount = 0;
    for (int32 i = 0; i < EffectiveSegments; ++i)
    {
        const TSharedPtr<FJsonValue>& V = (*SegArray)[i];
        if (!V.IsValid() || V->Type != EJson::Object) continue;
        const TSharedPtr<FJsonObject>& Seg = V->AsObject();
        if (!Seg.IsValid()) continue;

        FVector Start = FVector::ZeroVector;
        FVector End   = FVector::ZeroVector;
        FString ParamError;
        if (!FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Seg, TEXT("start"), Start, ParamError)) continue;
        if (!FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Seg, TEXT("end"), End, ParamError)) continue;

        FVector StartTangent = End - Start;
        FVector EndTangent   = StartTangent;
        if (Seg->HasField(TEXT("start_tangent")))
        {
            FVector T;
            if (FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Seg, TEXT("start_tangent"), T, ParamError))
            {
                StartTangent = T;
            }
        }
        if (Seg->HasField(TEXT("end_tangent")))
        {
            FVector T;
            if (FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Seg, TEXT("end_tangent"), T, ParamError))
            {
                EndTangent = T;
            }
        }

        const FName CompName(*FString::Printf(TEXT("SplineMesh_%d"), i));
        USplineMeshComponent* SMC = NewObject<USplineMeshComponent>(Parent, USplineMeshComponent::StaticClass(), CompName);
        if (!SMC) continue;
        SMC->SetMobility(EComponentMobility::Movable);
        SMC->SetupAttachment(Parent->GetRootComponent());
        SMC->RegisterComponent();
        SMC->SetStaticMesh(Mesh);
        if (Material)
        {
            SMC->SetMaterial(0, Material);
        }
        SMC->SetForwardAxis(ForwardAxis, /*bUpdateMesh=*/false);
        SMC->SetStartAndEnd(Start, StartTangent, End, EndTangent, /*bUpdateMesh=*/true);
        SMC->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        ++ComponentCount;
    }

    Parent->Modify();
    Parent->MarkPackageDirty();
    FEpicUnrealMCPCommonUtils::GetActorIndex().AddActor(Parent);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), Parent->GetName());
    Data->SetStringField(TEXT("actor_path"), Parent->GetPathName());
    Data->SetBoolField(TEXT("created_actor"), bCreated);
    Data->SetNumberField(TEXT("requested_segment_count"), RequestedSegments);
    Data->SetNumberField(TEXT("segment_count"), EffectiveSegments);
    Data->SetNumberField(TEXT("component_count"), ComponentCount);
    Data->SetStringField(TEXT("mesh_path"), MeshPath);
    Data->SetStringField(TEXT("forward_axis"), ForwardAxisStr);
    Data->SetArrayField(TEXT("warnings"), Warnings);

    TSharedPtr<FJsonObject> Resp = MakeShared<FJsonObject>();
    Resp->SetBoolField(TEXT("success"), true);
    Resp->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Resp;
}

// -------------------------------------------------------------------
// HandleCreateDataLayerForGeneration
// -------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPProceduralCommands::HandleCreateDataLayerForGeneration(
    const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString DataLayerName;
    if (!Params->TryGetStringField(TEXT("data_layer_name"), DataLayerName) || DataLayerName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'data_layer_name' parameter"));
    }

    const TArray<TSharedPtr<FJsonValue>>* IdsArray = nullptr;
    if (!Params->TryGetArrayField(TEXT("actor_mcp_ids"), IdsArray) || !IdsArray)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'actor_mcp_ids' array is required"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Create Data Layer For Generation")));

    const FName LayerTag(*FString::Printf(TEXT("data_layer:%s"), *DataLayerName));
    TArray<TSharedPtr<FJsonValue>> Skipped;
    int32 AssignedCount = 0;

    for (const TSharedPtr<FJsonValue>& V : *IdsArray)
    {
        if (!V.IsValid() || V->Type != EJson::String) continue;
        const FString McpId = V->AsString();
        if (McpId.IsEmpty()) continue;

        AActor* Actor = FEpicUnrealMCPCommonUtils::FindActorByMcpIdTag(World, McpId);
        if (!Actor)
        {
            TSharedPtr<FJsonObject> S = MakeShared<FJsonObject>();
            S->SetStringField(TEXT("actor_mcp_id"), McpId);
            S->SetStringField(TEXT("reason"), TEXT("actor not found by mcp_id tag"));
            Skipped.Add(MakeShared<FJsonValueObject>(S));
            continue;
        }
        Actor->Tags.AddUnique(FName(TEXT("managed_by_mcp")));
        Actor->Tags.AddUnique(LayerTag);
        Actor->Modify();
        Actor->MarkPackageDirty();
        ++AssignedCount;
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("data_layer_name"), DataLayerName);
    Data->SetStringField(TEXT("data_layer_tag"), LayerTag.ToString());
    Data->SetStringField(TEXT("method"), TEXT("tag"));
    Data->SetNumberField(TEXT("requested_count"), IdsArray->Num());
    Data->SetNumberField(TEXT("actors_assigned_count"), AssignedCount);
    Data->SetArrayField(TEXT("skipped"), Skipped);
    Data->SetStringField(TEXT("note"), TEXT("First-pass implementation uses actor tags as a logical data layer. A follow-up will wire UDataLayerEditorSubsystem when the level uses World Partition."));

    TSharedPtr<FJsonObject> Resp = MakeShared<FJsonObject>();
    Resp->SetBoolField(TEXT("success"), true);
    Resp->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Resp;
}

// -------------------------------------------------------------------
// HandleClearGeneratedGroup
// -------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPProceduralCommands::HandleClearGeneratedGroup(
    const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    FString GroupId;
    Params->TryGetStringField(TEXT("group_id"), GroupId);
    TArray<FString> RequiredTags = FEpicUnrealMCPCommonUtils::ReadStringArrayField(Params, TEXT("required_tags"));

    if (GroupId.IsEmpty() && RequiredTags.Num() == 0)
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"), TEXT("Refusing to clear without 'group_id' or non-empty 'required_tags'"));
        Err->SetStringField(TEXT("hint"), TEXT("Pass at least one filter so we never accidentally delete every actor in the level."));
        return Err;
    }

    bool bDryRun = true;
    Params->TryGetBoolField(TEXT("dry_run"), bDryRun);

    int32 MaxDelete = 10000;
    int32 MaxFromJson = 0;
    if (Params->TryGetNumberField(TEXT("max_delete"), MaxFromJson) && MaxFromJson > 0)
    {
        MaxDelete = MaxFromJson;
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    const FName GroupTag = !GroupId.IsEmpty()
        ? FName(*FString::Printf(TEXT("procedural_group:%s"), *GroupId))
        : FName(NAME_None);

    TArray<AActor*> Matches;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!Actor) continue;

        if (!GroupId.IsEmpty() && !Actor->Tags.Contains(GroupTag))
        {
            continue;
        }
        bool bAllTagsMatch = true;
        for (const FString& Required : RequiredTags)
        {
            if (Required.IsEmpty()) continue;
            if (!Actor->Tags.Contains(FName(*Required)))
            {
                bAllTagsMatch = false;
                break;
            }
        }
        if (!bAllTagsMatch) continue;

        Matches.Add(Actor);
        if (Matches.Num() >= MaxDelete)
        {
            break;
        }
    }

    TArray<TSharedPtr<FJsonValue>> Paths;
    for (AActor* Actor : Matches)
    {
        Paths.Add(MakeShared<FJsonValueString>(Actor->GetPathName()));
    }

    int32 DeletedCount = 0;
    if (!bDryRun)
    {
        FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Clear Generated Group")));
        for (AActor* Actor : Matches)
        {
            if (!Actor) continue;
            Actor->Modify();
            FEpicUnrealMCPCommonUtils::GetActorIndex().RemoveActor(Actor);
            if (Actor->Destroy())
            {
                ++DeletedCount;
            }
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetBoolField(TEXT("dry_run"), bDryRun);
    if (!GroupId.IsEmpty())
    {
        Data->SetStringField(TEXT("group_id"), GroupId);
        Data->SetStringField(TEXT("group_tag"), GroupTag.ToString());
    }
    if (RequiredTags.Num() > 0)
    {
        TArray<TSharedPtr<FJsonValue>> TagJson;
        for (const FString& T : RequiredTags) TagJson.Add(MakeShared<FJsonValueString>(T));
        Data->SetArrayField(TEXT("required_tags"), TagJson);
    }
    Data->SetNumberField(TEXT("matched_count"), Matches.Num());
    Data->SetNumberField(TEXT("would_delete_count"), bDryRun ? Matches.Num() : 0);
    Data->SetNumberField(TEXT("deleted_count"), DeletedCount);
    Data->SetNumberField(TEXT("max_delete_cap"), MaxDelete);
    Data->SetArrayField(TEXT("actor_paths"), Paths);

    TSharedPtr<FJsonObject> Resp = MakeShared<FJsonObject>();
    Resp->SetBoolField(TEXT("success"), true);
    Resp->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Resp;
}
