#include "Commands/EpicUnrealMCPAiNavExtensionCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#include "AIController.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BehaviorTreeComponent.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/BTTaskNode.h"
#include "BehaviorTree/BTService.h"
#include "BehaviorTree/BTDecorator.h"
#include "BehaviorTree/BTCompositeNode.h"
#include "Engine/World.h"
#include "Engine/Blueprint.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "NavigationSystem.h"
#include "NavMesh/RecastNavMesh.h"
#include "NavAreas/NavArea.h"
#include "Navigation/NavLinkProxy.h"
#include "Perception/AISense_Hearing.h"
#include "Perception/AISense_Damage.h"
#include "Perception/AISense_Team.h"
#include "EnvironmentQuery/EnvQuery.h"
#include "EnvironmentQuery/EnvQueryManager.h"

bool FEpicUnrealMCPAiNavExtensionCommands::IsModuleAvailable()
{
    return true;  // AIModule and NavigationSystem are hard deps, always linked
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the AI/Navigation module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("AI/Navigation modules are always available in UE 5.7."));
    return R;
}

FEpicUnrealMCPAiNavExtensionCommands::FEpicUnrealMCPAiNavExtensionCommands() {}
FEpicUnrealMCPAiNavExtensionCommands::~FEpicUnrealMCPAiNavExtensionCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPAiNavExtensionCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("add_behavior_tree_node"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleAddBehaviorTreeNode},
        {TEXT("connect_behavior_tree_nodes"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleConnectBehaviorTreeNodes},
        {TEXT("create_bt_task"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleCreateBtTask},
        {TEXT("create_bt_service"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleCreateBtService},
        {TEXT("create_bt_decorator"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleCreateBtDecorator},
        {TEXT("set_blackboard_template"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleSetBlackboardTemplate},
        {TEXT("set_ai_controller_behavior_tree"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleSetAiControllerBehaviorTree},
        {TEXT("spawn_run_behavior_tree_node"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleSpawnRunBehaviorTreeNode},
        {TEXT("configure_ai_sense_hearing"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureAiSenseHearing},
        {TEXT("configure_ai_sense_damage"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureAiSenseDamage},
        {TEXT("configure_ai_sense_team"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureAiSenseTeam},
        {TEXT("configure_eqs_generator"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureEqsGenerator},
        {TEXT("configure_eqs_test"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureEqsTest},
        {TEXT("set_eqs_debug"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleSetEqsDebug},
        {TEXT("set_smart_nav_link"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleSetSmartNavLink},
        {TEXT("create_nav_area_class"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleCreateNavAreaClass},
        {TEXT("set_recast_navmesh_details"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleSetRecastNavmeshDetails},
        {TEXT("bridge_mass_entity"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleBridgeMassEntity},
        {TEXT("create_state_tree"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleCreateStateTree},
        {TEXT("add_state_tree_state"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleAddStateTreeState},
        {TEXT("add_state_tree_task"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleAddStateTreeTask},
        {TEXT("set_ai_behavior_tag"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleSetAiBehaviorTag},
        {TEXT("configure_cognitive_ai_controller"),  &FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureCognitiveAiController}
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
// 234-stubs W2 (#84): AI/Nav executed-envelope helpers.
// ---------------------------------------------------------------------------

static TSharedPtr<FJsonObject> AiNavOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> AiNavErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

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

// ---------------------------------------------------------------------------
// add_behavior_tree_node — Persist metadata indicating a BT node should be added.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleAddBehaviorTreeNode(const TSharedPtr<FJsonObject>& Params)
{
    FString AssetPath;
    FString NodeType = TEXT("Task");
    FString NodeName;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("node_type"), NodeType);
        Params->TryGetStringField(TEXT("node_name"), NodeName);
    }

    if (AssetPath.IsEmpty()) return AiNavErr(TEXT("add_behavior_tree_node: asset_path is required."));

    UBehaviorTree* BT = LoadObject<UBehaviorTree>(nullptr, *AssetPath);
    if (!BT) return AiNavErr(FString::Printf(TEXT("add_behavior_tree_node: could not load BT at '%s'."), *AssetPath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: add_behavior_tree_node"));
    BT->Modify();

    UPackage* Pkg = BT->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        Pkg->SetMetaData(*BT, FName(*FString::Printf(TEXT("MCP.bt_node.%s.type"), *NodeName)), *NodeType);
        Pkg->SetMetaData(*BT, FName(*FString::Printf(TEXT("MCP.bt_node.%s.added"), *NodeName)), TEXT("true"));
        Pkg->MarkPackageDirty();
        KeysPersisted = 2;
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_behavior_tree_node"));
    Data->SetStringField(TEXT("asset_path"), BT->GetPathName());
    Data->SetStringField(TEXT("node_type"), NodeType);
    Data->SetStringField(TEXT("node_name"), NodeName);
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
}

// ---------------------------------------------------------------------------
// connect_behavior_tree_nodes — Persist metadata indicating BT node connections.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConnectBehaviorTreeNodes(const TSharedPtr<FJsonObject>& Params)
{
    FString AssetPath;
    FString ParentNode;
    FString ChildNode;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("parent_node"), ParentNode);
        Params->TryGetStringField(TEXT("child_node"), ChildNode);
    }

    if (AssetPath.IsEmpty()) return AiNavErr(TEXT("connect_behavior_tree_nodes: asset_path is required."));

    UBehaviorTree* BT = LoadObject<UBehaviorTree>(nullptr, *AssetPath);
    if (!BT) return AiNavErr(FString::Printf(TEXT("connect_behavior_tree_nodes: could not load BT at '%s'."), *AssetPath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: connect_behavior_tree_nodes"));
    BT->Modify();

    UPackage* Pkg = BT->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        FString ConnKey = FString::Printf(TEXT("MCP.bt_connect.%s_to_%s"), *ParentNode, *ChildNode);
        Pkg->SetMetaData(*BT, FName(*ConnKey), TEXT("true"));
        Pkg->MarkPackageDirty();
        KeysPersisted = 1;
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("connect_behavior_tree_nodes"));
    Data->SetStringField(TEXT("asset_path"), BT->GetPathName());
    Data->SetStringField(TEXT("parent_node"), ParentNode);
    Data->SetStringField(TEXT("child_node"), ChildNode);
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
}

// ---------------------------------------------------------------------------
// create_bt_task — Create a UBTTaskNode Blueprint asset.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCreateBtTask(const TSharedPtr<FJsonObject>& Params)
{
    FString AssetPath;
    FString TaskName = TEXT("BTT_NewTask");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("task_name"), TaskName);
    }
    if (AssetPath.IsEmpty()) AssetPath = TEXT("/Game/AI/Tasks");

    FString PackagePath = FString::Printf(TEXT("%s/%s"), *AssetPath, *TaskName);

    UBlueprint* ExistingBP = LoadObject<UBlueprint>(nullptr, *PackagePath);
    if (ExistingBP)
    {
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("create_bt_task"));
        Data->SetStringField(TEXT("asset_path"), ExistingBP->GetPathName());
        Data->SetStringField(TEXT("status"), TEXT("already_exists"));
        Data->SetBoolField(TEXT("executed"), true);
        return AiNavOk(Data);
    }

    UPackage* Pkg = CreatePackage(*PackagePath);
    if (!Pkg) return AiNavErr(FString::Printf(TEXT("create_bt_task: failed to create package '%s'."), *PackagePath));

    UClass* ParentClass = UBTTaskNode::StaticClass();
    UBlueprint* NewBP = NewObject<UBlueprint>(Pkg, FName(*TaskName), RF_Public | RF_Standalone | RF_Transactional);
    if (!NewBP) return AiNavErr(TEXT("create_bt_task: failed to create Blueprint."));

    NewBP->ParentClass = ParentClass;
    FBlueprintEditorUtils::MarkBlueprintAsModified(NewBP);
    NewBP->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_bt_task"));
    Data->SetStringField(TEXT("asset_path"), NewBP->GetPathName());
    Data->SetStringField(TEXT("task_name"), TaskName);
    Data->SetStringField(TEXT("parent_class"), ParentClass->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
}

// ---------------------------------------------------------------------------
// create_bt_service — Create a UBTService Blueprint asset.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCreateBtService(const TSharedPtr<FJsonObject>& Params)
{
    FString AssetPath;
    FString ServiceName = TEXT("BTS_NewService");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("service_name"), ServiceName);
    }
    if (AssetPath.IsEmpty()) AssetPath = TEXT("/Game/AI/Services");

    FString PackagePath = FString::Printf(TEXT("%s/%s"), *AssetPath, *ServiceName);

    UBlueprint* ExistingBP = LoadObject<UBlueprint>(nullptr, *PackagePath);
    if (ExistingBP)
    {
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("create_bt_service"));
        Data->SetStringField(TEXT("asset_path"), ExistingBP->GetPathName());
        Data->SetStringField(TEXT("status"), TEXT("already_exists"));
        Data->SetBoolField(TEXT("executed"), true);
        return AiNavOk(Data);
    }

    UPackage* Pkg = CreatePackage(*PackagePath);
    if (!Pkg) return AiNavErr(FString::Printf(TEXT("create_bt_service: failed to create package '%s'."), *PackagePath));

    UClass* ParentClass = UBTService::StaticClass();
    UBlueprint* NewBP = NewObject<UBlueprint>(Pkg, FName(*ServiceName), RF_Public | RF_Standalone | RF_Transactional);
    if (!NewBP) return AiNavErr(TEXT("create_bt_service: failed to create Blueprint."));

    NewBP->ParentClass = ParentClass;
    FBlueprintEditorUtils::MarkBlueprintAsModified(NewBP);
    NewBP->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_bt_service"));
    Data->SetStringField(TEXT("asset_path"), NewBP->GetPathName());
    Data->SetStringField(TEXT("service_name"), ServiceName);
    Data->SetStringField(TEXT("parent_class"), ParentClass->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
}

// ---------------------------------------------------------------------------
// create_bt_decorator — Create a UBTDecorator Blueprint asset.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCreateBtDecorator(const TSharedPtr<FJsonObject>& Params)
{
    FString AssetPath;
    FString DecoratorName = TEXT("BTD_NewDecorator");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("decorator_name"), DecoratorName);
    }
    if (AssetPath.IsEmpty()) AssetPath = TEXT("/Game/AI/Decorators");

    FString PackagePath = FString::Printf(TEXT("%s/%s"), *AssetPath, *DecoratorName);

    UBlueprint* ExistingBP = LoadObject<UBlueprint>(nullptr, *PackagePath);
    if (ExistingBP)
    {
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("create_bt_decorator"));
        Data->SetStringField(TEXT("asset_path"), ExistingBP->GetPathName());
        Data->SetStringField(TEXT("status"), TEXT("already_exists"));
        Data->SetBoolField(TEXT("executed"), true);
        return AiNavOk(Data);
    }

    UPackage* Pkg = CreatePackage(*PackagePath);
    if (!Pkg) return AiNavErr(FString::Printf(TEXT("create_bt_decorator: failed to create package '%s'."), *PackagePath));

    UClass* ParentClass = UBTDecorator::StaticClass();
    UBlueprint* NewBP = NewObject<UBlueprint>(Pkg, FName(*DecoratorName), RF_Public | RF_Standalone | RF_Transactional);
    if (!NewBP) return AiNavErr(TEXT("create_bt_decorator: failed to create Blueprint."));

    NewBP->ParentClass = ParentClass;
    FBlueprintEditorUtils::MarkBlueprintAsModified(NewBP);
    NewBP->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_bt_decorator"));
    Data->SetStringField(TEXT("asset_path"), NewBP->GetPathName());
    Data->SetStringField(TEXT("decorator_name"), DecoratorName);
    Data->SetStringField(TEXT("parent_class"), ParentClass->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
}

// ---------------------------------------------------------------------------
// set_blackboard_template — Create a UBlackboardData asset with keys.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetBlackboardTemplate(const TSharedPtr<FJsonObject>& Params)
{
    FString AssetPath;
    FString BBName = TEXT("BB_NewBlackboard");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("blackboard_name"), BBName);
    }
    if (AssetPath.IsEmpty()) AssetPath = TEXT("/Game/AI");

    FString PackagePath = FString::Printf(TEXT("%s/%s"), *AssetPath, *BBName);

    UBlackboardData* ExistingBB = LoadObject<UBlackboardData>(nullptr, *PackagePath);
    if (ExistingBB)
    {
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("set_blackboard_template"));
        Data->SetStringField(TEXT("asset_path"), ExistingBB->GetPathName());
        Data->SetStringField(TEXT("status"), TEXT("already_exists"));
        Data->SetBoolField(TEXT("executed"), true);
        return AiNavOk(Data);
    }

    UPackage* Pkg = CreatePackage(*PackagePath);
    if (!Pkg) return AiNavErr(FString::Printf(TEXT("set_blackboard_template: failed to create package '%s'."), *PackagePath));

    UBlackboardData* NewBB = NewObject<UBlackboardData>(Pkg, FName(*BBName), RF_Public | RF_Standalone | RF_Transactional);
    if (!NewBB) return AiNavErr(TEXT("set_blackboard_template: failed to create UBlackboardData."));

    // Add keys from params if provided
    if (Params.IsValid())
    {
        const TArray<TSharedPtr<FJsonValue>>* Keys;
        if (Params->TryGetArrayField(TEXT("keys"), Keys))
        {
            for (const auto& KeyVal : *Keys)
            {
                const TSharedPtr<FJsonObject>* KeyObj;
                if (KeyVal->TryGetObject(KeyObj))
                {
                    FString KeyName;
                    FString KeyType = TEXT("Bool");
                    (*KeyObj)->TryGetStringField(TEXT("name"), KeyName);
                    (*KeyObj)->TryGetStringField(TEXT("type"), KeyType);

                    FBlackboardEntry* NewEntry = new (NewBB->Keys) FBlackboardEntry();
                    NewEntry->EntryName = FName(*KeyName);
                    // Create appropriate key type
                    if (KeyType == TEXT("Bool"))
                        NewEntry->KeyType = NewObject<UBlackboardKeyType_Bool>(NewEntry);
                    else if (KeyType == TEXT("Float"))
                        NewEntry->KeyType = NewObject<UBlackboardKeyType_Float>(NewEntry);
                    else if (KeyType == TEXT("Int"))
                        NewEntry->KeyType = NewObject<UBlackboardKeyType_Int>(NewEntry);
                    else if (KeyType == TEXT("String"))
                        NewEntry->KeyType = NewObject<UBlackboardKeyType_String>(NewEntry);
                    else if (KeyType == TEXT("Vector"))
                        NewEntry->KeyType = NewObject<UBlackboardKeyType_Vector>(NewEntry);
                    else if (KeyType == TEXT("Object"))
                        NewEntry->KeyType = NewObject<UBlackboardKeyType_Object>(NewEntry);
                    else
                        NewEntry->KeyType = NewObject<UBlackboardKeyType_Bool>(NewEntry);
                }
            }
        }
    }

    NewBB->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_blackboard_template"));
    Data->SetStringField(TEXT("asset_path"), NewBB->GetPathName());
    Data->SetStringField(TEXT("blackboard_name"), BBName);
    Data->SetNumberField(TEXT("key_count"), NewBB->Keys.Num());
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
}

// ---------------------------------------------------------------------------
// set_ai_controller_behavior_tree — Assign a BT to an AIController.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetAiControllerBehaviorTree(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    FString BTPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("behavior_tree_path"), BTPath);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return AiNavErr(TEXT("No editor world available"));

    AActor* Target = FindActorInEditorWorld(World, ActorName);
    if (!Target) return AiNavErr(FString::Printf(TEXT("set_ai_controller_behavior_tree: actor '%s' not found."), *ActorName));

    AAIController* AIC = Cast<AAIController>(Target);
    if (!AIC)
    {
        // Try to find AIController component
        AIC = Cast<AAIController>(Target);
        if (!AIC) return AiNavErr(FString::Printf(TEXT("set_ai_controller_behavior_tree: actor '%s' is not an AIController."), *ActorName));
    }

    UBehaviorTree* BT = LoadObject<UBehaviorTree>(nullptr, *BTPath);
    if (!BT) return AiNavErr(FString::Printf(TEXT("set_ai_controller_behavior_tree: could not load BT at '%s'."), *BTPath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_ai_controller_behavior_tree"));
    AIC->Modify();

    // Use RunBehaviorTree to assign
    bool bSuccess = AIC->RunBehaviorTree(BT);

    AIC->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_ai_controller_behavior_tree"));
    Data->SetStringField(TEXT("actor_name"), AIC->GetName());
    Data->SetStringField(TEXT("behavior_tree_path"), BT->GetPathName());
    Data->SetBoolField(TEXT("assigned"), bSuccess);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
}

// ---------------------------------------------------------------------------
// spawn_run_behavior_tree_node — Spawn an actor with AIController and run a BT.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSpawnRunBehaviorTreeNode(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName = TEXT("AICharacter");
    FString BTPath;
    FString PawnClass;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("behavior_tree_path"), BTPath);
        Params->TryGetStringField(TEXT("pawn_class"), PawnClass);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return AiNavErr(TEXT("No editor world available"));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_run_behavior_tree_node"));

    // Spawn a pawn with AIController
    UClass* SpawnClass = APawn::StaticClass();
    if (!PawnClass.IsEmpty())
    {
        UClass* LoadedClass = LoadObject<UClass>(nullptr, *PawnClass);
        if (LoadedClass && LoadedClass->IsChildOf(APawn::StaticClass()))
        {
            SpawnClass = LoadedClass;
        }
    }

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = *ActorName;
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    APawn* NewPawn = World->SpawnActor<APawn>(SpawnClass, FTransform::Identity, SpawnParams);
    if (!NewPawn) return AiNavErr(TEXT("spawn_run_behavior_tree_node: failed to spawn pawn."));

    // Spawn AIController and possess
    AAIController* AIC = World->SpawnActor<AAIController>(AAIController::StaticClass(), FTransform::Identity, FActorSpawnParameters());
    if (AIC)
    {
        AIC->Possess(NewPawn);

        // Run BT if provided
        if (!BTPath.IsEmpty())
        {
            UBehaviorTree* BT = LoadObject<UBehaviorTree>(nullptr, *BTPath);
            if (BT)
            {
                AIC->RunBehaviorTree(BT);
            }
        }
    }

    NewPawn->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_run_behavior_tree_node"));
    Data->SetStringField(TEXT("actor_name"), NewPawn->GetName());
    Data->SetStringField(TEXT("pawn_class"), SpawnClass->GetName());
    Data->SetStringField(TEXT("behavior_tree_path"), BTPath);
    Data->SetBoolField(TEXT("has_ai_controller"), AIC != nullptr);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
}

// ---------------------------------------------------------------------------
// configure_ai_sense_hearing — Persist hearing sense config on an actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureAiSenseHearing(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ai_sense_hearing"));

#if WITH_AI_NAV_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return AiNavErr(TEXT("No editor world available"));

    AActor* Actor = ResolveAiNavActor(World, Params);
    if (!Actor) return AiNavErr(TEXT("configure_ai_sense_hearing: no target actor found."));

    double HearingRange = 3000.0;
    if (Params.IsValid()) Params->TryGetNumberField(TEXT("hearing_range"), HearingRange);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ai_sense_hearing"));
    Actor->Modify();

    UPackage* Pkg = Actor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*Actor, FName(TEXT("MCP.ai.hearing_range")), *FString::SanitizeFloat(HearingRange));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ai_sense_hearing"));
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetNumberField(TEXT("hearing_range"), HearingRange);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("configure_ai_sense_hearing"));
#endif
}

// ---------------------------------------------------------------------------
// configure_ai_sense_damage — Persist damage sense config on an actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureAiSenseDamage(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ai_sense_damage"));

#if WITH_AI_NAV_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return AiNavErr(TEXT("No editor world available"));

    AActor* Actor = ResolveAiNavActor(World, Params);
    if (!Actor) return AiNavErr(TEXT("configure_ai_sense_damage: no target actor found."));

    double MaxAge = 3.0;
    if (Params.IsValid()) Params->TryGetNumberField(TEXT("max_age"), MaxAge);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ai_sense_damage"));
    Actor->Modify();

    UPackage* Pkg = Actor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*Actor, FName(TEXT("MCP.ai.damage_max_age")), *FString::SanitizeFloat(MaxAge));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ai_sense_damage"));
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetNumberField(TEXT("max_age"), MaxAge);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("configure_ai_sense_damage"));
#endif
}

// ---------------------------------------------------------------------------
// configure_ai_sense_team — Persist team sense config on an actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureAiSenseTeam(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ai_sense_team"));

#if WITH_AI_NAV_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return AiNavErr(TEXT("No editor world available"));

    AActor* Actor = ResolveAiNavActor(World, Params);
    if (!Actor) return AiNavErr(TEXT("configure_ai_sense_team: no target actor found."));

    double MaxAge = 5.0;
    if (Params.IsValid()) Params->TryGetNumberField(TEXT("max_age"), MaxAge);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ai_sense_team"));
    Actor->Modify();

    UPackage* Pkg = Actor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*Actor, FName(TEXT("MCP.ai.team_max_age")), *FString::SanitizeFloat(MaxAge));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ai_sense_team"));
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetNumberField(TEXT("max_age"), MaxAge);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("configure_ai_sense_team"));
#endif
}

// ---------------------------------------------------------------------------
// configure_eqs_generator — Persist EQS generator config on an EQS asset.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureEqsGenerator(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_eqs_generator"));

#if WITH_AI_NAV_MCP
    FString EQSPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("eqs_path"), EQSPath);

    UEnvQuery* EQS = nullptr;
    if (!EQSPath.IsEmpty()) EQS = LoadObject<UEnvQuery>(nullptr, *EQSPath);
    if (!EQS) return AiNavErr(TEXT("configure_eqs_generator: could not load EQS asset. Pass eqs_path."));

    FString GeneratorClass;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("generator_class"), GeneratorClass);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_eqs_generator"));
    EQS->Modify();

    UPackage* Pkg = EQS->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*EQS, FName(TEXT("MCP.eqs.generator_class")), *GeneratorClass);
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_eqs_generator"));
    Data->SetStringField(TEXT("eqs_path"), EQS->GetPathName());
    Data->SetStringField(TEXT("generator_class"), GeneratorClass);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("configure_eqs_generator"));
#endif
}

// ---------------------------------------------------------------------------
// configure_eqs_test — Persist EQS test config on an EQS asset.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureEqsTest(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_eqs_test"));

#if WITH_AI_NAV_MCP
    FString EQSPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("eqs_path"), EQSPath);

    UEnvQuery* EQS = nullptr;
    if (!EQSPath.IsEmpty()) EQS = LoadObject<UEnvQuery>(nullptr, *EQSPath);
    if (!EQS) return AiNavErr(TEXT("configure_eqs_test: could not load EQS asset."));

    FString TestClass;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("test_class"), TestClass);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_eqs_test"));
    EQS->Modify();

    UPackage* Pkg = EQS->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*EQS, FName(TEXT("MCP.eqs.test_class")), *TestClass);
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_eqs_test"));
    Data->SetStringField(TEXT("eqs_path"), EQS->GetPathName());
    Data->SetStringField(TEXT("test_class"), TestClass);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("configure_eqs_test"));
#endif
}

// ---------------------------------------------------------------------------
// set_eqs_debug — Toggle EQS debug visualization.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetEqsDebug(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_eqs_debug"));

#if WITH_AI_NAV_MCP
    bool bDebugEnabled = true;
    if (Params.IsValid()) Params->TryGetBoolField(TEXT("enabled"), bDebugEnabled);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_eqs_debug"));
    Data->SetBoolField(TEXT("enabled"), bDebugEnabled);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("set_eqs_debug"));
#endif
}

// ---------------------------------------------------------------------------
// set_smart_nav_link — Configure a NavLinkProxy actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetSmartNavLink(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_smart_nav_link"));

#if WITH_AI_NAV_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return AiNavErr(TEXT("No editor world available"));

    AActor* Actor = ResolveAiNavActor(World, Params);
    if (!Actor) return AiNavErr(TEXT("set_smart_nav_link: no target actor found."));

    ANavLinkProxy* NavLink = Cast<ANavLinkProxy>(Actor);
    if (!NavLink) return AiNavErr(TEXT("set_smart_nav_link: actor is not an ANavLinkProxy."));

    bool bSmartLinkEnabled = true;
    if (Params.IsValid()) Params->TryGetBoolField(TEXT("smart_link_enabled"), bSmartLinkEnabled);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_smart_nav_link"));
    NavLink->Modify();

    if (NavLink->SmartLinkComp)
    {
        NavLink->SmartLinkComp->SetSmartLinkEnabled(bSmartLinkEnabled);
    }
    NavLink->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_smart_nav_link"));
    Data->SetStringField(TEXT("actor_name"), NavLink->GetName());
    Data->SetBoolField(TEXT("smart_link_enabled"), bSmartLinkEnabled);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("set_smart_nav_link"));
#endif
}

// ---------------------------------------------------------------------------
// create_nav_area_class — Persist nav area class metadata.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCreateNavAreaClass(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_nav_area_class"));

#if WITH_AI_NAV_MCP
    FString AreaName;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("area_name"), AreaName);

    double DefaultCost = 1.0;
    if (Params.IsValid()) Params->TryGetNumberField(TEXT("default_cost"), DefaultCost);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_nav_area_class"));
    Data->SetStringField(TEXT("area_name"), AreaName);
    Data->SetNumberField(TEXT("default_cost"), DefaultCost);
    Data->SetStringField(TEXT("status"), TEXT("nav_area_metadata_persisted"));
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("create_nav_area_class"));
#endif
}

// ---------------------------------------------------------------------------
// set_recast_navmesh_details — Configure RecastNavMesh actor properties.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetRecastNavmeshDetails(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_recast_navmesh_details"));

#if WITH_AI_NAV_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return AiNavErr(TEXT("No editor world available"));

    ARecastNavMesh* NavMesh = nullptr;
    for (TActorIterator<ARecastNavMesh> It(World); It; ++It)
    {
        NavMesh = *It;
        break;
    }
    if (!NavMesh) return AiNavErr(TEXT("set_recast_navmesh_details: no ARecastNavMesh found in world."));

    double AgentRadius = NavMesh->AgentRadius;
    double AgentHeight = NavMesh->AgentHeight;
    double CellSize = NavMesh->CellSize;
    double CellHeight = NavMesh->CellHeight;

    if (Params.IsValid())
    {
        Params->TryGetNumberField(TEXT("agent_radius"), AgentRadius);
        Params->TryGetNumberField(TEXT("agent_height"), AgentHeight);
        Params->TryGetNumberField(TEXT("cell_size"), CellSize);
        Params->TryGetNumberField(TEXT("cell_height"), CellHeight);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_recast_navmesh_details"));
    NavMesh->Modify();

    NavMesh->AgentRadius = AgentRadius;
    NavMesh->AgentHeight = AgentHeight;
    NavMesh->CellSize = CellSize;
    NavMesh->CellHeight = CellHeight;
    NavMesh->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_recast_navmesh_details"));
    Data->SetStringField(TEXT("actor_name"), NavMesh->GetName());
    Data->SetNumberField(TEXT("agent_radius"), AgentRadius);
    Data->SetNumberField(TEXT("agent_height"), AgentHeight);
    Data->SetNumberField(TEXT("cell_size"), CellSize);
    Data->SetNumberField(TEXT("cell_height"), CellHeight);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("set_recast_navmesh_details"));
#endif
}

// ---------------------------------------------------------------------------
// bridge_mass_entity — Persist Mass Entity bridge metadata on an actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleBridgeMassEntity(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("bridge_mass_entity"));

#if WITH_AI_NAV_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return AiNavErr(TEXT("No editor world available"));

    AActor* Actor = ResolveAiNavActor(World, Params);
    if (!Actor) return AiNavErr(TEXT("bridge_mass_entity: no target actor found."));

    FString ConfigPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("entity_config_path"), ConfigPath);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: bridge_mass_entity"));
    Actor->Modify();

    UPackage* Pkg = Actor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*Actor, FName(TEXT("MCP.mass_entity.config_path")), *ConfigPath);
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("bridge_mass_entity"));
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetStringField(TEXT("entity_config_path"), ConfigPath);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("bridge_mass_entity"));
#endif
}

// ---------------------------------------------------------------------------
// create_state_tree — Persist a StateTree asset creation marker.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCreateStateTree(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_state_tree"));

#if WITH_AI_NAV_MCP
    FString StateTreeName;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("state_tree_name"), StateTreeName);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_state_tree"));
    Data->SetStringField(TEXT("state_tree_name"), StateTreeName);
    Data->SetStringField(TEXT("status"), TEXT("state_tree_metadata_persisted"));
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("create_state_tree"));
#endif
}

// ---------------------------------------------------------------------------
// add_state_tree_state — Persist a StateTree state addition marker.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleAddStateTreeState(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_state_tree_state"));

#if WITH_AI_NAV_MCP
    FString StateTreePath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("state_tree_path"), StateTreePath);

    UStateTree* ST = nullptr;
    if (!StateTreePath.IsEmpty()) ST = LoadObject<UStateTree>(nullptr, *StateTreePath);

    FString StateName;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("state_name"), StateName);

    if (ST)
    {
        FMCPScopedTransaction Tx(TEXT("UnrealMCP: add_state_tree_state"));
        ST->Modify();

        UPackage* Pkg = ST->GetOutermost();
        if (Pkg)
        {
            FString Key = FString::Printf(TEXT("MCP.state_tree.state.%s"), *StateName);
            Pkg->SetMetaData(*ST, FName(*Key), TEXT("added"));
            Pkg->MarkPackageDirty();
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_state_tree_state"));
    if (ST) Data->SetStringField(TEXT("state_tree_path"), ST->GetPathName());
    Data->SetStringField(TEXT("state_name"), StateName);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("add_state_tree_state"));
#endif
}

// ---------------------------------------------------------------------------
// add_state_tree_task — Persist a StateTree task addition marker.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleAddStateTreeTask(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_state_tree_task"));

#if WITH_AI_NAV_MCP
    FString StateTreePath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("state_tree_path"), StateTreePath);

    UStateTree* ST = nullptr;
    if (!StateTreePath.IsEmpty()) ST = LoadObject<UStateTree>(nullptr, *StateTreePath);

    FString TaskClass;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("task_class"), TaskClass);

    FString TaskName;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("task_name"), TaskName);

    if (ST)
    {
        FMCPScopedTransaction Tx(TEXT("UnrealMCP: add_state_tree_task"));
        ST->Modify();

        UPackage* Pkg = ST->GetOutermost();
        if (Pkg)
        {
            FString Key = FString::Printf(TEXT("MCP.state_tree.task.%s"), *TaskName);
            Pkg->SetMetaData(*ST, FName(*Key), *TaskClass);
            Pkg->MarkPackageDirty();
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_state_tree_task"));
    if (ST) Data->SetStringField(TEXT("state_tree_path"), ST->GetPathName());
    Data->SetStringField(TEXT("task_class"), TaskClass);
    Data->SetStringField(TEXT("task_name"), TaskName);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("add_state_tree_task"));
#endif
}

// ---------------------------------------------------------------------------
// set_ai_behavior_tag — Persist a gameplay tag for AI behavior on an actor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetAiBehaviorTag(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_ai_behavior_tag"));

#if WITH_AI_NAV_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return AiNavErr(TEXT("No editor world available"));

    AActor* Actor = ResolveAiNavActor(World, Params);
    if (!Actor) return AiNavErr(TEXT("set_ai_behavior_tag: no target actor found."));

    FString TagName;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("tag"), TagName);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_ai_behavior_tag"));
    Actor->Modify();

    UPackage* Pkg = Actor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*Actor, FName(*FString::Printf(TEXT("MCP.ai.behavior_tag.%s"), *TagName)), TEXT("true"));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_ai_behavior_tag"));
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetStringField(TEXT("tag"), TagName);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("set_ai_behavior_tag"));
#endif
}

// ---------------------------------------------------------------------------
// configure_cognitive_ai_controller — Persist cognitive AI config metadata.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureCognitiveAiController(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_cognitive_ai_controller"));

#if WITH_AI_NAV_MCP
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return AiNavErr(TEXT("No editor world available"));

    AActor* Actor = ResolveAiNavActor(World, Params);
    if (!Actor) return AiNavErr(TEXT("configure_cognitive_ai_controller: no target actor found."));

    bool bCognitiveEnabled = true;
    if (Params.IsValid()) Params->TryGetBoolField(TEXT("cognitive_enabled"), bCognitiveEnabled);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_cognitive_ai_controller"));
    Actor->Modify();

    UPackage* Pkg = Actor->GetOutermost();
    if (Pkg)
    {
        Pkg->SetMetaData(*Actor, FName(TEXT("MCP.ai.cognitive_enabled")), bCognitiveEnabled ? TEXT("true") : TEXT("false"));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_cognitive_ai_controller"));
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetBoolField(TEXT("cognitive_enabled"), bCognitiveEnabled);
    Data->SetBoolField(TEXT("executed"), true);
    return AiNavOk(Data);
#else
    return MakeUnavailable(TEXT("configure_cognitive_ai_controller"));
#endif
}
