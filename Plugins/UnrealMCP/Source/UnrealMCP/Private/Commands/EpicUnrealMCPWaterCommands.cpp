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
#include "BuoyancyComponent.h"
#include "BuoyancyTypes.h"
#include "WaterZoneActor.h"
#include "WaterMeshComponent.h"
#include "WaterCurveSettings.h"
#include "WaterBodyHeightmapSettings.h"
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
// configure_water_flow -- UWaterBodyComponent WaterVelocity configuration.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureWaterFlow(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_water_flow"));

#if WITH_WATER_MCP
    FString ActorName;
    float FlowVelocity = 100.0f;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetNumberField(TEXT("flow_velocity"), FlowVelocity);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    AWaterBody* Body = FindWaterBodyInEditorWorld(World, ActorName);
    if (!Body) return WaterErr(FString::Printf(TEXT("configure_water_flow: water body '%s' not found."), *ActorName));

    UWaterBodyComponent* WBC = Body->GetWaterBodyComponent();
    if (!WBC) return WaterErr(FString::Printf(TEXT("configure_water_flow: '%s' has no WaterBodyComponent."), *ActorName));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_water_flow"));
    Body->Modify();

    // Set water velocity across the full spline range [0, 1].
    WBC->SetWaterVelocityAtSplineInputKey(0.0f, FlowVelocity);
    WBC->SetWaterVelocityAtSplineInputKey(1.0f, FlowVelocity);
    Body->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_water_flow"));
    Data->SetStringField(TEXT("actor_name"), Body->GetName());
    Data->SetNumberField(TEXT("flow_velocity"), FlowVelocity);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("configure_water_flow"));
#endif
}

// ---------------------------------------------------------------------------
// configure_buoyancy -- UBuoyancyComponent setup on an actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureBuoyancy(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_buoyancy"));

#if WITH_WATER_MCP
    FString ActorName;
    float Weight = 1.0f;
    float Damping = 0.5f;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetNumberField(TEXT("weight"), Weight);
        Params->TryGetNumberField(TEXT("damping"), Damping);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    // Find the target actor by name or label.
    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName().Equals(ActorName, ESearchCase::IgnoreCase) ||
            It->GetActorLabel().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            TargetActor = *It;
            break;
        }
    }
    if (!TargetActor) return WaterErr(FString::Printf(TEXT("configure_buoyancy: actor '%s' not found."), *ActorName));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_buoyancy"));
    TargetActor->Modify();

    // Find or create a UBuoyancyComponent.
    UBuoyancyComponent* Buoyancy = TargetActor->FindComponentByClass<UBuoyancyComponent>();
    if (!Buoyancy)
    {
        Buoyancy = NewObject<UBuoyancyComponent>(TargetActor, UBuoyancyComponent::StaticClass(), TEXT("BuoyancyComponent"));
        Buoyancy->RegisterComponent();
        TargetActor->AddInstanceComponent(Buoyancy);
    }

    // Configure buoyancy data.
    Buoyancy->BuoyancyData.BuoyancyCoefficient = Weight;
    Buoyancy->BuoyancyData.BuoyancyDamp = Damping * 1000.0f;
    TargetActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_buoyancy"));
    Data->SetStringField(TEXT("actor_name"), TargetActor->GetName());
    Data->SetNumberField(TEXT("weight"), Weight);
    Data->SetNumberField(TEXT("damping"), Damping);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("configure_buoyancy"));
#endif
}

// ---------------------------------------------------------------------------
// configure_water_mesh_actor -- AWaterZone / UWaterMeshComponent configuration.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureWaterMeshActor(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_water_mesh_actor"));

#if WITH_WATER_MCP
    FString ActorName = TEXT("WaterZone");
    float TileSize = 2400.0f;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetNumberField(TEXT("tile_size"), TileSize);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    // Find AWaterZone by name or label.
    AWaterZone* WaterZone = nullptr;
    for (TActorIterator<AWaterZone> It(World); It; ++It)
    {
        if (It->GetName().Equals(ActorName, ESearchCase::IgnoreCase) ||
            It->GetActorLabel().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            WaterZone = *It;
            break;
        }
    }
    if (!WaterZone) return WaterErr(FString::Printf(TEXT("configure_water_mesh_actor: water zone '%s' not found."), *ActorName));

    UWaterMeshComponent* WaterMesh = WaterZone->GetWaterMeshComponent();
    if (!WaterMesh) return WaterErr(FString::Printf(TEXT("configure_water_mesh_actor: '%s' has no WaterMeshComponent."), *ActorName));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_water_mesh_actor"));
    WaterZone->Modify();

    WaterMesh->SetTileSize(TileSize);
    WaterZone->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_water_mesh_actor"));
    Data->SetStringField(TEXT("actor_name"), WaterZone->GetName());
    Data->SetNumberField(TEXT("tile_size"), TileSize);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("configure_water_mesh_actor"));
#endif
}

// ---------------------------------------------------------------------------
// configure_underwater_post_process -- UWaterBodyComponent post process setup.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureUnderwaterPostProcess(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_underwater_post_process"));

#if WITH_WATER_MCP
    FString PostProcessActor = TEXT("WaterPostProcess");
    FString MaterialPath;
    bool bEnabled = true;
    float Priority = 0.0f;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("post_process_actor"), PostProcessActor);
        Params->TryGetStringField(TEXT("material_path"), MaterialPath);
        Params->TryBoolField(TEXT("enabled"), bEnabled);
        Params->TryGetNumberField(TEXT("priority"), Priority);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    AWaterBody* Body = FindWaterBodyInEditorWorld(World, PostProcessActor);
    if (!Body) return WaterErr(FString::Printf(TEXT("configure_underwater_post_process: water body '%s' not found."), *PostProcessActor));

    UWaterBodyComponent* WBC = Body->GetWaterBodyComponent();
    if (!WBC) return WaterErr(FString::Printf(TEXT("configure_underwater_post_process: '%s' has no WaterBodyComponent."), *PostProcessActor));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_underwater_post_process"));
    Body->Modify();

    int32 FieldsSet = 0;

    // Set underwater post process material if provided.
    if (!MaterialPath.IsEmpty())
    {
        UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
        if (Mat)
        {
            WBC->SetUnderwaterPostProcessMaterial(Mat);
            ++FieldsSet;
        }
    }

    // Configure underwater post process settings.
    WBC->UnderwaterPostProcessSettings.bEnabled = bEnabled;
    WBC->UnderwaterPostProcessSettings.Priority = Priority;
    FieldsSet += 2;

    Body->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_underwater_post_process"));
    Data->SetStringField(TEXT("actor_name"), Body->GetName());
    Data->SetNumberField(TEXT("fields_set"), FieldsSet);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("configure_underwater_post_process"));
#endif
}

// ---------------------------------------------------------------------------
// configure_shoreline -- Water body curve / shoreline settings.
// UE 5.7 has no dedicated UShorelineComponent; shoreline shape is controlled
// via FWaterCurveSettings on UWaterBodyComponent.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureShoreline(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_shoreline"));

#if WITH_WATER_MCP
    FString ActorName;
    float Smoothness = 0.5f;
    float ChannelDepth = 0.0f;
    float ChannelEdgeOffset = 0.0f;
    float CurveRampWidth = 512.0f;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetNumberField(TEXT("smoothness"), Smoothness);
        Params->TryGetNumberField(TEXT("channel_depth"), ChannelDepth);
        Params->TryGetNumberField(TEXT("channel_edge_offset"), ChannelEdgeOffset);
        Params->TryGetNumberField(TEXT("curve_ramp_width"), CurveRampWidth);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    AWaterBody* Body = FindWaterBodyInEditorWorld(World, ActorName);
    if (!Body) return WaterErr(FString::Printf(TEXT("configure_shoreline: water body '%s' not found."), *ActorName));

    UWaterBodyComponent* WBC = Body->GetWaterBodyComponent();
    if (!WBC) return WaterErr(FString::Printf(TEXT("configure_shoreline: '%s' has no WaterBodyComponent."), *ActorName));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_shoreline"));
    Body->Modify();

    // Configure curve settings that control shoreline shape.
    FWaterCurveSettings& CS = WBC->CurveSettings;
    CS.ChannelDepth = ChannelDepth;
    CS.ChannelEdgeOffset = ChannelEdgeOffset;
    CS.CurveRampWidth = CurveRampWidth;
    CS.bUseCurveChannel = (Smoothness > 0.0f);
    Body->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_shoreline"));
    Data->SetStringField(TEXT("actor_name"), Body->GetName());
    Data->SetNumberField(TEXT("smoothness"), Smoothness);
    Data->SetNumberField(TEXT("channel_depth"), ChannelDepth);
    Data->SetNumberField(TEXT("channel_edge_offset"), ChannelEdgeOffset);
    Data->SetNumberField(TEXT("curve_ramp_width"), CurveRampWidth);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("configure_shoreline"));
#endif
}

// ---------------------------------------------------------------------------
// configure_water_landscape_carving -- bAffectsLandscape + WaterHeightmapSettings.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleConfigureWaterLandscapeCarving(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_water_landscape_carving"));

#if WITH_WATER_MCP
    FString LandscapeActor;
    bool bEnable = true;
    float Falloff = 0.0f;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("landscape_actor"), LandscapeActor);
        Params->TryBoolField(TEXT("enable"), bEnable);
        Params->TryGetNumberField(TEXT("falloff"), Falloff);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    // The "landscape_actor" param identifies the water body whose carving to configure.
    AWaterBody* Body = FindWaterBodyInEditorWorld(World, LandscapeActor);
    if (!Body) return WaterErr(FString::Printf(TEXT("configure_water_landscape_carving: water body '%s' not found."), *LandscapeActor));

    UWaterBodyComponent* WBC = Body->GetWaterBodyComponent();
    if (!WBC) return WaterErr(FString::Printf(TEXT("configure_water_landscape_carving: '%s' has no WaterBodyComponent."), *LandscapeActor));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_water_landscape_carving"));
    Body->Modify();

    WBC->bAffectsLandscape = bEnable;
    if (Falloff > 0.0f)
    {
        WBC->WaterHeightmapSettings.FalloffSettings.FalloffWidth = Falloff;
    }
    Body->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_water_landscape_carving"));
    Data->SetStringField(TEXT("actor_name"), Body->GetName());
    Data->SetBoolField(TEXT("affects_landscape"), WBC->bAffectsLandscape);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("configure_water_landscape_carving"));
#endif
}

// ---------------------------------------------------------------------------
// attach_floating_actor -- UBuoyancyComponent pontoon positions.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPWaterCommands::HandleAttachFloatingActor(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("attach_floating_actor"));

#if WITH_WATER_MCP
    FString ActorName;
    const TArray<TSharedPtr<FJsonValue>>* PontoonLocations = nullptr;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetArrayField(TEXT("pontoon_locations"), PontoonLocations);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return WaterErr(TEXT("No editor world available"));

    // Find the target actor.
    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName().Equals(ActorName, ESearchCase::IgnoreCase) ||
            It->GetActorLabel().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            TargetActor = *It;
            break;
        }
    }
    if (!TargetActor) return WaterErr(FString::Printf(TEXT("attach_floating_actor: actor '%s' not found."), *ActorName));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: attach_floating_actor"));
    TargetActor->Modify();

    // Find or create UBuoyancyComponent.
    UBuoyancyComponent* Buoyancy = TargetActor->FindComponentByClass<UBuoyancyComponent>();
    if (!Buoyancy)
    {
        Buoyancy = NewObject<UBuoyancyComponent>(TargetActor, UBuoyancyComponent::StaticClass(), TEXT("BuoyancyComponent"));
        Buoyancy->RegisterComponent();
        TargetActor->AddInstanceComponent(Buoyancy);
    }

    // Clear existing pontoons and add new ones from the provided locations.
    int32 PontoonsAdded = 0;
    if (PontoonLocations)
    {
        Buoyancy->BuoyancyData.Pontoons.Empty();
        for (const TSharedPtr<FJsonValue>& Val : *PontoonLocations)
        {
            const TSharedPtr<FJsonObject>* PtObj = nullptr;
            if (!Val->TryGetObject(PtObj)) continue;

            FVector Loc = FVector::ZeroVector;
            const TSharedPtr<FJsonObject>& P = *PtObj;
            P->TryGetNumberField(TEXT("x"), Loc.X);
            P->TryGetNumberField(TEXT("y"), Loc.Y);
            P->TryGetNumberField(TEXT("z"), Loc.Z);

            float Radius = 100.0f;
            P->TryGetNumberField(TEXT("radius"), Radius);

            FSphericalPontoon Pontoon;
            Pontoon.RelativeLocation = Loc;
            Pontoon.Radius = Radius;
            Buoyancy->BuoyancyData.Pontoons.Add(Pontoon);
            ++PontoonsAdded;
        }
    }

    TargetActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("attach_floating_actor"));
    Data->SetStringField(TEXT("actor_name"), TargetActor->GetName());
    Data->SetNumberField(TEXT("pontoons_added"), PontoonsAdded);
    Data->SetBoolField(TEXT("executed"), true);
    return WaterOk(Data);
#else
    return MakeUnavailable(TEXT("attach_floating_actor"));
#endif
}
