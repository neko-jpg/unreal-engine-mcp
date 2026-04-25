#if WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"

#include "Commands/EpicUnrealMCPEditorCommands.h"
#include "Dom/JsonObject.h"
#include "Tests/MCPAutomationTestUtils.h"

using namespace UnrealMCP::Tests;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPEditorActorLifecycleTest, "UnrealMCP.L3.Editor.ActorLifecycle", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPEditorActorLifecycleTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;
	const FString ActorName = MakeUniqueName(TEXT("MCPEditorActor"));

	DestroyActorIfExists(ActorName);

	const TSharedPtr<FJsonObject> SpawnParams = MakeObject({
		{TEXT("type"), MakeStringValue(TEXT("StaticMeshActor"))},
		{TEXT("name"), MakeStringValue(ActorName)},
		{TEXT("location"), MakeArrayValue({100.0, 200.0, 300.0})}
	});

	TSharedPtr<FJsonObject> SpawnResult = Commands.HandleCommand(TEXT("spawn_actor"), SpawnParams);
	TestTrue(TEXT("spawn_actor should succeed"), IsSuccessResponse(SpawnResult));
	TestNotNull(TEXT("Spawned actor should exist"), FindActorByName(ActorName));

	const TSharedPtr<FJsonObject> FindParams = MakeObject({
		{TEXT("pattern"), MakeStringValue(ActorName)}
	});
	TSharedPtr<FJsonObject> FindResult = Commands.HandleCommand(TEXT("find_actors_by_name"), FindParams);
	const TArray<TSharedPtr<FJsonValue>>* MatchingActors = nullptr;
	TestTrue(TEXT("find_actors_by_name should return the spawned actor"), FindResult->TryGetArrayField(TEXT("actors"), MatchingActors) && MatchingActors->Num() > 0);

	const TSharedPtr<FJsonObject> TransformParams = MakeObject({
		{TEXT("name"), MakeStringValue(ActorName)},
		{TEXT("location"), MakeArrayValue({400.0, 500.0, 600.0})},
		{TEXT("rotation"), MakeArrayValue({0.0, 45.0, 0.0})},
		{TEXT("scale"), MakeArrayValue({1.5, 2.0, 2.5})}
	});
	TSharedPtr<FJsonObject> TransformResult = Commands.HandleCommand(TEXT("set_actor_transform"), TransformParams);
	TestTrue(TEXT("set_actor_transform should succeed"), TransformResult.IsValid() && !TransformResult->HasField(TEXT("error")));

	AActor* Actor = FindActorByName(ActorName);
	TestNotNull(TEXT("Actor should still exist after transform"), Actor);
	if (Actor)
	{
		TestEqual(TEXT("Location X should be updated"), static_cast<double>(Actor->GetActorLocation().X), 400.0);
		TestEqual(TEXT("Location Y should be updated"), static_cast<double>(Actor->GetActorLocation().Y), 500.0);
		TestEqual(TEXT("Location Z should be updated"), static_cast<double>(Actor->GetActorLocation().Z), 600.0);
	}

	const TSharedPtr<FJsonObject> DuplicateResult = Commands.HandleCommand(TEXT("spawn_actor"), SpawnParams);
	TestFalse(TEXT("Duplicate actor name should be rejected"), IsSuccessResponse(DuplicateResult));
	TestTrue(TEXT("Duplicate actor error should mention existing name"), GetErrorMessage(DuplicateResult).Contains(TEXT("already exists")));

	const TSharedPtr<FJsonObject> DeleteParams = MakeObject({
		{TEXT("name"), MakeStringValue(ActorName)}
	});
	TSharedPtr<FJsonObject> DeleteResult = Commands.HandleCommand(TEXT("delete_actor"), DeleteParams);
	TestTrue(TEXT("delete_actor should succeed"), DeleteResult.IsValid() && DeleteResult->HasField(TEXT("deleted_actor")));
	TestNull(TEXT("Actor should be removed after delete"), FindActorByName(ActorName));

	const TSharedPtr<FJsonObject> MissingActorResult = Commands.HandleCommand(TEXT("delete_actor"), DeleteParams);
	TestFalse(TEXT("Deleting a missing actor should fail"), IsSuccessResponse(MissingActorResult));
	TestTrue(TEXT("Missing actor error should be reported"), GetErrorMessage(MissingActorResult).Contains(TEXT("Actor not found")));

	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPEditorMcpIdTest, "UnrealMCP.L3.Editor.McpId", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPEditorMcpIdTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;
	const FString ActorName = MakeUniqueName(TEXT("MCPMcpIdActor"));

	DestroyActorIfExists(ActorName);

	// Test spawn_actor with mcp_id and tags
	const TSharedPtr<FJsonObject> SpawnParams = MakeObject({
		{TEXT("type"), MakeStringValue(TEXT("StaticMeshActor"))},
		{TEXT("name"), MakeStringValue(ActorName)},
		{TEXT("mcp_id"), MakeStringValue(TEXT("test_cube_001"))},
		{TEXT("tags"), MakeArrayValue({MakeStringValue(TEXT("managed_by_mcp")), MakeStringValue(TEXT("scene:main"))})},
		{TEXT("location"), MakeArrayValue({0.0, 0.0, 100.0})}
	});

	TSharedPtr<FJsonObject> SpawnResult = Commands.HandleCommand(TEXT("spawn_actor"), SpawnParams);
	TestTrue(TEXT("spawn_actor with mcp_id should succeed"), IsSuccessResponse(SpawnResult));

	// Verify tags are present in the response
	const TArray<TSharedPtr<FJsonValue>>* TagsArray = nullptr;
	if (SpawnResult->TryGetArrayField(TEXT("tags"), TagsArray))
	{
		TestTrue(TEXT("Spawned actor should have tags"), TagsArray->Num() >= 2);
	}

	// Verify actor exists and has tags
	AActor* Actor = FindActorByName(ActorName);
	TestNotNull(TEXT("Spawned actor should exist"), Actor);
	if (Actor)
	{
		const FName ExpectedMcpIdTag(*FString::Printf(TEXT("mcp_id:%s"), TEXT("test_cube_001")));
		TestTrue(TEXT("Actor should have mcp_id tag"), Actor->Tags.Contains(ExpectedMcpIdTag));
		TestTrue(TEXT("Actor should have managed_by_mcp tag"), Actor->Tags.Contains(FName(TEXT("managed_by_mcp"))));
	}

	// Test find_actor_by_mcp_id
	const TSharedPtr<FJsonObject> FindMcpParams = MakeObject({
		{TEXT("mcp_id"), MakeStringValue(TEXT("test_cube_001"))}
	});
	TSharedPtr<FJsonObject> FindMcpResult = Commands.HandleCommand(TEXT("find_actor_by_mcp_id"), FindMcpParams);
	TestTrue(TEXT("find_actor_by_mcp_id should succeed"), FindMcpResult.IsValid() && FindMcpResult->GetBoolField(TEXT("success")));

	// Test set_actor_transform_by_mcp_id
	const TSharedPtr<FJsonObject> TransformMcpParams = MakeObject({
		{TEXT("mcp_id"), MakeStringValue(TEXT("test_cube_001"))},
		{TEXT("location"), MakeArrayValue({500.0, 0.0, 0.0})}
	});
	TSharedPtr<FJsonObject> TransformMcpResult = Commands.HandleCommand(TEXT("set_actor_transform_by_mcp_id"), TransformMcpParams);
	TestTrue(TEXT("set_actor_transform_by_mcp_id should succeed"), TransformMcpResult.IsValid() && !TransformMcpResult->HasField(TEXT("error")));

	// Verify transform was applied
	Actor = FindActorByName(ActorName);
	TestNotNull(TEXT("Actor should still exist after transform"), Actor);
	if (Actor)
	{
		TestEqual(TEXT("Location X should be updated by mcp_id"), static_cast<double>(Actor->GetActorLocation().X), 500.0);
	}

	// Test delete_actor_by_mcp_id
	const TSharedPtr<FJsonObject> DeleteMcpParams = MakeObject({
		{TEXT("mcp_id"), MakeStringValue(TEXT("test_cube_001"))}
	});
	TSharedPtr<FJsonObject> DeleteMcpResult = Commands.HandleCommand(TEXT("delete_actor_by_mcp_id"), DeleteMcpParams);
	TestTrue(TEXT("delete_actor_by_mcp_id should succeed"), DeleteMcpResult.IsValid());

	// Test idempotent delete (actor already gone)
	TSharedPtr<FJsonObject> DeleteMcpAgainResult = Commands.HandleCommand(TEXT("delete_actor_by_mcp_id"), DeleteMcpParams);
	TestTrue(TEXT("delete_actor_by_mcp_id should succeed on missing actor"), DeleteMcpAgainResult.IsValid());
	TestTrue(TEXT("Idempotent delete should report deleted=false"), DeleteMcpAgainResult->GetBoolField(TEXT("deleted")) == false);

	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPEditorGetActorsTagsTest, "UnrealMCP.L3.Editor.GetActorsTags", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPEditorGetActorsTagsTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPEditorCommands Commands;
	const FString ActorName = MakeUniqueName(TEXT("MCPTagActor"));

	DestroyActorIfExists(ActorName);

	// Spawn actor with mcp_id
	const TSharedPtr<FJsonObject> SpawnParams = MakeObject({
		{TEXT("type"), MakeStringValue(TEXT("StaticMeshActor"))},
		{TEXT("name"), MakeStringValue(ActorName)},
		{TEXT("mcp_id"), MakeStringValue(TEXT("tag_test_001"))},
		{TEXT("tags"), MakeArrayValue({MakeStringValue(TEXT("my_tag"))})}
	});

	Commands.HandleCommand(TEXT("spawn_actor"), SpawnParams);

	// Verify get_actors_in_level returns tags
	const TSharedPtr<FJsonObject> GetParams = MakeObject({});
	TSharedPtr<FJsonObject> GetResult = Commands.HandleCommand(TEXT("get_actors_in_level"), GetParams);
	const TArray<TSharedPtr<FJsonValue>>* Actors = nullptr;
	TestTrue(TEXT("get_actors_in_level should return actors"), GetResult->TryGetArrayField(TEXT("actors"), Actors));

	bool bFoundTaggedActor = false;
	if (Actors)
	{
		for (const TSharedPtr<FJsonValue>& ActorVal : *Actors)
		{
			if (ActorVal->Type == EJson::Object)
			{
				TSharedPtr<FJsonObject> ActorObj = ActorVal->AsObject();
				if (ActorObj->GetStringField(TEXT("name")) == ActorName)
				{
					bFoundTaggedActor = true;
					const TArray<TSharedPtr<FJsonValue>>* ActorTags = nullptr;
					TestTrue(TEXT("Actor should have tags field"), ActorObj->TryGetArrayField(TEXT("tags"), ActorTags));
					if (ActorTags)
					{
						TestTrue(TEXT("Actor should have at least 2 tags (managed_by_mcp + mcp_id)"), ActorTags->Num() >= 2);
					}
					break;
				}
			}
		}
	}
	TestTrue(TEXT("Should find the tagged actor in actor listing"), bFoundTaggedActor);

	// Clean up
	const TSharedPtr<FJsonObject> DeleteParams = MakeObject({
		{TEXT("name"), MakeStringValue(ActorName)}
	});
	Commands.HandleCommand(TEXT("delete_actor"), DeleteParams);

	return true;
}

#endif
