#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPMobileXrCommands
{
public:
    FEpicUnrealMCPMobileXrCommands();
    ~FEpicUnrealMCPMobileXrCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleConfigureAndroidSettings(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureIosSettings(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureMobileRendering(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureTouchInput(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetDeviceProfile(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateScalabilityProfile(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleEnableXrPlugin(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureOpenxr(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnVrPawn(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureMotionController(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureHmdCamera(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureArSession(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureArPlaneDetection(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandlePlatformSpecificPackaging(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
