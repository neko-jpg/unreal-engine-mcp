#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPNetworkingCommands
{
public:
    FEpicUnrealMCPNetworkingCommands();
    ~FEpicUnrealMCPNetworkingCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateRpcServerFunction(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateRpcClientFunction(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateRpcMulticastFunction(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetRpcReliability(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetRepNotify(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleListReplicatedVariables(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNetworkPrediction(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureDedicatedServer(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleStartListenServer(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleStartClient(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureMultiPie(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetOnlineSubsystem(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateSession(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleFindSessions(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleJoinSession(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetIrisReplication(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetReplicationGraph(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleStartBandwidthProfiling(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAttachNetworkProfiler(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateNetworkComponent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetBlueprintVariableReplication(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
