#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPChaosCommands
{
public:
    FEpicUnrealMCPChaosCommands();
    ~FEpicUnrealMCPChaosCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateCollisionChannel(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateObjectChannel(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateTraceChannel(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateGeometryCollection(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleFractureGeometryCollection(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateChaosField(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureChaosSolver(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateChaosCache(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateChaosVehicle(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetVehicleWheel(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetVehicleSuspension(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetVehicleEngineTorque(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetClothSettings(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateChaosClothAsset(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetGroomPhysics(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetRagdoll(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleEditPhysicsAssetBody(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleEditPhysicsAssetConstraint(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAttachChaosVisualDebugger(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
