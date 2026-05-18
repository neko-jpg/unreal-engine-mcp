#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Instance / Draft-proxy handler class (Phase 4 / Issue #31 split from
 * FEpicUnrealMCPProceduralCommands).
 *
 * Hosts the HISM/ISM bulk-instancing surface plus the Draft Proxy
 * visualisation helpers.  Routed under id 24 by FEpicUnrealMCPRouter.
 *
 * Commands:
 *   - create_draft_proxy / update_draft_proxy / delete_draft_proxy
 *   - spawn_instance_set / update_instance_set / delete_instance_set
 *   - get_instance_set_state / list_instance_sets
 */
class UNREALMCP_API FEpicUnrealMCPInstanceCommands
{
public:
    FEpicUnrealMCPInstanceCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    UWorld* GetEditorWorld() const;

    // Draft proxy (HISM visualization)
    TSharedPtr<FJsonObject> HandleCreateDraftProxy(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleUpdateDraftProxy(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleDeleteDraftProxy(const TSharedPtr<FJsonObject>& Params);

    // InstanceSet commands (HISM/ISM bulk instancing)
    TSharedPtr<FJsonObject> HandleSpawnInstanceSet(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleUpdateInstanceSet(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleDeleteInstanceSet(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetInstanceSetState(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleListInstanceSets(const TSharedPtr<FJsonObject>& Params);
};
