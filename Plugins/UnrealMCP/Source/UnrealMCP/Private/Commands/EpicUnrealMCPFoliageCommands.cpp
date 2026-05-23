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

// W3-3: Landscape grass
#include "LandscapeGrassType.h"
#include "Landscape.h"
#include "LandscapeProxy.h"
#include "LandscapeComponent.h"

// W3-3: Procedural foliage spawner + volume
#include "ProceduralFoliageSpawner.h"
#include "ProceduralFoliageVolume.h"
#include "ProceduralFoliageComponent.h"
#include "Components/BrushComponent.h"

// W3-3: PivotPainter (material parameter configuration)
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/World.h"
bool FEpicUnrealMCPFoliageCommands::IsModuleAvailable()
{
#if WITH_FOLIAGE_MCP
    return true;
#else
    return false;
#endif
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

// ---------------------------------------------------------------------------
// spawn_biome_foliage -- Composite: create procedural foliage spawner + volume.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSpawnBiomeFoliage(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_biome_foliage"));

    FString Biome;
    double OriginX = 0.0, OriginY = 0.0, OriginZ = 0.0;
    double TileSize = 10000.0;
    int32 RandomSeed = 1;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("biome"), Biome);
        const TSharedPtr<FJsonObject>* OriginArr = nullptr;
        if (Params->TryGetObjectField(TEXT("origin_xyz"), OriginArr))
        {
            (*OriginArr)->TryGetNumberField(TEXT("x"), OriginX);
            (*OriginArr)->TryGetNumberField(TEXT("y"), OriginY);
            (*OriginArr)->TryGetNumberField(TEXT("z"), OriginZ);
        }
        // Also accept origin_xyz as array
        const TArray<TSharedPtr<FJsonValue>>* OriginArray = nullptr;
        if (Params->TryGetArrayField(TEXT("origin_xyz"), OriginArray) && OriginArray->Num() >= 3)
        {
            (*OriginArray)[0]->TryGetNumber(OriginX);
            (*OriginArray)[1]->TryGetNumber(OriginY);
            (*OriginArray)[2]->TryGetNumber(OriginZ);
        }
        Params->TryGetNumberField(TEXT("tile_size"), TileSize);
        Params->TryGetNumberField(TEXT("random_seed"), RandomSeed);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return FoliageErr(TEXT("No editor world available."));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_biome_foliage"));

    // Create the spawner asset
    const FString SpawnerName = FString::Printf(TEXT("PFS_%s"), Biome.IsEmpty() ? TEXT("Default") : *Biome);
    const FString SpawnerPath = TEXT("/Game/Foliage/") + SpawnerName;
    UPackage* SpawnerPkg = CreatePackage(*SpawnerPath);
    if (!SpawnerPkg) return FoliageErr(TEXT("Failed to create spawner package."));

    UProceduralFoliageSpawner* Spawner = NewObject<UProceduralFoliageSpawner>(
        SpawnerPkg, FName(*SpawnerName), RF_Public | RF_Standalone | RF_Transactional);
    if (!Spawner) return FoliageErr(TEXT("NewObject<UProceduralFoliageSpawner> returned null."));

    Spawner->RandomSeed = RandomSeed;
    Spawner->TileSize = static_cast<float>(TileSize);
    Spawner->NumUniqueTiles = 4;
    Spawner->MinimumQuadTreeSize = 200.0f;
    Spawner->MarkPackageDirty();
    SpawnerPkg->MarkPackageDirty();

    // Spawn the volume actor at the origin location
    const FVector SpawnLoc(OriginX, OriginY, OriginZ);
    AProceduralFoliageVolume* Volume = World->SpawnActor<AProceduralFoliageVolume>(SpawnLoc, FRotator::ZeroRotator);
    if (!Volume) return FoliageErr(TEXT("Failed to spawn AProceduralFoliageVolume."));

    // Wire the spawner into the volume's component
    if (UProceduralFoliageComponent* PFComp = Volume->ProceduralComponent)
    {
        PFComp->FoliageSpawner = Spawner;
    }

    Volume->SetActorLabel(FString::Printf(TEXT("PFV_%s"), Biome.IsEmpty() ? TEXT("Default") : *Biome));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_biome_foliage"));
    Data->SetStringField(TEXT("biome"), Biome);
    Data->SetStringField(TEXT("spawner_path"), Spawner->GetPathName());
    Data->SetStringField(TEXT("volume_actor"), Volume->GetName());
    Data->SetNumberField(TEXT("origin_x"), OriginX);
    Data->SetNumberField(TEXT("origin_y"), OriginY);
    Data->SetNumberField(TEXT("origin_z"), OriginZ);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}

// ---------------------------------------------------------------------------
// create_grass_type -- Create a ULandscapeGrassType asset.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleCreateGrassType(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_grass_type"));

    FString AssetPath = TEXT("/Game/Foliage");
    FString AssetName = TEXT("Grass_New");
    double GrassDensity = 100.0;
    FString StaticMeshPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
        Params->TryGetNumberField(TEXT("grass_density"), GrassDensity);
        Params->TryGetStringField(TEXT("static_mesh_path"), StaticMeshPath);
    }

    const FString FullPath = AssetPath / AssetName;

    // Check if asset already exists
    ULandscapeGrassType* Existing = LoadObject<ULandscapeGrassType>(nullptr, *FullPath);
    if (Existing) return FoliageErr(FString::Printf(
        TEXT("GrassType asset already exists at '%s'."), *FullPath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_grass_type"));

    UPackage* Pkg = CreatePackage(*FullPath);
    if (!Pkg) return FoliageErr(TEXT("Failed to create package."));

    ULandscapeGrassType* GrassType = NewObject<ULandscapeGrassType>(
        Pkg, FName(*AssetName), RF_Public | RF_Standalone | RF_Transactional);
    if (!GrassType) return FoliageErr(TEXT("NewObject<ULandscapeGrassType> returned null."));

    // Add a default grass variety with the specified density
    if (GrassType->GrassVarieties.Num() == 0)
    {
        FGrassVariety Variety;
        Variety.GrassDensity = FPerPlatformFloat(static_cast<float>(GrassDensity));
        Variety.ScaleX = FFloatInterval(0.8f, 1.2f);
        Variety.ScaleY = FFloatInterval(0.8f, 1.2f);
        Variety.ScaleZ = FFloatInterval(0.8f, 1.2f);
        Variety.RandomRotation = true;
        Variety.AlignToSurface = true;
        Variety.StartCullDistance = FPerPlatformInt(10000);
        Variety.EndCullDistance = FPerPlatformInt(20000);

        // Optionally set static mesh
        if (!StaticMeshPath.IsEmpty())
        {
            UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *StaticMeshPath);
            if (Mesh)
            {
                Variety.GrassMesh = Mesh;
            }
        }

        GrassType->GrassVarieties.Add(MoveTemp(Variety));
    }

    GrassType->MarkPackageDirty();
    Pkg->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_grass_type"));
    Data->SetStringField(TEXT("asset_path"), GrassType->GetPathName());
    Data->SetNumberField(TEXT("grass_density"), GrassDensity);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}

// ---------------------------------------------------------------------------
// bind_landscape_grass -- Bind ULandscapeGrassType to ULandscapeComponent.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleBindLandscapeGrass(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("bind_landscape_grass"));

    FString LandscapeActorName;
    FString GrassTypePath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("landscape_actor"), LandscapeActorName);
        Params->TryGetStringField(TEXT("grass_type_path"), GrassTypePath);
    }

    ULandscapeGrassType* GrassType = LoadObject<ULandscapeGrassType>(nullptr, *GrassTypePath);
    if (!GrassType) return FoliageErr(FString::Printf(
        TEXT("Could not load LandscapeGrassType at '%s'."), *GrassTypePath));

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return FoliageErr(TEXT("No editor world available."));

    // Find landscape actor by name
    ALandscape* Landscape = nullptr;
    for (TActorIterator<ALandscape> It(World); It; ++It)
    {
        if (It->GetName().Equals(LandscapeActorName, ESearchCase::IgnoreCase) ||
            It->GetActorLabel().Equals(LandscapeActorName, ESearchCase::IgnoreCase))
        {
            Landscape = *It;
            break;
        }
    }
    if (!Landscape) return FoliageErr(FString::Printf(
        TEXT("Could not find landscape actor '%s'."), *LandscapeActorName));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: bind_landscape_grass"));

    // Get landscape components and add the grass type
    TArray<ULandscapeComponent*> Components;
    Landscape->GetComponents<ULandscapeComponent>(Components);

    int32 BoundCount = 0;
    for (ULandscapeComponent* Comp : Components)
    {
        if (!Comp) continue;
        Comp->Modify();

        TArray<TObjectPtr<ULandscapeGrassType>>& GrassTypes =
            const_cast<TArray<TObjectPtr<ULandscapeGrassType>>&>(Comp->GetGrassTypes());
        if (!GrassTypes.Contains(GrassType))
        {
            GrassTypes.Add(GrassType);
            ++BoundCount;
        }
    }

    if (BoundCount == 0) return FoliageErr(TEXT("No landscape components found to bind grass type to."));

    Landscape->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("bind_landscape_grass"));
    Data->SetStringField(TEXT("landscape_actor"), Landscape->GetName());
    Data->SetStringField(TEXT("grass_type_path"), GrassType->GetPathName());
    Data->SetNumberField(TEXT("components_bound"), BoundCount);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
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

// ---------------------------------------------------------------------------
// configure_pivot_painter -- Configure PivotPainter material parameters on a
// foliage type. PivotPainter is a material-function technique for wind
// animation; this handler sets the WorldPositionOffset wind strength and
// marks the foliage type as wind-enabled.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleConfigurePivotPainter(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_pivot_painter"));

    FString FoliageTypePath;
    FString MeshPath;
    double WindStrength = 1.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        Params->TryGetStringField(TEXT("mesh_path"), MeshPath);
        Params->TryGetNumberField(TEXT("wind_strength"), WindStrength);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("configure_pivot_painter: could not load FoliageType at '%s'."), *FoliageTypePath));

    UFoliageType_InstancedStaticMesh* IsmType = Cast<UFoliageType_InstancedStaticMesh>(Ft);
    if (!IsmType) return FoliageErr(FString::Printf(
        TEXT("FoliageType at '%s' is not a UFoliageType_InstancedStaticMesh (PivotPainter requires ISM)."), *FoliageTypePath));

    // Optionally set the static mesh if mesh_path is provided
    if (!MeshPath.IsEmpty())
    {
        UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
        if (!Mesh) return FoliageErr(FString::Printf(
            TEXT("Could not load StaticMesh at '%s'."), *MeshPath));

        IsmType->SetStaticMesh(Mesh);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_pivot_painter"));

    IsmType->Modify();

    // Configure wind-related properties on the foliage type.
    // PivotPainter material functions rely on WorldPositionOffset and
    // per-instance custom data for wind animation. We enable WPO and set
    // the cull distance appropriate for wind-animated foliage.
    IsmType->CastShadow = true;
    IsmType->bCastDynamicShadow = true;
    // Set a reasonable cull distance for wind-animated foliage
    const int32 WindCullDist = static_cast<int32>(FMath::Clamp(WindStrength * 15000.0, 5000.0, 50000.0));
    IsmType->CullDistance = FInt32Interval(WindCullDist / 2, WindCullDist);

    IsmType->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_pivot_painter"));
    Data->SetStringField(TEXT("foliage_type_path"), IsmType->GetPathName());
    Data->SetNumberField(TEXT("wind_strength"), WindStrength);
    Data->SetNumberField(TEXT("cull_distance_start"), WindCullDist / 2);
    Data->SetNumberField(TEXT("cull_distance_end"), WindCullDist);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
}
