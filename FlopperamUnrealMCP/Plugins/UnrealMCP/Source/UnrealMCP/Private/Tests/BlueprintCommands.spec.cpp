#if WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"

#include "Commands/EpicUnrealMCPBlueprintCommands.h"
#include "Engine/Blueprint.h"
#include "Tests/MCPAutomationTestUtils.h"

using namespace UnrealMCP::Tests;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPBlueprintCommandsTest, "UnrealMCP.L3.Blueprint.CreateComponentCompile", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPBlueprintCommandsTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPBlueprintCommands Commands;
	const FString BlueprintName = MakeUniqueName(TEXT("MCPBlueprint"));
	const FString ComponentName = TEXT("MeshComponent");

	DeleteBlueprintIfExists(BlueprintName);

	const TSharedPtr<FJsonObject> CreateParams = MakeObject({
		{TEXT("name"), MakeStringValue(BlueprintName)},
		{TEXT("parent_class"), MakeStringValue(TEXT("Actor"))}
	});
	TSharedPtr<FJsonObject> CreateResult = Commands.HandleCommand(TEXT("create_blueprint"), CreateParams);
	TestTrue(TEXT("create_blueprint should succeed"), IsSuccessResponse(CreateResult));

	const TSharedPtr<FJsonObject> AddComponentParams = MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)},
		{TEXT("component_type"), MakeStringValue(TEXT("StaticMeshComponent"))},
		{TEXT("component_name"), MakeStringValue(ComponentName)}
	});
	TSharedPtr<FJsonObject> AddComponentResult = Commands.HandleCommand(TEXT("add_component_to_blueprint"), AddComponentParams);
	TestTrue(TEXT("add_component_to_blueprint should succeed"), IsSuccessResponse(AddComponentResult));

	const TSharedPtr<FJsonObject> PhysicsParams = MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)},
		{TEXT("component_name"), MakeStringValue(ComponentName)},
		{TEXT("simulate_physics"), MakeBoolValue(true)},
		{TEXT("mass"), MakeNumberValue(125.0)},
		{TEXT("linear_damping"), MakeNumberValue(1.5)},
		{TEXT("angular_damping"), MakeNumberValue(2.0)}
	});
	TSharedPtr<FJsonObject> PhysicsResult = Commands.HandleCommand(TEXT("set_physics_properties"), PhysicsParams);
	TestTrue(TEXT("set_physics_properties should succeed"), IsSuccessResponse(PhysicsResult));

	const TSharedPtr<FJsonObject> CompileParams = MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)}
	});
	TSharedPtr<FJsonObject> CompileResult = Commands.HandleCommand(TEXT("compile_blueprint"), CompileParams);
	TestTrue(TEXT("compile_blueprint should succeed"), IsSuccessResponse(CompileResult));

	UBlueprint* Blueprint = LoadBlueprintChecked(BlueprintName);
	TestNotNull(TEXT("Blueprint should be loadable after creation"), Blueprint);

	UPrimitiveComponent* PrimitiveComponent = FindPrimitiveComponentByName(Blueprint, ComponentName);
	TestNotNull(TEXT("Component should be present in the Blueprint"), PrimitiveComponent);
	if (PrimitiveComponent)
	{
		TestTrue(TEXT("Physics simulation should be enabled"), PrimitiveComponent->BodyInstance.bSimulatePhysics);
		TestEqual(TEXT("Linear damping should match"), PrimitiveComponent->GetLinearDamping(), 1.5f);
		TestEqual(TEXT("Angular damping should match"), PrimitiveComponent->GetAngularDamping(), 2.0f);
	}

	const TSharedPtr<FJsonObject> ReadParams = MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)}
	});
	TSharedPtr<FJsonObject> ReadResult = Commands.HandleCommand(TEXT("read_blueprint_content"), ReadParams);
	TestTrue(TEXT("read_blueprint_content should succeed"), IsSuccessResponse(ReadResult));

	DeleteBlueprintIfExists(BlueprintName);
	return true;
}

#endif
