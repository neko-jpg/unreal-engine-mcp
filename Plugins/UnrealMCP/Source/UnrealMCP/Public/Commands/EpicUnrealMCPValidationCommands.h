#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Validation handler class (Phase 4 / Issue #31 split from
 * FEpicUnrealMCPProceduralCommands).
 *
 * Hosts compile_all_blueprints / run_map_check / find_broken_references.
 * Routed under id 23 by FEpicUnrealMCPRouter.
 */
class UNREALMCP_API FEpicUnrealMCPValidationCommands
{
public:
    FEpicUnrealMCPValidationCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    UWorld* GetEditorWorld() const;

    TSharedPtr<FJsonObject> HandleCompileAllBlueprints(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRunMapCheck(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleFindBrokenReferences(const TSharedPtr<FJsonObject>& Params);
};
