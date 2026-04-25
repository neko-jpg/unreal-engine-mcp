#pragma once

#include "CoreMinimal.h"

class AActor;
class UBlueprint;
class UEdGraph;
class UEdGraphNode;
class UStaticMeshComponent;
class UPrimitiveComponent;
class FJsonObject;

namespace UnrealMCP::Tests
{
	FString MakeUniqueName(const FString& Prefix);

	TSharedPtr<FJsonObject> MakeObject(std::initializer_list<TPair<FString, TSharedPtr<FJsonValue>>> Fields);
	TSharedPtr<FJsonValue> MakeStringValue(const FString& Value);
	TSharedPtr<FJsonValue> MakeBoolValue(bool bValue);
	TSharedPtr<FJsonValue> MakeNumberValue(double Value);
	TSharedPtr<FJsonValue> MakeArrayValue(std::initializer_list<double> Values);
	TSharedPtr<FJsonValue> MakeArrayValue(std::initializer_list<TSharedPtr<FJsonValue>> Values);
	TSharedPtr<FJsonValue> MakeObjectValue(const TSharedPtr<FJsonObject>& Value);

	bool IsSuccessResponse(const TSharedPtr<FJsonObject>& Response);
	FString GetErrorMessage(const TSharedPtr<FJsonObject>& Response);
	FString ReadEnvelopeStatus(const FString& SerializedResponse);
	FString ReadEnvelopeError(const FString& SerializedResponse);
	TSharedPtr<FJsonObject> ReadEnvelopeResult(const FString& SerializedResponse);

	UBlueprint* LoadBlueprintChecked(const FString& BlueprintName);
	void DeleteBlueprintIfExists(const FString& BlueprintName);

	AActor* FindActorByName(const FString& ActorName);
	void DestroyActorIfExists(const FString& ActorName);

	UEdGraph* FindFunctionGraphByName(UBlueprint* Blueprint, const FString& FunctionName);
	UEdGraphNode* FindNodeById(UEdGraph* Graph, const FString& NodeId);
	UEdGraphNode* FindNodeByGuid(UEdGraph* Graph, const FString& NodeId);
	UStaticMeshComponent* FindStaticMeshComponentByName(UBlueprint* Blueprint, const FString& ComponentName);
	UPrimitiveComponent* FindPrimitiveComponentByName(UBlueprint* Blueprint, const FString& ComponentName);
}
