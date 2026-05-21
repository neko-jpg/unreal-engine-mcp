#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Physics handler class (Phase 4 / Issue #31 split from
 * FEpicUnrealMCPProceduralCommands).
 *
 * Hosts the collision / physics-body / physical-material / radial-force /
 * physics-constraint commands.  Routed under id 22 by
 * FEpicUnrealMCPRouter.
 */
class UNREALMCP_API FEpicUnrealMCPPhysicsCommands
{
public:
    FEpicUnrealMCPPhysicsCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    UWorld* GetEditorWorld() const;

    TSharedPtr<FJsonObject> HandleSetActorCollisionPreset(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetActorPhysics(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreatePhysicalMaterial(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnRadialForce(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnPhysicsConstraint(const TSharedPtr<FJsonObject>& Params);
};
