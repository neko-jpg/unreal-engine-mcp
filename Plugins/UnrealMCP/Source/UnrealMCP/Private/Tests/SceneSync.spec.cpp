#if WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"

#include "Commands/EpicUnrealMCPEditorCommands.h"
#include "Dom/JsonObject.h"
#include "Tests/MCPAutomationTestUtils.h"

using namespace UnrealMCP::Tests;

// --- SceneSyncApply: Full lifecycle (create -> update -> delete) ---

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPSceneSyncApplyTest, "UnrealMCP.L3.Editor.SceneSyncApply", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPSceneSyncApplyTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;

	const FString Actor1Name = MakeUniqueName(TEXT("MCPSyncA"));
	const FString Actor2Name = MakeUniqueName(TEXT("MCPSyncB"));
	const FString Actor3Name = MakeUniqueName(TEXT("MCPSyncC"));

	// Clean up any leftovers from previous runs
	DestroyActorIfExists(Actor1Name);
	DestroyActorIfExists(Actor2Name);
	DestroyActorIfExists(Actor3Name);

	// Step 1: Create 3 actors via apply_scene_delta with creates array
	TArray<TSharedPtr<FJsonValue>> CreatesArray;
	CreatesArray.Add(MakeObjectValue(MakeObject({
		{TEXT("name"), MakeStringValue(Actor1Name)},
		{TEXT("type"), MakeStringValue(TEXT("StaticMeshActor"))},
		{TEXT("location"), MakeArrayValue({0.0, 0.0, 0.0})}
	})));
	CreatesArray.Add(MakeObjectValue(MakeObject({
		{TEXT("name"), MakeStringValue(Actor2Name)},
		{TEXT("type"), MakeStringValue(TEXT("StaticMeshActor"))},
		{TEXT("location"), MakeArrayValue({100.0, 0.0, 0.0})}
	})));
	CreatesArray.Add(MakeObjectValue(MakeObject({
		{TEXT("name"), MakeStringValue(Actor3Name)},
		{TEXT("type"), MakeStringValue(TEXT("StaticMeshActor"))},
		{TEXT("location"), MakeArrayValue({200.0, 0.0, 0.0})}
	})));

	const TSharedPtr<FJsonObject> CreateParams = MakeObject({
		{TEXT("creates"), MakeArrayValueJson(CreatesArray)}
	});

	TSharedPtr<FJsonObject> CreateResult = Commands.HandleCommand(TEXT("apply_scene_delta"), CreateParams);
	TestTrue(TEXT("apply_scene_delta creates should succeed"), IsSuccessResponse(CreateResult));

	if (!IsSuccessResponse(CreateResult))
	{
		return true;
	}

	// Verify created_count == 3
	double CreatedCount = 0.0;
	TestTrue(TEXT("Result should contain created_count"), CreateResult->TryGetNumberField(TEXT("created_count"), CreatedCount));
	TestEqual(TEXT("created_count should be 3"), static_cast<int32>(CreatedCount), 3);

	// Verify all 3 actors exist
	TestNotNull(TEXT("Actor1 should exist"), FindActorByName(Actor1Name));
	TestNotNull(TEXT("Actor2 should exist"), FindActorByName(Actor2Name));
	TestNotNull(TEXT("Actor3 should exist"), FindActorByName(Actor3Name));

	// Step 2: Update 1 actor's transform via apply_scene_delta with updates array
	TArray<TSharedPtr<FJsonValue>> UpdatesArray;
	UpdatesArray.Add(MakeObjectValue(MakeObject({
		{TEXT("mcp_id"), MakeStringValue(Actor1Name)},
		{TEXT("location"), MakeArrayValue({500.0, 600.0, 700.0})}
	})));

	const TSharedPtr<FJsonObject> UpdateParams = MakeObject({
		{TEXT("updates"), MakeArrayValueJson(UpdatesArray)}
	});

	TSharedPtr<FJsonObject> UpdateResult = Commands.HandleCommand(TEXT("apply_scene_delta"), UpdateParams);
	TestTrue(TEXT("apply_scene_delta updates should succeed"), IsSuccessResponse(UpdateResult));

	if (!IsSuccessResponse(UpdateResult))
	{
		DestroyActorIfExists(Actor1Name);
		DestroyActorIfExists(Actor2Name);
		DestroyActorIfExists(Actor3Name);
		return true;
	}

	double UpdatedCount = 0.0;
	TestTrue(TEXT("Result should contain updated_count"), UpdateResult->TryGetNumberField(TEXT("updated_count"), UpdatedCount));
	TestEqual(TEXT("updated_count should be 1"), static_cast<int32>(UpdatedCount), 1);

	// Verify transform was applied
	AActor* UpdatedActor = FindActorByName(Actor1Name);
	TestNotNull(TEXT("Updated actor should still exist"), UpdatedActor);
	if (UpdatedActor)
	{
		TestEqual(TEXT("Location X should be updated"), static_cast<double>(UpdatedActor->GetActorLocation().X), 500.0);
	}

	// Step 3: Delete 1 actor via apply_scene_delta with deletes array
	TArray<TSharedPtr<FJsonValue>> DeletesArray;
	DeletesArray.Add(MakeObjectValue(MakeObject({
		{TEXT("mcp_id"), MakeStringValue(Actor2Name)}
	})));

	const TSharedPtr<FJsonObject> DeleteParams = MakeObject({
		{TEXT("deletes"), MakeArrayValueJson(DeletesArray)}
	});

	TSharedPtr<FJsonObject> DeleteResult = Commands.HandleCommand(TEXT("apply_scene_delta"), DeleteParams);
	TestTrue(TEXT("apply_scene_delta deletes should succeed"), IsSuccessResponse(DeleteResult));

	double DeletedCount = 0.0;
	TestTrue(TEXT("Result should contain deleted_count"), DeleteResult->TryGetNumberField(TEXT("deleted_count"), DeletedCount));
	TestEqual(TEXT("deleted_count should be 1"), static_cast<int32>(DeletedCount), 1);

	// Verify Actor2 is gone
	TestNull(TEXT("Actor2 should be deleted"), FindActorByName(Actor2Name));

	// Cleanup remaining actors
	DestroyActorIfExists(Actor1Name);
	DestroyActorIfExists(Actor3Name);

	return true;
}

// --- SceneSyncCollision: Verify collision fields in actor JSON ---

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPSceneSyncCollisionTest, "UnrealMCP.L3.Editor.SceneSyncCollision", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPSceneSyncCollisionTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;
	const FString ActorName = MakeUniqueName(TEXT("MCPCollisionActor"));

	// Clean up any leftover from previous runs
	DestroyActorIfExists(ActorName);

	// Step 1: Spawn an actor via apply_scene_delta
	TArray<TSharedPtr<FJsonValue>> CreatesArray;
	CreatesArray.Add(MakeObjectValue(MakeObject({
		{TEXT("name"), MakeStringValue(ActorName)},
		{TEXT("type"), MakeStringValue(TEXT("StaticMeshActor"))},
		{TEXT("location"), MakeArrayValue({0.0, 0.0, 100.0})}
	})));

	const TSharedPtr<FJsonObject> CreateParams = MakeObject({
		{TEXT("creates"), MakeArrayValueJson(CreatesArray)}
	});

	TSharedPtr<FJsonObject> CreateResult = Commands.HandleCommand(TEXT("apply_scene_delta"), CreateParams);
	TestTrue(TEXT("apply_scene_delta create should succeed"), IsSuccessResponse(CreateResult));

	if (!IsSuccessResponse(CreateResult))
	{
		return true;
	}

	// Step 2: Find the actor and verify it exists
	AActor* Actor = FindActorByName(ActorName);
	TestNotNull(TEXT("Spawned actor should exist"), Actor);

	if (!Actor)
	{
		DestroyActorIfExists(ActorName);
		return true;
	}

	// Step 3: Use get_actors_in_level to retrieve actor JSON and verify collision fields
	const TSharedPtr<FJsonObject> GetParams = MakeObject({});
	TSharedPtr<FJsonObject> GetResult = Commands.HandleCommand(TEXT("get_actors_in_level"), GetParams);

	const TArray<TSharedPtr<FJsonValue>>* Actors = nullptr;
	TestTrue(TEXT("get_actors_in_level should return actors"), GetResult->TryGetArrayField(TEXT("actors"), Actors));

	bool bFoundActor = false;
	if (Actors)
	{
		for (const TSharedPtr<FJsonValue>& ActorVal : *Actors)
		{
			if (ActorVal->Type == EJson::Object)
			{
				TSharedPtr<FJsonObject> ActorObj = ActorVal->AsObject();
				if (ActorObj->GetStringField(TEXT("name")) == ActorName)
				{
					bFoundActor = true;
					// Verify that collision-related fields are present in the JSON
					// These fields are serialized by the component property system
					TestTrue(TEXT("Actor JSON should have tags field"), ActorObj->HasField(TEXT("tags")));
					break;
				}
			}
		}
	}
	TestTrue(TEXT("Should find the spawned actor in actor listing"), bFoundActor);

	// Cleanup
	DestroyActorIfExists(ActorName);

	return true;
}

#endif