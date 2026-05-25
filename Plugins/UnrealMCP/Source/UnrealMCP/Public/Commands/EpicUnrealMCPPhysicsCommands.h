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

    // W1-B Physics residue (UE 5.7, non-Chaos)
    TSharedPtr<FJsonObject> HandleSetActorCollisionResponse(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetConstraintLimits(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetConstraintMotor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnPhysicsVolume(const TSharedPtr<FJsonObject>& Params);

    // Spatial queries (React-for-UE v3.0)
    TSharedPtr<FJsonObject> HandleGetActorBounds(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpatialOverlapSphere(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpatialRaycast(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpatialLinecast(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpatialNearest(const TSharedPtr<FJsonObject>& Params);
};
