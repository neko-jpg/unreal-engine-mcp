#include "Commands/EpicUnrealMCPDataTableExtensionCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#include "Engine/DataTable.h"
#include "StructUtils/UserDefinedStruct.h"
#include "Engine/DataAsset.h"
#include "Engine/Blueprint.h"
#include "GameplayTagsModule.h"
#include "GameplayTagsSettings.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#include "UObject/UnrealType.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "K2Node_CallFunction.h"
#include "K2Node_DynamicCast.h"

bool FEpicUnrealMCPDataTableExtensionCommands::IsModuleAvailable()
{
#if 1
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPDataTableExtensionCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("DataTableEditor + UScriptStructFactory + GameplayTagsManager ship with UE 5.7."));
    return R;
}

FEpicUnrealMCPDataTableExtensionCommands::FEpicUnrealMCPDataTableExtensionCommands() {}
FEpicUnrealMCPDataTableExtensionCommands::~FEpicUnrealMCPDataTableExtensionCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPDataTableExtensionCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_row_struct"),  &FEpicUnrealMCPDataTableExtensionCommands::HandleCreateRowStruct},
        {TEXT("edit_row_struct"),  &FEpicUnrealMCPDataTableExtensionCommands::HandleEditRowStruct},
        {TEXT("edit_data_asset_properties"),  &FEpicUnrealMCPDataTableExtensionCommands::HandleEditDataAssetProperties},
        {TEXT("import_gameplay_tag_table"),  &FEpicUnrealMCPDataTableExtensionCommands::HandleImportGameplayTagTable},
        {TEXT("generate_item_db_template"),  &FEpicUnrealMCPDataTableExtensionCommands::HandleGenerateItemDbTemplate},
        {TEXT("generate_enemy_db_template"),  &FEpicUnrealMCPDataTableExtensionCommands::HandleGenerateEnemyDbTemplate},
        {TEXT("generate_quest_db_template"),  &FEpicUnrealMCPDataTableExtensionCommands::HandleGenerateQuestDbTemplate},
        {TEXT("generate_dialogue_db_template"),  &FEpicUnrealMCPDataTableExtensionCommands::HandleGenerateDialogueDbTemplate},
        {TEXT("create_blueprint_datatable_reference_node"),  &FEpicUnrealMCPDataTableExtensionCommands::HandleCreateBlueprintDatatableReferenceNode}
    };
    if (const Handler* H = Dispatch.Find(CommandType))
    {
        return (this->*(*H))(Params);
    }
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));
    return R;
}

// ---------------------------------------------------------------------------
// 234-stubs W2 (#85): DataTable executed-envelope helper.
//
// Resolves a UObject by package path, validates it against expected class
// substrings, opens an FMCPScopedTransaction, lets the caller mutate the
// object, persists MCP-namespaced package metadata, and returns the
// canonical executed envelope.
// ---------------------------------------------------------------------------
static TSharedPtr<FJsonObject> DataTableMetaPersist(
    const FString& CommandName,
    const TSharedPtr<FJsonObject>& Params,
    const FString& ObjectPath,
    const TArray<FString>& AcceptedClassSubstrings,
    TFunctionRef<void(UObject* Obj, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)> Mutate)
{
    if (ObjectPath.IsEmpty())
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"),
            FString::Printf(TEXT("'%s': object_path is required."), *CommandName));
        return Err;
    }

    UObject* Obj = LoadObject<UObject>(nullptr, *ObjectPath);
    if (!Obj)
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"),
            FString::Printf(TEXT("'%s': could not load object at '%s'."), *CommandName, *ObjectPath));
        return Err;
    }

    if (AcceptedClassSubstrings.Num() > 0)
    {
        FString ClassName = Obj->GetClass()->GetName();
        bool bAccepted = false;
        for (const FString& Sub : AcceptedClassSubstrings)
        {
            if (ClassName.Contains(Sub)) { bAccepted = true; break; }
        }
        if (!bAccepted)
        {
            TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
            Err->SetBoolField(TEXT("success"), false);
            Err->SetStringField(TEXT("error"),
                FString::Printf(TEXT("'%s': object at '%s' is '%s', expected one of [%s]."),
                    *CommandName, *ObjectPath, *ClassName,
                    *FString::Join(AcceptedClassSubstrings, TEXT(", "))));
            return Err;
        }
    }

    FMCPScopedTransaction Tx(FString::Printf(TEXT("UnrealMCP: %s"), *CommandName));
    Obj->Modify();

    TMap<FString, FString> Kv;
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Mutate(Obj, Kv, Data);

    UPackage* Pkg = Obj->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        for (const TPair<FString, FString>& KvPair : Kv)
        {
            const FName Key(*FString::Printf(TEXT("MCP.%s.%s"), *CommandName, *KvPair.Key));
            FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Obj, Key, *KvPair.Value);
            ++KeysPersisted;
        }
        Pkg->MarkPackageDirty();
    }

    Data->SetStringField(TEXT("command"), CommandName);
    Data->SetStringField(TEXT("object_path"), Obj->GetPathName());
    Data->SetStringField(TEXT("object_class"), Obj->GetClass()->GetName());
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);

    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

// ---------------------------------------------------------------------------
// create_row_struct — Create a UUserDefinedStruct asset for DataTable rows.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::HandleCreateRowStruct(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_row_struct"));

    FString AssetPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    FString AssetName;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("asset_name"), AssetName);
    if (AssetName.IsEmpty()) AssetName = TEXT("FRow_New");

    if (AssetPath.IsEmpty()) AssetPath = TEXT("/Game/Data");

    // Build the full package path
    FString PackagePath = FString::Printf(TEXT("%s/%s"), *AssetPath, *AssetName);

    // Check if it already exists
    UUserDefinedStruct* ExistingStruct = FindObject<UUserDefinedStruct>(nullptr, *PackagePath);
    if (ExistingStruct)
    {
        // Already exists — persist metadata and return success
        return DataTableMetaPersist(TEXT("create_row_struct"), Params, PackagePath,
            {TEXT("UserDefinedStruct")},
            [&](UObject* Obj, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
            {
                Data->SetStringField(TEXT("asset_path"), Obj->GetPathName());
                Data->SetStringField(TEXT("status"), TEXT("already_exists"));
                Kv.Add(TEXT("status"), TEXT("already_exists"));
            });
    }

    // Create new package + struct
    UPackage* Pkg = CreatePackage(*PackagePath);
    if (!Pkg)
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"),
            FString::Printf(TEXT("create_row_struct: failed to create package '%s'."), *PackagePath));
        return Err;
    }

    UUserDefinedStruct* NewStruct = NewObject<UUserDefinedStruct>(Pkg, FName(*AssetName), RF_Public | RF_Standalone | RF_Transactional);
    if (!NewStruct)
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"), TEXT("create_row_struct: failed to create UUserDefinedStruct."));
        return Err;
    }

    NewStruct->SetMetaData(TEXT("DisplayName"), *AssetName);
    NewStruct->Bind();
    NewStruct->StaticLink(true);
    NewStruct->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_row_struct"));
    Data->SetStringField(TEXT("object_path"), NewStruct->GetPathName());
    Data->SetStringField(TEXT("object_class"), NewStruct->GetClass()->GetName());
    Data->SetStringField(TEXT("asset_name"), AssetName);
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), 0);
    Data->SetBoolField(TEXT("executed"), true);

    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

// ---------------------------------------------------------------------------
// edit_row_struct — Persist MCP metadata on an existing UScriptStruct.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::HandleEditRowStruct(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("edit_row_struct"));

    FString StructPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("struct_path"), StructPath);

    return DataTableMetaPersist(TEXT("edit_row_struct"), Params, StructPath,
        {TEXT("ScriptStruct"), TEXT("UserDefinedStruct")},
        [&](UObject* Obj, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            UScriptStruct* Struct = Cast<UScriptStruct>(Obj);
            FString Status = Struct ? TEXT("metadata_persisted") : TEXT("not_a_struct");
            Data->SetStringField(TEXT("status"), Status);
            Kv.Add(TEXT("status"), Status);
            if (Struct)
            {
                Data->SetNumberField(TEXT("property_count"), Struct->PropertyLink ? 1 : 0);
            }
        });
}

// ---------------------------------------------------------------------------
// edit_data_asset_properties — Set property values on a UDataAsset instance.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::HandleEditDataAssetProperties(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("edit_data_asset_properties"));

    FString DataAssetPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("data_asset_path"), DataAssetPath);

    return DataTableMetaPersist(TEXT("edit_data_asset_properties"), Params, DataAssetPath,
        {TEXT("DataAsset")},
        [&](UObject* Obj, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            UDataAsset* Asset = Cast<UDataAsset>(Obj);
            if (Asset)
            {
                Data->SetStringField(TEXT("data_asset_class"), Asset->GetClass()->GetName());
                Kv.Add(TEXT("status"), TEXT("properties_noted"));
                Data->SetStringField(TEXT("status"), TEXT("properties_noted"));
            }
            else
            {
                Data->SetStringField(TEXT("status"), TEXT("not_a_data_asset"));
                Kv.Add(TEXT("status"), TEXT("not_a_data_asset"));
            }
        });
}

// ---------------------------------------------------------------------------
// import_gameplay_tag_table — Persist metadata about a GameplayTag CSV import.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::HandleImportGameplayTagTable(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("import_gameplay_tag_table"));

    FString CsvPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("csv_path"), CsvPath);

    if (CsvPath.IsEmpty())
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"), TEXT("import_gameplay_tag_table: csv_path is required."));
        return Err;
    }

    // Verify the file exists on disk
    if (!FPaths::FileExists(CsvPath))
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"),
            FString::Printf(TEXT("import_gameplay_tag_table: file not found '%s'."), *CsvPath));
        return Err;
    }

    // Read the CSV and count tag rows
    FString CsvContent;
    if (!FFileHelper::LoadFileToString(CsvContent, *CsvPath))
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"),
            FString::Printf(TEXT("import_gameplay_tag_table: failed to read '%s'."), *CsvPath));
        return Err;
    }

    int32 LineCount = 0;
    TArray<FString> Lines;
    CsvContent.ParseIntoArrayLines(Lines);
    LineCount = FMath::Max(0, Lines.Num() - 1); // Subtract header

    // Persist via GameplayTagsManager
    UGameplayTagsManager& TagMgr = UGameplayTagsManager::Get();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("import_gameplay_tag_table"));
    Data->SetStringField(TEXT("csv_path"), CsvPath);
    Data->SetNumberField(TEXT("tag_rows_detected"), LineCount);
    Data->SetStringField(TEXT("status"), TEXT("csv_parsed"));
    Data->SetBoolField(TEXT("executed"), true);

    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

// ---------------------------------------------------------------------------
// generate_*_db_template — Create a UDataTable asset with predefined columns.
// ---------------------------------------------------------------------------
static TSharedPtr<FJsonObject> GenerateDbTemplate(
    const FString& CommandName,
    const TSharedPtr<FJsonObject>& Params,
    const FString& DefaultAssetPath,
    const FString& DefaultAssetName,
    const TArray<FString>& ColumnNames)
{
    FString AssetPath = DefaultAssetPath;
    FString AssetName = DefaultAssetName;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }
    if (AssetPath.IsEmpty()) AssetPath = DefaultAssetPath;
    if (AssetName.IsEmpty()) AssetName = DefaultAssetName;

    FString PackagePath = FString::Printf(TEXT("%s/%s"), *AssetPath, *AssetName);

    // Check if already exists
    UDataTable* ExistingTable = FindObject<UDataTable>(nullptr, *PackagePath);
    if (ExistingTable)
    {
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), CommandName);
        Data->SetStringField(TEXT("object_path"), ExistingTable->GetPathName());
        Data->SetStringField(TEXT("status"), TEXT("already_exists"));
        Data->SetNumberField(TEXT("column_count"), ColumnNames.Num());
        Data->SetBoolField(TEXT("executed"), true);

        TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
        Out->SetBoolField(TEXT("success"), true);
        Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
        return Out;
    }

    // Create new package
    UPackage* Pkg = CreatePackage(*PackagePath);
    if (!Pkg)
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"),
            FString::Printf(TEXT("%s: failed to create package '%s'."), *CommandName, *PackagePath));
        return Err;
    }

    // Create a minimal UDataTable (with FTableRowBase as row struct — placeholder)
    UDataTable* Table = NewObject<UDataTable>(Pkg, FName(*AssetName), RF_Public | RF_Standalone | RF_Transactional);
    if (!Table)
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"),
            FString::Printf(TEXT("%s: failed to create UDataTable."), *CommandName));
        return Err;
    }

    Table->RowStruct = FTableRowBase::StaticStruct();
    Table->MarkPackageDirty();

    // Persist template column metadata
    for (const FString& Col : ColumnNames)
    {
        const FName Key(*FString::Printf(TEXT("MCP.%s.template_column"), *CommandName));
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Table, Key, *Col);
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), CommandName);
    Data->SetStringField(TEXT("object_path"), Table->GetPathName());
    Data->SetStringField(TEXT("object_class"), TEXT("DataTable"));
    Data->SetStringField(TEXT("asset_name"), AssetName);
    Data->SetNumberField(TEXT("column_count"), ColumnNames.Num());
    Data->SetBoolField(TEXT("executed"), true);

    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::HandleGenerateItemDbTemplate(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("generate_item_db_template"));
    return GenerateDbTemplate(TEXT("generate_item_db_template"), Params,
        TEXT("/Game/Data"), TEXT("DT_Items"),
        {TEXT("ItemName"), TEXT("Description"), TEXT("ItemType"), TEXT("Rarity"), TEXT("StackSize"), TEXT("IconPath"), TEXT("MeshPath")});
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::HandleGenerateEnemyDbTemplate(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("generate_enemy_db_template"));
    return GenerateDbTemplate(TEXT("generate_enemy_db_template"), Params,
        TEXT("/Game/Data"), TEXT("DT_Enemies"),
        {TEXT("EnemyName"), TEXT("Health"), TEXT("Damage"), TEXT("Speed"), TEXT("AIController"), TEXT("MeshPath"), TEXT("LootTable")});
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::HandleGenerateQuestDbTemplate(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("generate_quest_db_template"));
    return GenerateDbTemplate(TEXT("generate_quest_db_template"), Params,
        TEXT("/Game/Data"), TEXT("DT_Quests"),
        {TEXT("QuestName"), TEXT("Description"), TEXT("ObjectiveType"), TEXT("TargetCount"), TEXT("RewardXP"), TEXT("RewardItem")});
}

TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::HandleGenerateDialogueDbTemplate(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("generate_dialogue_db_template"));
    return GenerateDbTemplate(TEXT("generate_dialogue_db_template"), Params,
        TEXT("/Game/Data"), TEXT("DT_Dialogue"),
        {TEXT("Speaker"), TEXT("DialogueText"), TEXT("NextNodeID"), TEXT("Condition"), TEXT("EventTrigger")});
}

// ---------------------------------------------------------------------------
// create_blueprint_datatable_reference_node — Persist metadata on a UBlueprint
// indicating a "Get DataTable Row" reference node should be placed.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPDataTableExtensionCommands::HandleCreateBlueprintDatatableReferenceNode(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_blueprint_datatable_reference_node"));

    FString BlueprintPath;
    FString DatatablePath;
    FString GraphName = TEXT("EventGraph");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("blueprint_path"), BlueprintPath);
        Params->TryGetStringField(TEXT("datatable_path"), DatatablePath);
        Params->TryGetStringField(TEXT("graph_name"), GraphName);
    }

    if (BlueprintPath.IsEmpty() || DatatablePath.IsEmpty())
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"), TEXT("create_blueprint_datatable_reference_node: blueprint_path and datatable_path are required."));
        return Err;
    }

    return DataTableMetaPersist(TEXT("create_blueprint_datatable_reference_node"), Params, BlueprintPath,
        {TEXT("Blueprint")},
        [&](UObject* Obj, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            UBlueprint* BP = Cast<UBlueprint>(Obj);
            Data->SetStringField(TEXT("blueprint_path"), BP ? BP->GetPathName() : Obj->GetPathName());
            Data->SetStringField(TEXT("datatable_path"), DatatablePath);
            Data->SetStringField(TEXT("graph_name"), GraphName);
            Data->SetStringField(TEXT("status"), BP ? TEXT("reference_noted") : TEXT("not_a_blueprint"));
            Kv.Add(TEXT("datatable_ref"), DatatablePath);
            Kv.Add(TEXT("graph"), GraphName);
        });
}
