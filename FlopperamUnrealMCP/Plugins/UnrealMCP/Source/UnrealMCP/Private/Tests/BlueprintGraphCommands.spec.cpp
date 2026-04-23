#if WITH_DEV_AUTOMATION_TESTS

#include "Misc/AutomationTest.h"

#include "Commands/EpicUnrealMCPBlueprintCommands.h"
#include "Commands/EpicUnrealMCPBlueprintGraphCommands.h"
#include "Engine/Blueprint.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "K2Node_Event.h"
#include "K2Node_CallFunction.h"
#include "Tests/MCPAutomationTestUtils.h"

using namespace UnrealMCP::Tests;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FUnrealMCPBlueprintGraphCommandsTest, "UnrealMCP.L3.BlueprintGraph.VariableFunctionNodeFlow", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUnrealMCPBlueprintGraphCommandsTest::RunTest(const FString& Parameters)
{
	FEpicUnrealMCPBlueprintCommands BlueprintCommands;
	FEpicUnrealMCPBlueprintGraphCommands GraphCommands;
	const FString BlueprintName = MakeUniqueName(TEXT("MCPGraph"));
	const FString VariableName = TEXT("Health");
	const FString FunctionName = TEXT("ApplyDamage");

	DeleteBlueprintIfExists(BlueprintName);
	BlueprintCommands.HandleCommand(TEXT("create_blueprint"), MakeObject({
		{TEXT("name"), MakeStringValue(BlueprintName)}
	}));

	TSharedPtr<FJsonObject> CreateVariableResult = GraphCommands.HandleCommand(TEXT("create_variable"), MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)},
		{TEXT("variable_name"), MakeStringValue(VariableName)},
		{TEXT("variable_type"), MakeStringValue(TEXT("float"))},
		{TEXT("default_value"), MakeNumberValue(100.0)}
	}));
	TestTrue(TEXT("create_variable should succeed"), IsSuccessResponse(CreateVariableResult));

	TSharedPtr<FJsonObject> SetVariableResult = GraphCommands.HandleCommand(TEXT("set_blueprint_variable_properties"), MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)},
		{TEXT("variable_name"), MakeStringValue(VariableName)},
		{TEXT("is_blueprint_writable"), MakeBoolValue(true)},
		{TEXT("tooltip"), MakeStringValue(TEXT("Health pool"))}
	}));
	TestTrue(TEXT("set_blueprint_variable_properties should succeed"), IsSuccessResponse(SetVariableResult));

	TSharedPtr<FJsonObject> CreateFunctionResult = GraphCommands.HandleCommand(TEXT("create_function"), MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)},
		{TEXT("function_name"), MakeStringValue(FunctionName)}
	}));
	TestTrue(TEXT("create_function should succeed"), IsSuccessResponse(CreateFunctionResult));

	TSharedPtr<FJsonObject> AddInputResult = GraphCommands.HandleCommand(TEXT("add_function_input"), MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)},
		{TEXT("function_name"), MakeStringValue(FunctionName)},
		{TEXT("param_name"), MakeStringValue(TEXT("DamageAmount"))},
		{TEXT("param_type"), MakeStringValue(TEXT("float"))}
	}));
	TestTrue(TEXT("add_function_input should succeed"), IsSuccessResponse(AddInputResult));

	TSharedPtr<FJsonObject> EventResult = GraphCommands.HandleCommand(TEXT("add_event_node"), MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)},
		{TEXT("event_name"), MakeStringValue(TEXT("ReceiveBeginPlay"))}
	}));
	TestTrue(TEXT("add_event_node should succeed"), IsSuccessResponse(EventResult));

	TSharedPtr<FJsonObject> PrintResult = GraphCommands.HandleCommand(TEXT("add_blueprint_node"), MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)},
		{TEXT("node_type"), MakeStringValue(TEXT("Print"))},
		{TEXT("node_params"), MakeObjectValue(MakeObject({
			{TEXT("message"), MakeStringValue(TEXT("Boot"))},
			{TEXT("pos_x"), MakeNumberValue(300.0)},
			{TEXT("pos_y"), MakeNumberValue(0.0)}
		}))}
	}));
	TestTrue(TEXT("add_blueprint_node should succeed"), IsSuccessResponse(PrintResult));

	FString EventNodeId;
	FString PrintNodeId;
	EventResult->TryGetStringField(TEXT("node_id"), EventNodeId);
	PrintResult->TryGetStringField(TEXT("node_id"), PrintNodeId);
	TestFalse(TEXT("Event node id should be returned"), EventNodeId.IsEmpty());
	TestFalse(TEXT("Print node id should be returned"), PrintNodeId.IsEmpty());

	TSharedPtr<FJsonObject> ConnectResult = GraphCommands.HandleCommand(TEXT("connect_nodes"), MakeObject({
		{TEXT("blueprint_name"), MakeStringValue(BlueprintName)},
		{TEXT("source_node_id"), MakeStringValue(EventNodeId)},
		{TEXT("source_pin_name"), MakeStringValue(TEXT("then"))},
		{TEXT("target_node_id"), MakeStringValue(PrintNodeId)},
		{TEXT("target_pin_name"), MakeStringValue(TEXT("execute"))}
	}));
	TestTrue(TEXT("connect_nodes should succeed"), IsSuccessResponse(ConnectResult));

	UBlueprint* Blueprint = LoadBlueprintChecked(BlueprintName);
	TestNotNull(TEXT("Blueprint should load for graph assertions"), Blueprint);

	if (Blueprint)
	{
		UEdGraph* EventGraph = Blueprint->UbergraphPages.Num() > 0 ? Blueprint->UbergraphPages[0] : nullptr;
		TestNotNull(TEXT("Event graph should exist"), EventGraph);
		if (EventGraph)
		{
			UEdGraphNode* EventNode = FindNodeById(EventGraph, EventNodeId);
			UEdGraphNode* PrintNode = FindNodeById(EventGraph, PrintNodeId);
			TestNotNull(TEXT("Event node should exist in graph"), EventNode);
			TestNotNull(TEXT("Print node should exist in graph"), PrintNode);
			if (EventNode && PrintNode)
			{
				UEdGraphPin* ThenPin = EventNode->FindPin(TEXT("then"));
				UEdGraphPin* ExecutePin = PrintNode->FindPin(TEXT("execute"));
				TestTrue(TEXT("Execution pins should be linked"), ThenPin && ExecutePin && ThenPin->LinkedTo.Contains(ExecutePin));
			}
		}

		UEdGraph* FunctionGraph = FindFunctionGraphByName(Blueprint, FunctionName);
		TestNotNull(TEXT("Function graph should exist after create_function"), FunctionGraph);
		TestTrue(TEXT("Blueprint should contain the created variable"), Blueprint->NewVariables.ContainsByPredicate([&VariableName](const FBPVariableDescription& Variable)
		{
			return Variable.VarName == FName(*VariableName);
		}));
	}

	DeleteBlueprintIfExists(BlueprintName);
	return true;
}

#endif
