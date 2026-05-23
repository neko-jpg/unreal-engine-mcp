#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPSequencerExtensionCommands
{
public:
    FEpicUnrealMCPSequencerExtensionCommands();
    ~FEpicUnrealMCPSequencerExtensionCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleSpawnCameraRail(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnCameraCrane(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSequencerRenderPreview(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRegisterTakeRecorderSource(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddControlRigTrack(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnLevelSequenceActor(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
