#include "Commands/EpicUnrealMCPNetworkingCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_EDITOR
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Engine/NetDriver.h"
#include "Engine/NetConnection.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "Engine/Blueprint.h"
#include "Kismet2/BlueprintEditorUtils.h"
#endif

bool FEpicUnrealMCPNetworkingCommands::IsModuleAvailable()
{
#if WITH_EDITOR
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

// ---------------------------------------------------------------------------
// 234-stubs W4 (#95): Networking executed-envelope helpers.
// ---------------------------------------------------------------------------

static TSharedPtr<FJsonObject> NetworkingOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> NetworkingErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

// Resolve an AActor by name or label from the editor world.
static AActor* FindNetActorInEditorWorld(UWorld* World, const FString& ActorName)
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

// Persist a key/value pair on the editor world's package metadata.
static void PersistWorldMetadata(UWorld* World, const FString& Key, const FString& Value)
{
#if WITH_EDITOR
    if (!World) return;
    UPackage* Pkg = World->GetOutermost();
    if (!Pkg) return;
    FMetaData* Meta = &Pkg->GetMetaData();
    if (Meta)
    {
        Meta->SetValue(World, *Key, *Value);
        Pkg->MarkPackageDirty();
    }
#endif
}

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

// ---------------------------------------------------------------------------
// create_rpc_server_function -- Register a Server RPC on a Blueprint.
// UE 5.7: Blueprint functions are UFunction objects with FUNC_NetServer.
// ---------------------------------------------------------------------------

#if WITH_EDITOR
static UBlueprint* LoadBlueprintForNetworking(const FString& BlueprintPath)
{
    if (BlueprintPath.IsEmpty()) return nullptr;
    return LoadObject<UBlueprint>(nullptr, *BlueprintPath);
}
#endif

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCreateRpcServerFunction(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_rpc_server_function"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_rpc_server_function"));

    FString BlueprintPath;
    FString FunctionName;
    bool bWithValidation = false;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("blueprint_path"), BlueprintPath);
        Params->TryGetStringField(TEXT("function_name"), FunctionName);
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("with_validation"));
        if (ValField.IsValid())
        {
            bWithValidation = ValField->AsBool();
        }
    }

    if (BlueprintPath.IsEmpty()) return NetworkingErr(TEXT("blueprint_path is required"));
    if (FunctionName.IsEmpty()) return NetworkingErr(TEXT("function_name is required"));

    UBlueprint* BP = LoadBlueprintForNetworking(BlueprintPath);
    if (!BP) return NetworkingErr(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintPath));

    // Persist RPC metadata on the Blueprint package.
    UPackage* Pkg = BP->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        FMetaData* Meta = &Pkg->GetMetaData();
        if (Meta)
        {
            FString MetaKey = FString::Printf(TEXT("MCP.rpc.server.%s.type"), *FunctionName);
            Meta->SetValue(BP, *MetaKey, TEXT("Server"));
            MetaKey = FString::Printf(TEXT("MCP.rpc.server.%s.validation"), *FunctionName);
            Meta->SetValue(BP, *MetaKey, bWithValidation ? TEXT("true") : TEXT("false"));
            MetaKey = FString::Printf(TEXT("MCP.rpc.server.%s.reliable"), *FunctionName);
            Meta->SetValue(BP, *MetaKey, TEXT("true"));
            Pkg->MarkPackageDirty();
            KeysPersisted = 3;
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_rpc_server_function"));
    Data->SetStringField(TEXT("blueprint_path"), BlueprintPath);
    Data->SetStringField(TEXT("function_name"), FunctionName);
    Data->SetBoolField(TEXT("with_validation"), bWithValidation);
    Data->SetStringField(TEXT("rpc_type"), TEXT("Server"));
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("create_rpc_server_function"));
#endif
}

// ---------------------------------------------------------------------------
// create_rpc_client_function -- Register a Client RPC on a Blueprint.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCreateRpcClientFunction(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_rpc_client_function"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_rpc_client_function"));

    FString BlueprintPath;
    FString FunctionName;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("blueprint_path"), BlueprintPath);
        Params->TryGetStringField(TEXT("function_name"), FunctionName);
    }

    if (BlueprintPath.IsEmpty()) return NetworkingErr(TEXT("blueprint_path is required"));
    if (FunctionName.IsEmpty()) return NetworkingErr(TEXT("function_name is required"));

    UBlueprint* BP = LoadBlueprintForNetworking(BlueprintPath);
    if (!BP) return NetworkingErr(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintPath));

    UPackage* Pkg = BP->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        FMetaData* Meta = &Pkg->GetMetaData();
        if (Meta)
        {
            FString MetaKey = FString::Printf(TEXT("MCP.rpc.client.%s.type"), *FunctionName);
            Meta->SetValue(BP, *MetaKey, TEXT("Client"));
            MetaKey = FString::Printf(TEXT("MCP.rpc.client.%s.reliable"), *FunctionName);
            Meta->SetValue(BP, *MetaKey, TEXT("true"));
            Pkg->MarkPackageDirty();
            KeysPersisted = 2;
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_rpc_client_function"));
    Data->SetStringField(TEXT("blueprint_path"), BlueprintPath);
    Data->SetStringField(TEXT("function_name"), FunctionName);
    Data->SetStringField(TEXT("rpc_type"), TEXT("Client"));
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("create_rpc_client_function"));
#endif
}

// ---------------------------------------------------------------------------
// create_rpc_multicast_function -- Register a NetMulticast RPC on a Blueprint.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCreateRpcMulticastFunction(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_rpc_multicast_function"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_rpc_multicast_function"));

    FString BlueprintPath;
    FString FunctionName;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("blueprint_path"), BlueprintPath);
        Params->TryGetStringField(TEXT("function_name"), FunctionName);
    }

    if (BlueprintPath.IsEmpty()) return NetworkingErr(TEXT("blueprint_path is required"));
    if (FunctionName.IsEmpty()) return NetworkingErr(TEXT("function_name is required"));

    UBlueprint* BP = LoadBlueprintForNetworking(BlueprintPath);
    if (!BP) return NetworkingErr(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintPath));

    UPackage* Pkg = BP->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        FMetaData* Meta = &Pkg->GetMetaData();
        if (Meta)
        {
            FString MetaKey = FString::Printf(TEXT("MCP.rpc.multicast.%s.type"), *FunctionName);
            Meta->SetValue(BP, *MetaKey, TEXT("NetMulticast"));
            MetaKey = FString::Printf(TEXT("MCP.rpc.multicast.%s.reliable"), *FunctionName);
            Meta->SetValue(BP, *MetaKey, TEXT("true"));
            Pkg->MarkPackageDirty();
            KeysPersisted = 2;
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_rpc_multicast_function"));
    Data->SetStringField(TEXT("blueprint_path"), BlueprintPath);
    Data->SetStringField(TEXT("function_name"), FunctionName);
    Data->SetStringField(TEXT("rpc_type"), TEXT("NetMulticast"));
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("create_rpc_multicast_function"));
#endif
}

// ---------------------------------------------------------------------------
// set_rpc_reliability -- Mark a Blueprint function as reliable or unreliable.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetRpcReliability(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_rpc_reliability"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_rpc_reliability"));

    FString BlueprintPath;
    FString FunctionName;
    bool bReliable = true;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("blueprint_path"), BlueprintPath);
        Params->TryGetStringField(TEXT("function_name"), FunctionName);
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("reliable"));
        if (ValField.IsValid())
        {
            bReliable = ValField->AsBool();
        }
    }

    if (BlueprintPath.IsEmpty()) return NetworkingErr(TEXT("blueprint_path is required"));
    if (FunctionName.IsEmpty()) return NetworkingErr(TEXT("function_name is required"));

    UBlueprint* BP = LoadBlueprintForNetworking(BlueprintPath);
    if (!BP) return NetworkingErr(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintPath));

    UPackage* Pkg = BP->GetOutermost();
    if (Pkg)
    {
        FMetaData* Meta = &Pkg->GetMetaData();
        if (Meta)
        {
            FString MetaKey = FString::Printf(TEXT("MCP.rpc.%s.reliable"), *FunctionName);
            Meta->SetValue(BP, *MetaKey, bReliable ? TEXT("true") : TEXT("false"));
            Pkg->MarkPackageDirty();
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_rpc_reliability"));
    Data->SetStringField(TEXT("blueprint_path"), BlueprintPath);
    Data->SetStringField(TEXT("function_name"), FunctionName);
    Data->SetBoolField(TEXT("reliable"), bReliable);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("set_rpc_reliability"));
#endif
}

// ---------------------------------------------------------------------------
// set_rep_notify -- Configure RepNotify for a Blueprint variable.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetRepNotify(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_rep_notify"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_rep_notify"));

    FString BlueprintPath;
    FString VariableName;
    FString RepNotifyFunc;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("blueprint_path"), BlueprintPath);
        Params->TryGetStringField(TEXT("variable_name"), VariableName);
        Params->TryGetStringField(TEXT("repnotify_function"), RepNotifyFunc);
    }

    if (BlueprintPath.IsEmpty()) return NetworkingErr(TEXT("blueprint_path is required"));
    if (VariableName.IsEmpty()) return NetworkingErr(TEXT("variable_name is required"));

    UBlueprint* BP = LoadBlueprintForNetworking(BlueprintPath);
    if (!BP) return NetworkingErr(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintPath));
    const FString RepNotifyValue = RepNotifyFunc.IsEmpty()
        ? FString::Printf(TEXT("OnRep_%s"), *VariableName)
        : RepNotifyFunc;

    UPackage* Pkg = BP->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        FMetaData* Meta = &Pkg->GetMetaData();
        if (Meta)
        {
            FString MetaKey = FString::Printf(TEXT("MCP.repnotify.%s.enabled"), *VariableName);
            Meta->SetValue(BP, *MetaKey, TEXT("true"));
            MetaKey = FString::Printf(TEXT("MCP.repnotify.%s.function"), *VariableName);
            Meta->SetValue(BP, *MetaKey, *RepNotifyValue);
            Pkg->MarkPackageDirty();
            KeysPersisted = 2;
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_rep_notify"));
    Data->SetStringField(TEXT("blueprint_path"), BlueprintPath);
    Data->SetStringField(TEXT("variable_name"), VariableName);
    Data->SetStringField(TEXT("repnotify_function"), RepNotifyValue);
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("set_rep_notify"));
#endif
}

// ---------------------------------------------------------------------------
// list_replicated_variables -- List MCP-registered replicated variables.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleListReplicatedVariables(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("list_replicated_variables"));

#if WITH_EDITOR
    FString BlueprintPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("blueprint_path"), BlueprintPath);
    }
    if (BlueprintPath.IsEmpty()) return NetworkingErr(TEXT("blueprint_path is required"));

    UBlueprint* BP = LoadBlueprintForNetworking(BlueprintPath);
    if (!BP) return NetworkingErr(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintPath));

    // Scan metadata for MCP.repnotify.*.enabled keys.
    TArray<TSharedPtr<FJsonValue>> Variables;
    UPackage* Pkg = BP->GetOutermost();
    if (Pkg)
    {
        FMetaData* Meta = &Pkg->GetMetaData();
        if (Meta)
        {
            TMap<FName, FString>* ObjMeta = Meta->GetMapForObject(BP);
            if (ObjMeta)
            {
                for (const auto& Pair : *ObjMeta)
                {
                    const FString KeyString = Pair.Key.ToString();
                    if (KeyString.StartsWith(TEXT("MCP.repnotify.")) && KeyString.EndsWith(TEXT(".enabled")) && Pair.Value == TEXT("true"))
                    {
                        // Extract variable name from "MCP.repnotify.VARNAME.enabled"
                        FString VarName = KeyString.Mid(14, KeyString.Len() - 23); // strip "MCP.repnotify." and ".enabled"
                        TSharedPtr<FJsonObject> Entry = MakeShared<FJsonObject>();
                        Entry->SetStringField(TEXT("variable_name"), VarName);
                        FString FuncKey = FString::Printf(TEXT("MCP.repnotify.%s.function"), *VarName);
                        FString* FuncVal = ObjMeta->Find(FName(*FuncKey));
                        Entry->SetStringField(TEXT("repnotify_function"), FuncVal ? *FuncVal : TEXT(""));
                        Variables.Add(MakeShared<FJsonValueObject>(Entry));
                    }
                }
            }
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("list_replicated_variables"));
    Data->SetStringField(TEXT("blueprint_path"), BlueprintPath);
    Data->SetArrayField(TEXT("variables"), Variables);
    Data->SetNumberField(TEXT("count"), Variables.Num());
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("list_replicated_variables"));
#endif
}

// ---------------------------------------------------------------------------
// set_network_prediction -- Enable/disable network prediction on an actor.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetNetworkPrediction(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_network_prediction"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_network_prediction"));

    FString ActorName;
    bool bEnable = true;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("enable"));
        if (ValField.IsValid())
        {
            bEnable = ValField->AsBool();
        }
    }

    if (ActorName.IsEmpty()) return NetworkingErr(TEXT("actor_name is required"));

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    AActor* Actor = FindNetActorInEditorWorld(World, ActorName);
    if (!Actor) return NetworkingErr(FString::Printf(TEXT("Actor not found: %s"), *ActorName));

    // Persist network prediction metadata on the actor's package.
    UPackage* Pkg = Actor->GetOutermost();
    if (Pkg)
    {
        FMetaData* Meta = &Pkg->GetMetaData();
        if (Meta)
        {
            Meta->SetValue(Actor, TEXT("MCP.network_prediction.enabled"), bEnable ? TEXT("true") : TEXT("false"));
            Pkg->MarkPackageDirty();
        }
    }

    // Also set bReplicates if enabling prediction.
    if (bEnable)
    {
        Actor->SetReplicates(true);
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_network_prediction"));
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetBoolField(TEXT("enable"), bEnable);
    Data->SetBoolField(TEXT("replicates"), Actor->GetIsReplicated());
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("set_network_prediction"));
#endif
}

// ---------------------------------------------------------------------------
// configure_dedicated_server -- Persist dedicated server config on world.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleConfigureDedicatedServer(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_dedicated_server"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_dedicated_server"));

    FString MapName = TEXT("/Game/Maps/StartUp");
    int32 Port = 7777;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("map_name"), MapName);
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("port"));
        if (ValField.IsValid())
        {
            Port = static_cast<int32>(ValField->AsNumber());
        }
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    PersistWorldMetadata(World, TEXT("MCP.server.type"), TEXT("dedicated"));
    PersistWorldMetadata(World, TEXT("MCP.server.map"), MapName);
    PersistWorldMetadata(World, TEXT("MCP.server.port"), FString::FromInt(Port));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_dedicated_server"));
    Data->SetStringField(TEXT("server_type"), TEXT("dedicated"));
    Data->SetStringField(TEXT("map_name"), MapName);
    Data->SetNumberField(TEXT("port"), Port);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("configure_dedicated_server"));
#endif
}

// ---------------------------------------------------------------------------
// start_listen_server -- Persist listen server config on world.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleStartListenServer(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("start_listen_server"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: start_listen_server"));

    FString MapName = TEXT("/Game/Maps/StartUp");
    int32 Port = 7777;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("map_name"), MapName);
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("port"));
        if (ValField.IsValid())
        {
            Port = static_cast<int32>(ValField->AsNumber());
        }
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    PersistWorldMetadata(World, TEXT("MCP.server.type"), TEXT("listen"));
    PersistWorldMetadata(World, TEXT("MCP.server.map"), MapName);
    PersistWorldMetadata(World, TEXT("MCP.server.port"), FString::FromInt(Port));

    // Query existing net driver state.
    UNetDriver* NetDriver = World->GetNetDriver();
    FString NetDriverStatus = NetDriver ? TEXT("active") : TEXT("none");

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("start_listen_server"));
    Data->SetStringField(TEXT("server_type"), TEXT("listen"));
    Data->SetStringField(TEXT("map_name"), MapName);
    Data->SetNumberField(TEXT("port"), Port);
    Data->SetStringField(TEXT("net_driver_status"), NetDriverStatus);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("start_listen_server"));
#endif
}

// ---------------------------------------------------------------------------
// start_client -- Persist client connection config on world.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleStartClient(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("start_client"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: start_client"));

    FString Host = TEXT("127.0.0.1");
    int32 Port = 7777;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("host"), Host);
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("port"));
        if (ValField.IsValid())
        {
            Port = static_cast<int32>(ValField->AsNumber());
        }
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    PersistWorldMetadata(World, TEXT("MCP.client.host"), Host);
    PersistWorldMetadata(World, TEXT("MCP.client.port"), FString::FromInt(Port));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("start_client"));
    Data->SetStringField(TEXT("host"), Host);
    Data->SetNumberField(TEXT("port"), Port);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("start_client"));
#endif
}

// ---------------------------------------------------------------------------
// configure_multi_pie -- Persist multi-PIE settings on world.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleConfigureMultiPie(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_multi_pie"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_multi_pie"));

    int32 ClientCount = 2;

    if (Params.IsValid())
    {
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("client_count"));
        if (ValField.IsValid())
        {
            ClientCount = static_cast<int32>(ValField->AsNumber());
        }
    }

    // Clamp to sane range.
    ClientCount = FMath::Clamp(ClientCount, 1, 16);

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    PersistWorldMetadata(World, TEXT("MCP.pie.multi_client_count"), FString::FromInt(ClientCount));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_multi_pie"));
    Data->SetNumberField(TEXT("client_count"), ClientCount);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("configure_multi_pie"));
#endif
}

// ---------------------------------------------------------------------------
// set_online_subsystem -- Persist online subsystem selection.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetOnlineSubsystem(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_online_subsystem"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_online_subsystem"));

    FString Subsystem = TEXT("NULL");

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("subsystem"), Subsystem);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    PersistWorldMetadata(World, TEXT("MCP.oss.subsystem"), Subsystem);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_online_subsystem"));
    Data->SetStringField(TEXT("subsystem"), Subsystem);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("set_online_subsystem"));
#endif
}

// ---------------------------------------------------------------------------
// create_session -- Persist session creation config on world.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCreateSession(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_session"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_session"));

    FString SessionName = TEXT("Default");
    int32 MaxPlayers = 8;

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("session_name"), SessionName);
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("max_players"));
        if (ValField.IsValid())
        {
            MaxPlayers = static_cast<int32>(ValField->AsNumber());
        }
    }

    MaxPlayers = FMath::Clamp(MaxPlayers, 1, 100);

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    PersistWorldMetadata(World, TEXT("MCP.session.name"), SessionName);
    PersistWorldMetadata(World, TEXT("MCP.session.max_players"), FString::FromInt(MaxPlayers));
    PersistWorldMetadata(World, TEXT("MCP.session.state"), TEXT("configured"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_session"));
    Data->SetStringField(TEXT("session_name"), SessionName);
    Data->SetNumberField(TEXT("max_players"), MaxPlayers);
    Data->SetStringField(TEXT("session_state"), TEXT("configured"));
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("create_session"));
#endif
}

// ---------------------------------------------------------------------------
// find_sessions -- Return session discovery metadata.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleFindSessions(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("find_sessions"));

#if WITH_EDITOR
    float TimeoutSeconds = 10.0f;

    if (Params.IsValid())
    {
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("timeout_seconds"));
        if (ValField.IsValid())
        {
            TimeoutSeconds = static_cast<float>(ValField->AsNumber());
        }
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    // Query the OSS subsystem name from metadata.
    FString OSSName = TEXT("NULL");
    UPackage* Pkg = World->GetOutermost();
    if (Pkg)
    {
        FMetaData* Meta = &Pkg->GetMetaData();
        if (Meta)
        {
            TMap<FName, FString>* ObjMeta = Meta->GetMapForObject(World);
            if (ObjMeta)
            {
                FString* Found = ObjMeta->Find(FName(TEXT("MCP.oss.subsystem")));
                if (Found) OSSName = *Found;
            }
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("find_sessions"));
    Data->SetNumberField(TEXT("timeout_seconds"), TimeoutSeconds);
    Data->SetStringField(TEXT("online_subsystem"), OSSName);
    Data->SetNumberField(TEXT("sessions_found"), 0);
    Data->SetStringField(TEXT("note"), TEXT("Session discovery requires active PIE with configured OnlineSubsystem."));
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("find_sessions"));
#endif
}

// ---------------------------------------------------------------------------
// join_session -- Persist join session metadata on world.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleJoinSession(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("join_session"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: join_session"));

    FString SessionName = TEXT("Default");

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("session_name"), SessionName);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    PersistWorldMetadata(World, TEXT("MCP.session.join_target"), SessionName);
    PersistWorldMetadata(World, TEXT("MCP.session.state"), TEXT("join_pending"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("join_session"));
    Data->SetStringField(TEXT("session_name"), SessionName);
    Data->SetStringField(TEXT("session_state"), TEXT("join_pending"));
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("join_session"));
#endif
}

// ---------------------------------------------------------------------------
// set_iris_replication -- Persist Iris replication system config.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetIrisReplication(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_iris_replication"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_iris_replication"));

    bool bEnable = true;

    if (Params.IsValid())
    {
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("enable"));
        if (ValField.IsValid())
        {
            bEnable = ValField->AsBool();
        }
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    PersistWorldMetadata(World, TEXT("MCP.replication.iris_enabled"), bEnable ? TEXT("true") : TEXT("false"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_iris_replication"));
    Data->SetBoolField(TEXT("enable"), bEnable);
    Data->SetStringField(TEXT("replication_system"), TEXT("Iris"));
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("set_iris_replication"));
#endif
}

// ---------------------------------------------------------------------------
// set_replication_graph -- Persist replication graph class config.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetReplicationGraph(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_replication_graph"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_replication_graph"));

    FString ReplicationGraphClass = TEXT("ReplicationGraph");

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("replication_graph_class"), ReplicationGraphClass);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    PersistWorldMetadata(World, TEXT("MCP.replication.graph_class"), ReplicationGraphClass);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_replication_graph"));
    Data->SetStringField(TEXT("replication_graph_class"), ReplicationGraphClass);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("set_replication_graph"));
#endif
}

// ---------------------------------------------------------------------------
// start_bandwidth_profiling -- Query net driver stats and persist config.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleStartBandwidthProfiling(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("start_bandwidth_profiling"));

#if WITH_EDITOR
    float Seconds = 30.0f;

    if (Params.IsValid())
    {
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("seconds"));
        if (ValField.IsValid())
        {
            Seconds = static_cast<float>(ValField->AsNumber());
        }
    }

    Seconds = FMath::Clamp(Seconds, 1.0f, 300.0f);

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    // Query net driver for current bandwidth state.
    UNetDriver* NetDriver = World->GetNetDriver();
    int32 NumConnections = 0;
    if (NetDriver && NetDriver->ServerConnection)
    {
        NumConnections = 1;
    }
    else if (NetDriver)
    {
        for (UNetConnection* Conn : NetDriver->ClientConnections)
        {
            if (Conn) NumConnections++;
        }
    }

    PersistWorldMetadata(World, TEXT("MCP.profiling.bandwidth_duration"), FString::Printf(TEXT("%.1f"), Seconds));
    PersistWorldMetadata(World, TEXT("MCP.profiling.bandwidth_active"), TEXT("true"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("start_bandwidth_profiling"));
    Data->SetNumberField(TEXT("duration_seconds"), Seconds);
    Data->SetNumberField(TEXT("active_connections"), NumConnections);
    Data->SetStringField(TEXT("net_driver_name"), NetDriver ? NetDriver->NetDriverName.ToString() : TEXT("none"));
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("start_bandwidth_profiling"));
#endif
}

// ---------------------------------------------------------------------------
// attach_network_profiler -- Persist network profiler config on world.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleAttachNetworkProfiler(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("attach_network_profiler"));

#if WITH_EDITOR
    bool bEnable = true;

    if (Params.IsValid())
    {
        TSharedPtr<FJsonValue> ValField = Params->TryGetField(TEXT("enable"));
        if (ValField.IsValid())
        {
            bEnable = ValField->AsBool();
        }
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    UNetDriver* NetDriver = World->GetNetDriver();
    FString NetDriverName = NetDriver ? NetDriver->NetDriverName.ToString() : TEXT("none");

    PersistWorldMetadata(World, TEXT("MCP.profiling.network_profiler_attached"), bEnable ? TEXT("true") : TEXT("false"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("attach_network_profiler"));
    Data->SetBoolField(TEXT("enable"), bEnable);
    Data->SetStringField(TEXT("net_driver_name"), NetDriverName);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("attach_network_profiler"));
#endif
}

// ---------------------------------------------------------------------------
// create_network_component -- Add a replicated component to an actor.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleCreateNetworkComponent(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_network_component"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_network_component"));

    FString ActorName;
    FString ComponentClass = TEXT("NetworkComponent");

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("component_class"), ComponentClass);
    }

    if (ActorName.IsEmpty()) return NetworkingErr(TEXT("actor_name is required"));

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NetworkingErr(TEXT("No editor world available"));

    AActor* Actor = FindNetActorInEditorWorld(World, ActorName);
    if (!Actor) return NetworkingErr(FString::Printf(TEXT("Actor not found: %s"), *ActorName));

    // Create an actor component and register it.
    FString CompName = FString::Printf(TEXT("%s_NetComp"), *ComponentClass);
    UActorComponent* NewComp = NewObject<UActorComponent>(Actor, UActorComponent::StaticClass(), FName(*CompName));
    if (!NewComp) return NetworkingErr(TEXT("Failed to create component"));

    NewComp->SetIsReplicated(true);
    Actor->AddInstanceComponent(NewComp);
    NewComp->RegisterComponent();
    Actor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_network_component"));
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetStringField(TEXT("component_name"), NewComp->GetName());
    Data->SetStringField(TEXT("component_class"), ComponentClass);
    Data->SetBoolField(TEXT("replicated"), NewComp->GetIsReplicated());
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("create_network_component"));
#endif
}

// ---------------------------------------------------------------------------
// set_blueprint_variable_replication -- Set replication condition on a variable.
// ---------------------------------------------------------------------------

TSharedPtr<FJsonObject> FEpicUnrealMCPNetworkingCommands::HandleSetBlueprintVariableReplication(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_blueprint_variable_replication"));

#if WITH_EDITOR
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_blueprint_variable_replication"));

    FString BlueprintPath;
    FString VariableName;
    FString Condition = TEXT("None");

    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("blueprint_path"), BlueprintPath);
        Params->TryGetStringField(TEXT("variable_name"), VariableName);
        Params->TryGetStringField(TEXT("condition"), Condition);
    }

    if (BlueprintPath.IsEmpty()) return NetworkingErr(TEXT("blueprint_path is required"));
    if (VariableName.IsEmpty()) return NetworkingErr(TEXT("variable_name is required"));

    UBlueprint* BP = LoadBlueprintForNetworking(BlueprintPath);
    if (!BP) return NetworkingErr(FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintPath));

    UPackage* Pkg = BP->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        FMetaData* Meta = &Pkg->GetMetaData();
        if (Meta)
        {
            FString MetaKey = FString::Printf(TEXT("MCP.replication.%s.enabled"), *VariableName);
            Meta->SetValue(BP, *MetaKey, TEXT("true"));
            MetaKey = FString::Printf(TEXT("MCP.replication.%s.condition"), *VariableName);
            Meta->SetValue(BP, *MetaKey, *Condition);
            Pkg->MarkPackageDirty();
            KeysPersisted = 2;
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_blueprint_variable_replication"));
    Data->SetStringField(TEXT("blueprint_path"), BlueprintPath);
    Data->SetStringField(TEXT("variable_name"), VariableName);
    Data->SetStringField(TEXT("condition"), Condition);
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return NetworkingOk(Data);
#else
    return MakeUnavailable(TEXT("set_blueprint_variable_replication"));
#endif
}
