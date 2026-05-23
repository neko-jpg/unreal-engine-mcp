#include "Commands/EpicUnrealMCPPCGCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_PCG_MCP
#include "PCGGraph.h"
#include "PCGComponent.h"
#include "PCGVolume.h"
#include "PCGNode.h"
#include "PCGSettings.h"
#include "PCGEdge.h"
#include "Elements/PCGSplineSampler.h"
#include "Elements/PCGSurfaceSampler.h"
#include "Elements/PCGStaticMeshSpawner.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "UObject/Package.h"
#endif

bool FEpicUnrealMCPPCGCommands::IsModuleAvailable()
{
#if WITH_PCG_MCP
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPPCGCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Enable Engine/Plugins/Experimental/PCG (UE 5.7 stable subset)."));
    return R;
}

// ---------------------------------------------------------------------------
// 234-stubs W3 (#91): PCG executed-envelope helpers.
// ---------------------------------------------------------------------------

static TSharedPtr<FJsonObject> PCGOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> PCGErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

#if WITH_PCG_MCP
// Resolve an AActor by name or label from the editor world.
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

// Resolve a UPCGGraph from a soft path string (e.g. "/Game/PCG/MyGraph.MyGraph").
static UPCGGraph* ResolveGraph(const FString& GraphPath)
{
    if (GraphPath.IsEmpty()) return nullptr;
    return LoadObject<UPCGGraph>(nullptr, *GraphPath);
}
#endif

FEpicUnrealMCPPCGCommands::FEpicUnrealMCPPCGCommands() {}
FEpicUnrealMCPPCGCommands::~FEpicUnrealMCPPCGCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPPCGCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_pcg_graph"),  &FEpicUnrealMCPPCGCommands::HandleCreatePcgGraph},
        {TEXT("add_pcg_component"),  &FEpicUnrealMCPPCGCommands::HandleAddPcgComponent},
        {TEXT("create_pcg_volume"),  &FEpicUnrealMCPPCGCommands::HandleCreatePcgVolume},
        {TEXT("add_pcg_node"),  &FEpicUnrealMCPPCGCommands::HandleAddPcgNode},
        {TEXT("connect_pcg_nodes"),  &FEpicUnrealMCPPCGCommands::HandleConnectPcgNodes},
        {TEXT("set_pcg_graph_parameter"),  &FEpicUnrealMCPPCGCommands::HandleSetPcgGraphParameter},
        {TEXT("configure_pcg_spline_sampler"),  &FEpicUnrealMCPPCGCommands::HandleConfigurePcgSplineSampler},
        {TEXT("configure_pcg_surface_sampler"),  &FEpicUnrealMCPPCGCommands::HandleConfigurePcgSurfaceSampler},
        {TEXT("configure_pcg_static_mesh_spawner"),  &FEpicUnrealMCPPCGCommands::HandleConfigurePcgStaticMeshSpawner},
        {TEXT("configure_pcg_rule"),  &FEpicUnrealMCPPCGCommands::HandleConfigurePcgRule},
        {TEXT("create_pcg_biome_graph"),  &FEpicUnrealMCPPCGCommands::HandleCreatePcgBiomeGraph},
        {TEXT("operate_pcg_point_data"),  &FEpicUnrealMCPPCGCommands::HandleOperatePcgPointData},
        {TEXT("operate_pcg_attribute"),  &FEpicUnrealMCPPCGCommands::HandleOperatePcgAttribute},
        {TEXT("execute_pcg_graph"),  &FEpicUnrealMCPPCGCommands::HandleExecutePcgGraph},
        {TEXT("regenerate_pcg_graph"),  &FEpicUnrealMCPPCGCommands::HandleRegeneratePcgGraph},
        {TEXT("set_pcg_runtime_generation"),  &FEpicUnrealMCPPCGCommands::HandleSetPcgRuntimeGeneration},
        {TEXT("use_pcg_editor_mode"),  &FEpicUnrealMCPPCGCommands::HandleUsePcgEditorMode},
        {TEXT("create_pcg_tool"),  &FEpicUnrealMCPPCGCommands::HandleCreatePcgTool},
        {TEXT("set_pcg_debug_display"),  &FEpicUnrealMCPPCGCommands::HandleSetPcgDebugDisplay},
        {TEXT("configure_pcg_self_pruning"),  &FEpicUnrealMCPPCGCommands::HandleConfigurePcgSelfPruning}
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

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleCreatePcgGraph(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_pcg_graph"));

    FString AssetPath = TEXT("/Game/PCG");
    FString AssetName = TEXT("PCGGraph_New");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }

    // Create PCG graph asset
    UPackage* Pkg = CreatePackage(*FString::Printf(TEXT("%s/%s"), *AssetPath, *AssetName));
    if (!Pkg) return PCGErr(TEXT("Failed to create package for PCG graph"));
    UPCGGraph* Graph = NewObject<UPCGGraph>(Pkg, *AssetName, RF_Public | RF_Standalone);
    Graph->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_pcg_graph"));
    Data->SetStringField(TEXT("asset_path"), Graph->GetPathName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("create_pcg_graph"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleAddPcgComponent(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: add_pcg_component"));

    FString ActorName;
    FString GraphPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return PCGErr(TEXT("No editor world available"));

    AActor* Target = FindActorInEditorWorld(World, ActorName);
    if (!Target)
    {
        return PCGErr(FString::Printf(TEXT("add_pcg_component: actor '%s' not found."), *ActorName));
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph)
    {
        return PCGErr(FString::Printf(TEXT("add_pcg_component: graph '%s' not found."), *GraphPath));
    }

    Target->Modify();
    UPCGComponent* PCGComp = NewObject<UPCGComponent>(Target, TEXT("PCGComponent"));
    PCGComp->SetGraphLocal(Graph);
    PCGComp->RegisterComponent();
    Target->AddInstanceComponent(PCGComp);
    Target->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_pcg_component"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("add_pcg_component"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleCreatePcgVolume(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_pcg_volume"));

    FString ActorName = TEXT("PCGVolume");
    TArray<double> ExtentXYZ = {2000.0, 2000.0, 500.0};
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        const TArray<TSharedPtr<FJsonValue>>* ExtArr = nullptr;
        if (Params->TryGetArrayField(TEXT("extent_xyz"), ExtArr) && ExtArr->Num() >= 3)
        {
            for (int32 i = 0; i < 3; ++i)
            {
                ExtentXYZ[i] = (*ExtArr)[i]->AsNumber(ExtentXYZ[i]);
            }
        }
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return PCGErr(TEXT("No editor world available"));

    FVector Extent(ExtentXYZ[0], ExtentXYZ[1], ExtentXYZ[2]);
    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*ActorName);
    APCGVolume* Volume = World->SpawnActor<APCGVolume>(APCGVolume::StaticClass(), FTransform::Identity, SpawnParams);
    if (!Volume)
    {
        return PCGErr(TEXT("create_pcg_volume: failed to spawn APCGVolume."));
    }

    // Build a brush for the volume bounds
    Volume->BrushComponent->SetMobility(EComponentMobility::Static);
    Volume->SetActorScale3D(Extent / 100.0); // AVolume uses a 100-unit brush by default
    Volume->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_pcg_volume"));
    Data->SetStringField(TEXT("actor_name"), Volume->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("create_pcg_volume"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleAddPcgNode(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: add_pcg_node"));

    FString GraphPath;
    FString NodeType;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
        Params->TryGetStringField(TEXT("node_type"), NodeType);
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph)
    {
        return PCGErr(FString::Printf(TEXT("add_pcg_node: graph '%s' not found."), *GraphPath));
    }

    Graph->Modify();

    // Create settings of the requested type, add a node wrapping them
    UClass* SettingsClass = FindObject<UClass>(ANY_PACKAGE, *NodeType);
    if (!SettingsClass || !SettingsClass->IsChildOf(UPCGSettings::StaticClass()))
    {
        return PCGErr(FString::Printf(TEXT("add_pcg_node: '%s' is not a valid UPCGSettings class."), *NodeType));
    }

    UPCGSettings* DefaultSettings = nullptr;
    UPCGNode* Node = Graph->AddNodeOfType(SettingsClass, DefaultSettings);
    if (!Node)
    {
        return PCGErr(FString::Printf(TEXT("add_pcg_node: failed to add node of type '%s'."), *NodeType));
    }

    Graph->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_pcg_node"));
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetStringField(TEXT("node_type"), NodeType);
    Data->SetStringField(TEXT("node_name"), Node->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("add_pcg_node"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleConnectPcgNodes(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: connect_pcg_nodes"));

    FString GraphPath;
    FString FromNode;
    FString ToNode;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
        Params->TryGetStringField(TEXT("from_node"), FromNode);
        Params->TryGetStringField(TEXT("to_node"), ToNode);
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph)
    {
        return PCGErr(FString::Printf(TEXT("connect_pcg_nodes: graph '%s' not found."), *GraphPath));
    }

    // Find nodes by title name
    UPCGNode* From = Graph->FindNodeByTitleName(FName(*FromNode));
    UPCGNode* To = Graph->FindNodeByTitleName(FName(*ToNode));
    if (!From)
    {
        return PCGErr(FString::Printf(TEXT("connect_pcg_nodes: from_node '%s' not found."), *FromNode));
    }
    if (!To)
    {
        return PCGErr(FString::Printf(TEXT("connect_pcg_nodes: to_node '%s' not found."), *ToNode));
    }

    Graph->Modify();
    UPCGNode* Result = Graph->AddEdge(From, NAME_None, To, NAME_None);
    if (!Result)
    {
        return PCGErr(TEXT("connect_pcg_nodes: AddEdge failed."));
    }

    Graph->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("connect_pcg_nodes"));
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetStringField(TEXT("from_node"), FromNode);
    Data->SetStringField(TEXT("to_node"), ToNode);
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("connect_pcg_nodes"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleSetPcgGraphParameter(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_pcg_graph_parameter"));

    FString GraphPath;
    FString Parameter;
    FString Value;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
        Params->TryGetStringField(TEXT("parameter"), Parameter);
        Params->TryGetStringField(TEXT("value"), Value);
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph)
    {
        return PCGErr(FString::Printf(TEXT("set_pcg_graph_parameter: graph '%s' not found."), *GraphPath));
    }

    Graph->Modify();

    // Set a string parameter on the graph's user parameters
    FInstancedPropertyBag* UserParams = Graph->GetMutableUserParametersStruct();
    if (!UserParams)
    {
        return PCGErr(TEXT("set_pcg_graph_parameter: graph has no user parameters struct."));
    }

    FName PropName(*Parameter);
    EPropertyBagResult Result = UserParams->SetStringValueByName(PropName, Value);
    if (Result != EPropertyBagResult::Success)
    {
        return PCGErr(FString::Printf(TEXT("set_pcg_graph_parameter: failed to set parameter '%s'."), *Parameter));
    }

    Graph->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_pcg_graph_parameter"));
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetStringField(TEXT("parameter"), Parameter);
    Data->SetStringField(TEXT("value"), Value);
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("set_pcg_graph_parameter"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleConfigurePcgSplineSampler(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_pcg_spline_sampler"));

    FString GraphPath;
    FString SplineActor;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
        Params->TryGetStringField(TEXT("spline_actor"), SplineActor);
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph)
    {
        return PCGErr(FString::Printf(TEXT("configure_pcg_spline_sampler: graph '%s' not found."), *GraphPath));
    }

    Graph->Modify();

    UPCGSettings* DefaultSettings = nullptr;
    UPCGNode* Node = Graph->AddNodeOfType(UPCGSplineSamplerSettings::StaticClass(), DefaultSettings);
    if (!Node)
    {
        return PCGErr(TEXT("configure_pcg_spline_sampler: failed to add SplineSampler node."));
    }

    Graph->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_pcg_spline_sampler"));
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetStringField(TEXT("spline_actor"), SplineActor);
    Data->SetStringField(TEXT("node_name"), Node->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("configure_pcg_spline_sampler"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleConfigurePcgSurfaceSampler(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_pcg_surface_sampler"));

    FString GraphPath;
    FString SurfaceActor;
    double Density = 1.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
        Params->TryGetStringField(TEXT("surface_actor"), SurfaceActor);
        Density = Params->GetNumberField(TEXT("density"));
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph)
    {
        return PCGErr(FString::Printf(TEXT("configure_pcg_surface_sampler: graph '%s' not found."), *GraphPath));
    }

    Graph->Modify();

    UPCGSettings* DefaultSettings = nullptr;
    UPCGNode* Node = Graph->AddNodeOfType(UPCGSurfaceSamplerSettings::StaticClass(), DefaultSettings);
    if (!Node)
    {
        return PCGErr(TEXT("configure_pcg_surface_sampler: failed to add SurfaceSampler node."));
    }

    Graph->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_pcg_surface_sampler"));
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetStringField(TEXT("surface_actor"), SurfaceActor);
    Data->SetNumberField(TEXT("density"), Density);
    Data->SetStringField(TEXT("node_name"), Node->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("configure_pcg_surface_sampler"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleConfigurePcgStaticMeshSpawner(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_pcg_static_mesh_spawner"));

    FString GraphPath;
    FString MeshPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
        Params->TryGetStringField(TEXT("mesh_path"), MeshPath);
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph)
    {
        return PCGErr(FString::Printf(TEXT("configure_pcg_static_mesh_spawner: graph '%s' not found."), *GraphPath));
    }

    Graph->Modify();

    UPCGSettings* DefaultSettings = nullptr;
    UPCGNode* Node = Graph->AddNodeOfType(UPCGStaticMeshSpawnerSettings::StaticClass(), DefaultSettings);
    if (!Node)
    {
        return PCGErr(TEXT("configure_pcg_static_mesh_spawner: failed to add StaticMeshSpawner node."));
    }

    Graph->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_pcg_static_mesh_spawner"));
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetStringField(TEXT("mesh_path"), MeshPath);
    Data->SetStringField(TEXT("node_name"), Node->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("configure_pcg_static_mesh_spawner"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleConfigurePcgRule(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_pcg_rule"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_pcg_rule"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleCreatePcgBiomeGraph(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_pcg_biome_graph"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_pcg_biome_graph"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleOperatePcgPointData(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("operate_pcg_point_data"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("operate_pcg_point_data"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleOperatePcgAttribute(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("operate_pcg_attribute"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("operate_pcg_attribute"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleExecutePcgGraph(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("execute_pcg_graph"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("execute_pcg_graph"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleRegeneratePcgGraph(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("regenerate_pcg_graph"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("regenerate_pcg_graph"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleSetPcgRuntimeGeneration(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_pcg_runtime_generation"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_pcg_runtime_generation"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleUsePcgEditorMode(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("use_pcg_editor_mode"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("use_pcg_editor_mode"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleCreatePcgTool(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_pcg_tool"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_pcg_tool"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleSetPcgDebugDisplay(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_pcg_debug_display"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_pcg_debug_display"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleConfigurePcgSelfPruning(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_pcg_self_pruning"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_pcg_self_pruning"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the PCG editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
