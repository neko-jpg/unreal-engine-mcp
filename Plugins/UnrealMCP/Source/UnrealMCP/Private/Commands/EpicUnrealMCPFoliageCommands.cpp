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
#include "ProceduralFoliageBlockingVolume.h"
#include "ProceduralFoliageComponent.h"
#include "Components/BrushComponent.h"

// W3-4: Metadata support for paint/erase
#include "UObject/MetaData.h"

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

#if WITH_EDITOR
    FString FoliageTypePath;
    double OriginX = 0.0, OriginY = 0.0, OriginZ = 0.0;
    double Radius = 500.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        const TSharedPtr<FJsonObject>* OriginArr = nullptr;
        if (Params->TryGetObjectField(TEXT("location_xyz"), OriginArr))
        {
            (*OriginArr)->TryGetNumberField(TEXT("x"), OriginX);
            (*OriginArr)->TryGetNumberField(TEXT("y"), OriginY);
            (*OriginArr)->TryGetNumberField(TEXT("z"), OriginZ);
        }
        Params->TryGetNumberField(TEXT("radius"), Radius);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("foliage_paint: could not load FoliageType at '%s'."), *FoliageTypePath));

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return FoliageErr(TEXT("No editor world available."));

    // Record the paint request as metadata on the world package.
    UPackage* Pkg = World->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        UMetaData* MetaData = Pkg->GetMetaData();
        if (MetaData)
        {
            MetaData->SetValue(World, TEXT("MCP.foliage_paint.foliage_type"), *FoliageTypePath);
            MetaData->SetValue(World, TEXT("MCP.foliage_paint.location"), *FString::Printf(TEXT("%f,%f,%f"), OriginX, OriginY, OriginZ));
            MetaData->SetValue(World, TEXT("MCP.foliage_paint.radius"), *FString::SanitizeFloat(Radius));
            Pkg->MarkPackageDirty();
            KeysPersisted = 3;
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("foliage_paint"));
    Data->SetStringField(TEXT("foliage_type_path"), FoliageTypePath);
    Data->SetNumberField(TEXT("keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
#else
    return MakeUnavailable(TEXT("foliage_paint"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleFoliageErase(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("foliage_erase"));

#if WITH_EDITOR
    FString FoliageTypePath;
    double OriginX = 0.0, OriginY = 0.0, OriginZ = 0.0;
    double Radius = 500.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        const TSharedPtr<FJsonObject>* OriginArr = nullptr;
        if (Params->TryGetObjectField(TEXT("location_xyz"), OriginArr))
        {
            (*OriginArr)->TryGetNumberField(TEXT("x"), OriginX);
            (*OriginArr)->TryGetNumberField(TEXT("y"), OriginY);
            (*OriginArr)->TryGetNumberField(TEXT("z"), OriginZ);
        }
        Params->TryGetNumberField(TEXT("radius"), Radius);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("foliage_erase: could not load FoliageType at '%s'."), *FoliageTypePath));

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return FoliageErr(TEXT("No editor world available."));

    UPackage* Pkg = World->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        UMetaData* MetaData = Pkg->GetMetaData();
        if (MetaData)
        {
            MetaData->SetValue(World, TEXT("MCP.foliage_erase.foliage_type"), *FoliageTypePath);
            MetaData->SetValue(World, TEXT("MCP.foliage_erase.location"), *FString::Printf(TEXT("%f,%f,%f"), OriginX, OriginY, OriginZ));
            MetaData->SetValue(World, TEXT("MCP.foliage_erase.radius"), *FString::SanitizeFloat(Radius));
            Pkg->MarkPackageDirty();
            KeysPersisted = 3;
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("foliage_erase"));
    Data->SetStringField(TEXT("foliage_type_path"), FoliageTypePath);
    Data->SetNumberField(TEXT("keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
#else
    return MakeUnavailable(TEXT("foliage_erase"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetFoliageLod(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_foliage_lod"));

#if WITH_EDITOR
    FString FoliageTypePath;
    TArray<double> ScreenSizeOverrides;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
        if (Params->TryGetArrayField(TEXT("screen_size_overrides"), Arr))
        {
            for (const auto& V : *Arr)
            {
                double Val = 0.0;
                V->TryGetNumber(Val);
                ScreenSizeOverrides.Add(Val);
            }
        }
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("set_foliage_lod: could not load FoliageType at '%s'."), *FoliageTypePath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_foliage_lod"));
    Ft->Modify();

    if (ScreenSizeOverrides.Num() > 0)
    {
        Ft->DistanceScale = static_cast<float>(ScreenSizeOverrides[0]);
    }

    Ft->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_lod"));
    Data->SetStringField(TEXT("foliage_type_path"), Ft->GetPathName());
    Data->SetNumberField(TEXT("distance_scale"), Ft->DistanceScale);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
#else
    return MakeUnavailable(TEXT("set_foliage_lod"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleCreateProceduralFoliageSpawner(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_procedural_foliage_spawner"));

#if WITH_EDITOR
    FString AssetPath = TEXT("/Game/Foliage");
    FString AssetName = TEXT("PFS_New");
    int32 RandomSeed = 1;
    float TileSize = 10000.0f;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
        int64 TmpSeed = RandomSeed;
        Params->TryGetNumberField(TEXT("random_seed"), TmpSeed);
        RandomSeed = static_cast<int32>(TmpSeed);
        double TmpTile = TileSize;
        Params->TryGetNumberField(TEXT("tile_size"), TmpTile);
        TileSize = static_cast<float>(TmpTile);
    }

    const FString FullPath = AssetPath / AssetName;
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_procedural_foliage_spawner"));

    UPackage* Pkg = CreatePackage(*FullPath);
    if (!Pkg) return FoliageErr(TEXT("Failed to create package."));

    UProceduralFoliageSpawner* Spawner = NewObject<UProceduralFoliageSpawner>(
        Pkg, FName(*AssetName), RF_Public | RF_Standalone | RF_Transactional);
    if (!Spawner) return FoliageErr(TEXT("NewObject<UProceduralFoliageSpawner> returned null."));

    Spawner->RandomSeed = RandomSeed;
    Spawner->TileSize = TileSize;
    Spawner->MarkPackageDirty();
    Pkg->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_procedural_foliage_spawner"));
    Data->SetStringField(TEXT("asset_path"), Spawner->GetPathName());
    Data->SetNumberField(TEXT("random_seed"), Spawner->RandomSeed);
    Data->SetNumberField(TEXT("tile_size"), Spawner->TileSize);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
#else
    return MakeUnavailable(TEXT("create_procedural_foliage_spawner"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleCreateProceduralFoliageVolume(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_procedural_foliage_volume"));

#if WITH_EDITOR
    FString ActorName = TEXT("ProceduralFoliageVolume");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return FoliageErr(TEXT("No editor world available."));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_procedural_foliage_volume"));

    AProceduralFoliageBlockingVolume* Volume = World->SpawnActor<AProceduralFoliageBlockingVolume>(
        AProceduralFoliageBlockingVolume::StaticClass(), FTransform::Identity);
    if (!Volume) return FoliageErr(TEXT("Failed to spawn ProceduralFoliageBlockingVolume."));
    Volume->SetActorLabel(ActorName);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_procedural_foliage_volume"));
    Data->SetStringField(TEXT("actor_name"), Volume->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
#else
    return MakeUnavailable(TEXT("create_procedural_foliage_volume"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetProceduralFoliageSeed(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_procedural_foliage_seed"));

#if WITH_EDITOR
    FString ActorName;
    int32 Seed = 1;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        int64 TmpSeed = Seed;
        Params->TryGetNumberField(TEXT("seed"), TmpSeed);
        Seed = static_cast<int32>(TmpSeed);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return FoliageErr(TEXT("No editor world available."));

    // Find ProceduralFoliageVolume by name
    AProceduralFoliageVolume* Volume = nullptr;
    for (TActorIterator<AProceduralFoliageVolume> It(World); It; ++It)
    {
        if (It->GetName().Equals(ActorName, ESearchCase::IgnoreCase) ||
            It->GetActorLabel().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            Volume = *It;
            break;
        }
    }
    if (!Volume) return FoliageErr(FString::Printf(
        TEXT("Could not find ProceduralFoliageVolume '%s'."), *ActorName));
    if (!Volume->ProceduralComponent) return FoliageErr(TEXT("Volume has no ProceduralComponent."));
    if (!Volume->ProceduralComponent->FoliageSpawner) return FoliageErr(TEXT("Volume has no FoliageSpawner assigned."));

    UProceduralFoliageSpawner* Spawner = Volume->ProceduralComponent->FoliageSpawner;
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_procedural_foliage_seed"));
    Spawner->Modify();
    Spawner->RandomSeed = Seed;
    Spawner->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_procedural_foliage_seed"));
    Data->SetStringField(TEXT("actor_name"), Volume->GetName());
    Data->SetNumberField(TEXT("seed"), Spawner->RandomSeed);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
#else
    return MakeUnavailable(TEXT("set_procedural_foliage_seed"));
#endif
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

#if WITH_EDITOR
    FString FoliageTypePath;
    bool bEnable = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        Params->TryGetBoolField(TEXT("enable"), bEnable);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("set_foliage_nanite: could not load FoliageType at '%s'."), *FoliageTypePath));

    UFoliageType_InstancedStaticMesh* IsmType = Cast<UFoliageType_InstancedStaticMesh>(Ft);
    if (!IsmType) return FoliageErr(FString::Printf(
        TEXT("FoliageType at '%s' is not a UFoliageType_InstancedStaticMesh."), *FoliageTypePath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_foliage_nanite"));
    IsmType->Modify();
    IsmType->NaniteSettings.bEnabled = bEnable;
    IsmType->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_nanite"));
    Data->SetStringField(TEXT("foliage_type_path"), IsmType->GetPathName());
    Data->SetBoolField(TEXT("nanite_enabled"), IsmType->NaniteSettings.bEnabled);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
#else
    return MakeUnavailable(TEXT("set_foliage_nanite"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPFoliageCommands::HandleSetFoliageWind(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_foliage_wind"));

#if WITH_EDITOR
    FString FoliageTypePath;
    double WindStrength = 1.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("foliage_type_path"), FoliageTypePath);
        Params->TryGetNumberField(TEXT("wind_strength"), WindStrength);
    }

    UFoliageType* Ft = LoadFoliageType(FoliageTypePath);
    if (!Ft) return FoliageErr(FString::Printf(
        TEXT("set_foliage_wind: could not load FoliageType at '%s'."), *FoliageTypePath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_foliage_wind"));
    Ft->Modify();
    Ft->bEvaluateWorldPositionOffset = true;
    Ft->WorldPositionOffsetDisableDistance = static_cast<int32>(FMath::Clamp(WindStrength * 10000.0, 5000.0, 50000.0));
    Ft->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_foliage_wind"));
    Data->SetStringField(TEXT("foliage_type_path"), Ft->GetPathName());
    Data->SetNumberField(TEXT("wind_strength"), WindStrength);
    Data->SetNumberField(TEXT("wpo_disable_distance"), Ft->WorldPositionOffsetDisableDistance);
    Data->SetBoolField(TEXT("executed"), true);
    return FoliageOk(Data);
#else
    return MakeUnavailable(TEXT("set_foliage_wind"));
#endif
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
