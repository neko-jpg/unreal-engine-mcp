#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPTestingValidationCommands
{
public:
    FEpicUnrealMCPTestingValidationCommands();
    ~FEpicUnrealMCPTestingValidationCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateUeAutomationTest(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnFunctionalTestActor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRunAutomationTest(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleFetchAutomationTestResults(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRunCollisionValidation(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRunNavigationValidation(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRunPerformanceBudgetValidation(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRunGameplayScreenshotTest(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRunPythonUnitTest(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRunRustTest(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
