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
#include "Containers/Ticker.h"
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
#include "HAL/CriticalSection.h"
#include "HAL/PlatformProcess.h"
#include "Misc/ScopeLock.h"
// ---------------------------------------------------------------------------
// Command-handler #includes -- only required in this translation unit because
// the bridge now owns its handlers exclusively through the registry's
// captured TSharedPtrs.  These do not need to leak into EpicUnrealMCPBridge.h.
// ---------------------------------------------------------------------------
#include "Commands/EpicUnrealMCPEditorCommands.h"
#include "Commands/EpicUnrealMCPActorCommands.h"
#include "Commands/EpicUnrealMCPNavigationCommands.h"
#include "Commands/EpicUnrealMCPBlueprintCommands.h"
#include "Commands/EpicUnrealMCPBlueprintGraphCommands.h"
#include "Commands/EpicUnrealMCPMaterialCommands.h"
#include "Commands/EpicUnrealMCPProjectEditorCommands.h"
#include "Commands/EpicUnrealMCPContentBrowserCommands.h"
#include "Commands/EpicUnrealMCPAssetImportCommands.h"
#include "Commands/EpicUnrealMCPMeshEditingCommands.h"
#include "Commands/EpicUnrealMCPEnhancedInputCommands.h"
#include "Commands/EpicUnrealMCPGameplayFrameworkCommands.h"
#include "Commands/EpicUnrealMCPUMGCommands.h"
#include "Commands/EpicUnrealMCPRenderingCommands.h"
#include "Commands/EpicUnrealMCPLightingAtmosphereCommands.h"
#include "Commands/EpicUnrealMCPDataTableCommands.h"
#include "Commands/EpicUnrealMCPAudioCommands.h"
#include "Commands/EpicUnrealMCPSequencerCommands.h"
#include "Commands/EpicUnrealMCPVroidCommands.h"
#include "Commands/EpicUnrealMCPCesiumCommands.h"
#include "Commands/EpicUnrealMCPProceduralCommands.h"
#include "Commands/EpicUnrealMCPNiagaraCommands.h"
#include "Commands/EpicUnrealMCPLandscapeCommands.h"
#include "Commands/EpicUnrealMCPAnimationRiggingCommands.h"
#include "Commands/EpicUnrealMCPAiNavExtensionCommands.h"
#include "Commands/EpicUnrealMCPMovieRenderQueueCommands.h"
#include "Commands/EpicUnrealMCPFoliageCommands.h"
#include "Commands/EpicUnrealMCPPCGCommands.h"
#include "Commands/EpicUnrealMCPNetworkingCommands.h"
#include "Commands/EpicUnrealMCPChaosCommands.h"
#include "Commands/EpicUnrealMCPGASCommands.h"
#include "Commands/EpicUnrealMCPWaterCommands.h"
#include "Commands/EpicUnrealMCPMobileXrCommands.h"
#include "Commands/EpicUnrealMCPSourceControlCommands.h"
#include "Commands/EpicUnrealMCPLocalizationCommands.h"
#include "Commands/EpicUnrealMCPTestingValidationCommands.h"
#include "Commands/EpicUnrealMCPDataTableExtensionCommands.h"
#include "Commands/EpicUnrealMCPMetaSoundCommands.h"
#include "Commands/EpicUnrealMCPSequencerExtensionCommands.h"
#include "Commands/EpicUnrealMCPPhysicsCommands.h"
#include "Commands/EpicUnrealMCPValidationCommands.h"
#include "Commands/EpicUnrealMCPInstanceCommands.h"
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

namespace
{
double GetDeferredEditorCommandDelaySeconds(const FString& CommandType)
{
    static const TSet<FString> SlowDeferredCommands = {
        TEXT("create_level"),
        TEXT("save_level"),
        TEXT("load_level"),
        TEXT("duplicate_level"),
        TEXT("rename_level"),
        TEXT("delete_level"),
        TEXT("add_sublevel"),
        TEXT("remove_sublevel"),
        TEXT("set_sublevel_visible"),
        TEXT("set_sublevel_loaded"),
        TEXT("create_streaming_volume"),
        TEXT("set_level_streaming_settings"),
        TEXT("enable_world_partition"),
        TEXT("set_world_partition_grid"),
        TEXT("load_world_partition_cell"),
        TEXT("unload_world_partition_cell"),
        TEXT("create_data_layer"),
        TEXT("add_actors_to_data_layer"),
        TEXT("remove_actors_from_data_layer"),
        TEXT("set_data_layer_enabled"),
        TEXT("create_hlod_layer"),
        TEXT("build_hlod"),
        TEXT("rebuild_hlod"),
        TEXT("set_one_file_per_actor"),
        TEXT("set_level_bounds"),
        TEXT("set_world_origin_rebasing"),
        TEXT("start_pie"),
        TEXT("stop_pie"),
        TEXT("start_standalone_game"),
        TEXT("start_simulate"),
        TEXT("undo"),
        TEXT("redo"),
        TEXT("save_all"),
        TEXT("save_asset"),
        TEXT("create_utility_widget"),
        TEXT("create_utility_blueprint"),
        TEXT("create_collapsed_graph"),
        TEXT("create_macro_graph"),
        TEXT("create_macro_instance"),
        TEXT("create_timeline"),
        TEXT("edit_timeline"),
        TEXT("import_fbx_mesh"),
        TEXT("import_texture"),
        TEXT("import_audio"),
        TEXT("import_gltf"),
        TEXT("import_obj"),
        TEXT("import_usd"),
        TEXT("import_mp3"),
        TEXT("import_alembic"),
        TEXT("import_datasmith"),
        TEXT("reimport_asset"),
        TEXT("export_asset"),
        TEXT("take_screenshot"),
        TEXT("export_level"),
        TEXT("save_import_preset"),
        TEXT("load_import_preset"),
        TEXT("create_input_action"),
        TEXT("create_input_mapping_context"),
        TEXT("add_enhanced_input_mapping"),
        TEXT("remove_enhanced_input_mapping"),
        TEXT("configure_enhanced_input_action"),
        TEXT("configure_enhanced_input_mapping"),
        TEXT("add_runtime_mapping_context"),
        TEXT("remove_runtime_mapping_context"),
        TEXT("setup_enhanced_input_binding"),
        TEXT("setup_rebind_ui"),
        TEXT("rebind_enhanced_input_key"),
        TEXT("configure_local_multiplayer_input"),
        TEXT("create_widget_blueprint"),
        TEXT("add_widget_to_widget_blueprint"),
        TEXT("remove_widget_from_widget_blueprint"),
        TEXT("set_widget_slot_properties"),
        TEXT("bind_widget_button_on_clicked"),
        TEXT("bind_widget_property"),
        TEXT("create_widget_animation"),
        TEXT("compile_widget_blueprint"),
        TEXT("create_ui_template")
    };

    if (SlowDeferredCommands.Contains(CommandType))
    {
        return 0.5;
    }

    static const TSet<FString> AssetLifecycleCommands = {
        TEXT("create_blueprint"),
        TEXT("compile_blueprint"),
        TEXT("create_folder"),
        TEXT("delete_folder"),
        TEXT("move_asset"),
        TEXT("copy_asset"),
        TEXT("duplicate_asset"),
        TEXT("rename_asset"),
        TEXT("delete_asset"),
        TEXT("unload_asset"),
        TEXT("save_assets"),
        TEXT("set_asset_metadata"),
        TEXT("tag_asset"),
        TEXT("fixup_redirectors"),
        TEXT("set_blueprint_parent_class"),
        TEXT("set_blueprint_class_settings"),
        TEXT("set_blueprint_class_defaults"),
        TEXT("set_component_defaults"),
        TEXT("edit_construction_script"),
        TEXT("create_event_dispatcher"),
        TEXT("bind_event_dispatcher"),
        TEXT("create_enum"),
        TEXT("create_struct"),
        TEXT("edit_enum"),
        TEXT("edit_struct"),
        TEXT("create_blueprint_interface"),
        TEXT("implement_interface"),
        TEXT("create_function_library"),
        TEXT("create_macro_library"),
        TEXT("add_comment_node"),
        TEXT("add_reroute_node"),
        TEXT("create_collapsed_graph"),
        TEXT("create_macro_graph"),
        TEXT("create_macro_instance"),
        TEXT("create_timeline"),
        TEXT("edit_timeline"),
        TEXT("bulk_rename"),
        TEXT("bulk_move"),
        TEXT("bulk_delete"),
        TEXT("create_primary_asset_label"),
        TEXT("delete_primary_asset_label"),
        TEXT("set_asset_manager_settings"),
        TEXT("add_primary_asset_bundle"),
        // Gameplay Framework commands that modify assets
        TEXT("create_gamemode_blueprint"),
        TEXT("create_gamemode_cpp_class"),
        TEXT("create_gamestate"),
        TEXT("create_playerstate"),
        TEXT("create_playercontroller"),
        TEXT("create_aicontroller"),
        TEXT("create_pawn"),
        TEXT("create_character"),
        TEXT("set_hud_class"),
        TEXT("set_spectator_pawn"),
        TEXT("set_camera_manager"),
        TEXT("setup_camera_component"),
        TEXT("setup_spring_arm"),
        TEXT("create_savegame_class"),
        TEXT("create_gameinstance"),
        TEXT("create_gameinstance_subsystem"),
        TEXT("create_world_subsystem"),
        TEXT("create_localplayer_subsystem"),
        TEXT("setup_gameplay_tags"),
        TEXT("add_gameplay_tag"),
        TEXT("place_player_start"),
        TEXT("create_widget_blueprint"),
        TEXT("add_widget_to_widget_blueprint"),
        TEXT("remove_widget_from_widget_blueprint"),
        TEXT("set_widget_text"),
        TEXT("set_widget_font"),
        TEXT("set_widget_color"),
        TEXT("set_widget_brush"),
        TEXT("set_widget_style"),
        TEXT("bind_widget_button_on_clicked"),
        TEXT("bind_widget_property"),
        TEXT("create_widget_animation"),
        TEXT("compile_widget_blueprint"),
        TEXT("create_ui_template")
    };

    return AssetLifecycleCommands.Contains(CommandType) ? 0.25 : 0.0;
}

FCriticalSection GDeferredEditorCommandMutex;
double GLastDeferredEditorCommandEndSeconds = 0.0;
}

template <typename HandlerType>
void UEpicUnrealMCPBridge::RegisterHandler(int32 RouteId)
{
    TSharedPtr<HandlerType> Handler = MakeShared<HandlerType>();
    CommandHandlerRegistry.Add(
        RouteId,
        [Handler](const FString& CommandType, const TSharedPtr<FJsonObject>& Params) -> TSharedPtr<FJsonObject>
        {
            return Handler->HandleCommand(CommandType, Params);
        }
    );
}

void UEpicUnrealMCPBridge::RegisterHandlers()
{
    // ---------------------------------------------------------------
    // The single source of truth for "which RouteId belongs to which
    // handler class" inside the bridge.  Adding a new handler is a
    // **single-line edit here** (plus a matching command-name -> RouteId
    // entry in EpicUnrealMCPRouter.cpp).
    // ---------------------------------------------------------------

    // Route 0: built-in ping handled inline (no dedicated handler class).
    CommandHandlerRegistry.Add(
        0,
        [](const FString& /*CommandType*/, const TSharedPtr<FJsonObject>& /*Params*/) -> TSharedPtr<FJsonObject>
        {
            TSharedPtr<FJsonObject> Result = MakeShareable(new FJsonObject);
            Result->SetStringField(TEXT("message"), TEXT("pong"));
            return Result;
        }
    );

    // Route 1..21: Phase 1/2/3 handler split lanes.  RouteId order is
    // intentionally preserved for backward compat with existing JSON
    // command -> route mappings inside EpicUnrealMCPRouter.cpp.
    RegisterHandler<FEpicUnrealMCPActorCommands>(1);             // Actor CRUD (Phase 2)
    RegisterHandler<FEpicUnrealMCPBlueprintCommands>(2);         // Blueprints
    RegisterHandler<FEpicUnrealMCPBlueprintGraphCommands>(3);    // Blueprint graph nodes
    RegisterHandler<FEpicUnrealMCPMaterialCommands>(4);          // Materials
    RegisterHandler<FEpicUnrealMCPProjectEditorCommands>(5);     // Project / editor
    RegisterHandler<FEpicUnrealMCPContentBrowserCommands>(6);    // Content browser
    RegisterHandler<FEpicUnrealMCPAssetImportCommands>(7);       // Asset import / export
    RegisterHandler<FEpicUnrealMCPMeshEditingCommands>(8);       // Static-mesh editing
    RegisterHandler<FEpicUnrealMCPEnhancedInputCommands>(9);     // Enhanced Input
    RegisterHandler<FEpicUnrealMCPGameplayFrameworkCommands>(10);// Gameplay framework
    RegisterHandler<FEpicUnrealMCPUMGCommands>(11);              // UMG / Common UI
    RegisterHandler<FEpicUnrealMCPRenderingCommands>(12);        // Rendering
    RegisterHandler<FEpicUnrealMCPLightingAtmosphereCommands>(13);// Lighting / atmosphere
    RegisterHandler<FEpicUnrealMCPDataTableCommands>(14);        // Data tables
    RegisterHandler<FEpicUnrealMCPAudioCommands>(15);            // Audio
    RegisterHandler<FEpicUnrealMCPSequencerCommands>(16);        // Sequencer
    RegisterHandler<FEpicUnrealMCPVroidCommands>(17);            // VRoid / VRM
    RegisterHandler<FEpicUnrealMCPCesiumCommands>(18);           // Cesium
    RegisterHandler<FEpicUnrealMCPProceduralCommands>(19);       // Procedural generation + request_cognitive_processing (Phase 4 trim)
    RegisterHandler<FEpicUnrealMCPNavigationCommands>(20);       // NavAI + Spline (Phase 3)
    RegisterHandler<FEpicUnrealMCPNiagaraCommands>(21);          // Niagara / VFX (Sub-batch I)
    RegisterHandler<FEpicUnrealMCPPhysicsCommands>(22);          // Collision / physics body / forces / constraints (Phase 4)
    RegisterHandler<FEpicUnrealMCPValidationCommands>(23);       // compile_all_blueprints / run_map_check / find_broken_references (Phase 4)
    RegisterHandler<FEpicUnrealMCPInstanceCommands>(24);
    RegisterHandler<FEpicUnrealMCPLandscapeCommands>(25);         // Landscape / Terrain (Sub-batch J)         // Draft Proxy + InstanceSet HISM/ISM (Phase 4)
    RegisterHandler<FEpicUnrealMCPAnimationRiggingCommands>(35); // Animation / Skeletal / Rigging (Sub-batch K)
    RegisterHandler<FEpicUnrealMCPAiNavExtensionCommands>(36);   // AI / Navigation extensions (Sub-batch L)
    RegisterHandler<FEpicUnrealMCPMovieRenderQueueCommands>(26); // Movie Render Queue (Sub-batch M)
    RegisterHandler<FEpicUnrealMCPFoliageCommands>(27); // Foliage / Vegetation (Sub-batch N, route 27, issue #44)
    RegisterHandler<FEpicUnrealMCPPCGCommands>(28); // PCG Framework (Sub-batch O, route 28, issue #45)
    RegisterHandler<FEpicUnrealMCPNetworkingCommands>(37); // Networking / Multiplayer (Sub-batch P, route 37, issue #41)
    RegisterHandler<FEpicUnrealMCPChaosCommands>(29); // Chaos / Physics extensions (Sub-batch Q, route 29, issue #51)
    RegisterHandler<FEpicUnrealMCPGASCommands>(30); // Gameplay Ability System (Sub-batch R, route 30, issue #55)
    RegisterHandler<FEpicUnrealMCPWaterCommands>(31); // Water System (Sub-batch S, route 31, issue #46)
    RegisterHandler<FEpicUnrealMCPMobileXrCommands>(38); // Mobile / XR (Sub-batch T, route 38, issue #59)
    RegisterHandler<FEpicUnrealMCPSourceControlCommands>(32); // Source Control / Multi-User (Sub-batch U, route 32, issue #60)
    RegisterHandler<FEpicUnrealMCPLocalizationCommands>(33); // Localization (Sub-batch V, route 33, issue #58)
    RegisterHandler<FEpicUnrealMCPTestingValidationCommands>(39); // Testing / Validation extensions (Sub-batch W, route 39, issue #57)
    RegisterHandler<FEpicUnrealMCPDataTableExtensionCommands>(40); // Data Tables / Data Assets extensions (Sub-batch X, route 40, issue #54)
    RegisterHandler<FEpicUnrealMCPMetaSoundCommands>(34); // MetaSound / Audio extensions (Sub-batch Y, route 34, issue #50)
    RegisterHandler<FEpicUnrealMCPSequencerExtensionCommands>(41); // Sequencer / Cinematics extensions (Sub-batch Z, route 41, issue #52)
}

UEpicUnrealMCPBridge::UEpicUnrealMCPBridge()
    : bIsRunning(false)
    , ListenerSocket(nullptr)
    , ConnectionSocket(nullptr)
    , ServerThread(nullptr)
    , Runnable(nullptr)
{
    RegisterHandlers();

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

    FIPv4Address LoopbackAddress;
    FIPv4Address::Parse(TEXT(MCP_SERVER_HOST), LoopbackAddress);
    if (ServerAddress != LoopbackAddress)
    {
        if (!Settings || !Settings->bAllowRemoteConnections)
        {
            UE_LOG(LogTemp, Error, TEXT("EpicUnrealMCPBridge: Remote binding '%s' rejected. Set bAllowRemoteConnections=true in Project Settings > Plugins > Unreal MCP to allow non-localhost connections."), *HostStr);
            FIPv4Address::Parse(TEXT(MCP_SERVER_HOST), ServerAddress);
            UE_LOG(LogTemp, Warning, TEXT("EpicUnrealMCPBridge: Falling back to 127.0.0.1 for safety."));
        }
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
    // The registry is the sole owner of every handler instance via the
    // captured TSharedPtrs.  Empty it explicitly here so handlers are
    // destroyed in a deterministic order (after the server thread is
    // stopped, before the rest of the bridge is torn down).
    CommandHandlerRegistry.Empty();
}

void UEpicUnrealMCPBridge::Initialize(FSubsystemCollectionBase& Collection)
{
    UE_LOG(LogTemp, Log, TEXT("EpicUnrealMCPBridge: Initializing"));
    // Defer actor index rebuild to first command -- editor world may not be ready yet
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

    FSocket* NewListenerSocket = SocketSubsystem->CreateSocket(NAME_Stream, TEXT("UnrealMCPListener"), false);
    if (!NewListenerSocket)
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
        SocketSubsystem->DestroySocket(NewListenerSocket);
        return;
    }

    if (!NewListenerSocket->Listen(5))
    {
        UE_LOG(LogTemp, Error, TEXT("EpicUnrealMCPBridge: Failed to start listening"));
        SocketSubsystem->DestroySocket(NewListenerSocket);
        return;
    }

    ListenerSocket = NewListenerSocket;
    bIsRunning = true;
    UE_LOG(LogTemp, Log, TEXT("EpicUnrealMCPBridge: Server started on %s:%d"), *ServerAddress.ToString(), Port);

    Runnable = MakeUnique<FMCPServerRunnable>(this, ListenerSocket);
    ServerThread = FRunnableThread::Create(
        Runnable.Get(),
        TEXT("UnrealMCPServerThread"),
        0, TPri_Normal
    );

    if (!ServerThread)
    {
        UE_LOG(LogTemp, Error, TEXT("EpicUnrealMCPBridge: Failed to create server thread"));
        Runnable.Reset();
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

    if (Runnable.IsValid())
    {
        Runnable->Stop();
    }

    if (ListenerSocket)
    {
        ListenerSocket->Close();
    }
    if (ConnectionSocket)
    {
        ConnectionSocket->Close();
    }

    if (ServerThread)
    {
        ServerThread->WaitForCompletion();
        delete ServerThread;
        ServerThread = nullptr;
    }

    Runnable.Reset();

    ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);

    if (ConnectionSocket)
    {
        if (SocketSubsystem)
        {
            SocketSubsystem->DestroySocket(ConnectionSocket);
        }
        ConnectionSocket = nullptr;
    }

    if (ListenerSocket)
    {
        if (SocketSubsystem)
        {
            SocketSubsystem->DestroySocket(ListenerSocket);
        }
        ListenerSocket = nullptr;
    }

    UE_LOG(LogTemp, Log, TEXT("EpicUnrealMCPBridge: Server stopped"));
}

void UEpicUnrealMCPBridge::EnsureActorIndexInitialized()
{
    if (ActorIndex.NameIndex.IsEmpty() && ActorIndex.McpIdIndex.IsEmpty())
    {
        UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
        if (World)
        {
            ActorIndex.RebuildFromWorld(World);
        }
    }
}

FString UEpicUnrealMCPBridge::ExecuteCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    UE_LOG(LogTemp, Log, TEXT("EpicUnrealMCPBridge: Executing command: %s"), *CommandType);

    const int32 Route = FEpicUnrealMCPRouter::RouteCommand(CommandType);

    auto ExecuteOnCurrentThread = [this, CommandType, Params, Route]() -> FString
    {
        EnsureActorIndexInitialized();

        TSharedPtr<FJsonObject> ResponseJson = MakeShareable(new FJsonObject);

        try
        {
            const FCommandHandlerFn* Handler = CommandHandlerRegistry.Find(Route);
            if (!Handler)
            {
                ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
                ResponseJson->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));

                FString UnknownCommandResult;
                TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
                    TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&UnknownCommandResult);
                FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
                return UnknownCommandResult;
            }

            TSharedPtr<FJsonObject> ResultJson = (*Handler)(CommandType, Params);

            bool bSuccess = true;
            FString ErrorMessage;

            if (ResultJson.IsValid() && ResultJson->HasField(TEXT("success")))
            {
                bSuccess = ResultJson->GetBoolField(TEXT("success"));
                if (!bSuccess && ResultJson->HasField(TEXT("error")))
                {
                    ErrorMessage = ResultJson->GetStringField(TEXT("error"));
                }
            }

            if (!ResultJson.IsValid())
            {
                ResultJson = MakeShareable(new FJsonObject);
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

    const double DeferredEditorCommandDelaySeconds = GetDeferredEditorCommandDelaySeconds(CommandType);
    if (DeferredEditorCommandDelaySeconds > 0.0)
    {
        FScopeLock DeferredCommandLock(&GDeferredEditorCommandMutex);
        const double SecondsUntilSafeDispatch =
            (GLastDeferredEditorCommandEndSeconds + DeferredEditorCommandDelaySeconds) - FPlatformTime::Seconds();
        if (SecondsUntilSafeDispatch > 0.0)
        {
            FPlatformProcess::Sleep(static_cast<float>(SecondsUntilSafeDispatch));
        }

        TSharedRef<TPromise<FString>, ESPMode::ThreadSafe> Promise =
            MakeShared<TPromise<FString>, ESPMode::ThreadSafe>();
        TFuture<FString> Future = Promise->GetFuture();

        FTSTicker::GetCoreTicker().AddTicker(
            TEXT("UnrealMCP.DeferredEditorCommand"),
            0.0f,
            [ExecuteOnCurrentThread, Promise](float) mutable
            {
                Promise->SetValue(ExecuteOnCurrentThread());
                return false;
            }
        );

        FString Result = Future.Get();
        GLastDeferredEditorCommandEndSeconds = FPlatformTime::Seconds();
        return Result;
    }

    TPromise<FString> Promise;
    TFuture<FString> Future = Promise.GetFuture();

    AsyncTask(ENamedThreads::GameThread, [ExecuteOnCurrentThread, Promise = MoveTemp(Promise)]() mutable
    {
        Promise.SetValue(ExecuteOnCurrentThread());
    });

    return Future.Get();
}
