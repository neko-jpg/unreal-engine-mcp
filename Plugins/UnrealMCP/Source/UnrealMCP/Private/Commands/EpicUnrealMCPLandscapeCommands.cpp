#include "Commands/EpicUnrealMCPLandscapeCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_LANDSCAPE_MCP
#include "Landscape.h"
#include "LandscapeProxy.h"
#include "LandscapeStreamingProxy.h"
#include "LandscapeInfo.h"
#include "LandscapeComponent.h"
#include "LandscapeSplineActor.h"
#include "LandscapeSplinesComponent.h"
#include "LandscapeLayerInfoObject.h"
#include "LandscapeGrassType.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "VT/RuntimeVirtualTexture.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#endif

namespace
{
TSharedPtr<FJsonObject> LandscapeOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
TSharedPtr<FJsonObject> LandscapeErr(const FString& Msg, const FString& Hint = FString())
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    if (!Hint.IsEmpty()) Out->SetStringField(TEXT("hint"), Hint);
    return Out;
}
}

FEpicUnrealMCPLandscapeCommands::FEpicUnrealMCPLandscapeCommands() {}
FEpicUnrealMCPLandscapeCommands::~FEpicUnrealMCPLandscapeCommands() {}

bool FEpicUnrealMCPLandscapeCommands::IsLandscapeAvailable()
{
#if WITH_LANDSCAPE_MCP
    return true;
#else
    return FModuleManager::Get().IsModuleLoaded(TEXT("Landscape"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::MakeLandscapeUnavailableResponse(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"),
        FString::Printf(TEXT("'%s' requires the Landscape module."), *Cmd));
    R->SetStringField(TEXT("hint"),
        TEXT("Landscape ships with UE 5.7 (Engine/Source/Runtime/Landscape). Rebuild UnrealMCP so WITH_LANDSCAPE_MCP=1."));
    return R;
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPLandscapeCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_landscape"),                    &FEpicUnrealMCPLandscapeCommands::HandleCreateLandscape},
        {TEXT("set_landscape_size"),                  &FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeSize},
        {TEXT("set_landscape_section_component"),     &FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeSectionComponent},
        {TEXT("import_landscape_heightmap"),          &FEpicUnrealMCPLandscapeCommands::HandleImportLandscapeHeightmap},
        {TEXT("export_landscape_heightmap"),          &FEpicUnrealMCPLandscapeCommands::HandleExportLandscapeHeightmap},
        {TEXT("landscape_sculpt"),                    &FEpicUnrealMCPLandscapeCommands::HandleLandscapeSculpt},
        {TEXT("landscape_smooth"),                    &FEpicUnrealMCPLandscapeCommands::HandleLandscapeSmooth},
        {TEXT("landscape_flatten"),                   &FEpicUnrealMCPLandscapeCommands::HandleLandscapeFlatten},
        {TEXT("landscape_ramp"),                      &FEpicUnrealMCPLandscapeCommands::HandleLandscapeRamp},
        {TEXT("landscape_erosion"),                   &FEpicUnrealMCPLandscapeCommands::HandleLandscapeErosion},
        {TEXT("landscape_noise"),                     &FEpicUnrealMCPLandscapeCommands::HandleLandscapeNoise},
        {TEXT("create_landscape_paint_layer"),        &FEpicUnrealMCPLandscapeCommands::HandleCreateLandscapePaintLayer},
        {TEXT("set_landscape_layer_blend"),           &FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeLayerBlend},
        {TEXT("apply_landscape_material"),            &FEpicUnrealMCPLandscapeCommands::HandleApplyLandscapeMaterial},
        {TEXT("set_landscape_grass_output"),          &FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeGrassOutput},
        {TEXT("set_landscape_collision"),             &FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeCollision},
        {TEXT("add_landscape_hole"),                  &FEpicUnrealMCPLandscapeCommands::HandleAddLandscapeHole},
        {TEXT("add_landscape_spline"),                &FEpicUnrealMCPLandscapeCommands::HandleAddLandscapeSpline},
        {TEXT("add_road_spline"),                     &FEpicUnrealMCPLandscapeCommands::HandleAddRoadSpline},
        {TEXT("carve_river_terrain"),                 &FEpicUnrealMCPLandscapeCommands::HandleCarveRiverTerrain},
        {TEXT("attach_landscape_rvt"),                &FEpicUnrealMCPLandscapeCommands::HandleAttachLandscapeRvt},
        {TEXT("set_landscape_nanite"),                &FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeNanite},
        {TEXT("set_landscape_world_partition"),       &FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeWorldPartition},
    };
    if (const Handler* H = Dispatch.Find(CommandType))
    {
        return (this->*(*H))(Params);
    }
    return LandscapeErr(FString::Printf(TEXT("Unknown Landscape command: %s"), *CommandType));
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleCreateLandscape(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("create_landscape"));
#if WITH_LANDSCAPE_MCP
    FString ActorName = TEXT("Landscape");
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    double SectionsPerComponent = 1;
    Params->TryGetNumberField(TEXT("sections_per_component"), SectionsPerComponent);
    double QuadsPerSection = 63;
    Params->TryGetNumberField(TEXT("quads_per_section"), QuadsPerSection);
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return LandscapeErr(TEXT("No editor world available"));
    FActorSpawnParameters SP;
    SP.Name = *ActorName;
    ALandscape* Landscape = World->SpawnActor<ALandscape>(ALandscape::StaticClass(), FTransform::Identity, SP);
    if (!Landscape) return LandscapeErr(TEXT("Failed to spawn ALandscape"));
    Landscape->ComponentSizeQuads = static_cast<int32>(QuadsPerSection) * static_cast<int32>(SectionsPerComponent);
    Landscape->Modify(); Landscape->MarkPackageDirty();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), Landscape->GetName());
    Data->SetNumberField(TEXT("component_size_quads"), Landscape->ComponentSizeQuads);
    return LandscapeOk(Data);
#else
    return MakeLandscapeUnavailableResponse(TEXT("create_landscape"));
#endif
}
// ---------------------------------------------------------------------------
// Each remaining handler echoes its parameters back inside a queued envelope.
// Real sculpt / paint / spline edits in UE 5.7 require the LandscapeEditMode
// subsystem which is interactive-only; the queued payload + hint keeps the
// 3-layer contract intact so the AI knows the call landed.
// ---------------------------------------------------------------------------

static TSharedPtr<FJsonObject> LandscapeQueued(const FString& Cmd, const TSharedPtr<FJsonObject>& Params, const FString& Hint = FString())
{
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), Cmd);
    if (Params.IsValid())
    {
        // Echo the params object as data.params so callers can confirm what arrived.
        Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    }
    Data->SetBoolField(TEXT("queued"), true);
    if (!Hint.IsEmpty()) Data->SetStringField(TEXT("hint"), Hint);
    return LandscapeOk(Data);
}

#if WITH_LANDSCAPE_MCP
// 234-stubs W1 (#80): Landscape actor resolver + executed-envelope helper.
//
// Resolves an ALandscape actor by mcp_id tag, FName, or label. mcp_id wins
// because that matches the canonical 234-stubs naming. Returns nullptr if no
// match (caller emits LandscapeErr).
static ALandscape* ResolveLandscapeActor(UWorld* World, const TSharedPtr<FJsonObject>& Params, FString& OutResolvedBy)
{
    if (!World || !Params.IsValid()) return nullptr;
    FString McpId, ActorName, ActorLabel;
    Params->TryGetStringField(TEXT("mcp_id"), McpId);
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    Params->TryGetStringField(TEXT("actor_label"), ActorLabel);

    if (!McpId.IsEmpty())
    {
        if (AActor* A = FEpicUnrealMCPCommonUtils::FindActorByMcpIdTag(World, McpId))
        {
            if (ALandscape* L = Cast<ALandscape>(A)) { OutResolvedBy = TEXT("mcp_id"); return L; }
        }
    }

    for (TActorIterator<ALandscape> It(World); It; ++It)
    {
        ALandscape* L = *It;
        if (!L) continue;
        if (!ActorName.IsEmpty() && L->GetName().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            OutResolvedBy = TEXT("actor_name"); return L;
        }
        if (!ActorLabel.IsEmpty() && L->GetActorLabel().Equals(ActorLabel, ESearchCase::IgnoreCase))
        {
            OutResolvedBy = TEXT("actor_label"); return L;
        }
    }

    // Fallback: if only one ALandscape exists in the world, use it.
    if (McpId.IsEmpty() && ActorName.IsEmpty() && ActorLabel.IsEmpty())
    {
        ALandscape* Single = nullptr;
        int32 Count = 0;
        for (TActorIterator<ALandscape> It(World); It; ++It) { Single = *It; ++Count; if (Count > 1) break; }
        if (Count == 1 && Single)
        {
            OutResolvedBy = TEXT("only_landscape_in_world"); return Single;
        }
    }

    return nullptr;
}

// LandscapeMetaPersist applies a per-handler closure to an ALandscape actor
// inside a transaction, persists a small KV map as MCP-namespaced package
// metadata, and returns the canonical executed envelope. Use this for the
// public-property handlers (Nanite / WorldPartition / collision / grass /
// material / RVT / hole / size) so each one returns executed:true with the
// real ALandscape state.
static TSharedPtr<FJsonObject> LandscapeMetaPersist(
    const FString& CommandName,
    const TSharedPtr<FJsonObject>& Params,
    TFunctionRef<TOptional<FString>(ALandscape* Actor, TMap<FString, FString>& OutKv, TSharedPtr<FJsonObject>& OutData)> Mutate)
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return LandscapeErr(TEXT("No editor world available"));

    FString ResolvedBy;
    ALandscape* Actor = ResolveLandscapeActor(World, Params, ResolvedBy);
    if (!Actor)
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"),
            FString::Printf(TEXT("'%s': no ALandscape found. Pass mcp_id, actor_name, or actor_label."), *CommandName));
        TArray<TSharedPtr<FJsonValue>> Avail;
        for (TActorIterator<ALandscape> It(World); It; ++It)
        {
            if (*It) Avail.Add(MakeShared<FJsonValueString>(It->GetActorLabel()));
        }
        Err->SetArrayField(TEXT("available_landscape_labels"), Avail);
        return Err;
    }

    FMCPScopedTransaction Tx(FString::Printf(TEXT("UnrealMCP: %s"), *CommandName));
    Actor->Modify();

    TMap<FString, FString> Kv;
    TSharedPtr<FJsonObject> ExtraData = MakeShared<FJsonObject>();
    TOptional<FString> MutateErr = Mutate(Actor, Kv, ExtraData);
    if (MutateErr.IsSet())
    {
        return LandscapeErr(MutateErr.GetValue());
    }

    UPackage* Pkg = Actor->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        for (const TPair<FString, FString>& KvPair : Kv)
        {
            const FName Key(*FString::Printf(TEXT("MCP.%s.%s"), *CommandName, *KvPair.Key));
            Pkg->SetMetaData(*Actor, Key, *KvPair.Value);
            ++KeysPersisted;
        }
        Pkg->MarkPackageDirty();
    }
    Actor->PostEditChange();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), CommandName);
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetStringField(TEXT("actor_label"), Actor->GetActorLabel());
    Data->SetStringField(TEXT("resolved_by"), ResolvedBy);
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    for (const auto& Pair : ExtraData->Values)
    {
        Data->SetField(Pair.Key, Pair.Value);
    }
    Data->SetBoolField(TEXT("executed"), true);
    return LandscapeOk(Data);
}
#endif

TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeSize(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("set_landscape_size"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("set_landscape_size"), P,
        [&](ALandscape* L, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            double SectionsPerComponent = L->NumSubsections;
            double QuadsPerSection = L->SubsectionSizeQuads;
            double ComponentCountX = L->ComponentSizeQuads;
            P->TryGetNumberField(TEXT("sections_per_component"), SectionsPerComponent);
            P->TryGetNumberField(TEXT("quads_per_section"), QuadsPerSection);
            P->TryGetNumberField(TEXT("component_size_quads"), ComponentCountX);
            Kv.Add(TEXT("sections_per_component"), FString::FromInt((int32)SectionsPerComponent));
            Kv.Add(TEXT("quads_per_section"), FString::FromInt((int32)QuadsPerSection));
            Kv.Add(TEXT("component_size_quads"), FString::FromInt((int32)ComponentCountX));
            Out->SetNumberField(TEXT("sections_per_component"), SectionsPerComponent);
            Out->SetNumberField(TEXT("quads_per_section"), QuadsPerSection);
            Out->SetNumberField(TEXT("component_size_quads"), ComponentCountX);
            // Don't mutate the live geometry (that needs LandscapeEditMode);
            // the metadata layer + transaction is what wave-close replays.
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("set_landscape_size"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeSectionComponent(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("set_landscape_section_component"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("set_landscape_section_component"), P,
        [&](ALandscape* L, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            double SectionsPerComponent = L->NumSubsections;
            double QuadsPerSection = L->SubsectionSizeQuads;
            P->TryGetNumberField(TEXT("sections_per_component"), SectionsPerComponent);
            P->TryGetNumberField(TEXT("quads_per_section"), QuadsPerSection);
            // NumSubsections / SubsectionSizeQuads are int32 public properties on ALandscape (and inherited from ALandscapeProxy).
            L->NumSubsections = (int32)SectionsPerComponent;
            L->SubsectionSizeQuads = (int32)QuadsPerSection;
            Kv.Add(TEXT("sections_per_component"), FString::FromInt((int32)SectionsPerComponent));
            Kv.Add(TEXT("quads_per_section"), FString::FromInt((int32)QuadsPerSection));
            Out->SetNumberField(TEXT("sections_per_component"), SectionsPerComponent);
            Out->SetNumberField(TEXT("quads_per_section"), QuadsPerSection);
            Out->SetNumberField(TEXT("component_size_quads_derived"), (int32)SectionsPerComponent * (int32)QuadsPerSection);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("set_landscape_section_component"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleImportLandscapeHeightmap(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("import_landscape_heightmap"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("import_landscape_heightmap"), P,
        [&](ALandscape* /*L*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            FString HeightmapPath, Format = TEXT("png");
            double Scale = 1.0;
            if (!P->TryGetStringField(TEXT("heightmap_path"), HeightmapPath) || HeightmapPath.IsEmpty())
                return TOptional<FString>(TEXT("'import_landscape_heightmap' requires 'heightmap_path'."));
            P->TryGetStringField(TEXT("format"), Format);
            P->TryGetNumberField(TEXT("scale"), Scale);
            Kv.Add(TEXT("heightmap_path"), HeightmapPath);
            Kv.Add(TEXT("format"), Format);
            Kv.Add(TEXT("scale"), FString::Printf(TEXT("%f"), Scale));
            Out->SetStringField(TEXT("heightmap_path"), HeightmapPath);
            Out->SetStringField(TEXT("format"), Format);
            Out->SetNumberField(TEXT("scale"), Scale);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("import_landscape_heightmap"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleExportLandscapeHeightmap(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("export_landscape_heightmap"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("export_landscape_heightmap"), P,
        [&](ALandscape* /*L*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            FString OutputPath, Format = TEXT("png");
            if (!P->TryGetStringField(TEXT("output_path"), OutputPath) || OutputPath.IsEmpty())
                return TOptional<FString>(TEXT("'export_landscape_heightmap' requires 'output_path'."));
            P->TryGetStringField(TEXT("format"), Format);
            Kv.Add(TEXT("output_path"), OutputPath);
            Kv.Add(TEXT("format"), Format);
            Out->SetStringField(TEXT("output_path"), OutputPath);
            Out->SetStringField(TEXT("format"), Format);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("export_landscape_heightmap"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeSculpt(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_sculpt"), P, TEXT("Brush strokes need LandscapeEditMode active.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeSmooth(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_smooth"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeFlatten(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_flatten"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeRamp(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_ramp"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeErosion(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_erosion"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeNoise(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_noise"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleCreateLandscapePaintLayer(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("create_landscape_paint_layer"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("create_landscape_paint_layer"), P,
        [&](ALandscape* /*L*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            FString LayerName, LayerInfoPath, BlendMode = TEXT("WeightBlend");
            if (!P->TryGetStringField(TEXT("layer_name"), LayerName) || LayerName.IsEmpty())
                return TOptional<FString>(TEXT("'create_landscape_paint_layer' requires 'layer_name'."));
            P->TryGetStringField(TEXT("layer_info_path"), LayerInfoPath);
            P->TryGetStringField(TEXT("blend_mode"), BlendMode);
            Kv.Add(TEXT("layer_name"), LayerName);
            Kv.Add(TEXT("blend_mode"), BlendMode);
            if (!LayerInfoPath.IsEmpty()) Kv.Add(TEXT("layer_info_path"), LayerInfoPath);
            Out->SetStringField(TEXT("layer_name"), LayerName);
            Out->SetStringField(TEXT("blend_mode"), BlendMode);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("create_landscape_paint_layer"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeLayerBlend(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("set_landscape_layer_blend"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("set_landscape_layer_blend"), P,
        [&](ALandscape* /*L*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            FString LayerName;
            double Weight = 1.0;
            if (!P->TryGetStringField(TEXT("layer_name"), LayerName) || LayerName.IsEmpty())
                return TOptional<FString>(TEXT("'set_landscape_layer_blend' requires 'layer_name'."));
            P->TryGetNumberField(TEXT("weight"), Weight);
            // Clamp to the legal weight range so the metadata reflects reality.
            const double Clamped = FMath::Clamp(Weight, 0.0, 1.0);
            Kv.Add(TEXT("layer_name"), LayerName);
            Kv.Add(TEXT("weight"), FString::Printf(TEXT("%f"), Clamped));
            Out->SetStringField(TEXT("layer_name"), LayerName);
            Out->SetNumberField(TEXT("weight"), Clamped);
            Out->SetBoolField(TEXT("weight_clamped"), Clamped != Weight);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("set_landscape_layer_blend"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleApplyLandscapeMaterial(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("apply_landscape_material"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("apply_landscape_material"), P,
        [&](ALandscape* L, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            FString MaterialPath;
            if (!P->TryGetStringField(TEXT("material_path"), MaterialPath) || MaterialPath.IsEmpty())
                return TOptional<FString>(TEXT("'apply_landscape_material' requires 'material_path'."));
            UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
            if (!Mat)
                return TOptional<FString>(FString::Printf(TEXT("UMaterialInterface not found at '%s'."), *MaterialPath));
            L->LandscapeMaterial = Mat;
            Kv.Add(TEXT("material_path"), Mat->GetPathName());
            Out->SetStringField(TEXT("material_path"), Mat->GetPathName());
            Out->SetStringField(TEXT("material_name"), Mat->GetName());
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("apply_landscape_material"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeGrassOutput(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("set_landscape_grass_output"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("set_landscape_grass_output"), P,
        [&](ALandscape* L, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            FString GrassTypePath, LayerName;
            P->TryGetStringField(TEXT("grass_type_path"), GrassTypePath);
            P->TryGetStringField(TEXT("layer_name"), LayerName);
            if (GrassTypePath.IsEmpty())
                return TOptional<FString>(TEXT("'set_landscape_grass_output' requires 'grass_type_path'."));
            ULandscapeGrassType* GrassType = LoadObject<ULandscapeGrassType>(nullptr, *GrassTypePath);
            if (!GrassType)
                return TOptional<FString>(FString::Printf(TEXT("ULandscapeGrassType not found at '%s'."), *GrassTypePath));
            Kv.Add(TEXT("grass_type_path"), GrassTypePath);
            if (!LayerName.IsEmpty()) Kv.Add(TEXT("layer_name"), LayerName);
            Out->SetStringField(TEXT("grass_type_path"), GrassType->GetPathName());
            Out->SetStringField(TEXT("grass_type_name"), GrassType->GetName());
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("set_landscape_grass_output"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeCollision(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("set_landscape_collision"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("set_landscape_collision"), P,
        [&](ALandscape* L, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            double MipLevel = L->CollisionMipLevel;
            double SimpleMipLevel = L->SimpleCollisionMipLevel;
            bool bGenerateOverlapEvents = L->bGenerateOverlapEvents;
            P->TryGetNumberField(TEXT("collision_mip_level"), MipLevel);
            P->TryGetNumberField(TEXT("simple_collision_mip_level"), SimpleMipLevel);
            P->TryGetBoolField(TEXT("generate_overlap_events"), bGenerateOverlapEvents);
            L->CollisionMipLevel = (int32)MipLevel;
            L->SimpleCollisionMipLevel = (int32)SimpleMipLevel;
            L->bGenerateOverlapEvents = bGenerateOverlapEvents;
            Kv.Add(TEXT("collision_mip_level"), FString::FromInt((int32)MipLevel));
            Kv.Add(TEXT("simple_collision_mip_level"), FString::FromInt((int32)SimpleMipLevel));
            Kv.Add(TEXT("generate_overlap_events"), bGenerateOverlapEvents ? TEXT("true") : TEXT("false"));
            Out->SetNumberField(TEXT("collision_mip_level"), MipLevel);
            Out->SetNumberField(TEXT("simple_collision_mip_level"), SimpleMipLevel);
            Out->SetBoolField(TEXT("generate_overlap_events"), bGenerateOverlapEvents);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("set_landscape_collision"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleAddLandscapeHole(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("add_landscape_hole"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("add_landscape_hole"), P,
        [&](ALandscape* /*L*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            FString Shape = TEXT("rect");
            double X = 0.0, Y = 0.0, Width = 0.0, Height = 0.0, Radius = 0.0;
            P->TryGetStringField(TEXT("shape"), Shape);
            P->TryGetNumberField(TEXT("x"), X);
            P->TryGetNumberField(TEXT("y"), Y);
            P->TryGetNumberField(TEXT("width"), Width);
            P->TryGetNumberField(TEXT("height"), Height);
            P->TryGetNumberField(TEXT("radius"), Radius);
            Kv.Add(TEXT("shape"), Shape);
            Kv.Add(TEXT("x"), FString::Printf(TEXT("%f"), X));
            Kv.Add(TEXT("y"), FString::Printf(TEXT("%f"), Y));
            Kv.Add(TEXT("width"), FString::Printf(TEXT("%f"), Width));
            Kv.Add(TEXT("height"), FString::Printf(TEXT("%f"), Height));
            Kv.Add(TEXT("radius"), FString::Printf(TEXT("%f"), Radius));
            Out->SetStringField(TEXT("shape"), Shape);
            Out->SetNumberField(TEXT("x"), X);
            Out->SetNumberField(TEXT("y"), Y);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("add_landscape_hole"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleAddLandscapeSpline(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("add_landscape_spline"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("add_landscape_spline"), P,
        [&](ALandscape* /*L*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            const TArray<TSharedPtr<FJsonValue>>* Points = nullptr;
            if (!P->TryGetArrayField(TEXT("points"), Points) || !Points || Points->Num() < 2)
                return TOptional<FString>(TEXT("'add_landscape_spline' requires 'points' (array of >=2 [x,y(,z)] entries)."));
            double SegmentLength = 256.0;
            P->TryGetNumberField(TEXT("segment_length"), SegmentLength);
            Kv.Add(TEXT("point_count"), FString::FromInt(Points->Num()));
            Kv.Add(TEXT("segment_length"), FString::Printf(TEXT("%f"), SegmentLength));
            Out->SetNumberField(TEXT("point_count"), Points->Num());
            Out->SetNumberField(TEXT("segment_length"), SegmentLength);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("add_landscape_spline"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleAddRoadSpline(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("add_road_spline"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("add_road_spline"), P,
        [&](ALandscape* /*L*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            const TArray<TSharedPtr<FJsonValue>>* Points = nullptr;
            if (!P->TryGetArrayField(TEXT("points"), Points) || !Points || Points->Num() < 2)
                return TOptional<FString>(TEXT("'add_road_spline' requires 'points' (array of >=2 [x,y(,z)] entries)."));
            FString MeshPath;
            double RoadWidth = 600.0;
            P->TryGetStringField(TEXT("road_mesh_path"), MeshPath);
            P->TryGetNumberField(TEXT("road_width"), RoadWidth);
            FString ResolvedMeshPath;
            if (!MeshPath.IsEmpty())
            {
                if (UObject* MeshAsset = StaticLoadObject(UObject::StaticClass(), nullptr, *MeshPath))
                {
                    ResolvedMeshPath = MeshAsset->GetPathName();
                }
            }
            Kv.Add(TEXT("point_count"), FString::FromInt(Points->Num()));
            Kv.Add(TEXT("road_width"), FString::Printf(TEXT("%f"), RoadWidth));
            if (!MeshPath.IsEmpty()) Kv.Add(TEXT("road_mesh_path"), MeshPath);
            Out->SetNumberField(TEXT("point_count"), Points->Num());
            Out->SetNumberField(TEXT("road_width"), RoadWidth);
            if (!ResolvedMeshPath.IsEmpty()) Out->SetStringField(TEXT("road_mesh_path"), ResolvedMeshPath);
            Out->SetBoolField(TEXT("mesh_resolved"), !ResolvedMeshPath.IsEmpty());
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("add_road_spline"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleCarveRiverTerrain(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("carve_river_terrain"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("carve_river_terrain"), P,
        [&](ALandscape* /*L*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            FString WaterBodyActor;
            double CarveDepth = 200.0, BankSlope = 0.0;
            P->TryGetStringField(TEXT("water_body_actor"), WaterBodyActor);
            P->TryGetNumberField(TEXT("carve_depth"), CarveDepth);
            P->TryGetNumberField(TEXT("bank_slope"), BankSlope);
            if (!WaterBodyActor.IsEmpty()) Kv.Add(TEXT("water_body_actor"), WaterBodyActor);
            Kv.Add(TEXT("carve_depth"), FString::Printf(TEXT("%f"), CarveDepth));
            Kv.Add(TEXT("bank_slope"), FString::Printf(TEXT("%f"), BankSlope));
            Out->SetStringField(TEXT("water_body_actor"), WaterBodyActor);
            Out->SetNumberField(TEXT("carve_depth"), CarveDepth);
            Out->SetNumberField(TEXT("bank_slope"), BankSlope);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("carve_river_terrain"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleAttachLandscapeRvt(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("attach_landscape_rvt"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("attach_landscape_rvt"), P,
        [&](ALandscape* L, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            FString RvtPath;
            if (!P->TryGetStringField(TEXT("rvt_path"), RvtPath) || RvtPath.IsEmpty())
                return TOptional<FString>(TEXT("'attach_landscape_rvt' requires 'rvt_path'."));
            URuntimeVirtualTexture* Rvt = LoadObject<URuntimeVirtualTexture>(nullptr, *RvtPath);
            if (!Rvt)
                return TOptional<FString>(FString::Printf(TEXT("URuntimeVirtualTexture not found at '%s'."), *RvtPath));
            // UE 5.7: ALandscape exposes RuntimeVirtualTextures (TArray<URuntimeVirtualTexture*>).
            L->RuntimeVirtualTextures.AddUnique(Rvt);
            Kv.Add(TEXT("rvt_path"), Rvt->GetPathName());
            Out->SetStringField(TEXT("rvt_path"), Rvt->GetPathName());
            Out->SetNumberField(TEXT("attached_rvt_count"), L->RuntimeVirtualTextures.Num());
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("attach_landscape_rvt"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeNanite(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("set_landscape_nanite"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("set_landscape_nanite"), P,
        [&](ALandscape* L, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            bool bEnable = L->bEnableNanite;
            P->TryGetBoolField(TEXT("enable_nanite"), bEnable);
            L->bEnableNanite = bEnable;
            Kv.Add(TEXT("enable_nanite"), bEnable ? TEXT("true") : TEXT("false"));
            Out->SetBoolField(TEXT("enable_nanite"), bEnable);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("set_landscape_nanite"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeWorldPartition(const TSharedPtr<FJsonObject>& P)
{
    if (!IsLandscapeAvailable()) return MakeLandscapeUnavailableResponse(TEXT("set_landscape_world_partition"));
#if WITH_LANDSCAPE_MCP
    return LandscapeMetaPersist(TEXT("set_landscape_world_partition"), P,
        [&](ALandscape* L, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Out) -> TOptional<FString>
        {
            bool bIncludeInWP = L->bIncludeGridSizeInNameForLandscapeActors;
            double GridSize = 2.0;
            P->TryGetBoolField(TEXT("include_grid_size_in_name"), bIncludeInWP);
            P->TryGetNumberField(TEXT("wp_grid_size"), GridSize);
            L->bIncludeGridSizeInNameForLandscapeActors = bIncludeInWP;
            Kv.Add(TEXT("include_grid_size_in_name"), bIncludeInWP ? TEXT("true") : TEXT("false"));
            Kv.Add(TEXT("wp_grid_size"), FString::Printf(TEXT("%f"), GridSize));
            Out->SetBoolField(TEXT("include_grid_size_in_name"), bIncludeInWP);
            Out->SetNumberField(TEXT("wp_grid_size"), GridSize);
            return TOptional<FString>();
        });
#else
    return MakeLandscapeUnavailableResponse(TEXT("set_landscape_world_partition"));
#endif
}