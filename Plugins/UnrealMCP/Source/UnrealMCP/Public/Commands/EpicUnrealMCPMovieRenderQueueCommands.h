#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPMovieRenderQueueCommands
{
public:
    FEpicUnrealMCPMovieRenderQueueCommands();
    ~FEpicUnrealMCPMovieRenderQueueCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateMrqJob(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSequenceToMrq(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqOutputDirectory(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqResolution(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqFrameRange(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqAntiAliasing(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqExrOutput(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqPngOutput(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqJpgOutput(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqVideoOutput(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqPathTracer(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqConsoleVariables(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMrqRenderPass(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqObjectIdPass(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqBurnIn(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMrqWarmUp(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleStartMrqRender(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCancelMrqRender(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetMrqRenderProgress(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleVerifyMrqRenderResult(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateMovieRenderGraph(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
