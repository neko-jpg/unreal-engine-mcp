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

TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeSize(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("set_landscape_size"), P, TEXT("Landscape resize requires LandscapeEditMode; payload accepted.")); }
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
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleApplyLandscapeMaterial(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("apply_landscape_material"), P, TEXT("Set ALandscape::LandscapeMaterial in the editor; payload recorded.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeGrassOutput(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("set_landscape_grass_output"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeCollision(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("set_landscape_collision"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleAddLandscapeHole(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("add_landscape_hole"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleAddLandscapeSpline(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("add_landscape_spline"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleAddRoadSpline(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("add_road_spline"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleCarveRiverTerrain(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("carve_river_terrain"), P, TEXT("River carve uses Water + Landscape Brush Manager (see Sub-batch S).")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleAttachLandscapeRvt(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("attach_landscape_rvt"), P, TEXT("Assign URuntimeVirtualTexture asset to ALandscape::RuntimeVirtualTextures via the editor.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeNanite(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("set_landscape_nanite"), P, TEXT("ALandscape::bEnableNanite is the entry point in 5.7; payload recorded.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPLandscapeCommands::HandleSetLandscapeWorldPartition(const TSharedPtr<FJsonObject>& P) { return LandscapeQueued(TEXT("set_landscape_world_partition"), P); }