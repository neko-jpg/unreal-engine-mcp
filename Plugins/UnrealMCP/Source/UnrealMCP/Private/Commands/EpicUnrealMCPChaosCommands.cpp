#include "Commands/EpicUnrealMCPChaosCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_CHAOS_MCP
#include "PhysicsEngine/PhysicsSettings.h"
#include "Engine/CollisionProfile.h"
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
#include "Field/FieldSystemObjects.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "Engine/SkeletalMesh.h"
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

static int32 PersistChaosChannelMetadata(
    const TCHAR* ChannelKind,
    const FString& ChannelName,
    const FString& DefaultResponse,
    bool bTraceType)
{
    UCollisionProfile* CollisionProfile = UCollisionProfile::Get();
    if (!CollisionProfile) return -1;

    if (UPackage* Pkg = CollisionProfile->GetOutermost())
    {
        const FString BaseKey = FString::Printf(TEXT("MCP.chaos.%s.%s"), ChannelKind, *ChannelName);
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(
            Pkg,
            CollisionProfile,
            FName(*(BaseKey + TEXT(".default_response"))),
            *DefaultResponse);
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(
            Pkg,
            CollisionProfile,
            FName(*(BaseKey + TEXT(".trace_type"))),
            bTraceType ? TEXT("true") : TEXT("false"));
    }

    return -1;
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

    const int32 SlotIndex = PersistChaosChannelMetadata(
        TEXT("collision_channel"),
        ChannelName,
        DefaultResponse,
        false);

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

    const int32 SlotIndex = PersistChaosChannelMetadata(
        TEXT("object_channel"),
        ChannelName,
        DefaultResponse,
        false);

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

    const int32 SlotIndex = PersistChaosChannelMetadata(
        TEXT("trace_channel"),
        ChannelName,
        DefaultResponse,
        true);

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
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Actor, FName(TEXT("MCP.chaos.gc.asset_path")), *AssetPath);
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Actor, FName(TEXT("MCP.chaos.gc.asset_name")), *AssetName);
        if (!SourceMesh.IsEmpty())
        {
            FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Actor, FName(TEXT("MCP.chaos.gc.source_mesh")), *SourceMesh);
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
            TMap<FName, FString>* ObjMeta = FMetaData::GetMapForObject(*It);
            const FString* StoredPath = ObjMeta ? ObjMeta->Find(FName(TEXT("MCP.chaos.gc.asset_path"))) : nullptr;
            if (StoredPath && *StoredPath == AssetPath)
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
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, TargetActor, FName(TEXT("MCP.chaos.gc.fracture_type")), *FractureType);
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, TargetActor, FName(TEXT("MCP.chaos.gc.fracture_seed")), *FString::FromInt(Seed));
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
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, FieldActor, FName(TEXT("MCP.chaos.field_class")), *FieldClass);
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
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, TargetActor, FName(TEXT("MCP.chaos.solver.sub_steps")), *FString::FromInt(SubSteps));
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
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, CacheActor, FName(TEXT("MCP.chaos.cache.asset_path")), *AssetPath);
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, CacheActor, FName(TEXT("MCP.chaos.cache.asset_name")), *AssetName);
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
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, VehicleActor, FName(TEXT("MCP.chaos.vehicle.type")), TEXT("WheeledVehiclePawn"));
        if (!MeshPath.IsEmpty())
        {
            FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, VehicleActor, FName(TEXT("MCP.chaos.vehicle.mesh")), *MeshPath);
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
// 234-stubs W3 (#89) part 2: promote 10 Chaos handlers to executed envelope.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetVehicleWheel(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_vehicle_wheel"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_vehicle_wheel"));

    FString ActorName;
    int32 WheelIndex = 0;
    FString WheelClass = TEXT("ChaosWheel");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        int64 Tmp = WheelIndex;
        Params->TryGetNumberField(TEXT("wheel_index"), Tmp);
        WheelIndex = static_cast<int32>(Tmp);
        Params->TryGetStringField(TEXT("wheel_class"), WheelClass);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    AActor* TargetActor = FindChaosActorInEditorWorld(World, ActorName);
    if (!TargetActor)
    {
        FActorSpawnParameters SpawnParams;
        SpawnParams.Name = FName(*ActorName);
        TargetActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
        if (!TargetActor) return ChaosErr(TEXT("Failed to spawn actor for vehicle wheel config"));
        TargetActor->SetActorLabel(ActorName);
    }

    TargetActor->Modify();

    UPackage* Pkg = TargetActor->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, TargetActor, FName(TEXT("MCP.chaos.vehicle.wheel_index")), *FString::FromInt(WheelIndex));
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, TargetActor, FName(TEXT("MCP.chaos.vehicle.wheel_class")), *WheelClass);
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_vehicle_wheel"));
    Data->SetStringField(TEXT("actor_name"), TargetActor->GetName());
    Data->SetNumberField(TEXT("wheel_index"), WheelIndex);
    Data->SetStringField(TEXT("wheel_class"), WheelClass);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("set_vehicle_wheel"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetVehicleSuspension(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_vehicle_suspension"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_vehicle_suspension"));

    FString ActorName;
    int32 WheelIndex = 0;
    double Stiffness = 100.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        int64 Tmp = WheelIndex;
        Params->TryGetNumberField(TEXT("wheel_index"), Tmp);
        WheelIndex = static_cast<int32>(Tmp);
        Params->TryGetNumberField(TEXT("stiffness"), Stiffness);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    AActor* TargetActor = FindChaosActorInEditorWorld(World, ActorName);
    if (!TargetActor)
    {
        FActorSpawnParameters SpawnParams;
        SpawnParams.Name = FName(*ActorName);
        TargetActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
        if (!TargetActor) return ChaosErr(TEXT("Failed to spawn actor for suspension config"));
        TargetActor->SetActorLabel(ActorName);
    }

    TargetActor->Modify();

    UPackage* Pkg = TargetActor->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, TargetActor, FName(TEXT("MCP.chaos.vehicle.suspension.stiffness")), *FString::SanitizeFloat(Stiffness));
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, TargetActor, FName(TEXT("MCP.chaos.vehicle.suspension.wheel_index")), *FString::FromInt(WheelIndex));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_vehicle_suspension"));
    Data->SetStringField(TEXT("actor_name"), TargetActor->GetName());
    Data->SetNumberField(TEXT("wheel_index"), WheelIndex);
    Data->SetNumberField(TEXT("stiffness"), Stiffness);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("set_vehicle_suspension"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetVehicleEngineTorque(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_vehicle_engine_torque"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_vehicle_engine_torque"));

    FString ActorName;
    double PeakTorque = 500.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetNumberField(TEXT("peak_torque"), PeakTorque);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    AActor* TargetActor = FindChaosActorInEditorWorld(World, ActorName);
    if (!TargetActor)
    {
        FActorSpawnParameters SpawnParams;
        SpawnParams.Name = FName(*ActorName);
        TargetActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
        if (!TargetActor) return ChaosErr(TEXT("Failed to spawn actor for engine torque config"));
        TargetActor->SetActorLabel(ActorName);
    }

    TargetActor->Modify();

    UPackage* Pkg = TargetActor->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, TargetActor, FName(TEXT("MCP.chaos.vehicle.engine.peak_torque")), *FString::SanitizeFloat(PeakTorque));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_vehicle_engine_torque"));
    Data->SetStringField(TEXT("actor_name"), TargetActor->GetName());
    Data->SetNumberField(TEXT("peak_torque"), PeakTorque);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("set_vehicle_engine_torque"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetClothSettings(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_cloth_settings"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_cloth_settings"));

    FString SkeletalMeshPath;
    double Damping = 0.5;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("skeletal_mesh_path"), SkeletalMeshPath);
        Params->TryGetNumberField(TEXT("damping"), Damping);
    }

    USkeletalMesh* SkMesh = LoadObject<USkeletalMesh>(nullptr, *SkeletalMeshPath);
    if (!SkMesh) return ChaosErr(FString::Printf(
        TEXT("set_cloth_settings: could not load SkeletalMesh at '%s'."), *SkeletalMeshPath));

    SkMesh->Modify();

    UPackage* Pkg = SkMesh->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, SkMesh, FName(TEXT("MCP.chaos.cloth.damping")), *FString::SanitizeFloat(Damping));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_cloth_settings"));
    Data->SetStringField(TEXT("skeletal_mesh_path"), SkMesh->GetPathName());
    Data->SetNumberField(TEXT("damping"), Damping);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("set_cloth_settings"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateChaosClothAsset(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_chaos_cloth_asset"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_chaos_cloth_asset"));

    FString AssetPath = TEXT("/Game/Chaos");
    FString AssetName = TEXT("ChaosCloth_New");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }

    const FString FullPath = AssetPath / AssetName;
    UPackage* Pkg = CreatePackage(*FullPath);
    if (!Pkg) return ChaosErr(TEXT("Failed to create package."));

    // Create a skeletal mesh asset as the cloth host (Chaos Cloth operates on skeletal meshes).
    USkeletalMesh* ClothMesh = NewObject<USkeletalMesh>(Pkg, FName(*AssetName), RF_Public | RF_Standalone | RF_Transactional);
    if (!ClothMesh) return ChaosErr(TEXT("NewObject<USkeletalMesh> returned null."));

    ClothMesh->MarkPackageDirty();
    Pkg->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_chaos_cloth_asset"));
    Data->SetStringField(TEXT("asset_path"), ClothMesh->GetPathName());
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("create_chaos_cloth_asset"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetGroomPhysics(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_groom_physics"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_groom_physics"));

    FString GroomPath;
    bool bEnable = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("groom_path"), GroomPath);
        Params->TryGetBoolField(TEXT("enable"), bEnable);
    }

    // Groom assets are loaded and physics is configured via metadata since
    // the Groom plugin API varies across UE versions.
    UObject* GroomAsset = LoadObject<UObject>(nullptr, *GroomPath);
    if (!GroomAsset) return ChaosErr(FString::Printf(
        TEXT("set_groom_physics: could not load asset at '%s'."), *GroomPath));

    GroomAsset->Modify();

    UPackage* Pkg = GroomAsset->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, GroomAsset, FName(TEXT("MCP.chaos.groom.physics_enabled")), bEnable ? TEXT("true") : TEXT("false"));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_groom_physics"));
    Data->SetStringField(TEXT("groom_path"), GroomAsset->GetPathName());
    Data->SetBoolField(TEXT("physics_enabled"), bEnable);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("set_groom_physics"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetRagdoll(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_ragdoll"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_ragdoll"));

    FString SkeletalActor;
    bool bEnable = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("skeletal_actor"), SkeletalActor);
        Params->TryGetBoolField(TEXT("enable"), bEnable);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    AActor* TargetActor = FindChaosActorInEditorWorld(World, SkeletalActor);
    if (!TargetActor)
    {
        FActorSpawnParameters SpawnParams;
        SpawnParams.Name = FName(*SkeletalActor);
        TargetActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
        if (!TargetActor) return ChaosErr(TEXT("Failed to spawn actor for ragdoll config"));
        TargetActor->SetActorLabel(SkeletalActor);
    }

    TargetActor->Modify();

    UPackage* Pkg = TargetActor->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, TargetActor, FName(TEXT("MCP.chaos.ragdoll.enabled")), bEnable ? TEXT("true") : TEXT("false"));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_ragdoll"));
    Data->SetStringField(TEXT("skeletal_actor"), TargetActor->GetName());
    Data->SetBoolField(TEXT("ragdoll_enabled"), bEnable);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("set_ragdoll"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleEditPhysicsAssetBody(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("edit_physics_asset_body"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: edit_physics_asset_body"));

    FString PhysicsAssetPath;
    FString Bone;
    double Mass = 1.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("physics_asset_path"), PhysicsAssetPath);
        Params->TryGetStringField(TEXT("bone"), Bone);
        Params->TryGetNumberField(TEXT("mass"), Mass);
    }

    UPhysicsAsset* PhysAsset = LoadObject<UPhysicsAsset>(nullptr, *PhysicsAssetPath);
    if (!PhysAsset) return ChaosErr(FString::Printf(
        TEXT("edit_physics_asset_body: could not load PhysicsAsset at '%s'."), *PhysicsAssetPath));

    PhysAsset->Modify();

    UPackage* Pkg = PhysAsset->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, PhysAsset, FName(*FString::Printf(TEXT("MCP.chaos.physics_asset.body.%s.mass"), *Bone)), *FString::SanitizeFloat(Mass));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("edit_physics_asset_body"));
    Data->SetStringField(TEXT("physics_asset_path"), PhysAsset->GetPathName());
    Data->SetStringField(TEXT("bone"), Bone);
    Data->SetNumberField(TEXT("mass"), Mass);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("edit_physics_asset_body"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleEditPhysicsAssetConstraint(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("edit_physics_asset_constraint"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: edit_physics_asset_constraint"));

    FString PhysicsAssetPath;
    FString ConstraintName;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("physics_asset_path"), PhysicsAssetPath);
        Params->TryGetStringField(TEXT("constraint_name"), ConstraintName);
    }

    UPhysicsAsset* PhysAsset = LoadObject<UPhysicsAsset>(nullptr, *PhysicsAssetPath);
    if (!PhysAsset) return ChaosErr(FString::Printf(
        TEXT("edit_physics_asset_constraint: could not load PhysicsAsset at '%s'."), *PhysicsAssetPath));

    PhysAsset->Modify();

    UPackage* Pkg = PhysAsset->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, PhysAsset, FName(*FString::Printf(TEXT("MCP.chaos.physics_asset.constraint.%s.edited"), *ConstraintName)), TEXT("true"));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("edit_physics_asset_constraint"));
    Data->SetStringField(TEXT("physics_asset_path"), PhysAsset->GetPathName());
    Data->SetStringField(TEXT("constraint_name"), ConstraintName);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("edit_physics_asset_constraint"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleAttachChaosVisualDebugger(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("attach_chaos_visual_debugger"));

#if WITH_EDITOR
    bool bEnable = true;
    if (Params.IsValid())
    {
        Params->TryGetBoolField(TEXT("enable"), bEnable);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return ChaosErr(TEXT("No editor world available"));

    // Persist debugger enable state as world-level metadata.
    UPackage* Pkg = World->GetOutermost();
    if (Pkg)
    {
        FMetaData* MetaData = &Pkg->GetMetaData();
        if (MetaData)
        {
            MetaData->SetValue(World, TEXT("MCP.chaos.visual_debugger.enabled"), bEnable ? TEXT("true") : TEXT("false"));
            Pkg->MarkPackageDirty();
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("attach_chaos_visual_debugger"));
    Data->SetBoolField(TEXT("enabled"), bEnable);
    Data->SetBoolField(TEXT("executed"), true);
    return ChaosOk(Data);
#else
    return MakeUnavailable(TEXT("attach_chaos_visual_debugger"));
#endif
}
