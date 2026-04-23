#if WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"

#include "EpicUnrealMCPBridge.h"
#include "Tests/MCPAutomationTestUtils.h"

using namespace UnrealMCP::Tests;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPBridgeRoutingTest, "UnrealMCP.L3.Bridge.RoutingAndEnvelope", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPBridgeRoutingTest::RunTest(const FString& Parameters)
{
	UEpicUnrealMCPBridge* Bridge = NewObject<UEpicUnrealMCPBridge>();
	TestNotNull(TEXT("Bridge instance should be created"), Bridge);
	if (!Bridge)
	{
		return false;
	}

	const FString PingEnvelope = Bridge->ExecuteCommand(TEXT("ping"), MakeObject({}));
	TestEqual(TEXT("ping should return a success envelope"), ReadEnvelopeStatus(PingEnvelope), FString(TEXT("success")));

	const FString UnknownEnvelope = Bridge->ExecuteCommand(TEXT("totally_unknown_command"), MakeObject({}));
	TestEqual(TEXT("Unknown command should return an error envelope"), ReadEnvelopeStatus(UnknownEnvelope), FString(TEXT("error")));
	TestTrue(TEXT("Unknown command should mention the command name"), ReadEnvelopeError(UnknownEnvelope).Contains(TEXT("totally_unknown_command")));

	const FString ActorName = MakeUniqueName(TEXT("MCPBridgeActor"));
	DestroyActorIfExists(ActorName);

	const FString SpawnEnvelope = Bridge->ExecuteCommand(TEXT("spawn_actor"), MakeObject({
		{TEXT("type"), MakeStringValue(TEXT("StaticMeshActor"))},
		{TEXT("name"), MakeStringValue(ActorName)}
	}));
	TestEqual(TEXT("spawn_actor should be routed successfully"), ReadEnvelopeStatus(SpawnEnvelope), FString(TEXT("success")));
	TestNotNull(TEXT("Actor should be spawned through the bridge"), FindActorByName(ActorName));

	Bridge->ExecuteCommand(TEXT("delete_actor"), MakeObject({
		{TEXT("name"), MakeStringValue(ActorName)}
	}));

	return true;
}

#endif
