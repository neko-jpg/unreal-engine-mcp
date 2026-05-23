#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPWaterCommands
{
public:
    FEpicUnrealMCPWaterCommands();
    ~FEpicUnrealMCPWaterCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleEnableWaterPlugin(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnWaterBodyOcean(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnWaterBodyLake(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnWaterBodyRiver(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnWaterBodyCustom(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureRiverSpline(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetWaterMaterial(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureWaterWave(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureWaterFlow(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureBuoyancy(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureWaterMeshActor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureUnderwaterPostProcess(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureShoreline(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureWaterLandscapeCarving(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAttachFloatingActor(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
