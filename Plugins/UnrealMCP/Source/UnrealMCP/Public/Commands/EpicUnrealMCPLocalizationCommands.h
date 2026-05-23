#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPLocalizationCommands
{
public:
    FEpicUnrealMCPLocalizationCommands();
    ~FEpicUnrealMCPLocalizationCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleOpenLocalizationDashboard(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddLocalizationCulture(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRunTextGather(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleExportPoFiles(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleImportPoFiles(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateStringTable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleEditStringTable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleLocalizeWidgetText(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleLocalizeDialogueWave(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureFontFallback(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
