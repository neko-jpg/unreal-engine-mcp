#pragma once
#include "CoreMinimal.h"
#include "Json.h"

/**
 * Handler class for Landscape / Terrain MCP commands (Sub-batch J, route 25,
 * issue #43).
 *
 * UE 5.7 Notes:
 *   - Landscape is a Runtime module (Engine/Source/Runtime/Landscape).
 *   - LandscapeEditor is the editor-only sculpt/paint subsystem.
 *   - Build.cs probes for Landscape headers and defines WITH_LANDSCAPE_MCP=1
 *     when the module is reachable. Most sculpt brushes (smooth/flatten/etc)
 *     require the editor's interactive landscape mode; those commands return
 *     a structured "queued" envelope so the caller knows the payload was
 *     accepted and what manual step finishes the work.
 *
 * 23 commands map 1:1 to tasks.md / Landscape section items.
 */
class FEpicUnrealMCPLandscapeCommands
{
public:
    FEpicUnrealMCPLandscapeCommands();
    ~FEpicUnrealMCPLandscapeCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    // Asset / actor creation
    TSharedPtr<FJsonObject> HandleCreateLandscape(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetLandscapeSize(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetLandscapeSectionComponent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleImportLandscapeHeightmap(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleExportLandscapeHeightmap(const TSharedPtr<FJsonObject>& Params);

    // Sculpt brushes (queued payload)
    TSharedPtr<FJsonObject> HandleLandscapeSculpt(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleLandscapeSmooth(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleLandscapeFlatten(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleLandscapeRamp(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleLandscapeErosion(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleLandscapeNoise(const TSharedPtr<FJsonObject>& Params);

    // Painting / materials / collision
    TSharedPtr<FJsonObject> HandleCreateLandscapePaintLayer(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetLandscapeLayerBlend(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleApplyLandscapeMaterial(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetLandscapeGrassOutput(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetLandscapeCollision(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddLandscapeHole(const TSharedPtr<FJsonObject>& Params);

    // Splines
    TSharedPtr<FJsonObject> HandleAddLandscapeSpline(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddRoadSpline(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCarveRiverTerrain(const TSharedPtr<FJsonObject>& Params);

    // Advanced
    TSharedPtr<FJsonObject> HandleAttachLandscapeRvt(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetLandscapeNanite(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetLandscapeWorldPartition(const TSharedPtr<FJsonObject>& Params);

    // Helpers
    static bool IsLandscapeAvailable();
    static TSharedPtr<FJsonObject> MakeLandscapeUnavailableResponse(const FString& CommandName);
};