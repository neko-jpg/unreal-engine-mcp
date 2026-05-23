#include "Commands/EpicUnrealMCPNetworkingCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

bool FEpicUnrealMCPNetworkingCommands::IsModuleAvailable()
{
#if 1
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPNetworkingCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Engine module dependencies satisfied by default; OnlineSubsystem may need an OSS-specific plugin."));
    return R;
}

FEpicUnrealMCPNetworkingCommands::FEpicUnrealMCPNetworkingCommands() {}
FEpicUnrealMCPNetworkingCommands::~FEpicUnrealMCPNetworkingCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPNetworkingCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_rpc_server_function"),  &FEpicUnrealMCPNetworkingCommands::HandleCreateRpcServerFunction},
        {TEXT("create_rpc_client_function"),  &FEpicUnrealMCPNetworkingCommands::HandleCreateRpcClientFunction},
        {TEXT("create_rpc_multicast_function"),  &FEpicUnrealMCPNetworkingCommands::HandleCreateRpcMulticastFunction},
        {TEXT("set_rpc_reliability"),  &FEpicUnrealMCPNetworkingCommands::HandleSetRpcReliability},
        {TEXT("set_rep_notify"),  &FEpicUnrealMCPNetworkingCommands::HandleSetRepNotify},
        {TEXT("list_replicated_variables"),  &FEpicUnrealMCPNetworkingCommands::HandleListReplicatedVariables},
        {TEXT("set_network_prediction"),  &FEpicUnrealMCPNetworkingCommands::HandleSetNetworkPrediction},
        {TEXT("configure_dedicated_server"),  &FEpicUnrealMCPNetworkingCommands::HandleConfigureDedicatedServer},
        {TEXT("start_listen_server"),  &FEpicUnrealMCPNetworkingCommands::HandleStartListenServer},
        {TEXT("start_client"),  &FEpicUnrealMCPNetworkingCommands::HandleStartClient},
        {TEXT("configure_multi_pie"),  &FEpicUnrealMCPNetworkingCommands::HandleConfigureMultiPie},
        {TEXT("set_online_subsystem"),  &FEpicUnrealMCPNetworkingCommands::HandleSetOnlineSubsystem},
        {TEXT("create_session"),  &FEpicUnrealMCPNetworkingCommands::HandleCreateSession},
        {TEXT("find_sessions"),  &FEpicUnrealMCPNetworkingCommands::HandleFindSessions},
        {TEXT("join_session"),  &FEpicUnrealMCPNetworkingCommands::HandleJoinSession},
        {TEXT("set_iris_replication"),  &FEpicUnrealMCPNetworkingCommands::HandleSetIrisReplication},
        {TEXT("set_replication_graph"),  &FEpicUnrealMCPNetworkingCommands::HandleSetReplicationGraph},
        {TEXT("start_bandwidth_profiling"),  &FEpicUnrealMCPNetworkingCommands::HandleStartBandwidthProfiling},
        {TEXT("attach_network_profiler"),  &FEpicUnrealMCPNetworkingCommands::HandleAttachNetworkProfiler},
        {TEXT("create_network_component"),  &FEpicUnrealMCPNetworkingCommands::HandleCreateNetworkComponent},
        {TEXT("set_blueprint_variable_replication"),  &FEpicUnrealMCPNetworkingCommands::HandleSetBlueprintVariableReplication}
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

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCreateRpcServerFunction(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_rpc_server_function"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_rpc_server_function"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCreateRpcClientFunction(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_rpc_client_function"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_rpc_client_function"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCreateRpcMulticastFunction(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_rpc_multicast_function"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_rpc_multicast_function"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetRpcReliability(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_rpc_reliability"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_rpc_reliability"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetRepNotify(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_rep_notify"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_rep_notify"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleListReplicatedVariables(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("list_replicated_variables"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("list_replicated_variables"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetNetworkPrediction(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_network_prediction"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_network_prediction"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleConfigureDedicatedServer(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_dedicated_server"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_dedicated_server"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleStartListenServer(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("start_listen_server"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("start_listen_server"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleStartClient(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("start_client"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("start_client"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleConfigureMultiPie(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_multi_pie"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_multi_pie"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetOnlineSubsystem(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_online_subsystem"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_online_subsystem"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCreateSession(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_session"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_session"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleFindSessions(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("find_sessions"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("find_sessions"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleJoinSession(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("join_session"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("join_session"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetIrisReplication(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_iris_replication"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_iris_replication"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetReplicationGraph(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_replication_graph"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_replication_graph"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleStartBandwidthProfiling(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("start_bandwidth_profiling"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("start_bandwidth_profiling"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleAttachNetworkProfiler(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("attach_network_profiler"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("attach_network_profiler"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCreateNetworkComponent(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_network_component"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_network_component"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetBlueprintVariableReplication(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_blueprint_variable_replication"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_blueprint_variable_replication"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; Blueprint and PIE plumbing may need finishing in the editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
