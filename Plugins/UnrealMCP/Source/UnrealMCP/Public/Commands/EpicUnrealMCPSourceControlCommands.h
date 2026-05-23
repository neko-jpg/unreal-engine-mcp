#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPSourceControlCommands
{
public:
    FEpicUnrealMCPSourceControlCommands();
    ~FEpicUnrealMCPSourceControlCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleRegisterGitProvider(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRegisterPerforceProvider(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSourceControlCheckout(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSourceControlCheckin(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSourceControlRevert(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSourceControlFileLockAcquire(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSourceControlFileLockRelease(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSourceControlCreateChangelist(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSourceControlAssetDiff(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSourceControlBlueprintDiff(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSourceControlMerge(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleMultiUserEditingStart(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleMultiUserSessionJoin(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
