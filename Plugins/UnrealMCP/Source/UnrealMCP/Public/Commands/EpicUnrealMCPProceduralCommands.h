#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Handler class for procedural generation commands (route 19).
 *
 * Phase 4 (Issue #31) extracted Physics, Validation, and Draft/Instance
 * commands into dedicated handler classes:
 *   - FEpicUnrealMCPPhysicsCommands     (route 22)
 *   - FEpicUnrealMCPValidationCommands  (route 23)
 *   - FEpicUnrealMCPInstanceCommands    (route 24)
 *
 * What remains here is the procedural-generation surface itself plus
 * request_cognitive_processing (a single command that does not yet
 * justify its own handler class).
 */
class UNREALMCP_API FEpicUnrealMCPProceduralCommands
{
public:
    FEpicUnrealMCPProceduralCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    UWorld* GetEditorWorld() const;

    // Procedural generation
    TSharedPtr<FJsonObject> HandleSpawnTileGrid(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnProceduralActorBatch(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateSplineMeshFromSegments(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateDataLayerForGeneration(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleClearGeneratedGroup(const TSharedPtr<FJsonObject>& Params);

    // Cognitive processing (single-command surface kept here for now)
    TSharedPtr<FJsonObject> HandleRequestCognitiveProcessing(const TSharedPtr<FJsonObject>& Params);
};
