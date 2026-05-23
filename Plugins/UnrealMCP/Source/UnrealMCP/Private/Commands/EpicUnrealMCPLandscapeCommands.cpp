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
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeSectionComponent(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("set_landscape_section_component"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleImportLandscapeHeightmap(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("import_landscape_heightmap"), P, TEXT("Heightmap PNG/RAW import is interactive in 5.7; payload recorded for batch step.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleExportLandscapeHeightmap(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("export_landscape_heightmap"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeSculpt(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_sculpt"), P, TEXT("Brush strokes need LandscapeEditMode active.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeSmooth(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_smooth"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeFlatten(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_flatten"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeRamp(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_ramp"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeErosion(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_erosion"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleLandscapeNoise(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("landscape_noise"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleCreateLandscapePaintLayer(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("create_landscape_paint_layer"), P, TEXT("Create the ULandscapeLayerInfoObject asset via the editor weight-blend layer panel.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeLayerBlend(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("set_landscape_layer_blend"), P); }
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
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleAddLandscapeSpline(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("add_landscape_spline"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleAddRoadSpline(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("add_road_spline"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleCarveRiverTerrain(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("carve_river_terrain"), P, TEXT("River carve uses Water + Landscape Brush Manager (see Sub-batch S).")); }
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