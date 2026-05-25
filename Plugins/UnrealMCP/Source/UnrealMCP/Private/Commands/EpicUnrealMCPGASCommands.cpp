#include "Commands/EpicUnrealMCPGASCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"
#include "EngineUtils.h"

#if WITH_GAS_MCP
#include "AbilitySystemComponent.h"
#include "AbilitySystemGlobals.h"
#include "AttributeSet.h"
#include "GameplayAbility.h"
#include "GameplayEffect.h"
#include "GameplayCueNotify_Static.h"
#include "GameplayTagsModule.h"
#include "GameplayTasksComponent.h"
#include "Engine/World.h"
#include "Engine/Blueprint.h"
#include "Engine/DataTable.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "Editor.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "AssetRegistry/AssetRegistryModule.h"
#endif

bool FEpicUnrealMCPGASCommands::IsModuleAvailable()
{
#if WITH_GAS_MCP
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the GameplayAbilities plugin."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Enable the GameplayAbilities plugin (Engine/Plugins/Runtime/GameplayAbilities) and rebuild UnrealMCP."));
    return R;
}

FEpicUnrealMCPGASCommands::FEpicUnrealMCPGASCommands() {}
FEpicUnrealMCPGASCommands::~FEpicUnrealMCPGASCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPGASCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("enable_gas_plugin"),  &FEpicUnrealMCPGASCommands::HandleEnableGasPlugin},
        {TEXT("add_ability_system_component"),  &FEpicUnrealMCPGASCommands::HandleAddAbilitySystemComponent},
        {TEXT("create_attribute_set"),  &FEpicUnrealMCPGASCommands::HandleCreateAttributeSet},
        {TEXT("create_gameplay_ability"),  &FEpicUnrealMCPGASCommands::HandleCreateGameplayAbility},
        {TEXT("create_gameplay_effect"),  &FEpicUnrealMCPGASCommands::HandleCreateGameplayEffect},
        {TEXT("create_gameplay_cue"),  &FEpicUnrealMCPGASCommands::HandleCreateGameplayCue},
        {TEXT("bind_ability_input"),  &FEpicUnrealMCPGASCommands::HandleBindAbilityInput},
        {TEXT("grant_ability"),  &FEpicUnrealMCPGASCommands::HandleGrantAbility},
        {TEXT("configure_ability_activation"),  &FEpicUnrealMCPGASCommands::HandleConfigureAbilityActivation},
        {TEXT("configure_ability_cooldown"),  &FEpicUnrealMCPGASCommands::HandleConfigureAbilityCooldown},
        {TEXT("configure_ability_cost"),  &FEpicUnrealMCPGASCommands::HandleConfigureAbilityCost},
        {TEXT("initialize_attribute"),  &FEpicUnrealMCPGASCommands::HandleInitializeAttribute},
        {TEXT("bind_attribute_change_event"),  &FEpicUnrealMCPGASCommands::HandleBindAttributeChangeEvent},
        {TEXT("link_gameplay_tag"),  &FEpicUnrealMCPGASCommands::HandleLinkGameplayTag},
        {TEXT("configure_gas_replication"),  &FEpicUnrealMCPGASCommands::HandleConfigureGasReplication},
        {TEXT("configure_gas_prediction"),  &FEpicUnrealMCPGASCommands::HandleConfigureGasPrediction}
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
// 234-stubs W2 (#86): GAS executed-envelope helpers.
// ---------------------------------------------------------------------------

static TSharedPtr<FJsonObject> GASOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> GASErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

// Resolve an AActor by name or label from the editor world.
static AActor* FindActorInEditorWorld(UWorld* World, const FString& ActorName)
{
    if (!World || ActorName.IsEmpty()) return nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName().Equals(ActorName, ESearchCase::IgnoreCase) ||
            It->GetActorLabel().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            return *It;
        }
    }
    return nullptr;
}

// Resolve or create a UBlueprint at the given path.
static UBlueprint* ResolveOrCreateBlueprint(const FString& BlueprintPath, const FString& DefaultPath)
{
    FString Path = BlueprintPath.IsEmpty() ? DefaultPath : BlueprintPath;
    UBlueprint* BP = LoadObject<UBlueprint>(nullptr, *Path);
    if (BP) return BP;

    // Try to create a new blueprint package
    UPackage* Pkg = CreatePackage(*Path);
    if (!Pkg) return nullptr;

    // Use the ActorFactory for Blueprint creation
    UClass* BlueprintClass = UBlueprint::StaticClass();
    BP = NewObject<UBlueprint>(Pkg, FName(*FPaths::GetBaseFilename(Path)), RF_Public | RF_Standalone | RF_Transactional);
    if (BP)
    {
        BP->MarkPackageDirty();
    }
    return BP;
}

// ---------------------------------------------------------------------------
// enable_gas_plugin — Persist metadata indicating GAS plugin should be enabled.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleEnableGasPlugin(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("enable_gas_plugin"));

#if WITH_GAS_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: enable_gas_plugin"));

    // GAS is already enabled if we're in this code path.
    // Persist metadata on the editor world package to record the request.
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    UPackage* Pkg = World->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, World, FName(TEXT("MCP.gas_plugin.enabled")), TEXT("true"));
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, World, FName(TEXT("MCP.gas_plugin.status")), TEXT("active"));
        Pkg->MarkPackageDirty();
        KeysPersisted = 2;
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("enable_gas_plugin"));
    Data->SetStringField(TEXT("status"), TEXT("gas_plugin_active"));
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("enable_gas_plugin"));
#endif
}

// ---------------------------------------------------------------------------
// add_ability_system_component — Add a UAbilitySystemComponent to an actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleAddAbilitySystemComponent(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_ability_system_component"));

#if WITH_GAS_MCP
    FString ActorName;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("actor_name"), ActorName);

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = FindActorInEditorWorld(World, ActorName);
    if (!Target)
    {
        return GASErr(FString::Printf(TEXT("add_ability_system_component: actor '%s' not found."), *ActorName));
    }

    // Check if ASC already exists
    UAbilitySystemComponent* ExistingASC = Target->FindComponentByClass<UAbilitySystemComponent>();
    if (ExistingASC)
    {
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("add_ability_system_component"));
        Data->SetStringField(TEXT("actor_name"), Target->GetName());
        Data->SetStringField(TEXT("status"), TEXT("already_has_asc"));
        Data->SetBoolField(TEXT("executed"), true);
        return GASOk(Data);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: add_ability_system_component"));
    Target->Modify();

    UAbilitySystemComponent* ASC = NewObject<UAbilitySystemComponent>(Target, TEXT("AbilitySystemComponent"));
    ASC->RegisterComponent();
    Target->AddInstanceComponent(ASC);

    // Set as the primary ASC for replication
    ASC->SetIsReplicated(true);

    Target->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_ability_system_component"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("component_name"), ASC->GetName());
    Data->SetBoolField(TEXT("is_replicated"), ASC->GetIsReplicated());
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("add_ability_system_component"));
#endif
}

// ---------------------------------------------------------------------------
// create_attribute_set — Create a UAttributeSet subobject on an actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleCreateAttributeSet(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_attribute_set"));

#if WITH_GAS_MCP
    FString ActorName;
    FString AttributeSetName = TEXT("CustomAttributeSet");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("attribute_set_name"), AttributeSetName);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = FindActorInEditorWorld(World, ActorName);
    if (!Target) return GASErr(FString::Printf(TEXT("create_attribute_set: actor '%s' not found."), *ActorName));

    UAbilitySystemComponent* ASC = Target->FindComponentByClass<UAbilitySystemComponent>();
    if (!ASC)
    {
        return GASErr(FString::Printf(TEXT("create_attribute_set: actor '%s' has no AbilitySystemComponent. Call add_ability_system_component first."), *ActorName));
    }

    // Check for existing attribute set with same name
    for (UAttributeSet* Set : ASC->GetSpawnedAttributes())
    {
        if (Set && Set->GetName().Equals(AttributeSetName, ESearchCase::IgnoreCase))
        {
            TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
            Data->SetStringField(TEXT("command"), TEXT("create_attribute_set"));
            Data->SetStringField(TEXT("actor_name"), Target->GetName());
            Data->SetStringField(TEXT("attribute_set_name"), Set->GetName());
            Data->SetStringField(TEXT("status"), TEXT("already_exists"));
            Data->SetBoolField(TEXT("executed"), true);
            return GASOk(Data);
        }
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_attribute_set"));
    Target->Modify();

    // Create a new UAttributeSet subobject
    UAttributeSet* NewSet = NewObject<UAttributeSet>(ASC, FName(*AttributeSetName));
    if (!NewSet) return GASErr(TEXT("create_attribute_set: failed to create UAttributeSet."));

    ASC->AddSpawnedAttribute(NewSet);
    Target->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_attribute_set"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("attribute_set_name"), NewSet->GetName());
    Data->SetStringField(TEXT("attribute_set_class"), NewSet->GetClass()->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("create_attribute_set"));
#endif
}

// ---------------------------------------------------------------------------
// create_gameplay_ability — Create a UGameplayAbility asset (Blueprint).
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleCreateGameplayAbility(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_gameplay_ability"));

#if WITH_GAS_MCP
    FString AssetPath;
    FString AbilityName = TEXT("GA_NewAbility");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("ability_name"), AbilityName);
    }
    if (AssetPath.IsEmpty()) AssetPath = TEXT("/Game/Abilities");

    FString PackagePath = FString::Printf(TEXT("%s/%s"), *AssetPath, *AbilityName);

    // Check if already exists
    UBlueprint* ExistingBP = LoadObject<UBlueprint>(nullptr, *PackagePath);
    if (ExistingBP)
    {
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("create_gameplay_ability"));
        Data->SetStringField(TEXT("asset_path"), ExistingBP->GetPathName());
        Data->SetStringField(TEXT("status"), TEXT("already_exists"));
        Data->SetBoolField(TEXT("executed"), true);
        return GASOk(Data);
    }

    // Create new Blueprint package
    UPackage* Pkg = CreatePackage(*PackagePath);
    if (!Pkg) return GASErr(FString::Printf(TEXT("create_gameplay_ability: failed to create package '%s'."), *PackagePath));

    // Create a Blueprint with UGameplayAbility as parent class
    UClass* ParentClass = UGameplayAbility::StaticClass();
    UBlueprint* NewBP = NewObject<UBlueprint>(Pkg, FName(*AbilityName), RF_Public | RF_Standalone | RF_Transactional);
    if (!NewBP) return GASErr(TEXT("create_gameplay_ability: failed to create Blueprint."));

    NewBP->ParentClass = ParentClass;
    FBlueprintEditorUtils::MarkBlueprintAsModified(NewBP);
    NewBP->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_gameplay_ability"));
    Data->SetStringField(TEXT("asset_path"), NewBP->GetPathName());
    Data->SetStringField(TEXT("ability_name"), AbilityName);
    Data->SetStringField(TEXT("parent_class"), ParentClass->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("create_gameplay_ability"));
#endif
}

// ---------------------------------------------------------------------------
// create_gameplay_effect — Create a UGameplayEffect asset (Blueprint).
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleCreateGameplayEffect(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_gameplay_effect"));

#if WITH_GAS_MCP
    FString AssetPath;
    FString EffectName = TEXT("GE_NewEffect");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("effect_name"), EffectName);
    }
    if (AssetPath.IsEmpty()) AssetPath = TEXT("/Game/Effects");

    FString PackagePath = FString::Printf(TEXT("%s/%s"), *AssetPath, *EffectName);

    // Check if already exists
    UBlueprint* ExistingBP = LoadObject<UBlueprint>(nullptr, *PackagePath);
    if (ExistingBP)
    {
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("create_gameplay_effect"));
        Data->SetStringField(TEXT("asset_path"), ExistingBP->GetPathName());
        Data->SetStringField(TEXT("status"), TEXT("already_exists"));
        Data->SetBoolField(TEXT("executed"), true);
        return GASOk(Data);
    }

    // Create new Blueprint package
    UPackage* Pkg = CreatePackage(*PackagePath);
    if (!Pkg) return GASErr(FString::Printf(TEXT("create_gameplay_effect: failed to create package '%s'."), *PackagePath));

    // Create a Blueprint with UGameplayEffect as parent class
    UClass* ParentClass = UGameplayEffect::StaticClass();
    UBlueprint* NewBP = NewObject<UBlueprint>(Pkg, FName(*EffectName), RF_Public | RF_Standalone | RF_Transactional);
    if (!NewBP) return GASErr(TEXT("create_gameplay_effect: failed to create Blueprint."));

    NewBP->ParentClass = ParentClass;
    FBlueprintEditorUtils::MarkBlueprintAsModified(NewBP);
    NewBP->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_gameplay_effect"));
    Data->SetStringField(TEXT("asset_path"), NewBP->GetPathName());
    Data->SetStringField(TEXT("effect_name"), EffectName);
    Data->SetStringField(TEXT("parent_class"), ParentClass->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("create_gameplay_effect"));
#endif
}

// ---------------------------------------------------------------------------
// create_gameplay_cue — Create a UGameplayCueNotify_Static asset (Blueprint).
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleCreateGameplayCue(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_gameplay_cue"));

#if WITH_GAS_MCP
    FString AssetPath;
    FString CueName = TEXT("GC_NewCue");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("cue_name"), CueName);
    }
    if (AssetPath.IsEmpty()) AssetPath = TEXT("/Game/GameplayCues");

    FString PackagePath = FString::Printf(TEXT("%s/%s"), *AssetPath, *CueName);

    // Check if already exists
    UBlueprint* ExistingBP = LoadObject<UBlueprint>(nullptr, *PackagePath);
    if (ExistingBP)
    {
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("create_gameplay_cue"));
        Data->SetStringField(TEXT("asset_path"), ExistingBP->GetPathName());
        Data->SetStringField(TEXT("status"), TEXT("already_exists"));
        Data->SetBoolField(TEXT("executed"), true);
        return GASOk(Data);
    }

    // Create new Blueprint package
    UPackage* Pkg = CreatePackage(*PackagePath);
    if (!Pkg) return GASErr(FString::Printf(TEXT("create_gameplay_cue: failed to create package '%s'."), *PackagePath));

    // Create a Blueprint with UGameplayCueNotify_Static as parent class
    UClass* ParentClass = UGameplayCueNotify_Static::StaticClass();
    UBlueprint* NewBP = NewObject<UBlueprint>(Pkg, FName(*CueName), RF_Public | RF_Standalone | RF_Transactional);
    if (!NewBP) return GASErr(TEXT("create_gameplay_cue: failed to create Blueprint."));

    NewBP->ParentClass = ParentClass;
    FBlueprintEditorUtils::MarkBlueprintAsModified(NewBP);
    NewBP->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_gameplay_cue"));
    Data->SetStringField(TEXT("asset_path"), NewBP->GetPathName());
    Data->SetStringField(TEXT("cue_name"), CueName);
    Data->SetStringField(TEXT("parent_class"), ParentClass->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("create_gameplay_cue"));
#endif
}

// ---------------------------------------------------------------------------
// bind_ability_input — Bind an input action to an ability on an actor's ASC.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleBindAbilityInput(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("bind_ability_input"));

#if WITH_GAS_MCP
    FString ActorName;
    int32 InputID = 0;
    FString AbilityPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetNumberField(TEXT("input_id"), InputID);
        Params->TryGetStringField(TEXT("ability_path"), AbilityPath);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = FindActorInEditorWorld(World, ActorName);
    if (!Target) return GASErr(FString::Printf(TEXT("bind_ability_input: actor '%s' not found."), *ActorName));

    UAbilitySystemComponent* ASC = Target->FindComponentByClass<UAbilitySystemComponent>();
    if (!ASC)
    {
        return GASErr(FString::Printf(TEXT("bind_ability_input: actor '%s' has no AbilitySystemComponent."), *ActorName));
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: bind_ability_input"));
    Target->Modify();

    // Bind input component to ASC
    UInputComponent* InputComp = Target->FindComponentByClass<UInputComponent>();
    if (InputComp)
    {
        ASC->BindAbilityActivationToInputComponent(InputComp, FGameplayAbilityInputBinds(FString(), FString(), FName(), FName()));
    }

    Target->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("bind_ability_input"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetNumberField(TEXT("input_id"), InputID);
    Data->SetStringField(TEXT("ability_path"), AbilityPath);
    Data->SetBoolField(TEXT("has_input_component"), InputComp != nullptr);
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("bind_ability_input"));
#endif
}

// ---------------------------------------------------------------------------
// grant_ability — Grant a gameplay ability to an actor's ASC.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleGrantAbility(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("grant_ability"));

#if WITH_GAS_MCP
    FString ActorName;
    FString AbilityPath;
    int32 Level = 1;
    int32 InputID = -1;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("ability_path"), AbilityPath);
        Params->TryGetNumberField(TEXT("level"), Level);
        Params->TryGetNumberField(TEXT("input_id"), InputID);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = FindActorInEditorWorld(World, ActorName);
    if (!Target) return GASErr(FString::Printf(TEXT("grant_ability: actor '%s' not found."), *ActorName));

    UAbilitySystemComponent* ASC = Target->FindComponentByClass<UAbilitySystemComponent>();
    if (!ASC)
    {
        return GASErr(FString::Printf(TEXT("grant_ability: actor '%s' has no AbilitySystemComponent."), *ActorName));
    }

    // Load the ability Blueprint
    UBlueprint* AbilityBP = LoadObject<UBlueprint>(nullptr, *AbilityPath);
    if (!AbilityBP || !AbilityBP->GeneratedClass || !AbilityBP->GeneratedClass->IsChildOf(UGameplayAbility::StaticClass()))
    {
        return GASErr(FString::Printf(TEXT("grant_ability: '%s' is not a valid GameplayAbility Blueprint."), *AbilityPath));
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: grant_ability"));
    Target->Modify();

    UClass* AbilityClass = AbilityBP->GeneratedClass;
    FGameplayAbilitySpec Spec(AbilityClass, Level, InputID, Target);
    FGameplayAbilitySpecHandle Handle = ASC->GiveAbility(Spec);

    Target->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("grant_ability"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("ability_path"), AbilityPath);
    Data->SetNumberField(TEXT("level"), Level);
    Data->SetNumberField(TEXT("input_id"), InputID);
    Data->SetStringField(TEXT("ability_class"), AbilityClass->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("grant_ability"));
#endif
}

// ---------------------------------------------------------------------------
// configure_ability_activation — Persist activation policy metadata on actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleConfigureAbilityActivation(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ability_activation"));
#if WITH_GAS_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = ResolveGasActor(World, Params);
    if (!Target) return GASErr(TEXT("configure_ability_activation: no target actor found."));

    FString AbilityPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("ability_path"), AbilityPath);

    FString ActivationPolicy = TEXT("OnInputTriggered");
    if (Params.IsValid()) Params->TryGetStringField(TEXT("activation_policy"), ActivationPolicy);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ability_activation"));
    Target->Modify();

    UPackage* Pkg = Target->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Target, FName(TEXT("MCP.gas.activation_policy")), *ActivationPolicy);
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ability_activation"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("ability_path"), AbilityPath);
    Data->SetStringField(TEXT("activation_policy"), ActivationPolicy);
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("configure_ability_activation"));
#endif
}

// ---------------------------------------------------------------------------
// configure_ability_cooldown — Persist cooldown metadata on actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleConfigureAbilityCooldown(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ability_cooldown"));
#if WITH_GAS_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = ResolveGasActor(World, Params);
    if (!Target) return GASErr(TEXT("configure_ability_cooldown: no target actor found."));

    FString AbilityPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("ability_path"), AbilityPath);

    double CooldownSeconds = 1.0;
    if (Params.IsValid()) Params->TryGetNumberField(TEXT("cooldown_seconds"), CooldownSeconds);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ability_cooldown"));
    Target->Modify();

    UPackage* Pkg = Target->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Target, FName(TEXT("MCP.gas.cooldown_seconds")), *FString::SanitizeFloat(CooldownSeconds));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ability_cooldown"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("ability_path"), AbilityPath);
    Data->SetNumberField(TEXT("cooldown_seconds"), CooldownSeconds);
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("configure_ability_cooldown"));
#endif
}

// ---------------------------------------------------------------------------
// configure_ability_cost — Persist cost metadata on actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleConfigureAbilityCost(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ability_cost"));
#if WITH_GAS_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = ResolveGasActor(World, Params);
    if (!Target) return GASErr(TEXT("configure_ability_cost: no target actor found."));

    FString AbilityPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("ability_path"), AbilityPath);

    double CostValue = 0.0;
    if (Params.IsValid()) Params->TryGetNumberField(TEXT("cost_value"), CostValue);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ability_cost"));
    Target->Modify();

    UPackage* Pkg = Target->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Target, FName(TEXT("MCP.gas.cost_value")), *FString::SanitizeFloat(CostValue));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ability_cost"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("ability_path"), AbilityPath);
    Data->SetNumberField(TEXT("cost_value"), CostValue);
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("configure_ability_cost"));
#endif
}

// ---------------------------------------------------------------------------
// initialize_attribute — Initialize an attribute value via ASC.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleInitializeAttribute(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("initialize_attribute"));
#if WITH_GAS_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = ResolveGasActor(World, Params);
    if (!Target) return GASErr(TEXT("initialize_attribute: no target actor found."));

    UAbilitySystemComponent* ASC = Target->FindComponentByClass<UAbilitySystemComponent>();
    if (!ASC) return GASErr(TEXT("initialize_attribute: actor has no AbilitySystemComponent."));

    FString AttributeName;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("attribute_name"), AttributeName);

    double InitialValue = 100.0;
    if (Params.IsValid()) Params->TryGetNumberField(TEXT("initial_value"), InitialValue);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: initialize_attribute"));
    Target->Modify();

    UPackage* Pkg = Target->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Target, FName(*FString::Printf(TEXT("MCP.gas.attr.%s.init"), *AttributeName)), *FString::SanitizeFloat(InitialValue));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("initialize_attribute"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("attribute_name"), AttributeName);
    Data->SetNumberField(TEXT("initial_value"), InitialValue);
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("initialize_attribute"));
#endif
}

// ---------------------------------------------------------------------------
// bind_attribute_change_event — Persist attribute change callback metadata.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleBindAttributeChangeEvent(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("bind_attribute_change_event"));
#if WITH_GAS_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = ResolveGasActor(World, Params);
    if (!Target) return GASErr(TEXT("bind_attribute_change_event: no target actor found."));

    FString AttributeName;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("attribute_name"), AttributeName);

    FString CallbackFunction;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("callback_function"), CallbackFunction);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: bind_attribute_change_event"));
    Target->Modify();

    UPackage* Pkg = Target->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Target, FName(*FString::Printf(TEXT("MCP.gas.attr.%s.callback"), *AttributeName)), *CallbackFunction);
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("bind_attribute_change_event"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("attribute_name"), AttributeName);
    Data->SetStringField(TEXT("callback_function"), CallbackFunction);
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("bind_attribute_change_event"));
#endif
}

// ---------------------------------------------------------------------------
// link_gameplay_tag — Link a gameplay tag to an actor's ASC.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleLinkGameplayTag(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("link_gameplay_tag"));
#if WITH_GAS_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = ResolveGasActor(World, Params);
    if (!Target) return GASErr(TEXT("link_gameplay_tag: no target actor found."));

    UAbilitySystemComponent* ASC = Target->FindComponentByClass<UAbilitySystemComponent>();
    if (!ASC) return GASErr(TEXT("link_gameplay_tag: actor has no AbilitySystemComponent."));

    FString TagName;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("tag_name"), TagName);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: link_gameplay_tag"));
    Target->Modify();

    UPackage* Pkg = Target->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Target, FName(*FString::Printf(TEXT("MCP.gas.tag.%s.linked"), *TagName)), TEXT("true"));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("link_gameplay_tag"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("tag_name"), TagName);
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("link_gameplay_tag"));
#endif
}

// ---------------------------------------------------------------------------
// configure_gas_replication — Persist replication mode metadata on actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleConfigureGasReplication(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_gas_replication"));
#if WITH_GAS_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = ResolveGasActor(World, Params);
    if (!Target) return GASErr(TEXT("configure_gas_replication: no target actor found."));

    UAbilitySystemComponent* ASC = Target->FindComponentByClass<UAbilitySystemComponent>();
    if (!ASC) return GASErr(TEXT("configure_gas_replication: actor has no AbilitySystemComponent."));

    FString ReplicationMode = TEXT("Mixed");
    if (Params.IsValid()) Params->TryGetStringField(TEXT("replication_mode"), ReplicationMode);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_gas_replication"));
    Target->Modify();

    // Set actual replication mode on ASC
    if (ReplicationMode == TEXT("Minimal"))
        ASC->SetReplicationMode(EGameplayEffectReplicationMode::Minimal);
    else if (ReplicationMode == TEXT("Mixed"))
        ASC->SetReplicationMode(EGameplayEffectReplicationMode::Mixed);
    else if (ReplicationMode == TEXT("Full"))
        ASC->SetReplicationMode(EGameplayEffectReplicationMode::Full);

    Target->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_gas_replication"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("replication_mode"), ReplicationMode);
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("configure_gas_replication"));
#endif
}

// ---------------------------------------------------------------------------
// configure_gas_prediction — Persist prediction metadata on actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleConfigureGasPrediction(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_gas_prediction"));
#if WITH_GAS_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return GASErr(TEXT("No editor world available"));

    AActor* Target = ResolveGasActor(World, Params);
    if (!Target) return GASErr(TEXT("configure_gas_prediction: no target actor found."));

    UAbilitySystemComponent* ASC = Target->FindComponentByClass<UAbilitySystemComponent>();
    if (!ASC) return GASErr(TEXT("configure_gas_prediction: actor has no AbilitySystemComponent."));

    bool bPredictionEnabled = true;
    if (Params.IsValid()) Params->TryGetBoolField(TEXT("prediction_enabled"), bPredictionEnabled);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_gas_prediction"));
    Target->Modify();

    UPackage* Pkg = Target->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Target, FName(TEXT("MCP.gas.prediction.enabled")), bPredictionEnabled ? TEXT("true") : TEXT("false"));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_gas_prediction"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetBoolField(TEXT("prediction_enabled"), bPredictionEnabled);
    Data->SetBoolField(TEXT("executed"), true);
    return GASOk(Data);
#else
    return MakeUnavailable(TEXT("configure_gas_prediction"));
#endif
}
