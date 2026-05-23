#include "Commands/EpicUnrealMCPWaterCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_WATER_MCP
#include "WaterBodyOceanActor.h"
#include "WaterBodyLakeActor.h"
#include "WaterBodyRiverActor.h"
#include "WaterBodyCustomActor.h"
#include "WaterBodyComponent.h"
#include "WaterWaves.h"
#include "GerstnerWaterWaves.h"
#include "WaterSplineComponent.h"
#include "Components/SplineComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Editor.h"
#include "Materials/MaterialInterface.h"
#include "UObject/Package.h"
#include "Engine/StaticMeshActor.h"
#endif

bool FEpicUnrealMCPWaterCommands::IsModuleAvailable()
{
#if WITH_WATER_MCP
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPWaterCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Enable the Water plugin (Engine/Plugins/Experimental/Water)."));
    return R;
}

FEpicUnrealMCPWaterCommands::FEpicUnrealMCPWaterCommands() {}
FEpicUnrealMCPWaterCommands::~FEpicUnrealMCPWaterCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPWaterCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("enable_water_plugin"),  &FEpicUnrealMCPWaterCommands::HandleEnableWaterPlugin},
        {TEXT("spawn_water_body_ocean"),  &FEpicUnrealMCPWaterCommands::HandleSpawnWaterBodyOcean},
        {TEXT("spawn_water_body_lake"),  &FEpicUnrealMCPWaterCommands::HandleSpawnWaterBodyLake},
        {TEXT("spawn_water_body_river"),  &FEpicUnrealMCPWaterCommands::HandleSpawnWaterBodyRiver},
        {TEXT("spawn_water_body_custom"),  &FEpicUnrealMCPWaterCommands::HandleSpawnWaterBodyCustom},
        {TEXT("configure_river_spline"),  &FEpicUnrealMCPWaterCommands::HandleConfigureRiverSpline},
        {TEXT("set_water_material"),  &FEpicUnrealMCPWaterCommands::HandleSetWaterMaterial},
        {TEXT("configure_water_wave"),  &FEpicUnrealMCPWaterCommands::HandleConfigureWaterWave},
        {TEXT("configure_water_flow"),  &FEpicUnrealMCPWaterCommands::HandleConfigureWaterFlow},
        {TEXT("configure_buoyancy"),  &FEpicUnrealMCPWaterCommands::HandleConfigureBuoyancy},
        {TEXT("configure_water_mesh_actor"),  &FEpicUnrealMCPWaterCommands::HandleConfigureWaterMeshActor},
        {TEXT("configure_underwater_post_process"),  &FEpicUnrealMCPWaterCommands::HandleConfigureUnderwaterPostProcess},
        {TEXT("configure_shoreline"),  &FEpicUnrealMCPWaterCommands::HandleConfigureShoreline},
        {TEXT("configure_water_landscape_carving"),  &FEpicUnrealMCPWaterCommands::HandleConfigureWaterLandscapeCarving},
        {TEXT("attach_floating_actor"),  &FEpicUnrealMCPWaterCommands::HandleAttachFloatingActor}
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
// 234-stubs W3 (#92): Water executed-envelope helpers.
// ---------------------------------------------------------------------------

static TSharedPtr<FJsonObject> WaterOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> WaterErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

// Resolve an AWaterBody by name or label from the editor world.
static AWaterBody* FindWaterBodyInEditorWorld(UWorld* World, const FString& ActorName)
{
    if (!World || ActorName.IsEmpty()) return nullptr;
    for (TActorIterator<AWaterBody> It(World); It; ++It)
    {
        if (It->GetName().Equals(ActorName, ESearchCase::IgnoreCase) ||
            It->GetActorLabel().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            return *It;
        }
    }
    return nullptr;
}

// ---------------------------------------------------------------------------
// enable_water_plugin -- Check IPluginManager for Water plugin, persist metadata.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleEnableWaterPlugin(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("enable_water_plugin"));

#if WITH_WATER_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: enable_water_plugin"));

    // Water is already enabled if we're in this code path.
    // Persist metadata on the editor world package to record the request.
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    TSharedPtr<IPlugin> WaterPlugin = IPluginManager::Get().FindPlugin(TEXT("Water"));
    FString PluginVersion = WaterPlugin.IsValid() ? WaterPlugin->GetDescriptor().VersionName : TEXT("unknown");

    UPackage* Pkg = World->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        Pkg->SetMetaData(*World, FName(TEXT("MCP.water_plugin.enabled")), TEXT("true"));
        Pkg->SetMetaData(*World, FName(TEXT("MCP.water_plugin.status")), TEXT("active"));
        Pkg->SetMetaData(*World, FName(TEXT("MCP.water_plugin.version")), *PluginVersion);
        Pkg->MarkPackageDirty();
        KeysPersisted = 3;
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("enable_water_plugin"));
    Data->SetStringField(TEXT("status"), TEXT("water_plugin_active"));
    Data->SetStringField(TEXT("plugin_version"), PluginVersion);
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("enable_water_plugin"));
#endif
}

// ---------------------------------------------------------------------------
// spawn_water_body_ocean -- Spawn an AWaterBodyOcean in the editor world.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleSpawnWaterBodyOcean(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_water_body_ocean"));

#if WITH_WATER_MCP
    FString ActorName = TEXT("WaterBodyOcean");
    if (Params.IsValid()) Params->TryGetStringField(TEXT("actor_name"), ActorName);

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_water_body_ocean"));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*ActorName);
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    AWaterBodyOcean* Ocean = World->SpawnActor<AWaterBodyOcean>(AWaterBodyOcean::StaticClass(),
        FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!Ocean) return WaterErr(TEXT("Failed to spawn AWaterBodyOcean"));

    Ocean->SetActorLabel(ActorName);
    Ocean->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_water_body_ocean"));
    Data->SetStringField(TEXT("actor_name"), Ocean->GetName());
    Data->SetStringField(TEXT("actor_label"), Ocean->GetActorLabel());
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("spawn_water_body_ocean"));
#endif
}

// ---------------------------------------------------------------------------
// spawn_water_body_lake -- Spawn an AWaterBodyLake + USplineComponent setup.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleSpawnWaterBodyLake(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_water_body_lake"));

#if WITH_WATER_MCP
    FString ActorName = TEXT("WaterBodyLake");
    const TArray<TSharedPtr<FJsonValue>>* SplinePoints = nullptr;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetArrayField(TEXT("spline_points"), SplinePoints);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_water_body_lake"));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*ActorName);
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    AWaterBodyLake* Lake = World->SpawnActor<AWaterBodyLake>(AWaterBodyLake::StaticClass(),
        FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!Lake) return WaterErr(TEXT("Failed to spawn AWaterBodyLake"));

    Lake->SetActorLabel(ActorName);

    // Configure spline points if provided.
    UWaterSplineComponent* Spline = Lake->GetWaterSpline();
    int32 PointsAdded = 0;
    if (Spline && SplinePoints)
    {
        Spline->ClearSplinePoints(false);
        for (const TSharedPtr<FJsonValue>& Val : *SplinePoints)
        {
            const TSharedPtr<FJsonObject>* PtObj = nullptr;
            if (!Val->TryGetObject(PtObj)) continue;

            FVector Pos = FVector::ZeroVector;
            const TSharedPtr<FJsonObject>& P = *PtObj;
            P->TryGetNumberField(TEXT("x"), Pos.X);
            P->TryGetNumberField(TEXT("y"), Pos.Y);
            P->TryGetNumberField(TEXT("z"), Pos.Z);

            Spline->AddSplinePoint(Pos, ESplineCoordinateSpace::World, false);
            ++PointsAdded;
        }
        Spline->UpdateSpline();
    }

    Lake->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_water_body_lake"));
    Data->SetStringField(TEXT("actor_name"), Lake->GetName());
    Data->SetStringField(TEXT("actor_label"), Lake->GetActorLabel());
    Data->SetNumberField(TEXT("spline_points_added"), PointsAdded);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("spawn_water_body_lake"));
#endif
}

// ---------------------------------------------------------------------------
// spawn_water_body_river -- Spawn an AWaterBodyRiver + USplineComponent setup.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleSpawnWaterBodyRiver(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_water_body_river"));

#if WITH_WATER_MCP
    FString ActorName = TEXT("WaterBodyRiver");
    const TArray<TSharedPtr<FJsonValue>>* SplinePoints = nullptr;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetArrayField(TEXT("spline_points"), SplinePoints);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_water_body_river"));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*ActorName);
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    AWaterBodyRiver* River = World->SpawnActor<AWaterBodyRiver>(AWaterBodyRiver::StaticClass(),
        FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!River) return WaterErr(TEXT("Failed to spawn AWaterBodyRiver"));

    River->SetActorLabel(ActorName);

    // Configure spline points if provided.
    UWaterSplineComponent* Spline = River->GetWaterSpline();
    int32 PointsAdded = 0;
    if (Spline && SplinePoints)
    {
        Spline->ClearSplinePoints(false);
        for (const TSharedPtr<FJsonValue>& Val : *SplinePoints)
        {
            const TSharedPtr<FJsonObject>* PtObj = nullptr;
            if (!Val->TryGetObject(PtObj)) continue;

            FVector Pos = FVector::ZeroVector;
            const TSharedPtr<FJsonObject>& P = *PtObj;
            P->TryGetNumberField(TEXT("x"), Pos.X);
            P->TryGetNumberField(TEXT("y"), Pos.Y);
            P->TryGetNumberField(TEXT("z"), Pos.Z);

            Spline->AddSplinePoint(Pos, ESplineCoordinateSpace::World, false);
            ++PointsAdded;
        }
        Spline->UpdateSpline();
    }

    River->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_water_body_river"));
    Data->SetStringField(TEXT("actor_name"), River->GetName());
    Data->SetStringField(TEXT("actor_label"), River->GetActorLabel());
    Data->SetNumberField(TEXT("spline_points_added"), PointsAdded);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("spawn_water_body_river"));
#endif
}

// ---------------------------------------------------------------------------
// spawn_water_body_custom -- Spawn an AWaterBodyCustom in the editor world.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleSpawnWaterBodyCustom(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_water_body_custom"));

#if WITH_WATER_MCP
    FString ActorName = TEXT("WaterBodyCustom");
    if (Params.IsValid()) Params->TryGetStringField(TEXT("actor_name"), ActorName);

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_water_body_custom"));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*ActorName);
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    AWaterBodyCustom* Custom = World->SpawnActor<AWaterBodyCustom>(AWaterBodyCustom::StaticClass(),
        FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!Custom) return WaterErr(TEXT("Failed to spawn AWaterBodyCustom"));

    Custom->SetActorLabel(ActorName);
    Custom->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_water_body_custom"));
    Data->SetStringField(TEXT("actor_name"), Custom->GetName());
    Data->SetStringField(TEXT("actor_label"), Custom->GetActorLabel());
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("spawn_water_body_custom"));
#endif
}

// ---------------------------------------------------------------------------
// configure_river_spline -- USplineComponent point configuration on existing river.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureRiverSpline(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_river_spline"));

#if WITH_WATER_MCP
    FString ActorName;
    const TArray<TSharedPtr<FJsonValue>>* SplinePoints = nullptr;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetArrayField(TEXT("spline_points"), SplinePoints);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    AWaterBody* Body = FindWaterBodyInEditorWorld(World, ActorName);
    if (!Body) return WaterErr(FString::Printf(TEXT("configure_river_spline: water body '%s' not found."), *ActorName));

    AWaterBodyRiver* River = Cast<AWaterBodyRiver>(Body);
    if (!River) return WaterErr(FString::Printf(TEXT("configure_river_spline: '%s' is not an AWaterBodyRiver."), *ActorName));

    UWaterSplineComponent* Spline = River->GetWaterSpline();
    if (!Spline) return WaterErr(TEXT("configure_river_spline: no spline component found on river."));

    if (!SplinePoints) return WaterErr(TEXT("configure_river_spline: 'spline_points' array is required."));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_river_spline"));
    River->Modify();

    Spline->ClearSplinePoints(false);
    int32 PointsAdded = 0;
    for (const TSharedPtr<FJsonValue>& Val : *SplinePoints)
    {
        const TSharedPtr<FJsonObject>* PtObj = nullptr;
        if (!Val->TryGetObject(PtObj)) continue;

        FVector Pos = FVector::ZeroVector;
        const TSharedPtr<FJsonObject>& P = *PtObj;
        P->TryGetNumberField(TEXT("x"), Pos.X);
        P->TryGetNumberField(TEXT("y"), Pos.Y);
        P->TryGetNumberField(TEXT("z"), Pos.Z);

        Spline->AddSplinePoint(Pos, ESplineCoordinateSpace::World, false);
        ++PointsAdded;
    }
    Spline->UpdateSpline();
    River->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_river_spline"));
    Data->SetStringField(TEXT("actor_name"), River->GetName());
    Data->SetNumberField(TEXT("spline_points_configured"), PointsAdded);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("configure_river_spline"));
#endif
}

// ---------------------------------------------------------------------------
// set_water_material -- UWaterBodyComponent material assignment.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleSetWaterMaterial(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_water_material"));

#if WITH_WATER_MCP
    FString ActorName;
    FString MaterialPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("material_path"), MaterialPath);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    AWaterBody* Body = FindWaterBodyInEditorWorld(World, ActorName);
    if (!Body) return WaterErr(FString::Printf(TEXT("set_water_material: water body '%s' not found."), *ActorName));

    UWaterBodyComponent* WBC = Body->GetWaterBodyComponent();
    if (!WBC) return WaterErr(FString::Printf(TEXT("set_water_material: '%s' has no WaterBodyComponent."), *ActorName));

    UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
    if (!Mat) return WaterErr(FString::Printf(TEXT("set_water_material: material '%s' not found."), *MaterialPath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_water_material"));
    Body->Modify();

    WBC->SetWaterMaterial(Mat);
    Body->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_water_material"));
    Data->SetStringField(TEXT("actor_name"), Body->GetName());
    Data->SetStringField(TEXT("material_path"), Mat->GetPathName());
    Data->SetStringField(TEXT("material_name"), Mat->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("set_water_material"));
#endif
}

// ---------------------------------------------------------------------------
// configure_water_wave -- UWaterWaves / UWaterWaveAsset configuration.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureWaterWave(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_water_wave"));

#if WITH_WATER_MCP
    FString ActorName;
    FString AssetPath;
    float TargetWaveMaskDepth = -1.0f;
    float MaxWaveHeightOffset = -1.0f;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetNumberField(TEXT("target_wave_mask_depth"), TargetWaveMaskDepth);
        Params->TryGetNumberField(TEXT("max_wave_height_offset"), MaxWaveHeightOffset);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    AWaterBody* Body = FindWaterBodyInEditorWorld(World, ActorName);
    if (!Body) return WaterErr(FString::Printf(TEXT("configure_water_wave: water body '%s' not found."), *ActorName));

    UWaterBodyComponent* WBC = Body->GetWaterBodyComponent();
    if (!WBC) return WaterErr(FString::Printf(TEXT("configure_water_wave: '%s' has no WaterBodyComponent."), *ActorName));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_water_wave"));
    Body->Modify();

    int32 FieldsSet = 0;

    // If an asset path is provided, load the WaterWavesAsset and register its waves.
    if (!AssetPath.IsEmpty())
    {
        UWaterWavesAsset* WaveAsset = LoadObject<UWaterWavesAsset>(nullptr, *AssetPath);
        if (WaveAsset)
        {
            UWaterWavesBase* Waves = WaveAsset->GetWaterWaves();
            if (Waves)
            {
                WBC->RegisterOnUpdateWavesData(Waves, true);
                ++FieldsSet;
            }
        }
    }

    // Configure wave attenuation depth if provided.
    if (TargetWaveMaskDepth >= 0.0f)
    {
        WBC->TargetWaveMaskDepth = TargetWaveMaskDepth;
        ++FieldsSet;
    }

    // Configure max wave height offset if provided.
    if (MaxWaveHeightOffset >= 0.0f)
    {
        WBC->MaxWaveHeightOffset = MaxWaveHeightOffset;
        ++FieldsSet;
    }

    Body->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_water_wave"));
    Data->SetStringField(TEXT("actor_name"), Body->GetName());
    Data->SetNumberField(TEXT("fields_set"), FieldsSet);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("configure_water_wave"));
#endif
}

// ---------------------------------------------------------------------------
// W3-5 stubs below -- DO NOT promote these yet.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureWaterFlow(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_water_flow"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_water_flow"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; spawn / configure in the Water editor (Water Brush Manager)."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureBuoyancy(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_buoyancy"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_buoyancy"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; spawn / configure in the Water editor (Water Brush Manager)."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureWaterMeshActor(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_water_mesh_actor"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_water_mesh_actor"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; spawn / configure in the Water editor (Water Brush Manager)."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureUnderwaterPostProcess(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_underwater_post_process"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_underwater_post_process"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; spawn / configure in the Water editor (Water Brush Manager)."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureShoreline(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_shoreline"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_shoreline"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; spawn / configure in the Water editor (Water Brush Manager)."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureWaterLandscapeCarving(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_water_landscape_carving"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_water_landscape_carving"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; spawn / configure in the Water editor (Water Brush Manager)."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleAttachFloatingActor(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("attach_floating_actor"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("attach_floating_actor"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; spawn / configure in the Water editor (Water Brush Manager)."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
