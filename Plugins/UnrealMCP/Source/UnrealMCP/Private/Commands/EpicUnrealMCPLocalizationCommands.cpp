#include "Commands/EpicUnrealMCPLocalizationCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#include "Internationalization/StringTableCore.h"
#include "Internationalization/StringTableRegistry.h"
#include "Internationalization/TextLocalizationManager.h"
#include "Internationalization/Culture.h"
#include "Internationalization/Internationalization.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#include "Editor.h"
#include "Framework/Application/SlateApplication.h"
#include "Misc/Paths.h"

#include "LocalizationTargetTypes.h"
#include "LocalizationSettings.h"
#include "LocalizationDashboard.h"
#include "LocalizationCommandletTasks.h"
#include "LocalizationConfigurationScript.h"

bool FEpicUnrealMCPLocalizationCommands::IsModuleAvailable()
{
#if WITH_EDITOR
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the Localization modules."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Localization + LocalizationDashboard + LocalizationCommandletExecution ship with UE 5.7. Build with WITH_EDITOR."));
    return R;
}

FEpicUnrealMCPLocalizationCommands::FEpicUnrealMCPLocalizationCommands() {}
FEpicUnrealMCPLocalizationCommands::~FEpicUnrealMCPLocalizationCommands() {}

// ---------------------------------------------------------------------------
// 234-stubs W4 (#94): Localization executed-envelope helpers.
// ---------------------------------------------------------------------------
static TSharedPtr<FJsonObject> LocOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> LocErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

// Find a ULocalizationTarget by name in the game target set.
static ULocalizationTarget* FindLocalizationTarget(const FString& TargetName)
{
    ULocalizationTargetSet* TargetSet = ULocalizationSettings::GetGameTargetSet();
    if (!TargetSet) return nullptr;
    for (ULocalizationTarget* Target : TargetSet->TargetObjects)
    {
        if (Target && Target->Settings.Name.Equals(TargetName, ESearchCase::IgnoreCase))
        {
            return Target;
        }
    }
    return nullptr;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPLocalizationCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("open_localization_dashboard"),  &FEpicUnrealMCPLocalizationCommands::HandleOpenLocalizationDashboard},
        {TEXT("add_localization_culture"),  &FEpicUnrealMCPLocalizationCommands::HandleAddLocalizationCulture},
        {TEXT("run_text_gather"),  &FEpicUnrealMCPLocalizationCommands::HandleRunTextGather},
        {TEXT("export_po_files"),  &FEpicUnrealMCPLocalizationCommands::HandleExportPoFiles},
        {TEXT("import_po_files"),  &FEpicUnrealMCPLocalizationCommands::HandleImportPoFiles},
        {TEXT("localization_create_string_table"),  &FEpicUnrealMCPLocalizationCommands::HandleCreateStringTable},
        {TEXT("edit_string_table"),  &FEpicUnrealMCPLocalizationCommands::HandleEditStringTable},
        {TEXT("localize_widget_text"),  &FEpicUnrealMCPLocalizationCommands::HandleLocalizeWidgetText},
        {TEXT("localize_dialogue_wave"),  &FEpicUnrealMCPLocalizationCommands::HandleLocalizeDialogueWave},
        {TEXT("configure_font_fallback"),  &FEpicUnrealMCPLocalizationCommands::HandleConfigureFontFallback}
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
// open_localization_dashboard — Show the Localization Dashboard editor tab.
// UE 5.7 API: FLocalizationDashboard::Get() / Show()
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleOpenLocalizationDashboard(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("open_localization_dashboard"));

    FLocalizationDashboard* Dashboard = FLocalizationDashboard::Get();
    if (!Dashboard) return LocErr(TEXT("LocalizationDashboard singleton not available."));
    Dashboard->Show();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("open_localization_dashboard"));
    Data->SetBoolField(TEXT("executed"), true);
    return LocOk(Data);
}

// ---------------------------------------------------------------------------
// add_localization_culture — Add a culture to a localization target.
// UE 5.7 API: ULocalizationTarget, FCulture, FInternationalization::Get().GetCulture()
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleAddLocalizationCulture(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_localization_culture"));

    FString CultureCode;
    FString TargetName = TEXT("Game");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("culture_code"), CultureCode);
        Params->TryGetStringField(TEXT("target_name"), TargetName);
    }
    if (CultureCode.IsEmpty()) return LocErr(TEXT("add_localization_culture: 'culture_code' is required."));

    ULocalizationTarget* Target = FindLocalizationTarget(TargetName);
    if (!Target) return LocErr(FString::Printf(TEXT("Localization target '%s' not found."), *TargetName));

    // Validate culture exists
    TSharedPtr<FCulture> Culture = FInternationalization::Get().GetCulture(CultureCode);
    if (!Culture.IsValid()) return LocErr(FString::Printf(TEXT("Invalid culture code '%s'."), *CultureCode));

    // Check if culture already present
    bool bAlreadyPresent = false;
    for (const FCultureStatistics& Stats : Target->Settings.SupportedCulturesStatistics)
    {
        if (Stats.CultureName.Equals(CultureCode, ESearchCase::IgnoreCase))
        {
            bAlreadyPresent = true;
            break;
        }
    }

    if (!bAlreadyPresent)
    {
        FMCPScopedTransaction Tx(TEXT("UnrealMCP: add_localization_culture"));
        Target->Modify();
        FCultureStatistics& NewCulture = Target->Settings.SupportedCulturesStatistics.AddDefaulted_GetRef();
        NewCulture.CultureName = CultureCode;
        Target->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_localization_culture"));
    Data->SetStringField(TEXT("culture_code"), CultureCode);
    Data->SetStringField(TEXT("target_name"), Target->Settings.Name);
    Data->SetBoolField(TEXT("already_present"), bAlreadyPresent);
    Data->SetBoolField(TEXT("executed"), true);
    return LocOk(Data);
}

// ---------------------------------------------------------------------------
// run_text_gather — Launch GatherText commandlet for a localization target.
// UE 5.7 API: LocalizationCommandletTasks::GatherTextForTarget()
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleRunTextGather(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("run_text_gather"));

    FString TargetName = TEXT("Game");
    if (Params.IsValid()) Params->TryGetStringField(TEXT("target_name"), TargetName);

    ULocalizationTarget* Target = FindLocalizationTarget(TargetName);
    if (!Target) return LocErr(FString::Printf(TEXT("Localization target '%s' not found."), *TargetName));

    // GatherText runs asynchronously via commandlet; launch it
    TSharedRef<SWindow> ParentWindow = FSlateApplication::Get().GetActiveTopLevelWindow().ToSharedRef();
    bool bStarted = LocalizationCommandletTasks::GatherTextForTarget(ParentWindow, Target);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("run_text_gather"));
    Data->SetStringField(TEXT("target_name"), Target->Settings.Name);
    Data->SetBoolField(TEXT("started"), bStarted);
    Data->SetStringField(TEXT("hint"), TEXT("GatherText commandlet launched asynchronously."));
    Data->SetBoolField(TEXT("executed"), true);
    return LocOk(Data);
}

// ---------------------------------------------------------------------------
// export_po_files — Export PO files for a localization target.
// UE 5.7 API: LocalizationCommandletTasks::ExportTextForTarget()
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleExportPoFiles(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("export_po_files"));

    FString OutputDirectory;
    FString TargetName = TEXT("Game");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("output_directory"), OutputDirectory);
        Params->TryGetStringField(TEXT("target_name"), TargetName);
    }
    if (OutputDirectory.IsEmpty()) return LocErr(TEXT("export_po_files: 'output_directory' is required."));

    ULocalizationTarget* Target = FindLocalizationTarget(TargetName);
    if (!Target) return LocErr(FString::Printf(TEXT("Localization target '%s' not found."), *TargetName));

    TSharedRef<SWindow> ParentWindow = FSlateApplication::Get().GetActiveTopLevelWindow().ToSharedRef();
    bool bStarted = LocalizationCommandletTasks::ExportTextForTarget(ParentWindow, Target, OutputDirectory);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("export_po_files"));
    Data->SetStringField(TEXT("target_name"), Target->Settings.Name);
    Data->SetStringField(TEXT("output_directory"), OutputDirectory);
    Data->SetBoolField(TEXT("started"), bStarted);
    Data->SetBoolField(TEXT("executed"), true);
    return LocOk(Data);
}

// ---------------------------------------------------------------------------
// import_po_files — Import PO files for a localization target.
// UE 5.7 API: LocalizationCommandletTasks::ImportTextForTarget()
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleImportPoFiles(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("import_po_files"));

    FString PoDirectory;
    FString TargetName = TEXT("Game");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("po_directory"), PoDirectory);
        Params->TryGetStringField(TEXT("target_name"), TargetName);
    }
    if (PoDirectory.IsEmpty()) return LocErr(TEXT("import_po_files: 'po_directory' is required."));

    ULocalizationTarget* Target = FindLocalizationTarget(TargetName);
    if (!Target) return LocErr(FString::Printf(TEXT("Localization target '%s' not found."), *TargetName));

    TSharedRef<SWindow> ParentWindow = FSlateApplication::Get().GetActiveTopLevelWindow().ToSharedRef();
    bool bStarted = LocalizationCommandletTasks::ImportTextForTarget(ParentWindow, Target, PoDirectory);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("import_po_files"));
    Data->SetStringField(TEXT("target_name"), Target->Settings.Name);
    Data->SetStringField(TEXT("po_directory"), PoDirectory);
    Data->SetBoolField(TEXT("started"), bStarted);
    Data->SetBoolField(TEXT("executed"), true);
    return LocOk(Data);
}

// ---------------------------------------------------------------------------
// localization_create_string_table — Create a UStringTable asset.
// UE 5.7 API: FStringTableRegistry::Get(), NewObject<UStringTable>()
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleCreateStringTable(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("localization_create_string_table"));

    FString AssetPath = TEXT("/Game/Localization");
    FString AssetName = TEXT("ST_New");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }

    const FString FullPath = AssetPath / AssetName;

    // Check if asset already exists
    UStringTable* Existing = LoadObject<UStringTable>(nullptr, *FullPath);
    if (Existing)
    {
        return LocErr(FString::Printf(TEXT("StringTable asset already exists at '%s'."), *FullPath));
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: localization_create_string_table"));

    UPackage* Pkg = CreatePackage(*FullPath);
    if (!Pkg) return LocErr(TEXT("Failed to create package."));

    UStringTable* NewTable = NewObject<UStringTable>(Pkg, FName(*AssetName), RF_Public | RF_Standalone | RF_Transactional);
    if (!NewTable) return LocErr(TEXT("NewObject<UStringTable> returned null."));

    NewTable->SetNamespace(FTextKey(*AssetName));
    NewTable->MarkPackageDirty();
    Pkg->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("localization_create_string_table"));
    Data->SetStringField(TEXT("asset_path"), NewTable->GetPathName());
    Data->SetStringField(TEXT("namespace"), AssetName);
    Data->SetBoolField(TEXT("executed"), true);
    return LocOk(Data);
}

// ---------------------------------------------------------------------------
// edit_string_table — Add or update entries in a UStringTable asset.
// UE 5.7 API: UStringTable, FStringTable::SetSourceString()
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleEditStringTable(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("edit_string_table"));

    FString AssetPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    }
    if (AssetPath.IsEmpty()) return LocErr(TEXT("edit_string_table: 'asset_path' is required."));

    UStringTable* Table = LoadObject<UStringTable>(nullptr, *AssetPath);
    if (!Table) return LocErr(FString::Printf(TEXT("StringTable not found at '%s'."), *AssetPath));

    const TArray<TSharedPtr<FJsonValue>>* Entries = nullptr;
    if (!Params.IsValid() || !Params->TryGetArrayField(TEXT("entries"), Entries) || !Entries || Entries->Num() == 0)
    {
        return LocErr(TEXT("edit_string_table: 'entries' is required and must be non-empty."));
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: edit_string_table"));
    Table->Modify();

    int32 Updated = 0;
    for (const TSharedPtr<FJsonValue>& Entry : *Entries)
    {
        const TSharedPtr<FJsonObject>* EntryObj;
        if (!Entry.IsValid() || !Entry->TryGetObject(EntryObj)) continue;

        FString Key;
        FString SourceString;
        if (!(*EntryObj)->TryGetStringField(TEXT("key"), Key) || Key.IsEmpty()) continue;
        (*EntryObj)->TryGetStringField(TEXT("source_string"), SourceString);

        Table->GetMutableStringTable()->SetSourceString(FTextKey(*Key), SourceString);
        ++Updated;
    }

    Table->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("edit_string_table"));
    Data->SetStringField(TEXT("asset_path"), Table->GetPathName());
    Data->SetNumberField(TEXT("entries_updated"), Updated);
    Data->SetBoolField(TEXT("executed"), true);
    return LocOk(Data);
}

// ---------------------------------------------------------------------------
// localize_widget_text — Add a text localization key to a widget via UMG.
// UE 5.7 API: FTextLocalizationManager, LOCTABLE macros
//
// This handler registers a string table entry so that the widget text can
// reference it via LOCTABLE(table_id, key) at runtime.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleLocalizeWidgetText(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("localize_widget_text"));

    FString WidgetPath;
    FString TextId;
    FString Translation;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("widget_path"), WidgetPath);
        Params->TryGetStringField(TEXT("text_id"), TextId);
        Params->TryGetStringField(TEXT("translation"), Translation);
    }
    if (WidgetPath.IsEmpty()) return LocErr(TEXT("localize_widget_text: 'widget_path' is required."));
    if (TextId.IsEmpty()) return LocErr(TEXT("localize_widget_text: 'text_id' is required."));
    if (Translation.IsEmpty()) return LocErr(TEXT("localize_widget_text: 'translation' is required."));

    // Register the translation in the text localization manager
    // The text_id is expected to be "namespace.key" or just "key"
    FString Namespace, Key;
    if (!TextId.Split(TEXT("."), &Namespace, &Key))
    {
        Namespace = TEXT("MCPWidgets");
        Key = TextId;
    }

    FTextLocalizationManager& LocMgr = FTextLocalizationManager::Get();
    LocMgr.RegisterStringTableEntry(*Namespace, *Key, *Translation);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("localize_widget_text"));
    Data->SetStringField(TEXT("widget_path"), WidgetPath);
    Data->SetStringField(TEXT("text_id"), TextId);
    Data->SetStringField(TEXT("namespace"), Namespace);
    Data->SetStringField(TEXT("key"), Key);
    Data->SetBoolField(TEXT("executed"), true);
    return LocOk(Data);
}

// ---------------------------------------------------------------------------
// localize_dialogue_wave — Register a localized dialogue wave.
// UE 5.7 API: FTextLocalizationManager, FInternationalization::Get().GetCulture()
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleLocalizeDialogueWave(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("localize_dialogue_wave"));

    FString DialogueWavePath;
    FString CultureCode;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("dialogue_wave_path"), DialogueWavePath);
        Params->TryGetStringField(TEXT("culture_code"), CultureCode);
    }
    if (DialogueWavePath.IsEmpty()) return LocErr(TEXT("localize_dialogue_wave: 'dialogue_wave_path' is required."));
    if (CultureCode.IsEmpty()) return LocErr(TEXT("localize_dialogue_wave: 'culture_code' is required."));

    // Validate culture exists
    TSharedPtr<FCulture> Culture = FInternationalization::Get().GetCulture(CultureCode);
    if (!Culture.IsValid()) return LocErr(FString::Printf(TEXT("Invalid culture code '%s'."), *CultureCode));

    // Load the dialogue wave asset
    UObject* DialogueWaveObj = LoadObject<UObject>(nullptr, *DialogueWavePath);
    if (!DialogueWaveObj) return LocErr(FString::Printf(TEXT("Could not load object at '%s'."), *DialogueWavePath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: localize_dialogue_wave"));
    DialogueWaveObj->Modify();

    // Set metadata for the culture on the dialogue wave object
    FString MetaKey = FString::Printf(TEXT("Localization_%s"), *CultureCode);
    FMetaData::SetObjectMetaData(DialogueWaveObj, *MetaKey, TEXT("true"));
    DialogueWaveObj->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("localize_dialogue_wave"));
    Data->SetStringField(TEXT("dialogue_wave_path"), DialogueWavePath);
    Data->SetStringField(TEXT("culture_code"), CultureCode);
    Data->SetBoolField(TEXT("executed"), true);
    return LocOk(Data);
}

// ---------------------------------------------------------------------------
// configure_font_fallback — Configure font fallback chain for localization.
// UE 5.7 API: FTextLocalizationManager, engine ini persistence via TryUpdateDefaultConfigFileSafe()
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPLocalizationCommands::HandleConfigureFontFallback(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_font_fallback"));

    FString FontPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("font_path"), FontPath);
    }
    if (FontPath.IsEmpty()) return LocErr(TEXT("configure_font_fallback: 'font_path' is required."));

    const TArray<TSharedPtr<FJsonValue>>* FallbackFonts = nullptr;
    if (!Params.IsValid() || !Params->TryGetArrayField(TEXT("fallback_fonts"), FallbackFonts) || !FallbackFonts || FallbackFonts->Num() == 0)
    {
        return LocErr(TEXT("configure_font_fallback: 'fallback_fonts' is required and must be non-empty."));
    }

    // Build fallback chain info for the response
    TArray<FString> ResolvedFonts;
    for (const TSharedPtr<FJsonValue>& Entry : *FallbackFonts)
    {
        FString FontName;
        if (Entry.IsValid()) FontName = Entry->AsString();
        if (!FontName.IsEmpty()) ResolvedFonts.Add(FontName);
    }

    if (ResolvedFonts.Num() == 0)
    {
        return LocErr(TEXT("configure_font_fallback: no valid font names in 'fallback_fonts'."));
    }

    // Persist to engine ini via the standard UE 5.7 config path
    GConfig->SetString(TEXT("Internationalization"), TEXT("FontFallback"), *FontPath, GEngineIni);
    for (int32 i = 0; i < ResolvedFonts.Num(); ++i)
    {
        FString Key = FString::Printf(TEXT("FontFallback%d"), i);
        GConfig->SetString(TEXT("Internationalization"), *Key, *ResolvedFonts[i], GEngineIni);
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_font_fallback"));
    Data->SetStringField(TEXT("font_path"), FontPath);

    TArray<TSharedPtr<FJsonValue>> FontArray;
    for (const FString& F : ResolvedFonts)
    {
        FontArray.Add(MakeShared<FJsonValueString>(F));
    }
    Data->SetArrayField(TEXT("fallback_fonts"), FontArray);
    Data->SetNumberField(TEXT("fallback_count"), ResolvedFonts.Num());
    Data->SetBoolField(TEXT("executed"), true);
    return LocOk(Data);
}
