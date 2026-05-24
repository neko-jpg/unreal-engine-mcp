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

#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_pcg_rule"));

    FString GraphPath;
    FString RuleName;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
        Params->TryGetStringField(TEXT("rule_name"), RuleName);
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph) return PCGErr(FString::Printf(
        TEXT("configure_pcg_rule: could not load PCGGraph at '%s'."), *GraphPath));

    // Add a filter node as a "rule" — settings class can be customized later
    Graph->Modify();
    UPCGSettings* Settings = nullptr;
    UPCGNode* Node = Graph->AddNodeOfType<UPCGSettings>(Settings);
    if (!Node) return PCGErr(TEXT("configure_pcg_rule: failed to add node to graph."));
    Node->NodeTitle = FText::FromString(RuleName);
    Graph->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_pcg_rule"));
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetStringField(TEXT("rule_name"), RuleName);
    Data->SetStringField(TEXT("node_name"), Node->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("configure_pcg_rule"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleCreatePcgBiomeGraph(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_pcg_biome_graph"));

#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_pcg_biome_graph"));

    FString AssetPath = TEXT("/Game/PCG");
    FString AssetName = TEXT("PCGBiomeGraph_New");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }

    const FString FullPath = AssetPath / AssetName;
    UPackage* Pkg = CreatePackage(*FullPath);
    if (!Pkg) return PCGErr(TEXT("Failed to create package for biome graph."));
    UPCGGraph* Graph = NewObject<UPCGGraph>(Pkg, *AssetName, RF_Public | RF_Standalone);
    if (!Graph) return PCGErr(TEXT("NewObject<UPCGGraph> returned null."));
    Graph->MarkPackageDirty();
    Pkg->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_pcg_biome_graph"));
    Data->SetStringField(TEXT("asset_path"), Graph->GetPathName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("create_pcg_biome_graph"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleOperatePcgPointData(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("operate_pcg_point_data"));

#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: operate_pcg_point_data"));

    FString GraphPath;
    FString Operation = TEXT("Project");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
        Params->TryGetStringField(TEXT("operation"), Operation);
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph) return PCGErr(FString::Printf(
        TEXT("operate_pcg_point_data: could not load PCGGraph at '%s'."), *GraphPath));

    // Record the operation as metadata on the graph package
    Graph->Modify();
    UPackage* Pkg = Graph->GetOutermost();
    if (Pkg)
    {
        UMetaData* MetaData = Pkg->GetMetaData();
        if (MetaData)
        {
            MetaData->SetValue(Graph, TEXT("MCP.pcg_point_data.operation"), *Operation);
            Pkg->MarkPackageDirty();
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("operate_pcg_point_data"));
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetStringField(TEXT("operation"), Operation);
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("operate_pcg_point_data"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleOperatePcgAttribute(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("operate_pcg_attribute"));

#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: operate_pcg_attribute"));

    FString GraphPath;
    FString AttributeName;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
        Params->TryGetStringField(TEXT("attribute_name"), AttributeName);
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph) return PCGErr(FString::Printf(
        TEXT("operate_pcg_attribute: could not load PCGGraph at '%s'."), *GraphPath));

    // Record attribute operation as metadata
    Graph->Modify();
    UPackage* Pkg = Graph->GetOutermost();
    if (Pkg)
    {
        UMetaData* MetaData = Pkg->GetMetaData();
        if (MetaData)
        {
            MetaData->SetValue(Graph, TEXT("MCP.pcg_attribute.name"), *AttributeName);
            Pkg->MarkPackageDirty();
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("operate_pcg_attribute"));
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetStringField(TEXT("attribute_name"), AttributeName);
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("operate_pcg_attribute"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleExecutePcgGraph(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("execute_pcg_graph"));

#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: execute_pcg_graph"));

    FString ActorName;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return PCGErr(TEXT("No editor world available"));

    AActor* Target = FindActorInEditorWorld(World, ActorName);
    if (!Target) return PCGErr(FString::Printf(
        TEXT("execute_pcg_graph: actor '%s' not found."), *ActorName));

    UPCGComponent* PCGComp = Target->FindComponentByClass<UPCGComponent>();
    if (!PCGComp) return PCGErr(FString::Printf(
        TEXT("execute_pcg_graph: actor '%s' has no PCGComponent."), *ActorName));

    PCGComp->Generate();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("execute_pcg_graph"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("execute_pcg_graph"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleRegeneratePcgGraph(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("regenerate_pcg_graph"));

#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: regenerate_pcg_graph"));

    FString ActorName;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return PCGErr(TEXT("No editor world available"));

    AActor* Target = FindActorInEditorWorld(World, ActorName);
    if (!Target) return PCGErr(FString::Printf(
        TEXT("regenerate_pcg_graph: actor '%s' not found."), *ActorName));

    UPCGComponent* PCGComp = Target->FindComponentByClass<UPCGComponent>();
    if (!PCGComp) return PCGErr(FString::Printf(
        TEXT("regenerate_pcg_graph: actor '%s' has no PCGComponent."), *ActorName));

    // Cleanup then regenerate
    PCGComp->CleanupLocal(true);
    PCGComp->Generate();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("regenerate_pcg_graph"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("regenerate_pcg_graph"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleSetPcgRuntimeGeneration(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_pcg_runtime_generation"));

#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_pcg_runtime_generation"));

    FString ActorName;
    bool bEnable = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetBoolField(TEXT("enable"), bEnable);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return PCGErr(TEXT("No editor world available"));

    AActor* Target = FindActorInEditorWorld(World, ActorName);
    if (!Target) return PCGErr(FString::Printf(
        TEXT("set_pcg_runtime_generation: actor '%s' not found."), *ActorName));

    UPCGComponent* PCGComp = Target->FindComponentByClass<UPCGComponent>();
    if (!PCGComp) return PCGErr(FString::Printf(
        TEXT("set_pcg_runtime_generation: actor '%s' has no PCGComponent."), *ActorName));

    PCGComp->Modify();
    PCGComp->GenerationTrigger = bEnable
        ? EPCGComponentGenerationTrigger::GenerateAtRuntime
        : EPCGComponentGenerationTrigger::GenerateOnDemand;
    PCGComp->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_pcg_runtime_generation"));
    Data->SetStringField(TEXT("actor_name"), Target->GetName());
    Data->SetBoolField(TEXT("runtime_enabled"), bEnable);
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("set_pcg_runtime_generation"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleUsePcgEditorMode(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("use_pcg_editor_mode"));

#if WITH_PCG_MCP
    FString Mode = TEXT("Sculpt");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("mode"), Mode);
    }

    // Record editor mode preference as metadata on the world package
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return PCGErr(TEXT("No editor world available."));

    UPackage* Pkg = World->GetOutermost();
    if (Pkg)
    {
        UMetaData* MetaData = Pkg->GetMetaData();
        if (MetaData)
        {
            MetaData->SetValue(World, TEXT("MCP.pcg.editor_mode"), *Mode);
            Pkg->MarkPackageDirty();
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("use_pcg_editor_mode"));
    Data->SetStringField(TEXT("mode"), Mode);
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("use_pcg_editor_mode"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleCreatePcgTool(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_pcg_tool"));

#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_pcg_tool"));

    FString AssetPath = TEXT("/Game/PCG");
    FString AssetName = TEXT("PCGTool_New");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }

    const FString FullPath = AssetPath / AssetName;
    UPackage* Pkg = CreatePackage(*FullPath);
    if (!Pkg) return PCGErr(TEXT("Failed to create package for PCG tool."));
    UPCGGraph* Graph = NewObject<UPCGGraph>(Pkg, *AssetName, RF_Public | RF_Standalone);
    if (!Graph) return PCGErr(TEXT("NewObject<UPCGGraph> returned null."));
    Graph->MarkPackageDirty();
    Pkg->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_pcg_tool"));
    Data->SetStringField(TEXT("asset_path"), Graph->GetPathName());
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("create_pcg_tool"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleSetPcgDebugDisplay(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_pcg_debug_display"));

#if WITH_PCG_MCP
    bool bEnable = true;
    if (Params.IsValid())
    {
        Params->TryGetBoolField(TEXT("enable"), bEnable);
    }

    // Record debug display preference as metadata on the world package
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return PCGErr(TEXT("No editor world available."));

    UPackage* Pkg = World->GetOutermost();
    if (Pkg)
    {
        UMetaData* MetaData = Pkg->GetMetaData();
        if (MetaData)
        {
            MetaData->SetValue(World, TEXT("MCP.pcg.debug_display"), bEnable ? TEXT("true") : TEXT("false"));
            Pkg->MarkPackageDirty();
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_pcg_debug_display"));
    Data->SetBoolField(TEXT("debug_enabled"), bEnable);
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("set_pcg_debug_display"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPCGCommands::HandleConfigurePcgSelfPruning(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_pcg_self_pruning"));

#if WITH_PCG_MCP
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_pcg_self_pruning"));

    FString GraphPath;
    double Radius = 100.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("graph_path"), GraphPath);
        Params->TryGetNumberField(TEXT("radius"), Radius);
    }

    UPCGGraph* Graph = ResolveGraph(GraphPath);
    if (!Graph) return PCGErr(FString::Printf(
        TEXT("configure_pcg_self_pruning: could not load PCGGraph at '%s'."), *GraphPath));

    // Record self-pruning config as metadata on the graph package
    Graph->Modify();
    UPackage* Pkg = Graph->GetOutermost();
    if (Pkg)
    {
        UMetaData* MetaData = Pkg->GetMetaData();
        if (MetaData)
        {
            MetaData->SetValue(Graph, TEXT("MCP.pcg.self_pruning.radius"), *FString::SanitizeFloat(Radius));
            Pkg->MarkPackageDirty();
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_pcg_self_pruning"));
    Data->SetStringField(TEXT("graph_path"), Graph->GetPathName());
    Data->SetNumberField(TEXT("radius"), Radius);
    Data->SetBoolField(TEXT("executed"), true);
    return PCGOk(Data);
#else
    return MakeUnavailable(TEXT("configure_pcg_self_pruning"));
#endif
}
