// =====================================================================
// EpicUnrealMCPNavigationCommands
//
// Phase 3 refactor: split out from EpicUnrealMCPEditorCommands.cpp.
//
// Owns the NavAI + Spline command surface:
//   NavMesh      : create_nav_mesh_volume, create_nav_modifier_volume,
//                  create_nav_link_proxy
//   AI           : create_patrol_route, set_ai_behavior,
//                  create_behavior_tree, create_blackboard
//   Spline       : create_spline_from_points (L-System output consumer)
//
// HandleCreatePatrolRoute is intentionally bundled here (rather than in a
// separate spline file) because it composes both spline geometry and AI
// patrol semantics.  Future spline-only commands can either join this
// file or split into their own EpicUnrealMCPSplineCommands when the
// spline surface grows.
// =====================================================================

#include "Commands/EpicUnrealMCPNavigationCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"
#include "EpicUnrealMCPBridge.h"

#include "Editor.h"
#include "EngineUtils.h"
#include "ScopedTransaction.h"
#include "AssetRegistry/AssetRegistryModule.h"

#include "GameFramework/Actor.h"
#include "Engine/Selection.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet2/KismetEditorUtilities.h"

#include "Components/StaticMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"

#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavigationSystem.h"
#include "NavModifierVolume.h"
#include "Navigation/NavLinkProxy.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/Blackboard/BlackboardKey.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Bool.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Int.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Float.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_String.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Name.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Vector.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Rotator.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Object.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Class.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISenseConfig_Sight.h"
#include "Perception/AISense_Sight.h"
#include "AIController.h"
#include "NavMesh/RecastNavMesh.h"
#include "EnvironmentQuery/EnvQuery.h"
#include "Navigation/CrowdFollowingComponent.h"

#include "EditorAssetLibrary.h"

namespace
{
    FActorIndex& GetActorIndex()
    {
        UEpicUnrealMCPBridge* Bridge = GEditor->GetEditorSubsystem<UEpicUnrealMCPBridge>();
        check(Bridge);
        return Bridge->ActorIndex;
    }
}

FEpicUnrealMCPNavigationCommands::FEpicUnrealMCPNavigationCommands()
{
}

UWorld* FEpicUnrealMCPNavigationCommands::GetEditorWorld() const
{
    if (!GEditor)
    {
        return nullptr;
    }
    return GEditor->GetEditorWorldContext().World();
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPNavigationCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        // NavMesh / Navigation
        {TEXT("create_nav_mesh_volume"),     &FEpicUnrealMCPNavigationCommands::HandleCreateNavMeshVolume},
        {TEXT("create_nav_modifier_volume"), &FEpicUnrealMCPNavigationCommands::HandleCreateNavModifierVolume},
        {TEXT("create_nav_link_proxy"),      &FEpicUnrealMCPNavigationCommands::HandleCreateNavLinkProxy},

        // AI
        {TEXT("create_patrol_route"),        &FEpicUnrealMCPNavigationCommands::HandleCreatePatrolRoute},
        {TEXT("set_ai_behavior"),            &FEpicUnrealMCPNavigationCommands::HandleSetAIBehavior},
        {TEXT("create_behavior_tree"),       &FEpicUnrealMCPNavigationCommands::HandleCreateBehaviorTree},
        {TEXT("create_blackboard"),          &FEpicUnrealMCPNavigationCommands::HandleCreateBlackboard},
        {TEXT("add_blackboard_key"),         &FEpicUnrealMCPNavigationCommands::HandleAddBlackboardKey},     // W1-D
        {TEXT("remove_blackboard_key"),      &FEpicUnrealMCPNavigationCommands::HandleRemoveBlackboardKey},  // W1-D
        {TEXT("add_ai_perception"),          &FEpicUnrealMCPNavigationCommands::HandleAddAIPerception},      // W1-D
        {TEXT("configure_ai_sense_sight"),   &FEpicUnrealMCPNavigationCommands::HandleConfigureAISenseSight},// W1-D
        {TEXT("set_recast_navmesh_agent"),   &FEpicUnrealMCPNavigationCommands::HandleSetRecastNavMeshAgent},// W1-D
        {TEXT("create_eqs_query"),           &FEpicUnrealMCPNavigationCommands::HandleCreateEQSQuery},          // W1-G
        {TEXT("set_crowd_following_enable"), &FEpicUnrealMCPNavigationCommands::HandleSetCrowdFollowingEnable}, // W1-G

        // Spline
        {TEXT("create_spline_from_points"),  &FEpicUnrealMCPNavigationCommands::HandleCreateSplineFromPoints},
    };

    const Handler* H = Dispatch.Find(CommandType);
    if (H)
    {
        return (this->*(*H))(Params);
    }

    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown navigation command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleCreateNavMeshVolume(const TSharedPtr<FJsonObject>& Params)
{
    // Parse parameters
    FString VolumeName = TEXT("NavMeshVolume");
    Params->TryGetStringField(TEXT("volume_name"), VolumeName);

    // Parse location
    FVector Location = FVector::ZeroVector;
    FString ParamError;
    if (Params->HasField(TEXT("location")))
    {
        if (!FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Params, TEXT("location"), Location, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'location': %s"), *ParamError));
        }
    }

    // Parse extent (default 500,500,500)
    FVector Extent(500.0f, 500.0f, 500.0f);
    if (Params->HasField(TEXT("extent")))
    {
        if (!FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Params, TEXT("extent"), Extent, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'extent': %s"), *ParamError));
        }
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // Create NavMeshBoundsVolume
    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Create NavMesh Volume")));
    ANavMeshBoundsVolume* NavMeshVolume = World->SpawnActor<ANavMeshBoundsVolume>(Location, FRotator::ZeroRotator);
    if (!NavMeshVolume)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn NavMeshBoundsVolume"));
    }

    // UE 5.7 no longer exposes the old brush-building helper used here. Scaling
    // the spawned volume keeps this command usable while preserving the extent
    // in the response for callers.
    NavMeshVolume->SetActorScale3D(FVector(
        FMath::Max(Extent.X / 100.0f, 0.01f),
        FMath::Max(Extent.Y / 100.0f, 0.01f),
        FMath::Max(Extent.Z / 100.0f, 0.01f)
    ));

    // Set name and folder
    NavMeshVolume->SetActorLabel(*VolumeName);
    NavMeshVolume->SetFolderPath(FName(TEXT("NavMesh")));

    NavMeshVolume->Tags.AddUnique(FName(TEXT("managed_by_mcp")));

    // Add to actor index
    GetActorIndex().AddActor(NavMeshVolume);

    // Request NavMesh rebuild
    UNavigationSystemV1* NavSys = UNavigationSystemV1::GetCurrent(World);
    if (NavSys)
    {
        NavSys->Build();
    }

    // Build result JSON
    auto MakeVecJson = [](const FVector& V) -> TSharedPtr<FJsonObject> {
        TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
        Obj->SetNumberField(TEXT("x"), V.X);
        Obj->SetNumberField(TEXT("y"), V.Y);
        Obj->SetNumberField(TEXT("z"), V.Z);
        return Obj;
    };

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("volume_name"), VolumeName);
    ResultObj->SetStringField(TEXT("actor_name"), NavMeshVolume->GetName());
    ResultObj->SetObjectField(TEXT("location"), MakeVecJson(Location));
    ResultObj->SetObjectField(TEXT("extent"), MakeVecJson(Extent));
    ResultObj->SetBoolField(TEXT("navmesh_rebuilt"), NavSys != nullptr);
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleCreatePatrolRoute(const TSharedPtr<FJsonObject>& Params)
{
    FString RouteName = TEXT("PatrolRoute");
    Params->TryGetStringField(TEXT("patrol_route_name"), RouteName);

    // Parse patrol points
    const TArray<TSharedPtr<FJsonValue>>* PointsArray = nullptr;
    if (!Params->TryGetArrayField(TEXT("points"), PointsArray) || !PointsArray || PointsArray->Num() < 2)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Patrol route requires at least 2 points"));
    }

    bool bClosedLoop = false;
    Params->TryGetBoolField(TEXT("closed_loop"), bClosedLoop);

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // Create a spline-based actor for the patrol route
    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = *RouteName;
    AActor* RouteActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!RouteActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn patrol route actor"));
    }

    RouteActor->SetActorLabel(*RouteName);

    // Bare AActor has no RootComponent by default; create one so the
    // SplineComponent has something to attach to.
    if (!RouteActor->GetRootComponent())
    {
        USceneComponent* RootComp = NewObject<USceneComponent>(RouteActor, USceneComponent::StaticClass(), TEXT("DefaultSceneRoot"));
        RootComp->RegisterComponent();
        RouteActor->SetRootComponent(RootComp);
    }

    // Add SplineComponent
    USplineComponent* SplineComp = NewObject<USplineComponent>(RouteActor, USplineComponent::StaticClass(), *FString::Printf(TEXT("PatrolSpline_%s"), *RouteName));
    if (!SplineComp)
    {
        RouteActor->Destroy();
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create SplineComponent"));
    }

    SplineComp->RegisterComponent();
    SplineComp->AttachToComponent(RouteActor->GetRootComponent(), FAttachmentTransformRules::KeepRelativeTransform);

    // Set spline points from params
    SplineComp->ClearSplinePoints();
    auto MakeVecJson = [](const FVector& V) {
        TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
        Obj->SetNumberField(TEXT("x"), V.X);
        Obj->SetNumberField(TEXT("y"), V.Y);
        Obj->SetNumberField(TEXT("z"), V.Z);
        return Obj;
    };

    TArray<TSharedPtr<FJsonValue>> PointJsonArray;
    for (int32 i = 0; i < PointsArray->Num(); ++i)
    {
        const TSharedPtr<FJsonObject>* PointObj = nullptr;
        if (!(*PointsArray)[i]->TryGetObject(PointObj) || !PointObj)
        {
            continue;
        }
        double X = 0.0, Y = 0.0, Z = 0.0;
        (*PointObj)->TryGetNumberField(TEXT("x"), X);
        (*PointObj)->TryGetNumberField(TEXT("y"), Y);
        (*PointObj)->TryGetNumberField(TEXT("z"), Z);
        FVector Point(X, Y, Z);
        SplineComp->AddSplinePoint(Point, ESplineCoordinateSpace::World, false);
        PointJsonArray.Add(MakeShared<FJsonValueObject>(MakeVecJson(Point)));
    }

    SplineComp->SetClosedLoop(bClosedLoop);
    SplineComp->UpdateSpline();

    // Add mcp_id tag
    RouteActor->Tags.Add(FName(TEXT("managed_by_mcp")));
    RouteActor->Tags.Add(FName(*FString::Printf(TEXT("mcp_id:%s"), *RouteName)));

    // Register in actor index
    GetActorIndex().AddActor(RouteActor);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("route_name"), RouteName);
    ResultObj->SetStringField(TEXT("actor_name"), RouteActor->GetName());
    ResultObj->SetArrayField(TEXT("points"), PointJsonArray);
    ResultObj->SetBoolField(TEXT("closed_loop"), bClosedLoop);
    ResultObj->SetNumberField(TEXT("point_count"), PointsArray->Num());
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleSetAIBehavior(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing required parameter: actor_name"));
    }

    FString BehaviorTreePath;
    Params->TryGetStringField(TEXT("behavior_tree_path"), BehaviorTreePath);

    double PerceptionRadius = 1000.0;
    Params->TryGetNumberField(TEXT("perception_radius"), PerceptionRadius);

    FString Faction = TEXT("neutral");
    Params->TryGetStringField(TEXT("faction"), Faction);

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // Find the actor
    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName || It->GetActorLabel() == ActorName)
        {
            TargetActor = *It;
            break;
        }
    }

    if (!TargetActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    // Store AI behavior configuration as tags on the actor for runtime lookup
    TargetActor->Tags.Add(FName(*FString::Printf(TEXT("ai_faction:%s"), *Faction)));
    TargetActor->Tags.Add(FName(*FString::Printf(TEXT("ai_perception_radius:%.1f"), PerceptionRadius)));

    if (!BehaviorTreePath.IsEmpty())
    {
        TargetActor->Tags.Add(FName(*FString::Printf(TEXT("ai_behavior_tree:%s"), *BehaviorTreePath)));
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("actor_name"), TargetActor->GetName());
    ResultObj->SetStringField(TEXT("faction"), Faction);
    ResultObj->SetNumberField(TEXT("perception_radius"), PerceptionRadius);
    if (!BehaviorTreePath.IsEmpty())
    {
        ResultObj->SetStringField(TEXT("behavior_tree_path"), BehaviorTreePath);
    }
    ResultObj->SetBoolField(TEXT("success"), true);
    return ResultObj;
}

// ============================================================================
// Behavior Tree / Blackboard Commands
// ============================================================================

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleCreateBehaviorTree(
    const TSharedPtr<FJsonObject>& Params)
{
    FString AssetName;
    if (!Params->TryGetStringField(TEXT("asset_name"), AssetName) || AssetName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'asset_name' parameter"));
    }

    FString PackagePath = TEXT("/Game/AI/");
    Params->TryGetStringField(TEXT("package_path"), PackagePath);
    if (!PackagePath.EndsWith(TEXT("/")))
    {
        PackagePath += TEXT("/");
    }

    FString FullPackageName = PackagePath + AssetName;
    UPackage* Package = CreatePackage(*FullPackageName);
    if (!Package)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package"));
    }

    UBehaviorTree* BehaviorTree = NewObject<UBehaviorTree>(Package, FName(*AssetName), RF_Public | RF_Standalone);
    if (!BehaviorTree)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create BehaviorTree asset"));
    }

    FAssetRegistryModule::AssetCreated(BehaviorTree);
    Package->MarkPackageDirty();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("asset_name"), AssetName);
    ResultObj->SetStringField(TEXT("path"), FullPackageName);
    ResultObj->SetStringField(TEXT("type"), TEXT("UBehaviorTree"));
    ResultObj->SetStringField(TEXT("note"), TEXT("Use the Behavior Tree Editor to add Blackboard and Composite nodes."));
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleCreateBlackboard(
    const TSharedPtr<FJsonObject>& Params)
{
    FString AssetName;
    if (!Params->TryGetStringField(TEXT("asset_name"), AssetName) || AssetName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'asset_name' parameter"));
    }

    FString PackagePath = TEXT("/Game/AI/");
    Params->TryGetStringField(TEXT("package_path"), PackagePath);
    if (!PackagePath.EndsWith(TEXT("/")))
    {
        PackagePath += TEXT("/");
    }

    FString FullPackageName = PackagePath + AssetName;
    UPackage* Package = CreatePackage(*FullPackageName);
    if (!Package)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package"));
    }

    UBlackboardData* Blackboard = NewObject<UBlackboardData>(Package, FName(*AssetName), RF_Public | RF_Standalone);
    if (!Blackboard)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create Blackboard asset"));
    }

    FAssetRegistryModule::AssetCreated(Blackboard);
    Package->MarkPackageDirty();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("asset_name"), AssetName);
    ResultObj->SetStringField(TEXT("path"), FullPackageName);
    ResultObj->SetStringField(TEXT("type"), TEXT("UBlackboardData"));
    ResultObj->SetStringField(TEXT("note"), TEXT("Use the Blackboard Editor to add keys and their types."));
    return ResultObj;
}

// ============================================================================
// Navigation Commands
// ============================================================================

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleCreateNavModifierVolume(
    const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No active world found"));
    }

    FString VolumeName = TEXT("NavModifierVolume");
    Params->TryGetStringField(TEXT("name"), VolumeName);

    FVector Location = FVector::ZeroVector;
    const TSharedPtr<FJsonObject>* LocationObj = nullptr;
    if (Params->TryGetObjectField(TEXT("location"), LocationObj))
    {
        Location = FEpicUnrealMCPCommonUtils::GetVectorFromJson(*LocationObj, TEXT("value"));
    }

    FVector Extent = FVector(500.0f, 500.0f, 250.0f);
    const TSharedPtr<FJsonObject>* ExtentObj = nullptr;
    if (Params->TryGetObjectField(TEXT("extent"), ExtentObj))
    {
        Extent = FEpicUnrealMCPCommonUtils::GetVectorFromJson(*ExtentObj, TEXT("value"));
    }

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*VolumeName);
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    ANavModifierVolume* Volume = World->SpawnActor<ANavModifierVolume>(
        ANavModifierVolume::StaticClass(), Location, FRotator::ZeroRotator, SpawnParams);

    if (!Volume)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn NavModifierVolume"));
    }

    Volume->SetActorScale3D(Extent / 50.0f);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("name"), Volume->GetName());
    ResultObj->SetStringField(TEXT("location"), Location.ToString());
    ResultObj->SetStringField(TEXT("extent"), Extent.ToString());
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleCreateNavLinkProxy(
    const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No active world found"));
    }

    FString ProxyName = TEXT("NavLinkProxy");
    Params->TryGetStringField(TEXT("name"), ProxyName);

    FVector Location = FVector::ZeroVector;
    const TSharedPtr<FJsonObject>* LocationObj = nullptr;
    if (Params->TryGetObjectField(TEXT("location"), LocationObj))
    {
        Location = FEpicUnrealMCPCommonUtils::GetVectorFromJson(*LocationObj, TEXT("value"));
    }

    FVector LeftPoint = FVector(-100.0f, 0.0f, 0.0f);
    const TSharedPtr<FJsonObject>* LeftObj = nullptr;
    if (Params->TryGetObjectField(TEXT("left"), LeftObj))
    {
        LeftPoint = FEpicUnrealMCPCommonUtils::GetVectorFromJson(*LeftObj, TEXT("value"));
    }

    FVector RightPoint = FVector(100.0f, 0.0f, 0.0f);
    const TSharedPtr<FJsonObject>* RightObj = nullptr;
    if (Params->TryGetObjectField(TEXT("right"), RightObj))
    {
        RightPoint = FEpicUnrealMCPCommonUtils::GetVectorFromJson(*RightObj, TEXT("value"));
    }

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*ProxyName);
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    ANavLinkProxy* Proxy = World->SpawnActor<ANavLinkProxy>(
        ANavLinkProxy::StaticClass(), Location, FRotator::ZeroRotator, SpawnParams);

    if (!Proxy)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn NavLinkProxy"));
    }

    Proxy->SetActorLocation(Location);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("name"), Proxy->GetName());
    ResultObj->SetStringField(TEXT("location"), Location.ToString());
    ResultObj->SetStringField(TEXT("left"), LeftPoint.ToString());
    ResultObj->SetStringField(TEXT("right"), RightPoint.ToString());
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleCreateSplineFromPoints(const TSharedPtr<FJsonObject>& Params)
{
    FString SplineName = TEXT("SplineFromPoints");
    Params->TryGetStringField(TEXT("spline_name"), SplineName);

    FString McpId = SplineName;
    Params->TryGetStringField(TEXT("mcp_id"), McpId);

    bool bClosedLoop = false;
    Params->TryGetBoolField(TEXT("closed_loop"), bClosedLoop);

    bool bFocusViewport = true;
    Params->TryGetBoolField(TEXT("focus_viewport"), bFocusViewport);

    double MergeTolerance = 0.01;
    Params->TryGetNumberField(TEXT("point_merge_tolerance"), MergeTolerance);
    const double MergeToleranceSq = FMath::Square(FMath::Max(MergeTolerance, 0.0));

    FString TangentModeStr = TEXT("curve");
    Params->TryGetStringField(TEXT("tangent_mode"), TangentModeStr);
    const ESplinePointType::Type PointType = TangentModeStr.Equals(TEXT("linear"), ESearchCase::IgnoreCase)
        ? ESplinePointType::Linear
        : ESplinePointType::Curve;

    auto TryParsePointObject = [](const TSharedPtr<FJsonObject>& Obj, FVector& OutPoint, FString& OutError) -> bool
    {
        if (!Obj.IsValid())
        {
            OutError = TEXT("point must be an object");
            return false;
        }

        double X = 0.0;
        double Y = 0.0;
        double Z = 0.0;
        if (!Obj->TryGetNumberField(TEXT("x"), X) ||
            !Obj->TryGetNumberField(TEXT("y"), Y) ||
            !Obj->TryGetNumberField(TEXT("z"), Z))
        {
            OutError = TEXT("point requires numeric x, y, and z fields");
            return false;
        }

        OutPoint = FVector(X, Y, Z);
        if (!FMath::IsFinite(OutPoint.X) || !FMath::IsFinite(OutPoint.Y) || !FMath::IsFinite(OutPoint.Z))
        {
            OutError = TEXT("point contains NaN or Infinity");
            return false;
        }
        return true;
    };

    auto TryParsePointValue = [&TryParsePointObject](const TSharedPtr<FJsonValue>& Value, FVector& OutPoint, FString& OutError) -> bool
    {
        const TSharedPtr<FJsonObject>* Obj = nullptr;
        if (Value.IsValid() && Value->TryGetObject(Obj) && Obj && Obj->IsValid())
        {
            return TryParsePointObject(*Obj, OutPoint, OutError);
        }
        OutError = TEXT("point value must be an object");
        return false;
    };

    auto MakeVecJson = [](const FVector& V)
    {
        TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
        Obj->SetNumberField(TEXT("x"), V.X);
        Obj->SetNumberField(TEXT("y"), V.Y);
        Obj->SetNumberField(TEXT("z"), V.Z);
        return Obj;
    };

    auto PointsNearlyEqual = [MergeToleranceSq](const FVector& A, const FVector& B) -> bool
    {
        return FVector::DistSquared(A, B) <= MergeToleranceSq;
    };

    TArray<TArray<FVector>> PointChains;
    int32 SegmentCount = 0;

    const TArray<TSharedPtr<FJsonValue>>* PointsArray = nullptr;
    if (Params->TryGetArrayField(TEXT("points"), PointsArray) && PointsArray)
    {
        if (PointsArray->Num() < 2)
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("create_spline_from_points requires at least 2 points"));
        }

        TArray<FVector> Chain;
        Chain.Reserve(PointsArray->Num());
        for (int32 i = 0; i < PointsArray->Num(); ++i)
        {
            FVector Point;
            FString Error;
            if (!TryParsePointValue((*PointsArray)[i], Point, Error))
            {
                return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid points[%d]: %s"), i, *Error));
            }
            Chain.Add(Point);
        }
        SegmentCount = FMath::Max(0, Chain.Num() - 1);
        PointChains.Add(MoveTemp(Chain));
    }
    else
    {
        const TArray<TSharedPtr<FJsonValue>>* SegmentsArray = nullptr;
        if (!Params->TryGetArrayField(TEXT("segments"), SegmentsArray) || !SegmentsArray || SegmentsArray->Num() < 1)
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("create_spline_from_points requires 'points' or at least 1 segment"));
        }

        TArray<FVector> CurrentChain;
        for (int32 i = 0; i < SegmentsArray->Num(); ++i)
        {
            const TSharedPtr<FJsonObject>* SegObj = nullptr;
            if (!(*SegmentsArray)[i].IsValid() || !(*SegmentsArray)[i]->TryGetObject(SegObj) || !SegObj || !SegObj->IsValid())
            {
                return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid segments[%d]: segment must be an object"), i));
            }

            const TSharedPtr<FJsonObject>* StartObj = nullptr;
            const TSharedPtr<FJsonObject>* EndObj = nullptr;
            if (!(*SegObj)->TryGetObjectField(TEXT("start"), StartObj) || !(*SegObj)->TryGetObjectField(TEXT("end"), EndObj))
            {
                return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid segments[%d]: requires start and end"), i));
            }

            FVector StartPt;
            FVector EndPt;
            FString Error;
            if (!TryParsePointObject(*StartObj, StartPt, Error))
            {
                return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid segments[%d].start: %s"), i, *Error));
            }
            if (!TryParsePointObject(*EndObj, EndPt, Error))
            {
                return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid segments[%d].end: %s"), i, *Error));
            }
            if (PointsNearlyEqual(StartPt, EndPt))
            {
                continue;
            }

            if (CurrentChain.Num() == 0)
            {
                CurrentChain.Add(StartPt);
                CurrentChain.Add(EndPt);
            }
            else if (PointsNearlyEqual(CurrentChain.Last(), StartPt))
            {
                CurrentChain.Add(EndPt);
            }
            else
            {
                PointChains.Add(MoveTemp(CurrentChain));
                CurrentChain.Add(StartPt);
                CurrentChain.Add(EndPt);
            }
            ++SegmentCount;
        }

        if (CurrentChain.Num() > 0)
        {
            PointChains.Add(MoveTemp(CurrentChain));
        }
    }

    int32 TotalPointCount = 0;
    for (const TArray<FVector>& Chain : PointChains)
    {
        TotalPointCount += Chain.Num();
    }
    if (TotalPointCount < 2 || PointChains.Num() == 0)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("create_spline_from_points produced no drawable spline points"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FScopedTransaction Transaction(FText::FromString(FString::Printf(TEXT("UnrealMCP: Create Spline %s"), *SplineName)));
    AActor* SplineActor = GetActorIndex().FindByMcpId(McpId);
    if (!SplineActor)
    {
        // Fallback to tag-based search for actors not yet in the index.
        SplineActor = FEpicUnrealMCPCommonUtils::FindActorByMcpIdTag(World, McpId);
    }
    bool bCreatedActor = false;
    if (!SplineActor)
    {
        FActorSpawnParameters SpawnParams;
        SpawnParams.Name = MakeUniqueObjectName(World, AActor::StaticClass(), FName(*SplineName));
        SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        SplineActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
        if (!SplineActor)
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn spline actor"));
        }
        bCreatedActor = true;
    }

    SplineActor->SetFlags(RF_Transactional);
    SplineActor->Modify();
    SplineActor->SetActorLabel(*SplineName);

    if (!SplineActor->GetRootComponent())
    {
        USceneComponent* RootComp = NewObject<USceneComponent>(SplineActor, USceneComponent::StaticClass(), TEXT("DefaultSceneRoot"));
        RootComp->RegisterComponent();
        SplineActor->SetRootComponent(RootComp);
    }

    TArray<USplineComponent*> ExistingSplineComponents;
    SplineActor->GetComponents<USplineComponent>(ExistingSplineComponents);
    for (USplineComponent* ExistingComp : ExistingSplineComponents)
    {
        if (ExistingComp)
        {
            ExistingComp->DestroyComponent();
        }
    }

    TArray<TSharedPtr<FJsonValue>> PointJsonArray;
    TArray<TSharedPtr<FJsonValue>> ChainLengthsJson;
    int32 ComponentCount = 0;
    for (int32 ChainIndex = 0; ChainIndex < PointChains.Num(); ++ChainIndex)
    {
        const TArray<FVector>& Chain = PointChains[ChainIndex];
        if (Chain.Num() < 2)
        {
            continue;
        }

        const FName ComponentName(*FString::Printf(TEXT("ProceduralSpline_%d"), ChainIndex));
        USplineComponent* SplineComp = NewObject<USplineComponent>(SplineActor, USplineComponent::StaticClass(), ComponentName, RF_Transactional);
        if (!SplineComp)
        {
            if (bCreatedActor)
            {
                SplineActor->Destroy();
            }
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create SplineComponent"));
        }

        SplineComp->SetFlags(RF_Transactional);
        SplineComp->AttachToComponent(SplineActor->GetRootComponent(), FAttachmentTransformRules::KeepWorldTransform);
        SplineActor->AddInstanceComponent(SplineComp);
        SplineComp->RegisterComponent();
        SplineComp->ClearSplinePoints(false);

        for (int32 PointIndex = 0; PointIndex < Chain.Num(); ++PointIndex)
        {
            SplineComp->AddSplinePoint(Chain[PointIndex], ESplineCoordinateSpace::World, false);
            SplineComp->SetSplinePointType(PointIndex, PointType, false);
            PointJsonArray.Add(MakeShared<FJsonValueObject>(MakeVecJson(Chain[PointIndex])));
        }

        SplineComp->SetClosedLoop(bClosedLoop && PointChains.Num() == 1);
        SplineComp->UpdateSpline();
        ChainLengthsJson.Add(MakeShared<FJsonValueNumber>(Chain.Num()));
        ++ComponentCount;
    }

    SplineActor->Tags.AddUnique(FName(TEXT("managed_by_mcp")));
    if (!McpId.IsEmpty())
    {
        SplineActor->Tags.AddUnique(FName(*FString::Printf(TEXT("mcp_id:%s"), *McpId)));
    }
    GetActorIndex().AddActor(SplineActor);
    SplineActor->MarkPackageDirty();

    if (bFocusViewport && GEditor)
    {
        GEditor->SelectNone(false, true, false);
        GEditor->SelectActor(SplineActor, true, true, true, true);
        GEditor->MoveViewportCamerasToActor(*SplineActor, false);
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("spline_name"), SplineName);
    ResultObj->SetStringField(TEXT("mcp_id"), McpId);
    ResultObj->SetStringField(TEXT("actor_name"), SplineActor->GetName());
    ResultObj->SetStringField(TEXT("actor_label"), SplineActor->GetActorLabel());
    ResultObj->SetArrayField(TEXT("points"), PointJsonArray);
    ResultObj->SetArrayField(TEXT("chain_lengths"), ChainLengthsJson);
    ResultObj->SetBoolField(TEXT("closed_loop"), bClosedLoop && PointChains.Num() == 1);
    ResultObj->SetStringField(TEXT("tangent_mode"), TangentModeStr);
    ResultObj->SetNumberField(TEXT("point_count"), TotalPointCount);
    ResultObj->SetNumberField(TEXT("segment_count"), SegmentCount);
    ResultObj->SetNumberField(TEXT("component_count"), ComponentCount);
    ResultObj->SetBoolField(TEXT("created_actor"), bCreatedActor);
    ResultObj->SetBoolField(TEXT("success"), true);
    return ResultObj;
}

// W1-D_AI_BEGIN
// W1-D AI / Behavior Tree expansion (UE 5.7)

namespace
{
    static UClass* ResolveBlackboardKeyTypeClass(const FString& KeyType)
    {
        if (KeyType.Equals(TEXT("Bool"), ESearchCase::IgnoreCase)) return UBlackboardKeyType_Bool::StaticClass();
        if (KeyType.Equals(TEXT("Int"), ESearchCase::IgnoreCase) || KeyType.Equals(TEXT("Integer"), ESearchCase::IgnoreCase)) return UBlackboardKeyType_Int::StaticClass();
        if (KeyType.Equals(TEXT("Float"), ESearchCase::IgnoreCase)) return UBlackboardKeyType_Float::StaticClass();
        if (KeyType.Equals(TEXT("String"), ESearchCase::IgnoreCase)) return UBlackboardKeyType_String::StaticClass();
        if (KeyType.Equals(TEXT("Name"), ESearchCase::IgnoreCase)) return UBlackboardKeyType_Name::StaticClass();
        if (KeyType.Equals(TEXT("Vector"), ESearchCase::IgnoreCase)) return UBlackboardKeyType_Vector::StaticClass();
        if (KeyType.Equals(TEXT("Rotator"), ESearchCase::IgnoreCase)) return UBlackboardKeyType_Rotator::StaticClass();
        if (KeyType.Equals(TEXT("Object"), ESearchCase::IgnoreCase)) return UBlackboardKeyType_Object::StaticClass();
        if (KeyType.Equals(TEXT("Class"), ESearchCase::IgnoreCase)) return UBlackboardKeyType_Class::StaticClass();
        return nullptr;
    }
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleAddBlackboardKey(const TSharedPtr<FJsonObject>& Params)
{
    FString BlackboardPath, KeyName, KeyType;
    if (!Params->TryGetStringField(TEXT("blackboard_path"), BlackboardPath) || BlackboardPath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blackboard_path' parameter"));
    if (!Params->TryGetStringField(TEXT("key_name"), KeyName) || KeyName.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'key_name' parameter"));
    if (!Params->TryGetStringField(TEXT("key_type"), KeyType) || KeyType.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'key_type' parameter (Bool/Int/Float/String/Name/Vector/Rotator/Object/Class)"));
    bool bInstanceSynced = false;
    Params->TryGetBoolField(TEXT("instance_synced"), bInstanceSynced);

    UBlackboardData* Blackboard = LoadObject<UBlackboardData>(nullptr, *BlackboardPath);
    if (!Blackboard)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("BlackboardData not found: %s"), *BlackboardPath));

    UClass* KeyTypeClass = ResolveBlackboardKeyTypeClass(KeyType);
    if (!KeyTypeClass)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Unknown blackboard key type: %s"), *KeyType));

    // Reject duplicate names within this BB (parent chain not checked).
    const FName KeyFName(*KeyName);
    for (const FBlackboardEntry& Existing : Blackboard->Keys)
    {
        if (Existing.EntryName == KeyFName)
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Blackboard key already exists: %s"), *KeyName));
        }
    }

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Add Blackboard Key")));
    Blackboard->Modify();

    FBlackboardEntry Entry;
    Entry.EntryName = KeyFName;
    Entry.bInstanceSynced = bInstanceSynced ? 1 : 0;
    Entry.KeyType = NewObject<UBlackboardKeyType>(Blackboard, KeyTypeClass);
    Blackboard->Keys.Add(MoveTemp(Entry));
    Blackboard->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("blackboard_path"), BlackboardPath);
    Result->SetStringField(TEXT("key_name"), KeyName);
    Result->SetStringField(TEXT("key_type"), KeyType);
    Result->SetBoolField(TEXT("instance_synced"), bInstanceSynced);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleRemoveBlackboardKey(const TSharedPtr<FJsonObject>& Params)
{
    FString BlackboardPath, KeyName;
    if (!Params->TryGetStringField(TEXT("blackboard_path"), BlackboardPath) || BlackboardPath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blackboard_path' parameter"));
    if (!Params->TryGetStringField(TEXT("key_name"), KeyName) || KeyName.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'key_name' parameter"));

    UBlackboardData* Blackboard = LoadObject<UBlackboardData>(nullptr, *BlackboardPath);
    if (!Blackboard)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("BlackboardData not found: %s"), *BlackboardPath));

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Remove Blackboard Key")));
    Blackboard->Modify();

    const FName KeyFName(*KeyName);
    const int32 Removed = Blackboard->Keys.RemoveAll([&KeyFName](const FBlackboardEntry& Entry)
    {
        return Entry.EntryName == KeyFName;
    });

    if (Removed == 0)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Blackboard key not found: %s"), *KeyName));
    }

    Blackboard->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("blackboard_path"), BlackboardPath);
    Result->SetStringField(TEXT("key_name"), KeyName);
    Result->SetNumberField(TEXT("removed"), Removed);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleAddAIPerception(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter (AIController or owner actor)"));

    UWorld* World = GetEditorWorld();
    if (!World)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));

    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName || It->GetActorLabel() == ActorName)
        {
            TargetActor = *It;
            break;
        }
    }
    if (!TargetActor)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Actor not found: %s"), *ActorName));

    // Check for existing component
    UAIPerceptionComponent* Existing = TargetActor->FindComponentByClass<UAIPerceptionComponent>();
    if (Existing)
    {
        TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
        R->SetBoolField(TEXT("success"), true);
        R->SetStringField(TEXT("actor_name"), ActorName);
        R->SetBoolField(TEXT("already_existed"), true);
        R->SetStringField(TEXT("component_name"), Existing->GetName());
        return R;
    }

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Add AI Perception")));
    TargetActor->Modify();

    UAIPerceptionComponent* Perception = NewObject<UAIPerceptionComponent>(TargetActor, UAIPerceptionComponent::StaticClass(), TEXT("AIPerception"));
    if (!Perception)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create UAIPerceptionComponent"));

    Perception->RegisterComponent();
    TargetActor->AddInstanceComponent(Perception);
    TargetActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    Result->SetStringField(TEXT("component_name"), Perception->GetName());
    Result->SetBoolField(TEXT("already_existed"), false);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleConfigureAISenseSight(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));

    UWorld* World = GetEditorWorld();
    if (!World)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));

    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName || It->GetActorLabel() == ActorName)
        {
            TargetActor = *It;
            break;
        }
    }
    if (!TargetActor)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Actor not found: %s"), *ActorName));

    UAIPerceptionComponent* Perception = TargetActor->FindComponentByClass<UAIPerceptionComponent>();
    if (!Perception)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("Actor has no UAIPerceptionComponent. Call add_ai_perception first."));

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Configure AI Sight")));
    Perception->Modify();

    UAISenseConfig_Sight* SightConfig = NewObject<UAISenseConfig_Sight>(Perception);
    double SightRadius = -1.0;
    double LoseSightRadius = -1.0;
    double PeripheralVisionAngle = -1.0;
    double AutoSuccessRangeFromLastSeen = -1.0;
    Params->TryGetNumberField(TEXT("sight_radius"), SightRadius);
    Params->TryGetNumberField(TEXT("lose_sight_radius"), LoseSightRadius);
    Params->TryGetNumberField(TEXT("peripheral_vision_angle_degrees"), PeripheralVisionAngle);
    Params->TryGetNumberField(TEXT("auto_success_range_from_last_seen"), AutoSuccessRangeFromLastSeen);

    if (SightRadius >= 0.0) SightConfig->SightRadius = static_cast<float>(SightRadius);
    if (LoseSightRadius >= 0.0) SightConfig->LoseSightRadius = static_cast<float>(LoseSightRadius);
    if (PeripheralVisionAngle >= 0.0) SightConfig->PeripheralVisionAngleDegrees = static_cast<float>(PeripheralVisionAngle);
    if (AutoSuccessRangeFromLastSeen >= 0.0) SightConfig->AutoSuccessRangeFromLastSeenLocation = static_cast<float>(AutoSuccessRangeFromLastSeen);

    bool bDetectNeutrals = true, bDetectFriendlies = true, bDetectEnemies = true;
    Params->TryGetBoolField(TEXT("detect_neutrals"), bDetectNeutrals);
    Params->TryGetBoolField(TEXT("detect_friendlies"), bDetectFriendlies);
    Params->TryGetBoolField(TEXT("detect_enemies"), bDetectEnemies);
    SightConfig->DetectionByAffiliation.bDetectNeutrals = bDetectNeutrals;
    SightConfig->DetectionByAffiliation.bDetectFriendlies = bDetectFriendlies;
    SightConfig->DetectionByAffiliation.bDetectEnemies = bDetectEnemies;

    Perception->ConfigureSense(*SightConfig);
    // Make Sight the dominant sense when none is set yet.
    if (!Perception->GetDominantSense())
    {
        Perception->SetDominantSense(UAISense_Sight::StaticClass());
    }

    TargetActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    Result->SetNumberField(TEXT("sight_radius"), SightConfig->SightRadius);
    Result->SetNumberField(TEXT("lose_sight_radius"), SightConfig->LoseSightRadius);
    Result->SetNumberField(TEXT("peripheral_vision_angle_degrees"), SightConfig->PeripheralVisionAngleDegrees);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleSetRecastNavMeshAgent(const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));

    ARecastNavMesh* NavMesh = nullptr;
    for (TActorIterator<ARecastNavMesh> It(World); It; ++It)
    {
        NavMesh = *It;
        break;
    }
    if (!NavMesh)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("No ARecastNavMesh in the editor world. Drop a NavMeshBoundsVolume or create_nav_mesh_volume first."));

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Set Recast Agent")));
    NavMesh->Modify();

    bool bChanged = false;
    double AgentRadius = -1.0, AgentHeight = -1.0, AgentMaxStepHeight = -1.0;
    double TileSizeUU = -1.0, MaxSimplificationError = -1.0;

    if (Params->TryGetNumberField(TEXT("agent_radius"), AgentRadius) && AgentRadius > 0.0)
    { NavMesh->AgentRadius = static_cast<float>(AgentRadius); bChanged = true; }
    if (Params->TryGetNumberField(TEXT("agent_height"), AgentHeight) && AgentHeight > 0.0)
    { NavMesh->AgentHeight = static_cast<float>(AgentHeight); bChanged = true; }
    if (Params->TryGetNumberField(TEXT("agent_max_step_height"), AgentMaxStepHeight) && AgentMaxStepHeight > 0.0)
    { NavMesh->AgentMaxStepHeight = static_cast<float>(AgentMaxStepHeight); bChanged = true; }
    if (Params->TryGetNumberField(TEXT("tile_size_uu"), TileSizeUU) && TileSizeUU > 0.0)
    { NavMesh->TileSizeUU = static_cast<float>(TileSizeUU); bChanged = true; }
    if (Params->TryGetNumberField(TEXT("max_simplification_error"), MaxSimplificationError) && MaxSimplificationError >= 0.0)
    { NavMesh->MaxSimplificationError = static_cast<float>(MaxSimplificationError); bChanged = true; }

    if (!bChanged)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("Provide at least one agent_radius/agent_height/agent_max_step_height/tile_size_uu/max_simplification_error"));

    // UE 5.7: per-instance changes don't auto-rebuild; mark dirty so user can RebuildAll.
    NavMesh->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetNumberField(TEXT("agent_radius"), NavMesh->AgentRadius);
    Result->SetNumberField(TEXT("agent_height"), NavMesh->AgentHeight);
    Result->SetNumberField(TEXT("agent_max_step_height"), NavMesh->AgentMaxStepHeight);
    Result->SetNumberField(TEXT("tile_size_uu"), NavMesh->TileSizeUU);
    Result->SetNumberField(TEXT("max_simplification_error"), NavMesh->MaxSimplificationError);
    Result->SetStringField(TEXT("note"), TEXT("Per-instance change; re-run NavMesh build to apply to tiles."));
    return Result;
}

// W1-G_EQS_BEGIN
// W1-G EQS Query asset + Crowd Following component (UE 5.7)

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleCreateEQSQuery(const TSharedPtr<FJsonObject>& Params)
{
    FString AssetPath;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath) || AssetPath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset_path' parameter"));

    if (LoadObject<UObject>(nullptr, *AssetPath))
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Asset already exists: %s"), *AssetPath));

    FString AssetName = FPaths::GetBaseFilename(AssetPath);
    UPackage* Package = CreatePackage(*AssetPath);
    if (!Package)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package for EQS Query"));

    UEnvQuery* Query = NewObject<UEnvQuery>(Package, FName(*AssetName), RF_Public | RF_Standalone);
    if (!Query)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create UEnvQuery asset"));

    // UE 5.7: UEnvQuery::QueryName is protected and friended only to UEnvQueryManager.
    // Renaming the asset triggers UEnvQuery::PostRename() which keeps QueryName in
    // sync with the UObject name, so we re-rename instead of assigning directly.
    FString QueryName;
    if (Params->TryGetStringField(TEXT("query_name"), QueryName) && !QueryName.IsEmpty())
    {
        const FName DesiredName(*QueryName);
        if (Query->GetFName() != DesiredName)
        {
            Query->Rename(*QueryName, Query->GetOuter(), REN_DontCreateRedirectors | REN_NonTransactional);
        }
    }

    FAssetRegistryModule::AssetCreated(Query);
    Package->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("asset_path"), Query->GetPathName());
    Result->SetStringField(TEXT("note"), TEXT("Empty UEnvQuery. Add UEnvQueryGenerator/Test in the EQS editor."));
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNavigationCommands::HandleSetCrowdFollowingEnable(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter (typically an AAIController)"));
    bool bEnable = true;
    Params->TryGetBoolField(TEXT("enable"), bEnable);

    UWorld* World = GetEditorWorld();
    if (!World)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));

    AAIController* Controller = nullptr;
    for (TActorIterator<AAIController> It(World); It; ++It)
    {
        if (It->GetName() == ActorName || It->GetActorLabel() == ActorName)
        {
            Controller = *It;
            break;
        }
    }
    if (!Controller)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("AAIController not found: %s"), *ActorName));
    }

    UCrowdFollowingComponent* Existing = Controller->FindComponentByClass<UCrowdFollowingComponent>();
    bool bAlreadyExisted = (Existing != nullptr);

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Set Crowd Following")));
    Controller->Modify();

    if (bEnable)
    {
        if (!Existing)
        {
            UCrowdFollowingComponent* Crowd = NewObject<UCrowdFollowingComponent>(Controller, UCrowdFollowingComponent::StaticClass(), TEXT("CrowdFollowing"));
            if (!Crowd)
                return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create UCrowdFollowingComponent"));
            Crowd->RegisterComponent();
            Controller->AddInstanceComponent(Crowd);
            Existing = Crowd;
        }
    }
    else
    {
        if (Existing)
        {
            Controller->RemoveInstanceComponent(Existing);
            Existing->DestroyComponent();
            Existing = nullptr;
        }
    }

    Controller->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    Result->SetBoolField(TEXT("enabled"), Existing != nullptr);
    Result->SetBoolField(TEXT("already_existed"), bAlreadyExisted);
    return Result;
}
