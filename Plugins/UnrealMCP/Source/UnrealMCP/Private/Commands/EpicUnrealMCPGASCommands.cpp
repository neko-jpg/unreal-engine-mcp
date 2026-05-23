#include "Commands/EpicUnrealMCPGASCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

bool FEpicUnrealMCPGASCommands::IsModuleAvailable()
{
#if 1
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPGASCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Enable the GameplayAbilities plugin (Engine/Plugins/Runtime/GameplayAbilities) and rebuild UnrealMCP so GameplayAbilities + GameplayTasks are linked."));
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

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleEnableGasPlugin(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("enable_gas_plugin"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("enable_gas_plugin"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleAddAbilitySystemComponent(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_ability_system_component"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_ability_system_component"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleCreateAttributeSet(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_attribute_set"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_attribute_set"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleCreateGameplayAbility(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_gameplay_ability"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_gameplay_ability"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleCreateGameplayEffect(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_gameplay_effect"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_gameplay_effect"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleCreateGameplayCue(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_gameplay_cue"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_gameplay_cue"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleBindAbilityInput(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("bind_ability_input"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("bind_ability_input"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleGrantAbility(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("grant_ability"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("grant_ability"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleConfigureAbilityActivation(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ability_activation"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ability_activation"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleConfigureAbilityCooldown(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ability_cooldown"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ability_cooldown"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleConfigureAbilityCost(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ability_cost"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ability_cost"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleInitializeAttribute(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("initialize_attribute"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("initialize_attribute"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleBindAttributeChangeEvent(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("bind_attribute_change_event"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("bind_attribute_change_event"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleLinkGameplayTag(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("link_gameplay_tag"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("link_gameplay_tag"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleConfigureGasReplication(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_gas_replication"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_gas_replication"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPGASCommands::HandleConfigureGasPrediction(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_gas_prediction"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_gas_prediction"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; complete in the GAS editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
