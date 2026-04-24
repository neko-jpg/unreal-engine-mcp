#include "EpicUnrealMCPBridge.h"
#include "MCPServerRunnable.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "HAL/RunnableThread.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Interfaces/IPv4/IPv4Endpoint.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonWriter.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Camera/CameraActor.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "JsonObjectConverter.h"
#include "GameFramework/Actor.h"
#include "Engine/Selection.h"
#include "Kismet/GameplayStatics.h"
#include "Async/Async.h"
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Factories/BlueprintFactory.h"
#include "EdGraphSchema_K2.h"
#include "K2Node_Event.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/SphereComponent.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "UObject/Field.h"
#include "UObject/FieldPath.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "K2Node_CallFunction.h"
#include "K2Node_InputAction.h"
#include "K2Node_Self.h"
#include "GameFramework/InputSettings.h"
#include "EditorSubsystem.h"
#include "Subsystems/EditorActorSubsystem.h"
#include "Commands/EpicUnrealMCPEditorCommands.h"
#include "Commands/EpicUnrealMCPBlueprintCommands.h"
#include "Commands/EpicUnrealMCPBlueprintGraphCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"
#include "UnrealMCPSettings.h"

static TAutoConsoleVariable<FString> CVarMCPHost(
    TEXT("unreal.mcp.host"),
    TEXT(""),
    TEXT("Optional host override for the MCP server. Empty uses Project Settings."),
    ECVF_Default
);

static TAutoConsoleVariable<int32> CVarMCPPort(
    TEXT("unreal.mcp.port"),
    0,
    TEXT("Optional port override for the MCP server. 0 uses Project Settings."),
    ECVF_Default
);

#define MCP_SERVER_HOST "127.0.0.1"
#define MCP_SERVER_PORT 55557

UEpicUnrealMCPBridge::UEpicUnrealMCPBridge()
    : bIsRunning(false)
    , ServerThread(nullptr)
    , Runnable(nullptr)
{
    EditorCommands = MakeShared<FEpicUnrealMCPEditorCommands>();
    BlueprintCommands = MakeShared<FEpicUnrealMCPBlueprintCommands>();
    BlueprintGraphCommands = MakeShared<FEpicUnrealMCPBlueprintGraphCommands>();

    const UUnrealMCPSettings* Settings = GetDefault<UUnrealMCPSettings>();
    FString HostStr = Settings ? Settings->Host : TEXT(MCP_SERVER_HOST);
    const FString CVarHost = CVarMCPHost.GetValueOnAnyThread();
    if (!CVarHost.IsEmpty())
    {
        HostStr = CVarHost;
    }
    if (HostStr.IsEmpty())
    {
        HostStr = TEXT(MCP_SERVER_HOST);
    }
    if (!FIPv4Address::Parse(HostStr, ServerAddress))
    {
        UE_LOG(LogTemp, Warning, TEXT("EpicUnrealMCPBridge: Invalid unreal.mcp.host '%s', falling back to 127.0.0.1"), *HostStr);
        FIPv4Address::Parse(TEXT(MCP_SERVER_HOST), ServerAddress);
    }

    int32 ConfiguredPort = Settings ? Settings->Port : MCP_SERVER_PORT;
    const int32 CVarPort = CVarMCPPort.GetValueOnAnyThread();
    if (CVarPort > 0)
    {
        ConfiguredPort = CVarPort;
    }
    if (ConfiguredPort < 1 || ConfiguredPort > 65535)
    {
        UE_LOG(LogTemp, Warning, TEXT("EpicUnrealMCPBridge: Invalid MCP port %d, falling back to %d"), ConfiguredPort, MCP_SERVER_PORT);
        ConfiguredPort = MCP_SERVER_PORT;
    }
    Port = static_cast<uint16>(ConfiguredPort);
}

UEpicUnrealMCPBridge::~UEpicUnrealMCPBridge()
{
    StopServer();
    EditorCommands.Reset();
    BlueprintCommands.Reset();
    BlueprintGraphCommands.Reset();
}

void UEpicUnrealMCPBridge::Initialize(FSubsystemCollectionBase& Collection)
{
    UE_LOG(LogTemp, Log, TEXT("EpicUnrealMCPBridge: Initializing"));
    StartServer();
}

void UEpicUnrealMCPBridge::Deinitialize()
{
    UE_LOG(LogTemp, Log, TEXT("EpicUnrealMCPBridge: Shutting down"));
    StopServer();
}

void UEpicUnrealMCPBridge::StartServer()
{
    if (bIsRunning)
    {
        UE_LOG(LogTemp, Warning, TEXT("EpicUnrealMCPBridge: Server is already running"));
        return;
    }

    ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
    if (!SocketSubsystem)
    {
        UE_LOG(LogTemp, Error, TEXT("EpicUnrealMCPBridge: Failed to get socket subsystem"));
        return;
    }

    TSharedPtr<FSocket> NewListenerSocket = MakeShareable(SocketSubsystem->CreateSocket(NAME_Stream, TEXT("UnrealMCPListener"), false));
    if (!NewListenerSocket.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("EpicUnrealMCPBridge: Failed to create listener socket"));
        return;
    }

    NewListenerSocket->SetReuseAddr(true);
    NewListenerSocket->SetNonBlocking(true);

    FIPv4Endpoint Endpoint(ServerAddress, Port);
    if (!NewListenerSocket->Bind(*Endpoint.ToInternetAddr()))
    {
        UE_LOG(LogTemp, Error, TEXT("EpicUnrealMCPBridge: Failed to bind listener socket to %s:%d"), *ServerAddress.ToString(), Port);
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(NewListenerSocket.Get());
        return;
    }

    if (!NewListenerSocket->Listen(5))
    {
        UE_LOG(LogTemp, Error, TEXT("EpicUnrealMCPBridge: Failed to start listening"));
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(NewListenerSocket.Get());
        return;
    }

    ListenerSocket = NewListenerSocket;
    bIsRunning = true;
    UE_LOG(LogTemp, Log, TEXT("EpicUnrealMCPBridge: Server started on %s:%d"), *ServerAddress.ToString(), Port);

    Runnable = new FMCPServerRunnable(this, ListenerSocket);
    ServerThread = FRunnableThread::Create(
        Runnable,
        TEXT("UnrealMCPServerThread"),
        0, TPri_Normal
    );

    if (!ServerThread)
    {
        UE_LOG(LogTemp, Error, TEXT("EpicUnrealMCPBridge: Failed to create server thread"));
        StopServer();
        return;
    }
}

void UEpicUnrealMCPBridge::StopServer()
{
    if (!bIsRunning)
    {
        return;
    }

    bIsRunning = false;

    if (Runnable)
    {
        Runnable->Stop();
    }

    if (ListenerSocket.IsValid())
    {
        ListenerSocket->Close();
    }
    if (ConnectionSocket.IsValid())
    {
        ConnectionSocket->Close();
    }

    if (ServerThread)
    {
        ServerThread->WaitForCompletion();
        delete ServerThread;
        ServerThread = nullptr;
    }

    if (Runnable)
    {
        delete Runnable;
        Runnable = nullptr;
    }

    if (ConnectionSocket.IsValid())
    {
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ConnectionSocket.Get());
        ConnectionSocket.Reset();
    }

    if (ListenerSocket.IsValid())
    {
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ListenerSocket.Get());
        ListenerSocket.Reset();
    }

    UE_LOG(LogTemp, Log, TEXT("EpicUnrealMCPBridge: Server stopped"));
}

FString UEpicUnrealMCPBridge::ExecuteCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    UE_LOG(LogTemp, Log, TEXT("EpicUnrealMCPBridge: Executing command: %s"), *CommandType);

    auto ExecuteOnCurrentThread = [this, &CommandType, &Params]() -> FString
    {
        TSharedPtr<FJsonObject> ResponseJson = MakeShareable(new FJsonObject);

        try
        {
            TSharedPtr<FJsonObject> ResultJson;

            if (CommandType == TEXT("ping"))
            {
                ResultJson = MakeShareable(new FJsonObject);
                ResultJson->SetStringField(TEXT("message"), TEXT("pong"));
            }
            else if (CommandType == TEXT("get_actors_in_level") ||
                     CommandType == TEXT("find_actors_by_name") ||
                     CommandType == TEXT("spawn_actor") ||
                     CommandType == TEXT("delete_actor") ||
                     CommandType == TEXT("set_actor_transform") ||
                     CommandType == TEXT("spawn_blueprint_actor"))
            {
                ResultJson = EditorCommands->HandleCommand(CommandType, Params);
            }
            else if (CommandType == TEXT("create_blueprint") ||
                     CommandType == TEXT("add_component_to_blueprint") ||
                     CommandType == TEXT("set_physics_properties") ||
                     CommandType == TEXT("compile_blueprint") ||
                     CommandType == TEXT("set_static_mesh_properties") ||
                     CommandType == TEXT("set_mesh_material_color") ||
                     CommandType == TEXT("get_available_materials") ||
                     CommandType == TEXT("apply_material_to_actor") ||
                     CommandType == TEXT("apply_material_to_blueprint") ||
                     CommandType == TEXT("get_actor_material_info") ||
                     CommandType == TEXT("get_blueprint_material_info") ||
                     CommandType == TEXT("read_blueprint_content") ||
                     CommandType == TEXT("analyze_blueprint_graph") ||
                     CommandType == TEXT("get_blueprint_variable_details") ||
                     CommandType == TEXT("get_blueprint_function_details"))
            {
                ResultJson = BlueprintCommands->HandleCommand(CommandType, Params);
            }
            else if (CommandType == TEXT("add_blueprint_node") ||
                     CommandType == TEXT("connect_nodes") ||
                     CommandType == TEXT("create_variable") ||
                     CommandType == TEXT("set_blueprint_variable_properties") ||
                     CommandType == TEXT("add_event_node") ||
                     CommandType == TEXT("delete_node") ||
                     CommandType == TEXT("set_node_property") ||
                     CommandType == TEXT("create_function") ||
                     CommandType == TEXT("add_function_input") ||
                     CommandType == TEXT("add_function_output") ||
                     CommandType == TEXT("delete_function") ||
                     CommandType == TEXT("rename_function"))
            {
                ResultJson = BlueprintGraphCommands->HandleCommand(CommandType, Params);
            }
            else
            {
                ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                ResponseJson->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));

                FString UnknownCommandResult;
                TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
                    TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&UnknownCommandResult);
                FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
                return UnknownCommandResult;
            }

            bool bSuccess = true;
            FString ErrorMessage;

            if (ResultJson->HasField(TEXT("success")))
            {
                bSuccess = ResultJson->GetBoolField(TEXT("success"));
                if (!bSuccess && ResultJson->HasField(TEXT("error")))
                {
                    ErrorMessage = ResultJson->GetStringField(TEXT("error"));
                }
            }

            if (bSuccess)
            {
                ResponseJson->SetStringField(TEXT("status"), TEXT("success"));
                ResponseJson->SetObjectField(TEXT("result"), ResultJson);
            }
            else
            {
                ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                ResponseJson->SetStringField(TEXT("error"), ErrorMessage);
            }
        }
        catch (const std::exception& e)
        {
            ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
            ResponseJson->SetStringField(TEXT("error"), UTF8_TO_TCHAR(e.what()));
        }

        FString ResultString;
        TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
            TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&ResultString);
        FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
        return ResultString;
    };

    if (IsInGameThread())
    {
        return ExecuteOnCurrentThread();
    }

    TPromise<FString> Promise;
    TFuture<FString> Future = Promise.GetFuture();

    AsyncTask(ENamedThreads::GameThread, [ExecuteOnCurrentThread, Promise = MoveTemp(Promise)]() mutable
    {
        Promise.SetValue(ExecuteOnCurrentThread());
    });

    return Future.Get();
}
