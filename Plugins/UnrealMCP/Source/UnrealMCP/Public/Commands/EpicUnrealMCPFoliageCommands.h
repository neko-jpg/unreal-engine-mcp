#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPFoliageCommands
{
public:
    FEpicUnrealMCPFoliageCommands();
    ~FEpicUnrealMCPFoliageCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateFoliageType(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRegisterStaticMeshFoliage(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRegisterActorFoliage(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleFoliagePaint(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleFoliageErase(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetFoliageDensity(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetFoliageScaleRange(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetFoliageRandomYaw(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetFoliageAlignToNormal(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetFoliageCullDistance(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetFoliageLod(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateProceduralFoliageSpawner(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateProceduralFoliageVolume(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetProceduralFoliageSeed(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnBiomeFoliage(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateGrassType(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleBindLandscapeGrass(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetFoliageNanite(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetFoliageWind(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigurePivotPainter(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
