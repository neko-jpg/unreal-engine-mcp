#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPAiNavExtensionCommands
{
public:
    FEpicUnrealMCPAiNavExtensionCommands();
    ~FEpicUnrealMCPAiNavExtensionCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleAddBehaviorTreeNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConnectBehaviorTreeNodes(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateBtTask(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateBtService(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateBtDecorator(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetBlackboardTemplate(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetAiControllerBehaviorTree(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnRunBehaviorTreeNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureAiSenseHearing(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureAiSenseDamage(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureAiSenseTeam(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureEqsGenerator(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureEqsTest(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetEqsDebug(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetSmartNavLink(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateNavAreaClass(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetRecastNavmeshDetails(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleBridgeMassEntity(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateStateTree(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddStateTreeState(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddStateTreeTask(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetAiBehaviorTag(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureCognitiveAiController(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
