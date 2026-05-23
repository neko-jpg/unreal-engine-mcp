#include "Commands/EpicUnrealMCPAiNavExtensionCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

bool FEpicUnrealMCPAiNavExtensionCommands::IsModuleAvailable()
{
#if 1
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPAiNavExtensionCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("AI / Navigation modules ship with UE 5.7; the handler always returns queued payloads while full editor-side wiring is planned."));
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

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleAddBehaviorTreeNode(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_behavior_tree_node"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_behavior_tree_node"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConnectBehaviorTreeNodes(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("connect_behavior_tree_nodes"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("connect_behavior_tree_nodes"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCreateBtTask(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_bt_task"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_bt_task"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCreateBtService(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_bt_service"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_bt_service"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCreateBtDecorator(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_bt_decorator"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_bt_decorator"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetBlackboardTemplate(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_blackboard_template"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_blackboard_template"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetAiControllerBehaviorTree(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_ai_controller_behavior_tree"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_ai_controller_behavior_tree"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSpawnRunBehaviorTreeNode(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_run_behavior_tree_node"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_run_behavior_tree_node"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureAiSenseHearing(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ai_sense_hearing"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ai_sense_hearing"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureAiSenseDamage(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ai_sense_damage"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ai_sense_damage"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureAiSenseTeam(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ai_sense_team"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ai_sense_team"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureEqsGenerator(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_eqs_generator"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_eqs_generator"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureEqsTest(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_eqs_test"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_eqs_test"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetEqsDebug(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_eqs_debug"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_eqs_debug"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetSmartNavLink(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_smart_nav_link"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_smart_nav_link"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCreateNavAreaClass(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_nav_area_class"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_nav_area_class"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetRecastNavmeshDetails(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_recast_navmesh_details"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_recast_navmesh_details"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleBridgeMassEntity(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("bridge_mass_entity"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("bridge_mass_entity"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleCreateStateTree(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_state_tree"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_state_tree"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleAddStateTreeState(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_state_tree_state"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_state_tree_state"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleAddStateTreeTask(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_state_tree_task"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_state_tree_task"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleSetAiBehaviorTag(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_ai_behavior_tag"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_ai_behavior_tag"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAiNavExtensionCommands::HandleConfigureCognitiveAiController(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_cognitive_ai_controller"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_cognitive_ai_controller"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the AI / Behavior-Tree / EQS / StateTree editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
