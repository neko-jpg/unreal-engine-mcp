#if WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"

#include "Commands/EpicUnrealMCPEditorCommands.h"
#include "Dom/JsonObject.h"
#include "Tests/MCPAutomationTestUtils.h"

using namespace UnrealMCP::Tests;

// --- NavMeshVolume ---

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPNavMeshVolumeTest, "UnrealMCP.L3.Editor.NavMeshVolume", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPNavMeshVolumeTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;
	const FString VolumeName = MakeUniqueName(TEXT("MCPNavMeshVol"));

	// Clean up any leftover from previous runs
	DestroyActorIfExists(VolumeName);

	// Build params: volume_name, location{x,y,z}, extent{x,y,z}
	const TSharedPtr<FJsonObject> Params = MakeObject({
		{TEXT("volume_name"), MakeStringValue(VolumeName)},
		{TEXT("location"), MakeArrayValue({100.0, 200.0, 300.0})},
		{TEXT("extent"), MakeArrayValue({500.0, 500.0, 500.0})}
	});

	TSharedPtr<FJsonObject> Result = Commands.HandleCommand(TEXT("create_nav_mesh_volume"), Params);
	TestTrue(TEXT("create_nav_mesh_volume should succeed"), IsSuccessResponse(Result));

	if (!IsSuccessResponse(Result))
	{
		return true;
	}

	// Verify volume_name is present in result
	FString OutVolumeName;
	TestTrue(TEXT("Result should contain volume_name"), Result->TryGetStringField(TEXT("volume_name"), OutVolumeName));
	TestEqual(TEXT("volume_name should match"), OutVolumeName, VolumeName);

	// Verify navmesh_rebuilt field
	bool bNavMeshRebuilt = false;
	TestTrue(TEXT("Result should contain navmesh_rebuilt"), Result->TryGetBoolField(TEXT("navmesh_rebuilt"), bNavMeshRebuilt));

	// Cleanup: destroy the spawned NavMeshBoundsVolume
	DestroyActorIfExists(VolumeName);

	return true;
}

// --- PatrolRoute ---

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPPatrolRouteTest, "UnrealMCP.L3.Editor.PatrolRoute", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPPatrolRouteTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;
	const FString RouteName = MakeUniqueName(TEXT("MCPPatrolRoute"));

	// Clean up any leftover from previous runs
	DestroyActorIfExists(RouteName);

	// Build params: patrol_route_name, points[{x,y,z},...], closed_loop
	TArray<TSharedPtr<FJsonValue>> PointsArray;
	PointsArray.Add(MakeObjectValue(MakeObject({
		{TEXT("x"), MakeNumberValue(0.0)},
		{TEXT("y"), MakeNumberValue(0.0)},
		{TEXT("z"), MakeNumberValue(0.0)}
	})));
	PointsArray.Add(MakeObjectValue(MakeObject({
		{TEXT("x"), MakeNumberValue(100.0)},
		{TEXT("y"), MakeNumberValue(0.0)},
		{TEXT("z"), MakeNumberValue(0.0)}
	})));
	PointsArray.Add(MakeObjectValue(MakeObject({
		{TEXT("x"), MakeNumberValue(100.0)},
		{TEXT("y"), MakeNumberValue(100.0)},
		{TEXT("z"), MakeNumberValue(0.0)}
	})));

	const TSharedPtr<FJsonObject> Params = MakeObject({
		{TEXT("patrol_route_name"), MakeStringValue(RouteName)},
		{TEXT("points"), MakeArrayValueJson(PointsArray)},
		{TEXT("closed_loop"), MakeBoolValue(true)}
	});

	TSharedPtr<FJsonObject> Result = Commands.HandleCommand(TEXT("create_patrol_route"), Params);
	TestTrue(TEXT("create_patrol_route should succeed"), IsSuccessResponse(Result));

	if (!IsSuccessResponse(Result))
	{
		return true;
	}

	// Verify route_name
	FString OutRouteName;
	TestTrue(TEXT("Result should contain route_name"), Result->TryGetStringField(TEXT("route_name"), OutRouteName));
	TestEqual(TEXT("route_name should match"), OutRouteName, RouteName);

	// Verify point_count
	double PointCount = 0.0;
	TestTrue(TEXT("Result should contain point_count"), Result->TryGetNumberField(TEXT("point_count"), PointCount));
	TestEqual(TEXT("point_count should be 3"), static_cast<int32>(PointCount), 3);

	// Verify closed_loop
	bool bClosedLoop = false;
	TestTrue(TEXT("Result should contain closed_loop"), Result->TryGetBoolField(TEXT("closed_loop"), bClosedLoop));
	TestTrue(TEXT("closed_loop should be true"), bClosedLoop);

	// Cleanup: destroy the spawned actor
	DestroyActorIfExists(RouteName);

	return true;
}

// --- AIBehavior ---

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPAIBehaviorTest, "UnrealMCP.L3.Editor.AIBehavior", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPAIBehaviorTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;
	const FString ActorName = MakeUniqueName(TEXT("MCPAIActor"));

	// Clean up any leftover from previous runs
	DestroyActorIfExists(ActorName);

	// First spawn an actor, then set AI behavior on it
	const TSharedPtr<FJsonObject> SpawnParams = MakeObject({
		{TEXT("type"), MakeStringValue(TEXT("StaticMeshActor"))},
		{TEXT("name"), MakeStringValue(ActorName)},
		{TEXT("location"), MakeArrayValue({0.0, 0.0, 0.0})}
	});

	TSharedPtr<FJsonObject> SpawnResult = Commands.HandleCommand(TEXT("spawn_actor"), SpawnParams);
	TestTrue(TEXT("spawn_actor should succeed"), IsSuccessResponse(SpawnResult));

	if (!IsSuccessResponse(SpawnResult))
	{
		return true;
	}

	// Build params: actor_name, behavior_tree_path, perception_radius, faction
	const TSharedPtr<FJsonObject> BehaviorParams = MakeObject({
		{TEXT("actor_name"), MakeStringValue(ActorName)},
		{TEXT("behavior_tree_path"), MakeStringValue(TEXT("/Game/AI/BT_Enemy"))},
		{TEXT("perception_radius"), MakeNumberValue(1500.0)},
		{TEXT("faction"), MakeStringValue(TEXT("hostile"))}
	});

	TSharedPtr<FJsonObject> BehaviorResult = Commands.HandleCommand(TEXT("set_ai_behavior"), BehaviorParams);
	TestTrue(TEXT("set_ai_behavior should succeed"), IsSuccessResponse(BehaviorResult));

	if (!IsSuccessResponse(BehaviorResult))
	{
		DestroyActorIfExists(ActorName);
		return true;
	}

	// Verify faction
	FString OutFaction;
	TestTrue(TEXT("Result should contain faction"), BehaviorResult->TryGetStringField(TEXT("faction"), OutFaction));
	TestEqual(TEXT("faction should match"), OutFaction, TEXT("hostile"));

	// Verify perception_radius
	double OutRadius = 0.0;
	TestTrue(TEXT("Result should contain perception_radius"), BehaviorResult->TryGetNumberField(TEXT("perception_radius"), OutRadius));
	TestEqual(TEXT("perception_radius should match"), OutRadius, 1500.0);

	// Cleanup: destroy the actor
	DestroyActorIfExists(ActorName);

	return true;
}

// --- Boundary & Error Cases ---

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPNavMeshVolumeZeroExtentTest, "UnrealMCP.L3.Editor.NavMeshVolume.ZeroExtent", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPNavMeshVolumeZeroExtentTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;
	const FString VolumeName = MakeUniqueName(TEXT("MCPNavMeshVolZero"));

	DestroyActorIfExists(VolumeName);

	const TSharedPtr<FJsonObject> Params = MakeObject({
		{TEXT("volume_name"), MakeStringValue(VolumeName)},
		{TEXT("location"), MakeArrayValue({0.0, 0.0, 0.0})},
		{TEXT("extent"), MakeArrayValue({0.0, 0.0, 0.0})}
	});

	TSharedPtr<FJsonObject> Result = Commands.HandleCommand(TEXT("create_nav_mesh_volume"), Params);
	TestTrue(TEXT("create_nav_mesh_volume with zero extent should succeed (clamped to min scale)"), IsSuccessResponse(Result));

	if (IsSuccessResponse(Result))
	{
		FString OutActorName;
		TestTrue(TEXT("Result should contain actor_name"), Result->TryGetStringField(TEXT("actor_name"), OutActorName));
		TestFalse(TEXT("actor_name should not be empty"), OutActorName.IsEmpty());
	}

	DestroyActorIfExists(VolumeName);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPPatrolRouteSinglePointErrorTest, "UnrealMCP.L3.Editor.PatrolRoute.SinglePointError", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPPatrolRouteSinglePointErrorTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;
	const FString RouteName = MakeUniqueName(TEXT("MCPPatrolRouteBad"));

	TArray<TSharedPtr<FJsonValue>> PointsArray;
	PointsArray.Add(MakeObjectValue(MakeObject({
		{TEXT("x"), MakeNumberValue(0.0)},
		{TEXT("y"), MakeNumberValue(0.0)},
		{TEXT("z"), MakeNumberValue(0.0)}
	})));

	const TSharedPtr<FJsonObject> Params = MakeObject({
		{TEXT("patrol_route_name"), MakeStringValue(RouteName)},
		{TEXT("points"), MakeArrayValueJson(PointsArray)},
		{TEXT("closed_loop"), MakeBoolValue(false)}
	});

	TSharedPtr<FJsonObject> Result = Commands.HandleCommand(TEXT("create_patrol_route"), Params);
	TestFalse(TEXT("create_patrol_route with 1 point should fail"), IsSuccessResponse(Result));

	FString ErrorMsg = GetErrorMessage(Result);
	TestTrue(TEXT("Error should mention 'at least 2 points'"), ErrorMsg.Contains(TEXT("at least 2 points")));

	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPAIBehaviorMissingActorTest, "UnrealMCP.L3.Editor.AIBehavior.MissingActor", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPAIBehaviorMissingActorTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;
	const FString MissingActorName = MakeUniqueName(TEXT("MCPMissingActor"));

	const TSharedPtr<FJsonObject> BehaviorParams = MakeObject({
		{TEXT("actor_name"), MakeStringValue(MissingActorName)},
		{TEXT("behavior_tree_path"), MakeStringValue(TEXT("/Game/AI/BT_Enemy"))},
		{TEXT("perception_radius"), MakeNumberValue(1500.0)},
		{TEXT("faction"), MakeStringValue(TEXT("hostile"))}
	});

	TSharedPtr<FJsonObject> Result = Commands.HandleCommand(TEXT("set_ai_behavior"), BehaviorParams);
	TestFalse(TEXT("set_ai_behavior on missing actor should fail"), IsSuccessResponse(Result));

	FString ErrorMsg = GetErrorMessage(Result);
	TestTrue(TEXT("Error should mention 'Actor not found'"), ErrorMsg.Contains(TEXT("Actor not found")));

	return true;
}

#endif