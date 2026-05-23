#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPPCGCommands
{
public:
    FEpicUnrealMCPPCGCommands();
    ~FEpicUnrealMCPPCGCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreatePcgGraph(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddPcgComponent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreatePcgVolume(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddPcgNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConnectPcgNodes(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetPcgGraphParameter(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigurePcgSplineSampler(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigurePcgSurfaceSampler(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigurePcgStaticMeshSpawner(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigurePcgRule(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreatePcgBiomeGraph(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleOperatePcgPointData(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleOperatePcgAttribute(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleExecutePcgGraph(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRegeneratePcgGraph(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetPcgRuntimeGeneration(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleUsePcgEditorMode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreatePcgTool(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetPcgDebugDisplay(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigurePcgSelfPruning(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
