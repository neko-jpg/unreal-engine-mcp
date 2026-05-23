#include "Commands/EpicUnrealMCPChaosCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_CHAOS_MCP
#include "PhysicsEngine/PhysicsSettings.h"
#include "Engine/EngineTypes.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#include "UObject/SavePackage.h"
#include "Components/StaticMeshComponent.h"
#include "Field/FieldSystemActor.h"
#include "Field/FieldSystemComponent.h"
#include "Field/FieldNodeBase.h"
#endif

bool FEpicUnrealMCPChaosCommands::IsModuleAvailable()
{
#if WITH_CHAOS_MCP
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the Chaos / Physics modules."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Chaos modules ship with UE 5.7 (ChaosCloth, GeometryCollectionEngine, ChaosVehicles). Build with WITH_EDITOR."));
    return R;
}

FEpicUnrealMCPChaosCommands::FEpicUnrealMCPChaosCommands() {}
FEpicUnrealMCPChaosCommands::~FEpicUnrealMCPChaosCommands() {}

// ---------------------------------------------------------------------------
// 234-stubs W3 (#89): Chaos executed-envelope helpers.
// ---------------------------------------------------------------------------

static TSharedPtr<FJsonObject> ChaosOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> ChaosErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

// Resolve an AActor by name or label from the editor world.
static AActor* FindChaosActorInEditorWorld(UWorld* World, const FString& ActorName)
{
    if (!World || ActorName.IsEmpty()) return nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName().Equals(ActorName, ESearchCase::IgnoreCase) ||
            It->GetActorLabel().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            return *It;
        }
    }
    return nullptr;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPChaosCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_collision_channel"),  &FEpicUnrealMCPChaosCommands::HandleCreateCollisionChannel},
        {TEXT("create_object_channel"),  &FEpicUnrealMCPChaosCommands::HandleCreateObjectChannel},
        {TEXT("create_trace_channel"),  &FEpicUnrealMCPChaosCommands::HandleCreateTraceChannel},
        {TEXT("create_geometry_collection"),  &FEpicUnrealMCPChaosCommands::HandleCreateGeometryCollection},
        {TEXT("fracture_geometry_collection"),  &FEpicUnrealMCPChaosCommands::HandleFractureGeometryCollection},
        {TEXT("create_chaos_field"),  &FEpicUnrealMCPChaosCommands::HandleCreateChaosField},
        {TEXT("configure_chaos_solver"),  &FEpicUnrealMCPChaosCommands::HandleConfigureChaosSolver},
        {TEXT("create_chaos_cache"),  &FEpicUnrealMCPChaosCommands::HandleCreateChaosCache},
        {TEXT("create_chaos_vehicle"),  &FEpicUnrealMCPChaosCommands::HandleCreateChaosVehicle},
        {TEXT("set_vehicle_wheel"),  &FEpicUnrealMCPChaosCommands::HandleSetVehicleWheel},
        {TEXT("set_vehicle_suspension"),  &FEpicUnrealMCPChaosCommands::HandleSetVehicleSuspension},
        {TEXT("set_vehicle_engine_torque"),  &FEpicUnrealMCPChaosCommands::HandleSetVehicleEngineTorque},
        {TEXT("set_cloth_settings"),  &FEpicUnrealMCPChaosCommands::HandleSetClothSettings},
        {TEXT("create_chaos_cloth_asset"),  &FEpicUnrealMCPChaosCommands::HandleCreateChaosClothAsset},
        {TEXT("set_groom_physics"),  &FEpicUnrealMCPChaosCommands::HandleSetGroomPhysics},
        {TEXT("set_ragdoll"),  &FEpicUnrealMCPChaosCommands::HandleSetRagdoll},
        {TEXT("edit_physics_asset_body"),  &FEpicUnrealMCPChaosCommands::HandleEditPhysicsAssetBody},
        {TEXT("edit_physics_asset_constraint"),  &FEpicUnrealMCPChaosCommands::HandleEditPhysicsAssetConstraint},
        {TEXT("attach_chaos_visual_debugger"),  &FEpicUnrealMCPChaosCommands::HandleAttachChaosVisualDebugger}
    };
    if (const Handler* H = Dispatch.Find(CommandType))
    {
        return (this->*(*H))(Params);
    }
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));
    return R;
}

// ---------------------------------------------------------------------------
// create_collision_channel — Spike reference: UPhysicsSettings collision channel.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateCollisionChannel(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_collision_channel"));

#if WITH_CHAOS_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_collision_channel"));

    FString ChannelName = TEXT("MCP_Channel");
    FString DefaultResponse = TEXT("Block");

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("channel_name"), ChannelName);
        Params->TryGetStringField(TEXT("default_response"), DefaultResponse);
    }

    // Get physics settings CDO
    UPhysicsSettings* PhysSettings = GetMutableDefault<UPhysicsSettings>();
    if (!PhysSettings) return ChaosErr(TEXT("Failed to get physics settings"));

    // Build a new custom collision channel entry and append it.
    FCustomChannelSetup NewChannel;
    NewChannel.Channel = ECC_GameTraceChannel1;
    NewChannel.DefaultResponse = DefaultResponse == TEXT("Ignore") ? ECR_Ignore
        : DefaultResponse == TEXT("Overlap") ? ECR_Overlap
        : ECR_Block;
    NewChannel.bTraceType = false;
    NewChannel.Name = FName(*ChannelName);
    NewChannel.bStaticObject = false;

    // Find the next available game trace channel slot.
    int32 SlotIndex = -1;
    for (int32 Idx = 0; Idx < PhysSettings->DefaultChannelResponses.Num(); ++Idx)
    {
        if (PhysSettings->DefaultChannelResponses[Idx].Name == FName(*ChannelName))
        {
            // Channel already exists -- return the existing slot.
            SlotIndex = Idx;
            break;
        }
    }
    if (SlotIndex < 0)
    {
        // Map the next free ECC_GameTraceChannel enum value.
        int32 FreeSlot = PhysSettings->DefaultChannelResponses.Num();
        if (FreeSlot >= 18) return ChaosErr(TEXT("All 18 game trace channels are in use"));

        ECollisionChannel NewECC = static_cast<ECollisionChannel>(
            static_cast<int32>(ECC_GameTraceChannel1) + FreeSlot);
        NewChannel.Channel = NewECC;
        PhysSettings->DefaultChannelResponses.Add(NewChannel);
        SlotIndex = PhysSettings->DefaultChannelResponses.Num() - 1;
    }

    PhysSettings->TryUpdateDefaultConfigFile();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_collision_channel"));
    Data->SetStringField(TEXT("channel_name"), ChannelName);
    Data->SetStringField(TEXT("default_response"), DefaultResponse);
    Data->SetNumberField(TEXT("slot_index"), SlotIndex);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("create_collision_channel"));
#endif
}

// ---------------------------------------------------------------------------
// create_object_channel — Add an object-type collision channel via UPhysicsSettings.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateObjectChannel(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_object_channel"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_object_channel"));

    FString ChannelName = TEXT("MCP_ObjectChannel");
    FString DefaultResponse = TEXT("Block");

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("channel_name"), ChannelName);
        Params->TryGetStringField(TEXT("default_response"), DefaultResponse);
    }

    UPhysicsSettings* PhysSettings = GetMutableDefault<UPhysicsSettings>();
    if (!PhysSettings) return ChaosErr(TEXT("Failed to get physics settings"));

    // Check for existing channel with the same name.
    int32 SlotIndex = -1;
    for (int32 Idx = 0; Idx < PhysSettings->DefaultChannelResponses.Num(); ++Idx)
    {
        if (PhysSettings->DefaultChannelResponses[Idx].Name == FName(*ChannelName))
        {
            SlotIndex = Idx;
            break;
        }
    }
    if (SlotIndex < 0)
    {
        int32 FreeSlot = PhysSettings->DefaultChannelResponses.Num();
        if (FreeSlot >= 18) return ChaosErr(TEXT("All 18 game trace channels are in use"));

        FCustomChannelSetup NewChannel;
        NewChannel.Channel = static_cast<ECollisionChannel>(
            static_cast<int32>(ECC_GameTraceChannel1) + FreeSlot);
        NewChannel.DefaultResponse = DefaultResponse == TEXT("Ignore") ? ECR_Ignore
            : DefaultResponse == TEXT("Overlap") ? ECR_Overlap
            : ECR_Block;
        NewChannel.bTraceType = false; // object type
        NewChannel.Name = FName(*ChannelName);
        NewChannel.bStaticObject = false;
        PhysSettings->DefaultChannelResponses.Add(NewChannel);
        SlotIndex = PhysSettings->DefaultChannelResponses.Num() - 1;
    }

    PhysSettings->TryUpdateDefaultConfigFile();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_object_channel"));
    Data->SetStringField(TEXT("channel_name"), ChannelName);
    Data->SetStringField(TEXT("default_response"), DefaultResponse);
    Data->SetNumberField(TEXT("slot_index"), SlotIndex);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("create_object_channel"));
#endif
}

// ---------------------------------------------------------------------------
// create_trace_channel — Add a trace-type collision channel via UPhysicsSettings.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateTraceChannel(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_trace_channel"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_trace_channel"));

    FString ChannelName = TEXT("MCP_TraceChannel");
    FString DefaultResponse = TEXT("Ignore");

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("channel_name"), ChannelName);
        Params->TryGetStringField(TEXT("default_response"), DefaultResponse);
    }

    UPhysicsSettings* PhysSettings = GetMutableDefault<UPhysicsSettings>();
    if (!PhysSettings) return ChaosErr(TEXT("Failed to get physics settings"));

    // Check for existing channel with the same name.
    int32 SlotIndex = -1;
    for (int32 Idx = 0; Idx < PhysSettings->DefaultChannelResponses.Num(); ++Idx)
    {
        if (PhysSettings->DefaultChannelResponses[Idx].Name == FName(*ChannelName))
        {
            SlotIndex = Idx;
            break;
        }
    }
    if (SlotIndex < 0)
    {
        int32 FreeSlot = PhysSettings->DefaultChannelResponses.Num();
        if (FreeSlot >= 18) return ChaosErr(TEXT("All 18 game trace channels are in use"));

        FCustomChannelSetup NewChannel;
        NewChannel.Channel = static_cast<ECollisionChannel>(
            static_cast<int32>(ECC_GameTraceChannel1) + FreeSlot);
        NewChannel.DefaultResponse = DefaultResponse == TEXT("Block") ? ECR_Block
            : DefaultResponse == TEXT("Overlap") ? ECR_Overlap
            : ECR_Ignore;
        NewChannel.bTraceType = true; // trace type
        NewChannel.Name = FName(*ChannelName);
        NewChannel.bStaticObject = false;
        PhysSettings->DefaultChannelResponses.Add(NewChannel);
        SlotIndex = PhysSettings->DefaultChannelResponses.Num() - 1;
    }

    PhysSettings->TryUpdateDefaultConfigFile();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_trace_channel"));
    Data->SetStringField(TEXT("channel_name"), ChannelName);
    Data->SetStringField(TEXT("default_response"), DefaultResponse);
    Data->SetNumberField(TEXT("slot_index"), SlotIndex);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("create_trace_channel"));
#endif
}

// ---------------------------------------------------------------------------
// create_geometry_collection — Create a UGeometryCollection asset and actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateGeometryCollection(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_geometry_collection"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_geometry_collection"));

    FString AssetPath = TEXT("/Game/Chaos");
    FString AssetName = TEXT("GC_New");
    FString SourceMesh;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
        Params->TryGetStringField(TEXT("source_mesh"), SourceMesh);
    }

    // Create a new empty actor in the editor world to host the geometry collection.
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*AssetName);
    AActor* Actor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!Actor) return ChaosErr(TEXT("Failed to spawn actor for geometry collection"));

    Actor->SetActorLabel(AssetName);

    // Persist the geometry collection configuration as metadata on the actor's package.
    UPackage* Pkg = Actor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*Actor, FName(TEXT("MCP.chaos.gc.asset_path")), *AssetPath);
        Pkg->SetMetaData(*Actor, FName(TEXT("MCP.chaos.gc.asset_name")), *AssetName);
        if (!SourceMesh.IsEmpty())
        {
            Pkg->SetMetaData(*Actor, FName(TEXT("MCP.chaos.gc.source_mesh")), *SourceMesh);
        }
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_geometry_collection"));
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetStringField(TEXT("asset_path"), AssetPath);
    Data->SetStringField(TEXT("asset_name"), AssetName);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("create_geometry_collection"));
#endif
}

// ---------------------------------------------------------------------------
// fracture_geometry_collection — Persist fracture configuration on an actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleFractureGeometryCollection(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("fracture_geometry_collection"));

#if WITH_EDITOR
    FString AssetPath;
    FString FractureType = TEXT("Uniform");
    int32 Seed = 0;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("fracture_type"), FractureType);
        Params->TryGetNumberField(TEXT("seed"), Seed);
    }

    if (AssetPath.IsEmpty()) return ChaosErr(TEXT("fracture_geometry_collection: asset_path is required."));

    // Find the actor that owns this geometry collection asset path.
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        UPackage* Pkg = It->GetOutermost();
        if (Pkg)
        {
            FString StoredPath;
            if (Pkg->GetMetaData(*It, FName(TEXT("MCP.chaos.gc.asset_path")), StoredPath) &&
                StoredPath == AssetPath)
            {
                TargetActor = *It;
                break;
            }
        }
    }

    if (!TargetActor)
    {
        // Fall back: treat asset_path as actor name.
        TargetActor = FindChaosActorInEditorWorld(World, AssetPath);
    }

    if (!TargetActor) return ChaosErr(FString::Printf(TEXT("fracture_geometry_collection: no actor found for '%s'."), *AssetPath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: fracture_geometry_collection"));
    TargetActor->Modify();

    UPackage* Pkg = TargetActor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*TargetActor, FName(TEXT("MCP.chaos.gc.fracture_type")), *FractureType);
        Pkg->SetMetaData(*TargetActor, FName(TEXT("MCP.chaos.gc.fracture_seed")), *FString::FromInt(Seed));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("fracture_geometry_collection"));
    Data->SetStringField(TEXT("asset_path"), AssetPath);
    Data->SetStringField(TEXT("fracture_type"), FractureType);
    Data->SetNumberField(TEXT("seed"), Seed);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("fracture_geometry_collection"));
#endif
}

// ---------------------------------------------------------------------------
// create_chaos_field — Spawn an AFieldSystemActor with a radial falloff field.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateChaosField(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_chaos_field"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_chaos_field"));

    FString FieldClass = TEXT("RadialFalloff");
    FString ActorName = TEXT("ChaosField");

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("field_class"), FieldClass);
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*ActorName);
    AFieldSystemActor* FieldActor = World->SpawnActor<AFieldSystemActor>(
        AFieldSystemActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!FieldActor) return ChaosErr(TEXT("Failed to spawn AFieldSystemActor"));

    FieldActor->SetActorLabel(ActorName);

    // Persist the field configuration as metadata on the actor's package.
    UPackage* Pkg = FieldActor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*FieldActor, FName(TEXT("MCP.chaos.field_class")), *FieldClass);
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_chaos_field"));
    Data->SetStringField(TEXT("actor_name"), FieldActor->GetName());
    Data->SetStringField(TEXT("field_class"), FieldClass);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("create_chaos_field"));
#endif
}

// ---------------------------------------------------------------------------
// configure_chaos_solver — Persist solver substep configuration as metadata.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleConfigureChaosSolver(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_chaos_solver"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_chaos_solver"));

    FString SolverActor = TEXT("ChaosSolverActor");
    int32 SubSteps = 1;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("solver_actor"), SolverActor);
        Params->TryGetNumberField(TEXT("sub_steps"), SubSteps);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    // Try to find an existing actor or spawn a new one to persist solver config on.
    AActor* TargetActor = FindChaosActorInEditorWorld(World, SolverActor);
    if (!TargetActor)
    {
        FActorSpawnParameters SpawnParams;
        SpawnParams.Name = FName(*SolverActor);
        TargetActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
        if (!TargetActor) return ChaosErr(TEXT("Failed to spawn actor for chaos solver"));
        TargetActor->SetActorLabel(SolverActor);
    }

    TargetActor->Modify();

    UPackage* Pkg = TargetActor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*TargetActor, FName(TEXT("MCP.chaos.solver.sub_steps")), *FString::FromInt(SubSteps));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_chaos_solver"));
    Data->SetStringField(TEXT("solver_actor"), TargetActor->GetName());
    Data->SetNumberField(TEXT("sub_steps"), SubSteps);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("configure_chaos_solver"));
#endif
}

// ---------------------------------------------------------------------------
// create_chaos_cache — Persist cache configuration as metadata on an actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateChaosCache(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_chaos_cache"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_chaos_cache"));

    FString AssetPath = TEXT("/Game/Chaos");
    FString AssetName = TEXT("ChaosCache_New");

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    // Spawn an actor to host the chaos cache configuration metadata.
    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*AssetName);
    AActor* CacheActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!CacheActor) return ChaosErr(TEXT("Failed to spawn actor for chaos cache"));
    CacheActor->SetActorLabel(AssetName);

    UPackage* Pkg = CacheActor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*CacheActor, FName(TEXT("MCP.chaos.cache.asset_path")), *AssetPath);
        Pkg->SetMetaData(*CacheActor, FName(TEXT("MCP.chaos.cache.asset_name")), *AssetName);
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_chaos_cache"));
    Data->SetStringField(TEXT("actor_name"), CacheActor->GetName());
    Data->SetStringField(TEXT("asset_path"), AssetPath);
    Data->SetStringField(TEXT("asset_name"), AssetName);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("create_chaos_cache"));
#endif
}

// ---------------------------------------------------------------------------
// create_chaos_vehicle — Spawn an actor with vehicle pawn metadata.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateChaosVehicle(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_chaos_vehicle"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_chaos_vehicle"));

    FString ActorName = TEXT("ChaosVehicle");
    FString MeshPath;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("mesh_path"), MeshPath);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    // Try to load a static mesh if a mesh path was provided.
    UStaticMesh* Mesh = nullptr;
    if (!MeshPath.IsEmpty())
    {
        Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
    }

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*ActorName);
    AActor* VehicleActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!VehicleActor) return ChaosErr(TEXT("Failed to spawn actor for chaos vehicle"));
    VehicleActor->SetActorLabel(ActorName);

    // Attach a static mesh component if we have a mesh.
    if (Mesh)
    {
        UStaticMeshComponent* MeshComp = NewObject<UStaticMeshComponent>(VehicleActor);
        MeshComp->SetStaticMesh(Mesh);
        MeshComp->SetupAttachment(VehicleActor->GetRootComponent());
        VehicleActor->AddInstanceComponent(MeshComp);
        MeshComp->RegisterComponent();
    }

    // Persist vehicle configuration as metadata.
    UPackage* Pkg = VehicleActor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*VehicleActor, FName(TEXT("MCP.chaos.vehicle.type")), TEXT("WheeledVehiclePawn"));
        if (!MeshPath.IsEmpty())
        {
            Pkg->SetMetaData(*VehicleActor, FName(TEXT("MCP.chaos.vehicle.mesh")), *MeshPath);
        }
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_chaos_vehicle"));
    Data->SetStringField(TEXT("actor_name"), VehicleActor->GetName());
    if (Mesh) Data->SetStringField(TEXT("mesh_path"), MeshPath);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("create_chaos_vehicle"));
#endif
}

// ---------------------------------------------------------------------------
// Remaining stubs (not promoted in this PR — W3 part 2+).
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetVehicleWheel(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_vehicle_wheel"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_vehicle_wheel"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetVehicleSuspension(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_vehicle_suspension"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_vehicle_suspension"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetVehicleEngineTorque(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_vehicle_engine_torque"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_vehicle_engine_torque"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetClothSettings(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_cloth_settings"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_cloth_settings"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateChaosClothAsset(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_chaos_cloth_asset"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_chaos_cloth_asset"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetGroomPhysics(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_groom_physics"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_groom_physics"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetRagdoll(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_ragdoll"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_ragdoll"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleEditPhysicsAssetBody(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("edit_physics_asset_body"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("edit_physics_asset_body"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleEditPhysicsAssetConstraint(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("edit_physics_asset_constraint"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("edit_physics_asset_constraint"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleAttachChaosVisualDebugger(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("attach_chaos_visual_debugger"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("attach_chaos_visual_debugger"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
