#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPDataTableExtensionCommands
{
public:
    FEpicUnrealMCPDataTableExtensionCommands();
    ~FEpicUnrealMCPDataTableExtensionCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateRowStruct(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleEditRowStruct(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleEditDataAssetProperties(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleImportGameplayTagTable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGenerateItemDbTemplate(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGenerateEnemyDbTemplate(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGenerateQuestDbTemplate(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGenerateDialogueDbTemplate(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateBlueprintDatatableReferenceNode(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
