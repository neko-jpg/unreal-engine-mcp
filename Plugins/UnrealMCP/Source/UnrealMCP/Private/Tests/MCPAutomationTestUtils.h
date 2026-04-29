#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

class AActor;
class UBlueprint;
class UEdGraph;
class UEdGraphNode;
class UStaticMeshComponent;
class UPrimitiveComponent;

namespace UnrealMCP::Tests
{
	FString MakeUniqueName(const FString& Prefix);

	inline TSharedPtr<FJsonObject> MakeObject(std::initializer_list<TPair<FString, TSharedPtr<FJsonValue>>> Fields)
	{
		TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
		for (const TPair<FString, TSharedPtr<FJsonValue>>& Field : Fields)
		{
			Result->SetField(Field.Key, Field.Value);
		}
		return Result;
	}

	inline TSharedPtr<FJsonValue> MakeStringValue(const FString& Value)
	{
		return MakeShared<FJsonValueString>(Value);
	}

	inline TSharedPtr<FJsonValue> MakeBoolValue(bool bValue)
	{
		return MakeShared<FJsonValueBoolean>(bValue);
	}

	inline TSharedPtr<FJsonValue> MakeNumberValue(double Value)
	{
		return MakeShared<FJsonValueNumber>(Value);
	}

	inline TSharedPtr<FJsonValue> MakeArrayValue(std::initializer_list<double> Values)
	{
		TArray<TSharedPtr<FJsonValue>> Array;
		for (double V : Values)
		{
			Array.Add(MakeNumberValue(V));
		}
		return MakeShared<FJsonValueArray>(Array);
	}

	TSharedPtr<FJsonValue> MakeArrayValue(std::initializer_list<TSharedPtr<FJsonValue>> Values);

	inline TSharedPtr<FJsonValue> MakeArrayValueJson(std::initializer_list<TSharedPtr<FJsonValue>> Values)
	{
		return MakeArrayValue(Values);
	}

	inline TSharedPtr<FJsonValue> MakeArrayValueJson(const TArray<TSharedPtr<FJsonValue>>& Values)
	{
		return MakeShared<FJsonValueArray>(Values);
	}

	inline TSharedPtr<FJsonValue> MakeObjectValue(const TSharedPtr<FJsonObject>& Value)
	{
		return MakeShared<FJsonValueObject>(Value);
	}

	inline bool IsSuccessResponse(const TSharedPtr<FJsonObject>& Response)
	{
		if (!Response.IsValid())
		{
			return false;
		}

		bool bSuccess = false;
		if (Response->TryGetBoolField(TEXT("success"), bSuccess))
		{
			return bSuccess;
		}

		return !Response->HasField(TEXT("error"));
	}

	inline FString GetErrorMessage(const TSharedPtr<FJsonObject>& Response)
	{
		if (!Response.IsValid())
		{
			return TEXT("Invalid response");
		}

		FString ErrorMessage;
		Response->TryGetStringField(TEXT("error"), ErrorMessage);
		return ErrorMessage;
	}

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
