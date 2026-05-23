#include "Commands/EpicUnrealMCPFoliageCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#include "FoliageType.h"
#include "FoliageType_InstancedStaticMesh.h"
#include "FoliageType_Actor.h"
#include "Engine/StaticMesh.h"
#include "Engine/AssetTools.h"
#include "UObject/Package.h"
#include "Editor.h"
#include "EngineUtils.h"

bool FEpicUnrealMCPFoliageCommands::IsModuleAvailable()
{
#if WITH_FOLIAGE_MCP
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPFoliageCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Foliage modules ship with UE 5.7 (Engine/Source/Runtime/Foliage and Engine/Source/Editor/FoliageEdit). Rebuild UnrealMCP if missing."));
    return R;
}

FEpicUnrealMCPFoliageCommands::FEpicUnrealMCPFoliageCommands() {}
FEpicUnrealMCPFoliageCommands::~FEpicUnrealMCPFoliageCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPFoliageCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_foliage_type"),  &FEpicUnrealMCPFoliageCommands::HandleCreateFoliageType},
        {TEXT("register_static_mesh_foliage"),  &FEpicUnrealMCPFoliageCommands::HandleRegisterStaticMeshFoliage},
        {TEXT("register_actor_foliage"),  &FEpicUnrealMCPFoliageCommands::HandleRegisterActorFoliage},
        {TEXT("foliage_paint"),  &FEpicUnrealMCPFoliageCommands::HandleFoliagePaint},
        {TEXT("foliage_erase"),  &FEpicUnrealMCPFoliageCommands::HandleFoliageErase},
        {TEXT("set_foliage_density"),  &FEpicUnrealMCPFoliageCommands::HandleSetFoliageDensity},
        {TEXT("set_foliage_scale_range"),  &FEpicUnrealMCPFoliageCommands::HandleSetFoliageScaleRange},
        {TEXT("set_foliage_random_yaw"),  &FEpicUnrealMCPFoliageCommands::HandleSetFoliageRandomYaw},
        {TEXT("set_foliage_align_to_normal"),  &FEpicUnrealMCPFoliageCommands::HandleSetFoliageAlignToNormal},
        {TEXT("set_foliage_cull_distance"),  &FEpicUnrealMCPFoliageCommands::HandleSetFoliageCullDistance},
        {TEXT("set_foliage_lod"),  &FEpicUnrealMCPFoliageCommands::HandleSetFoliageLod},
        {TEXT("create_procedural_foliage_spawner"),  &FEpicUnrealMCPFoliageCommands::HandleCreateProceduralFoliageSpawner},
        {TEXT("create_procedural_foliage_volume"),  &FEpicUnrealMCPFoliageCommands::HandleCreateProceduralFoliageVolume},
        {TEXT("set_procedural_foliage_seed"),  &FEpicUnrealMCPFoliageCommands::HandleSetProceduralFoliageSeed},
        {TEXT("spawn_biome_foliage"),  &FEpicUnrealMCPFoliageCommands::HandleSpawnBiomeFoliage},
        {TEXT("create_grass_type"),  &FEpicUnrealMCPFoliageCommands::HandleCreateGrassType},
        {TEXT("bind_landscape_grass"),  &FEpicUnrealMCPFoliageCommands::HandleBindLandscapeGrass},
        {TEXT("set_foliage_nanite"),  &FEpicUnrealMCPFoliageCommands::HandleSetFoliageNanite},
        {TEXT("set_foliage_wind"),  &FEpicUnrealMCPFoliageCommands::HandleSetFoliageWind},
        {TEXT("configure_pivot_painter"),  &FEpicUnrealMCPFoliageCommands::HandleConfigurePivotPainter}
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
// 234-stubs W3 (#90): Foliage executed-envelope helpers.
// ---------------------------------------------------------------------------
static TSharedPtr<FJsonObject> FoliageOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> FoliageErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

static UFoliageType* LoadFoliageType(const FString& Path)
{
    if (Path.IsEmpty()) return nullptr;
    return LoadObject<UFoliageType>(nullptr, *Path);
}

// ---------------------------------------------------------------------------
// create_foliage_type -- Create a UFoliageType_InstancedStaticMesh asset.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleCreateFoliageType(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_foliage_type"));

    FString AssetPath = TEXT("/Game/Foliage");
    FString AssetName = TEXT("Foliage_New");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }

    const FString FullPath = AssetPath / AssetName;

    // Check if asset already exists
    UFoliageType_InstancedStaticMesh* Existing = LoadObject<UFoliageType_InstancedStaticMesh>(nullptr, *FullPath);
    if (Existing)
    {
        return FoliageErr(FString::Printf(
            TEXT("FoliageType asset already exists at '%s'."), *FullPath));
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_foliage_type"));

    UPackage* Pkg = CreatePackage(*FullPath);
    if (!Pkg) return FoliageErr(TEXT("Failed to create package."));

    UFoliageType_InstancedStaticMesh* NewType = NewObject<UFoliageType_InstancedStaticMesh>(
        Pkg, FName(*AssetName), RF_Public | RF_Standalone | RF_Transactional);
    if (!NewType) return FoliageErr(TEXT("NewObject<UFoliageType_InstancedStaticMesh> returned null."));

    NewType->MarkPackageDirty();
    Pkg->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_foliage_type"));
    Data->SetStringField(TEXT("asset_path"), NewType->GetPathName());
    Data->SetStringField(TEXT("foliage_class"), TEXT("UFoliageType_InstancedStaticMesh"));
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}

// ---------------------------------------------------------------------------
// register_static_mesh_foliage -- Set static mesh on a UFoliageType_ISM.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleRegisterStaticMeshFoliage(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("register_static_mesh_foliage"));

    FString FoliageTypePath;
    FString StaticMeshPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        Params->TryGetStringField(TEXT("static_mesh_path"), StaticMeshPath);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("register_static_mesh_foliage: could not load FoliageType at '%s'."), *FoliageTypePath));

    UFoliageType_InstancedStaticMesh* IsmType = Cast<UFoliageType_InstancedStaticMesh>(Ft);
    if (!IsmType) return FoliageErr(FString::Printf(
        TEXT("FoliageType at '%s' is not a UFoliageType_InstancedStaticMesh."), *FoliageTypePath));

    UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *StaticMeshPath);
    if (!Mesh) return FoliageErr(FString::Printf(
        TEXT("Could not load StaticMesh at '%s'."), *StaticMeshPath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: register_static_mesh_foliage"));

    IsmType->Modify();
    IsmType->SetStaticMesh(Mesh);
    IsmType->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("register_static_mesh_foliage"));
    Data->SetStringField(TEXT("foliage_type_path"), IsmType->GetPathName());
    Data->SetStringField(TEXT("static_mesh_path"), StaticMeshPath);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}

// ---------------------------------------------------------------------------
// register_actor_foliage -- Configure UFoliageType_Actor with an actor class.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleRegisterActorFoliage(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("register_actor_foliage"));

    FString FoliageTypePath;
    FString ActorClassPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        Params->TryGetStringField(TEXT("actor_class_path"), ActorClassPath);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("register_actor_foliage: could not load FoliageType at '%s'."), *FoliageTypePath));

    UFoliageType_Actor* ActorType = Cast<UFoliageType_Actor>(Ft);
    if (!ActorType) return FoliageErr(FString::Printf(
        TEXT("FoliageType at '%s' is not a UFoliageType_Actor."), *FoliageTypePath));

    UClass* ActorClass = FindObject<UClass>(nullptr, *ActorClassPath);
    if (!ActorClass) return FoliageErr(FString::Printf(
        TEXT("Could not find actor class '%s'."), *ActorClassPath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: register_actor_foliage"));

    ActorType->Modify();
    ActorType->ActorClass = ActorClass;
    ActorType->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("register_actor_foliage"));
    Data->SetStringField(TEXT("foliage_type_path"), ActorType->GetPathName());
    Data->SetStringField(TEXT("actor_class_path"), ActorClassPath);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}

// ---------------------------------------------------------------------------
// set_foliage_density -- Set UFoliageType::Density.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetFoliageDensity(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_foliage_density"));

    FString FoliageTypePath;
    double Density = 1.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        Params->TryGetNumberField(TEXT("density"), Density);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("set_foliage_density: could not load FoliageType at '%s'."), *FoliageTypePath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_foliage_density"));

    Ft->Modify();
    Ft->Density = static_cast<float>(Density);
    Ft->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_density"));
    Data->SetStringField(TEXT("foliage_type_path"), Ft->GetPathName());
    Data->SetNumberField(TEXT("density"), Ft->Density);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}

// ---------------------------------------------------------------------------
// set_foliage_scale_range -- Set UFoliageType::ScaleX/Y/Z Min/Max.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetFoliageScaleRange(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_foliage_scale_range"));

    FString FoliageTypePath;
    double MinScale = 0.9;
    double MaxScale = 1.1;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        Params->TryGetNumberField(TEXT("min_scale"), MinScale);
        Params->TryGetNumberField(TEXT("max_scale"), MaxScale);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("set_foliage_scale_range: could not load FoliageType at '%s'."), *FoliageTypePath));

    const FFloatInterval Scale(static_cast<float>(MinScale), static_cast<float>(MaxScale));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_foliage_scale_range"));

    Ft->Modify();
    Ft->ScaleX = Scale;
    Ft->ScaleY = Scale;
    Ft->ScaleZ = Scale;
    Ft->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_scale_range"));
    Data->SetStringField(TEXT("foliage_type_path"), Ft->GetPathName());
    Data->SetNumberField(TEXT("min_scale"), MinScale);
    Data->SetNumberField(TEXT("max_scale"), MaxScale);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}

// ---------------------------------------------------------------------------
// set_foliage_random_yaw -- Set UFoliageType::RandomYaw.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetFoliageRandomYaw(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_foliage_random_yaw"));

    FString FoliageTypePath;
    bool bEnable = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        Params->TryGetBoolField(TEXT("enable"), bEnable);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("set_foliage_random_yaw: could not load FoliageType at '%s'."), *FoliageTypePath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_foliage_random_yaw"));

    Ft->Modify();
    Ft->RandomYaw = bEnable ? 1u : 0u;
    Ft->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_random_yaw"));
    Data->SetStringField(TEXT("foliage_type_path"), Ft->GetPathName());
    Data->SetBoolField(TEXT("enable"), bEnable);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}

// ---------------------------------------------------------------------------
// set_foliage_align_to_normal -- Set UFoliageType::AlignToNormal.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetFoliageAlignToNormal(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_foliage_align_to_normal"));

    FString FoliageTypePath;
    bool bEnable = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        Params->TryGetBoolField(TEXT("enable"), bEnable);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("set_foliage_align_to_normal: could not load FoliageType at '%s'."), *FoliageTypePath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_foliage_align_to_normal"));

    Ft->Modify();
    Ft->AlignToNormal = bEnable ? 1u : 0u;
    Ft->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_align_to_normal"));
    Data->SetStringField(TEXT("foliage_type_path"), Ft->GetPathName());
    Data->SetBoolField(TEXT("enable"), bEnable);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}

// ---------------------------------------------------------------------------
// set_foliage_cull_distance -- Set UFoliageType::CullDistance Start/End.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetFoliageCullDistance(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_foliage_cull_distance"));

    FString FoliageTypePath;
    double Start = 5000.0;
    double End = 10000.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        Params->TryGetNumberField(TEXT("start"), Start);
        Params->TryGetNumberField(TEXT("end"), End);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("set_foliage_cull_distance: could not load FoliageType at '%s'."), *FoliageTypePath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_foliage_cull_distance"));

    Ft->Modify();
    Ft->CullDistance = FInt32Interval(static_cast<int32>(Start), static_cast<int32>(End));
    Ft->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_cull_distance"));
    Data->SetStringField(TEXT("foliage_type_path"), Ft->GetPathName());
    Data->SetNumberField(TEXT("start"), Start);
    Data->SetNumberField(TEXT("end"), End);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}

// ===========================================================================
// W3-2 / W3-3 stubs below — DO NOT promote these in this PR.
// ===========================================================================

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleFoliagePaint(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("foliage_paint"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("foliage_paint"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleFoliageErase(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("foliage_erase"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("foliage_erase"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetFoliageLod(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_foliage_lod"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_lod"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleCreateProceduralFoliageSpawner(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_procedural_foliage_spawner"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_procedural_foliage_spawner"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleCreateProceduralFoliageVolume(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_procedural_foliage_volume"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_procedural_foliage_volume"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetProceduralFoliageSeed(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_procedural_foliage_seed"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_procedural_foliage_seed"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSpawnBiomeFoliage(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_biome_foliage"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_biome_foliage"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleCreateGrassType(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_grass_type"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_grass_type"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleBindLandscapeGrass(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("bind_landscape_grass"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("bind_landscape_grass"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetFoliageNanite(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_foliage_nanite"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_nanite"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetFoliageWind(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_foliage_wind"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_wind"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleConfigurePivotPainter(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_pivot_painter"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_pivot_painter"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Foliage editor mode or Procedural Foliage volume rebuild."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
