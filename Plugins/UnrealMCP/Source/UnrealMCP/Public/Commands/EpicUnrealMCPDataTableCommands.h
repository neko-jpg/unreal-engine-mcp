#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Handler class for Data Table MCP commands.
 */
class FEpicUnrealMCPDataTableCommands
{
public:
    FEpicUnrealMCPDataTableCommands();
    ~FEpicUnrealMCPDataTableCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateDataTable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleImportCSVToDataTable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddDataTableRow(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleDeleteDataTableRow(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleUpdateDataTableRow(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleExportDataTableCSV(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleExportDataTableJSON(const TSharedPtr<FJsonObject>& Params);

    // W1-B Data Tables residue (UE 5.7)
    TSharedPtr<FJsonObject> HandleCreateDataTableFromJSON(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateCurveTable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateStringTable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetStringTableEntry(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateDataAsset(const TSharedPtr<FJsonObject>& Params);

    // Helper to find a UScriptStruct by path
    UScriptStruct* FindRowStruct(const FString& StructPath, FString& OutError);
    // Helper to set struct property from JSON value
    bool SetStructProperty(void* StructMemory, FProperty* Property, const TSharedPtr<FJsonValue>& JsonValue, FString& OutError);
};
