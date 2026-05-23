#include "Commands/EpicUnrealMCPDataTableCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"
#include "Engine/DataTable.h"
#include "Engine/EngineTypes.h"
#include "UObject/Package.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/Paths.h"
#include "HAL/PlatformFilemanager.h"
#include "Misc/FileHelper.h"
#include "Engine/CurveTable.h"
#include "Internationalization/StringTable.h"
#include "Internationalization/StringTableCore.h"
#include "Engine/DataAsset.h"
#include "Engine/AssetManagerTypes.h"

FEpicUnrealMCPDataTableCommands::FEpicUnrealMCPDataTableCommands()
{
}

FEpicUnrealMCPDataTableCommands::~FEpicUnrealMCPDataTableCommands()
{
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPDataTableCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_data_table"), &FEpicUnrealMCPDataTableCommands::HandleCreateDataTable},
        {TEXT("import_csv_to_data_table"), &FEpicUnrealMCPDataTableCommands::HandleImportCSVToDataTable},
        {TEXT("add_data_table_row"), &FEpicUnrealMCPDataTableCommands::HandleAddDataTableRow},
        {TEXT("delete_data_table_row"), &FEpicUnrealMCPDataTableCommands::HandleDeleteDataTableRow},
        {TEXT("update_data_table_row"), &FEpicUnrealMCPDataTableCommands::HandleUpdateDataTableRow},
        {TEXT("export_data_table_csv"), &FEpicUnrealMCPDataTableCommands::HandleExportDataTableCSV},
        {TEXT("export_data_table_json"), &FEpicUnrealMCPDataTableCommands::HandleExportDataTableJSON},
        {TEXT("create_data_table_from_json"), &FEpicUnrealMCPDataTableCommands::HandleCreateDataTableFromJSON},
        {TEXT("create_curve_table"), &FEpicUnrealMCPDataTableCommands::HandleCreateCurveTable},
        {TEXT("create_string_table"), &FEpicUnrealMCPDataTableCommands::HandleCreateStringTable},
        {TEXT("set_string_table_entry"), &FEpicUnrealMCPDataTableCommands::HandleSetStringTableEntry},
        {TEXT("create_data_asset"), &FEpicUnrealMCPDataTableCommands::HandleCreateDataAsset},
    };

    const Handler* H = Dispatch.Find(CommandType);
    if (H)
    {
        return (this->*(*H))(Params);
    }

    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown data table command: %s"), *CommandType));
}

UScriptStruct* FEpicUnrealMCPDataTableCommands::FindRowStruct(const FString& StructPath, FString& OutError)
{
    // Try loading as an object path first (e.g., /Game/MyStruct.MyStruct)
    UScriptStruct* RowStruct = LoadObject<UScriptStruct>(nullptr, *StructPath);
    if (RowStruct)
    {
        return RowStruct;
    }

    // Try finding by name in memory
    RowStruct = FindObject<UScriptStruct>(nullptr, *StructPath);
    if (RowStruct)
    {
        return RowStruct;
    }

    OutError = FString::Printf(TEXT("Row struct not found: %s"), *StructPath);
    return nullptr;
}

bool FEpicUnrealMCPDataTableCommands::SetStructProperty(void* StructMemory, FProperty* Property, const TSharedPtr<FJsonValue>& JsonValue, FString& OutError)
{
    if (!Property || !JsonValue.IsValid())
    {
        OutError = TEXT("Invalid property or JSON value");
        return false;
    }

    void* PropertyValue = Property->ContainerPtrToValuePtr<void>(StructMemory);

    if (FNumericProperty* NumericProp = CastField<FNumericProperty>(Property))
    {
        if (NumericProp->IsInteger())
        {
            NumericProp->SetIntPropertyValue(PropertyValue, static_cast<int64>(JsonValue->AsNumber()));
        }
        else
        {
            NumericProp->SetFloatingPointPropertyValue(PropertyValue, JsonValue->AsNumber());
        }
        return true;
    }
    else if (FBoolProperty* BoolProp = CastField<FBoolProperty>(Property))
    {
        BoolProp->SetPropertyValue(PropertyValue, JsonValue->AsBool());
        return true;
    }
    else if (FStrProperty* StrProp = CastField<FStrProperty>(Property))
    {
        StrProp->SetPropertyValue(PropertyValue, JsonValue->AsString());
        return true;
    }
    else if (FNameProperty* NameProp = CastField<FNameProperty>(Property))
    {
        NameProp->SetPropertyValue(PropertyValue, FName(*JsonValue->AsString()));
        return true;
    }
    else if (FTextProperty* TextProp = CastField<FTextProperty>(Property))
    {
        TextProp->SetPropertyValue(PropertyValue, FText::FromString(JsonValue->AsString()));
        return true;
    }
    else if (FStructProperty* StructProp = CastField<FStructProperty>(Property))
    {
        if (StructProp->Struct == TBaseStructure<FVector>::Get())
        {
            const TArray<TSharedPtr<FJsonValue>>* Array = nullptr;
            if (JsonValue->TryGetArray(Array) && Array->Num() >= 3)
            {
                FVector* Vec = static_cast<FVector*>(PropertyValue);
                Vec->X = static_cast<float>((*Array)[0]->AsNumber());
                Vec->Y = static_cast<float>((*Array)[1]->AsNumber());
                Vec->Z = static_cast<float>((*Array)[2]->AsNumber());
                return true;
            }
            OutError = TEXT("FVector property expects [X, Y, Z] array");
            return false;
        }
        else if (StructProp->Struct == TBaseStructure<FLinearColor>::Get())
        {
            const TArray<TSharedPtr<FJsonValue>>* Array = nullptr;
            if (JsonValue->TryGetArray(Array) && Array->Num() >= 3)
            {
                FLinearColor* Color = static_cast<FLinearColor*>(PropertyValue);
                Color->R = static_cast<float>((*Array)[0]->AsNumber());
                Color->G = static_cast<float>((*Array)[1]->AsNumber());
                Color->B = static_cast<float>((*Array)[2]->AsNumber());
                if (Array->Num() >= 4)
                {
                    Color->A = static_cast<float>((*Array)[3]->AsNumber());
                }
                return true;
            }
            OutError = TEXT("FLinearColor property expects [R, G, B, A] array");
            return false;
        }
        OutError = FString::Printf(TEXT("Unsupported struct type for property %s"), *Property->GetName());
        return false;
    }

    OutError = FString::Printf(TEXT("Unsupported property type for %s"), *Property->GetName());
    return false;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleCreateDataTable(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'table_path' parameter (e.g. /Game/Data/MyTable)"));
    }

    FString RowStructPath;
    if (!Params->TryGetStringField(TEXT("row_struct_path"), RowStructPath) || RowStructPath.IsEmpty())
    {
        // Default to a common built-in struct if available, otherwise error
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'row_struct_path' parameter"));
    }

    FString Error;
    UScriptStruct* RowStruct = FindRowStruct(RowStructPath, Error);
    if (!RowStruct)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(Error);
    }

    FString TableName = FPaths::GetBaseFilename(TablePath);
    UPackage* Package = CreatePackage(*TablePath);
    if (!Package)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package for data table"));
    }

    UDataTable* NewDataTable = NewObject<UDataTable>(Package, FName(*TableName), RF_Public | RF_Standalone);
    if (!NewDataTable)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create DataTable object"));
    }

    NewDataTable->RowStruct = RowStruct;
    Package->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(NewDataTable);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetStringField(TEXT("table_name"), TableName);
    Result->SetStringField(TEXT("row_struct"), RowStruct->GetName());
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleImportCSVToDataTable(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'table_path' parameter"));
    }

    FString CSVContent;
    if (!Params->TryGetStringField(TEXT("csv_content"), CSVContent) || CSVContent.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'csv_content' parameter"));
    }

    UDataTable* DataTable = LoadObject<UDataTable>(nullptr, *TablePath);
    if (!DataTable)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("DataTable not found: %s"), *TablePath));
    }

    TArray<FString> Errors = DataTable->CreateTableFromCSVString(CSVContent);
    if (Errors.Num() > 0)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("CSV import errors: %s"), *FString::Join(Errors, TEXT("; "))));
    }

    DataTable->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetNumberField(TEXT("row_count"), DataTable->GetRowMap().Num());
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleAddDataTableRow(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'table_path' parameter"));
    }

    FString RowName;
    if (!Params->TryGetStringField(TEXT("row_name"), RowName) || RowName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'row_name' parameter"));
    }

    const TSharedPtr<FJsonObject>* RowDataObj = nullptr;
    if (!Params->TryGetObjectField(TEXT("row_data"), RowDataObj) || !RowDataObj->IsValid())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or invalid 'row_data' parameter (JSON object)"));
    }

    UDataTable* DataTable = LoadObject<UDataTable>(nullptr, *TablePath);
    if (!DataTable)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("DataTable not found: %s"), *TablePath));
    }

    UScriptStruct* RowStruct = DataTable->RowStruct;
    if (!RowStruct)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("DataTable has no RowStruct assigned"));
    }

    // Allocate memory for the row struct
    uint8* RowMemory = static_cast<uint8*>(FMemory::Malloc(RowStruct->GetStructureSize()));
    RowStruct->InitializeStruct(RowMemory);

    // Set properties from JSON
    for (const auto& Pair : (*RowDataObj)->Values)
    {
        FProperty* Property = RowStruct->FindPropertyByName(FName(*Pair.Key));
        if (!Property)
        {
            FMemory::Free(RowMemory);
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Property '%s' not found in row struct"), *Pair.Key));
        }

        FString Error;
        if (!SetStructProperty(RowMemory, Property, Pair.Value, Error))
        {
            FMemory::Free(RowMemory);
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(Error);
        }
    }

    // Add row to table (this copies the memory)
    DataTable->AddRow(FName(*RowName), RowMemory, RowStruct);

    // Free our temporary allocation
    RowStruct->DestroyStruct(RowMemory);
    FMemory::Free(RowMemory);

    DataTable->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetStringField(TEXT("row_name"), RowName);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleDeleteDataTableRow(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'table_path' parameter"));
    }

    FString RowName;
    if (!Params->TryGetStringField(TEXT("row_name"), RowName) || RowName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'row_name' parameter"));
    }

    UDataTable* DataTable = LoadObject<UDataTable>(nullptr, *TablePath);
    if (!DataTable)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("DataTable not found: %s"), *TablePath));
    }

    const TMap<FName, uint8*>& RowMap = DataTable->GetRowMap();
    if (!RowMap.Contains(FName(*RowName)))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Row '%s' not found in DataTable"), *RowName));
    }

    DataTable->RemoveRow(FName(*RowName));
    DataTable->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetStringField(TEXT("row_name"), RowName);
    Result->SetNumberField(TEXT("row_count"), DataTable->GetRowMap().Num());
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleUpdateDataTableRow(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'table_path' parameter"));
    }

    FString RowName;
    if (!Params->TryGetStringField(TEXT("row_name"), RowName) || RowName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'row_name' parameter"));
    }

    const TSharedPtr<FJsonObject>* RowDataObj = nullptr;
    if (!Params->TryGetObjectField(TEXT("row_data"), RowDataObj) || !RowDataObj->IsValid())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or invalid 'row_data' parameter (JSON object)"));
    }

    UDataTable* DataTable = LoadObject<UDataTable>(nullptr, *TablePath);
    if (!DataTable)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("DataTable not found: %s"), *TablePath));
    }

    UScriptStruct* RowStruct = DataTable->RowStruct;
    if (!RowStruct)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("DataTable has no RowStruct assigned"));
    }

    // Remove existing row if present
    const TMap<FName, uint8*>& RowMap = DataTable->GetRowMap();
    const bool bRowExisted = RowMap.Contains(FName(*RowName));
    if (bRowExisted)
    {
        DataTable->RemoveRow(FName(*RowName));
    }

    // Allocate memory for the row struct
    uint8* RowMemory = static_cast<uint8*>(FMemory::Malloc(RowStruct->GetStructureSize()));
    RowStruct->InitializeStruct(RowMemory);

    // Set properties from JSON
    for (const auto& Pair : (*RowDataObj)->Values)
    {
        FProperty* Property = RowStruct->FindPropertyByName(FName(*Pair.Key));
        if (!Property)
        {
            RowStruct->DestroyStruct(RowMemory);
            FMemory::Free(RowMemory);
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Property '%s' not found in row struct"), *Pair.Key));
        }

        FString Error;
        if (!SetStructProperty(RowMemory, Property, Pair.Value, Error))
        {
            RowStruct->DestroyStruct(RowMemory);
            FMemory::Free(RowMemory);
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(Error);
        }
    }

    // Add row to table (this copies the memory)
    DataTable->AddRow(FName(*RowName), RowMemory, RowStruct);

    // Free our temporary allocation
    RowStruct->DestroyStruct(RowMemory);
    FMemory::Free(RowMemory);

    DataTable->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetStringField(TEXT("row_name"), RowName);
    Result->SetBoolField(TEXT("row_existed"), bRowExisted);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleExportDataTableCSV(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'table_path' parameter"));
    }

    UDataTable* DataTable = LoadObject<UDataTable>(nullptr, *TablePath);
    if (!DataTable)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("DataTable not found: %s"), *TablePath));
    }

    FString CSVContent = DataTable->GetTableAsCSV();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetStringField(TEXT("csv_content"), CSVContent);
    Result->SetNumberField(TEXT("row_count"), DataTable->GetRowMap().Num());
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleExportDataTableJSON(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'table_path' parameter"));
    }

    UDataTable* DataTable = LoadObject<UDataTable>(nullptr, *TablePath);
    if (!DataTable)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("DataTable not found: %s"), *TablePath));
    }

    FString JSONContent = DataTable->GetTableAsJSON();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetStringField(TEXT("json_content"), JSONContent);
    Result->SetNumberField(TEXT("row_count"), DataTable->GetRowMap().Num());
    return Result;
}

// W1-B_DATATABLE_BEGIN
// W1-B Data Tables residue (UE 5.7): JSON DataTable / CurveTable / StringTable /
// SetStringTableEntry / CreateDataAsset.

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleCreateDataTableFromJSON(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'table_path' parameter"));
    FString RowStructPath;
    if (!Params->TryGetStringField(TEXT("row_struct_path"), RowStructPath) || RowStructPath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'row_struct_path' parameter"));
    FString JsonContent;
    if (!Params->TryGetStringField(TEXT("json_content"), JsonContent) || JsonContent.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'json_content' parameter"));

    FString Error;
    UScriptStruct* RowStruct = FindRowStruct(RowStructPath, Error);
    if (!RowStruct)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(Error);

    UDataTable* DataTable = LoadObject<UDataTable>(nullptr, *TablePath);
    bool bNewlyCreated = false;
    if (!DataTable)
    {
        FString TableName = FPaths::GetBaseFilename(TablePath);
        UPackage* Package = CreatePackage(*TablePath);
        if (!Package)
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package for data table"));
        DataTable = NewObject<UDataTable>(Package, FName(*TableName), RF_Public | RF_Standalone);
        if (!DataTable)
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create DataTable object"));
        DataTable->RowStruct = RowStruct;
        FAssetRegistryModule::AssetCreated(DataTable);
        bNewlyCreated = true;
    }
    else
    {
        DataTable->RowStruct = RowStruct;
    }

    TArray<FString> Errors = DataTable->CreateTableFromJSONString(JsonContent);
    if (Errors.Num() > 0)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("JSON import errors: %s"), *FString::Join(Errors, TEXT("; "))));
    }
    DataTable->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetStringField(TEXT("row_struct"), RowStruct->GetName());
    Result->SetNumberField(TEXT("row_count"), DataTable->GetRowMap().Num());
    Result->SetBoolField(TEXT("newly_created"), bNewlyCreated);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleCreateCurveTable(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'table_path' parameter"));
    FString CsvContent;
    Params->TryGetStringField(TEXT("csv_content"), CsvContent);
    FString InterpModeStr = TEXT("Linear");
    Params->TryGetStringField(TEXT("interp_mode"), InterpModeStr);

    ERichCurveInterpMode InterpMode = RCIM_Linear;
    if (InterpModeStr.Equals(TEXT("Cubic"), ESearchCase::IgnoreCase)) InterpMode = RCIM_Cubic;
    else if (InterpModeStr.Equals(TEXT("Constant"), ESearchCase::IgnoreCase)) InterpMode = RCIM_Constant;

    UCurveTable* CurveTable = LoadObject<UCurveTable>(nullptr, *TablePath);
    bool bNewlyCreated = false;
    if (!CurveTable)
    {
        FString TableName = FPaths::GetBaseFilename(TablePath);
        UPackage* Package = CreatePackage(*TablePath);
        if (!Package)
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package for curve table"));
        CurveTable = NewObject<UCurveTable>(Package, FName(*TableName), RF_Public | RF_Standalone);
        if (!CurveTable)
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create CurveTable object"));
        FAssetRegistryModule::AssetCreated(CurveTable);
        bNewlyCreated = true;
    }

    int32 RowCount = 0;
    if (!CsvContent.IsEmpty())
    {
        TArray<FString> Errors = CurveTable->CreateTableFromCSVString(CsvContent, InterpMode);
        if (Errors.Num() > 0)
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Curve CSV import errors: %s"), *FString::Join(Errors, TEXT("; "))));
        }
        RowCount = CurveTable->GetRowMap().Num();
    }
    CurveTable->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetStringField(TEXT("interp_mode"), InterpModeStr);
    Result->SetNumberField(TEXT("row_count"), RowCount);
    Result->SetBoolField(TEXT("newly_created"), bNewlyCreated);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleCreateStringTable(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'table_path' parameter"));

    UStringTable* Table = LoadObject<UStringTable>(nullptr, *TablePath);
    bool bNewlyCreated = false;
    if (!Table)
    {
        FString TableName = FPaths::GetBaseFilename(TablePath);
        UPackage* Package = CreatePackage(*TablePath);
        if (!Package)
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package for string table"));
        Table = NewObject<UStringTable>(Package, FName(*TableName), RF_Public | RF_Standalone);
        if (!Table)
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create StringTable object"));
        FAssetRegistryModule::AssetCreated(Table);
        bNewlyCreated = true;
    }

    // Optional Namespace (defaults to TablePath if not provided).
    FString Namespace;
    Params->TryGetStringField(TEXT("namespace"), Namespace);
    if (Namespace.IsEmpty())
    {
        Namespace = TablePath;
    }

    FStringTableRef MutableRef = Table->GetMutableStringTable();
    MutableRef->SetNamespace(Namespace);

    // Optional initial entries map
    const TSharedPtr<FJsonObject>* EntriesObj = nullptr;
    int32 EntriesAdded = 0;
    if (Params->TryGetObjectField(TEXT("entries"), EntriesObj) && EntriesObj && (*EntriesObj).IsValid())
    {
        for (const auto& Pair : (*EntriesObj)->Values)
        {
            if (Pair.Value.IsValid() && Pair.Value->Type == EJson::String)
            {
                MutableRef->SetSourceString(Pair.Key, Pair.Value->AsString());
                ++EntriesAdded;
            }
        }
    }
    Table->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetStringField(TEXT("namespace"), Namespace);
    Result->SetNumberField(TEXT("entries_added"), EntriesAdded);
    Result->SetBoolField(TEXT("newly_created"), bNewlyCreated);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleSetStringTableEntry(const TSharedPtr<FJsonObject>& Params)
{
    FString TablePath;
    if (!Params->TryGetStringField(TEXT("table_path"), TablePath) || TablePath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'table_path' parameter"));
    FString Key;
    if (!Params->TryGetStringField(TEXT("key"), Key) || Key.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'key' parameter"));
    FString Value;
    if (!Params->TryGetStringField(TEXT("value"), Value))
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'value' parameter"));

    UStringTable* Table = LoadObject<UStringTable>(nullptr, *TablePath);
    if (!Table)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("StringTable not found: %s"), *TablePath));

    FStringTableRef MutableRef = Table->GetMutableStringTable();
    MutableRef->SetSourceString(Key, Value);
    Table->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("table_path"), TablePath);
    Result->SetStringField(TEXT("key"), Key);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableCommands::HandleCreateDataAsset(const TSharedPtr<FJsonObject>& Params)
{
    FString AssetPath;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath) || AssetPath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path' parameter"));
    FString ClassPath;
    if (!Params->TryGetStringField(TEXT("class_path"), ClassPath) || ClassPath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'class_path' parameter"));

    UClass* AssetClass = LoadObject<UClass>(nullptr, *ClassPath);
    if (!AssetClass)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Asset class not found: %s"), *ClassPath));
    if (!AssetClass->IsChildOf(UDataAsset::StaticClass()))
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Class is not UDataAsset-derived: %s"), *ClassPath));

    if (LoadObject<UObject>(nullptr, *AssetPath))
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Asset already exists at path: %s"), *AssetPath));

    FString AssetName = FPaths::GetBaseFilename(AssetPath);
    UPackage* Package = CreatePackage(*AssetPath);
    if (!Package)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package for data asset"));

    UDataAsset* NewAsset = NewObject<UDataAsset>(Package, AssetClass, FName(*AssetName), RF_Public | RF_Standalone);
    if (!NewAsset)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create DataAsset"));
    FAssetRegistryModule::AssetCreated(NewAsset);
    Package->MarkPackageDirty();

    const bool bIsPrimary = AssetClass->IsChildOf(UPrimaryDataAsset::StaticClass());

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("asset_path"), AssetPath);
    Result->SetStringField(TEXT("class_path"), ClassPath);
    Result->SetBoolField(TEXT("is_primary"), bIsPrimary);
    return Result;
}
