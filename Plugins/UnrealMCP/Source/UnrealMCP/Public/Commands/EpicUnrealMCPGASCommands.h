#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPGASCommands
{
public:
    FEpicUnrealMCPGASCommands();
    ~FEpicUnrealMCPGASCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleEnableGasPlugin(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddAbilitySystemComponent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateAttributeSet(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateGameplayAbility(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateGameplayEffect(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateGameplayCue(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleBindAbilityInput(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGrantAbility(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureAbilityActivation(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureAbilityCooldown(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureAbilityCost(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleInitializeAttribute(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleBindAttributeChangeEvent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleLinkGameplayTag(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureGasReplication(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureGasPrediction(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
