#include "Tests/MCPAutomationTestUtils.h"

#include "Commands/EpicUnrealMCPCommonUtils.h"
#include "EditorAssetLibrary.h"
#include "Engine/Blueprint.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"

namespace UnrealMCP::Tests
{
	FString MakeUniqueName(const FString& Prefix)
	{
		return FString::Printf(TEXT("%s_%s"), *Prefix, *FGuid::NewGuid().ToString(EGuidFormats::Digits));
	}

	TSharedPtr<FJsonValue> MakeArrayValue(std::initializer_list<TSharedPtr<FJsonValue>> Values)
	{
		TArray<TSharedPtr<FJsonValue>> Array;
		for (const TSharedPtr<FJsonValue>& V : Values)
		{
			Array.Add(V);
		}
		return MakeShared<FJsonValueArray>(Array);
	}

	static TSharedPtr<FJsonObject> ParseEnvelope(const FString& SerializedResponse)
	{
		TSharedPtr<FJsonObject> Envelope;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(SerializedResponse);
		if (!FJsonSerializer::Deserialize(Reader, Envelope) || !Envelope.IsValid())
		{
			return nullptr;
		}
		return Envelope;
	}

	FString ReadEnvelopeStatus(const FString& SerializedResponse)
	{
		const TSharedPtr<FJsonObject> Envelope = ParseEnvelope(SerializedResponse);
		if (!Envelope.IsValid())
		{
			return TEXT("");
		}

		FString Status;
		Envelope->TryGetStringField(TEXT("status"), Status);
		return Status;
	}

	FString ReadEnvelopeError(const FString& SerializedResponse)
	{
		const TSharedPtr<FJsonObject> Envelope = ParseEnvelope(SerializedResponse);
		if (!Envelope.IsValid())
		{
			return TEXT("");
		}

		FString ErrorMessage;
		Envelope->TryGetStringField(TEXT("error"), ErrorMessage);
		return ErrorMessage;
	}

	TSharedPtr<FJsonObject> ReadEnvelopeResult(const FString& SerializedResponse)
	{
		const TSharedPtr<FJsonObject> Envelope = ParseEnvelope(SerializedResponse);
		if (!Envelope.IsValid())
		{
			return nullptr;
		}

		const TSharedPtr<FJsonObject>* ResultObject = nullptr;
		return Envelope->TryGetObjectField(TEXT("result"), ResultObject) ? *ResultObject : nullptr;
	}

	UBlueprint* LoadBlueprintChecked(const FString& BlueprintName)
	{
		return FEpicUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
	}

	void DeleteBlueprintIfExists(const FString& BlueprintName)
	{
		const FString AssetPath = FString::Printf(TEXT("/Game/Blueprints/%s"), *BlueprintName);
		if (UEditorAssetLibrary::DoesAssetExist(AssetPath))
		{
			UEditorAssetLibrary::DeleteAsset(AssetPath);
		}
	}

	AActor* FindActorByName(const FString& ActorName)
	{
		UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
		if (!World)
		{
			return nullptr;
		}

		TArray<AActor*> Actors;
		UGameplayStatics::GetAllActorsOfClass(World, AActor::StaticClass(), Actors);
		for (AActor* Actor : Actors)
		{
			if (Actor && Actor->GetName() == ActorName)
			{
				return Actor;
			}
		}

		return nullptr;
	}

	void DestroyActorIfExists(const FString& ActorName)
	{
		if (AActor* Actor = FindActorByName(ActorName))
		{
			Actor->Destroy();
		}
	}

	UEdGraph* FindFunctionGraphByName(UBlueprint* Blueprint, const FString& FunctionName)
	{
		if (!Blueprint)
		{
			return nullptr;
		}

		for (UEdGraph* Graph : Blueprint->FunctionGraphs)
		{
			if (Graph && Graph->GetName().Contains(FunctionName))
			{
				return Graph;
			}
		}

		return nullptr;
	}

	UEdGraphNode* FindNodeByGuid(UEdGraph* Graph, const FString& NodeId)
	{
		if (!Graph)
		{
			return nullptr;
		}

		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (Node && Node->NodeGuid.ToString().Equals(NodeId, ESearchCase::IgnoreCase))
			{
				return Node;
			}
		}

		return nullptr;
	}

	UEdGraphNode* FindNodeById(UEdGraph* Graph, const FString& NodeId)
	{
		if (UEdGraphNode* Node = FindNodeByGuid(Graph, NodeId))
		{
			return Node;
		}

		if (!Graph)
		{
			return nullptr;
		}

		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (Node && Node->GetName().Equals(NodeId, ESearchCase::IgnoreCase))
			{
				return Node;
			}
		}

		return nullptr;
	}

	UStaticMeshComponent* FindStaticMeshComponentByName(UBlueprint* Blueprint, const FString& ComponentName)
	{
		if (!Blueprint || !Blueprint->SimpleConstructionScript)
		{
			return nullptr;
		}

		for (USCS_Node* Node : Blueprint->SimpleConstructionScript->GetAllNodes())
		{
			if (Node && Node->GetVariableName().ToString() == ComponentName)
			{
				return Cast<UStaticMeshComponent>(Node->ComponentTemplate);
			}
		}

		return nullptr;
	}

	UPrimitiveComponent* FindPrimitiveComponentByName(UBlueprint* Blueprint, const FString& ComponentName)
	{
		if (!Blueprint || !Blueprint->SimpleConstructionScript)
		{
			return nullptr;
		}

		for (USCS_Node* Node : Blueprint->SimpleConstructionScript->GetAllNodes())
		{
			if (Node && Node->GetVariableName().ToString() == ComponentName)
			{
				return Cast<UPrimitiveComponent>(Node->ComponentTemplate);
			}
		}

		return nullptr;
	}
}
