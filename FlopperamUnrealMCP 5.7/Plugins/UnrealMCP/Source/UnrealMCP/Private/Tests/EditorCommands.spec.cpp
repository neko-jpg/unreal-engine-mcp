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

#endif
