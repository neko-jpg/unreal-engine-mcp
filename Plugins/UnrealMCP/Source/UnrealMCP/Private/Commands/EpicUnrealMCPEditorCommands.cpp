#include "Commands/EpicUnrealMCPEditorCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"
#include "EpicUnrealMCPBridge.h"
#include "Editor.h"
#include "EditorViewportClient.h"
#include "LevelEditorViewport.h"
#include "ImageUtils.h"
#include "HighResScreenshot.h"
#include "Engine/GameViewportClient.h"
#include "Misc/FileHelper.h"
#include "GameFramework/Actor.h"
#include "Engine/Selection.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Camera/CameraActor.h"
#include "Components/StaticMeshComponent.h"
#include "EditorSubsystem.h"
#include "Subsystems/EditorActorSubsystem.h"
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "EditorAssetLibrary.h"
#include "ScopedTransaction.h"

FEpicUnrealMCPEditorCommands::FEpicUnrealMCPEditorCommands()
{
}

static FActorIndex& GetActorIndex()
{
    UEpicUnrealMCPBridge* Bridge = GEditor->GetEditorSubsystem<UEpicUnrealMCPBridge>();
    check(Bridge);
    return Bridge->ActorIndex;
}

UWorld* FEpicUnrealMCPEditorCommands::GetEditorWorld() const
{
    if (!GEditor)
    {
        return nullptr;
    }
    return GEditor->GetEditorWorldContext().World();
}

TSharedPtr<FJsonObject> FEpicUnrealMCPEditorCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPEditorCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("get_actors_in_level"), &FEpicUnrealMCPEditorCommands::HandleGetActorsInLevel},
        {TEXT("find_actors_by_name"), &FEpicUnrealMCPEditorCommands::HandleFindActorsByName},
        {TEXT("spawn_actor"), &FEpicUnrealMCPEditorCommands::HandleSpawnActor},
        {TEXT("delete_actor"), &FEpicUnrealMCPEditorCommands::HandleDeleteActor},
        {TEXT("set_actor_transform"), &FEpicUnrealMCPEditorCommands::HandleSetActorTransform},
        {TEXT("find_actor_by_mcp_id"), &FEpicUnrealMCPEditorCommands::HandleFindActorByMcpId},
        {TEXT("set_actor_transform_by_mcp_id"), &FEpicUnrealMCPEditorCommands::HandleSetActorTransformByMcpId},
        {TEXT("delete_actor_by_mcp_id"), &FEpicUnrealMCPEditorCommands::HandleDeleteActorByMcpId},
    };

    const Handler* H = Dispatch.Find(CommandType);
    if (H)
    {
        return (this->*(*H))(Params);
    }

    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown editor command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FEpicUnrealMCPEditorCommands::HandleGetActorsInLevel(const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(World, AActor::StaticClass(), AllActors);
    
    TArray<TSharedPtr<FJsonValue>> ActorArray;
    for (AActor* Actor : AllActors)
    {
        if (Actor)
        {
            ActorArray.Add(FEpicUnrealMCPCommonUtils::ActorToJson(Actor));
        }
    }
    
    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetArrayField(TEXT("actors"), ActorArray);
    
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPEditorCommands::HandleFindActorsByName(const TSharedPtr<FJsonObject>& Params)
{
    FString Pattern;
    if (!Params->TryGetStringField(TEXT("pattern"), Pattern))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'pattern' parameter"));
    }
    
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(World, AActor::StaticClass(), AllActors);
    
    TArray<TSharedPtr<FJsonValue>> MatchingActors;
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName().Contains(Pattern, ESearchCase::IgnoreCase))
        {
            MatchingActors.Add(FEpicUnrealMCPCommonUtils::ActorToJson(Actor));
        }
    }
    
    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetArrayField(TEXT("actors"), MatchingActors);
    
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPEditorCommands::HandleSpawnActor(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString ActorType;
    if (!Params->TryGetStringField(TEXT("type"), ActorType))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'type' parameter"));
    }

    // Get actor name (required parameter)
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Get optional transform parameters
    FVector Location(0.0f, 0.0f, 0.0f);
    FRotator Rotation(0.0f, 0.0f, 0.0f);
    FVector Scale(1.0f, 1.0f, 1.0f);
    FString ParamError;

    if (Params->HasField(TEXT("location")))
    {
        if (!FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Params, TEXT("location"), Location, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'location': %s"), *ParamError));
        }
    }
    if (Params->HasField(TEXT("rotation")))
    {
        if (!FEpicUnrealMCPCommonUtils::TryGetRotatorFromJson(Params, TEXT("rotation"), Rotation, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'rotation': %s"), *ParamError));
        }
    }
    if (Params->HasField(TEXT("scale")))
    {
        if (!FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Params, TEXT("scale"), Scale, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'scale': %s"), *ParamError));
        }
    }

    // Create the actor based on type
    AActor* NewActor = nullptr;
    UWorld* World = GEditor->GetEditorWorldContext().World();

    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // Check if an actor with this name already exists (O(1) via index)
    if (GetActorIndex().FindByName(FName(*ActorName)))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor with name '%s' already exists"), *ActorName));
    }

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Spawn Actor")));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = *ActorName;

    if (ActorType == TEXT("StaticMeshActor"))
    {
        AStaticMeshActor* NewMeshActor = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), Location, Rotation, SpawnParams);
        if (NewMeshActor)
        {
            // Check for an optional static_mesh parameter to assign a mesh
            FString MeshPath;
            if (Params->TryGetStringField(TEXT("static_mesh"), MeshPath))
            {
                UStaticMesh* Mesh = Cast<UStaticMesh>(UEditorAssetLibrary::LoadAsset(MeshPath));
                if (Mesh)
                {
                    NewMeshActor->GetStaticMeshComponent()->SetStaticMesh(Mesh);
                }
                else
                {
                    UE_LOG(LogTemp, Warning, TEXT("Could not find static mesh at path: %s"), *MeshPath);
                }
            }
        }
        NewActor = NewMeshActor;
    }
    else if (ActorType == TEXT("PointLight"))
    {
        NewActor = World->SpawnActor<APointLight>(APointLight::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorType == TEXT("SpotLight"))
    {
        NewActor = World->SpawnActor<ASpotLight>(ASpotLight::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorType == TEXT("DirectionalLight"))
    {
        NewActor = World->SpawnActor<ADirectionalLight>(ADirectionalLight::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorType == TEXT("CameraActor"))
    {
        NewActor = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), Location, Rotation, SpawnParams);
    }
    else
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown actor type: %s"), *ActorType));
    }

    if (NewActor)
    {
        // Set scale (since SpawnActor only takes location and rotation)
        FTransform Transform = NewActor->GetTransform();
        Transform.SetScale3D(Scale);
        NewActor->SetActorTransform(Transform);

        // Apply mcp_id tag if provided
        FString McpId;
        if (Params->TryGetStringField(TEXT("mcp_id"), McpId) && !McpId.IsEmpty())
        {
            NewActor->Tags.AddUnique(FName(TEXT("managed_by_mcp")));
            NewActor->Tags.AddUnique(FName(*FString::Printf(TEXT("mcp_id:%s"), *McpId)));
        }

        // Apply additional tags if provided
        if (Params->HasField(TEXT("tags")))
        {
            const TArray<TSharedPtr<FJsonValue>>* TagsJsonArray;
            if (Params->TryGetArrayField(TEXT("tags"), TagsJsonArray))
            {
                for (const TSharedPtr<FJsonValue>& TagValue : *TagsJsonArray)
                {
                    if (TagValue->Type == EJson::String)
                    {
                        FString TagStr = TagValue->AsString();
                        if (!TagStr.IsEmpty())
                        {
                            NewActor->Tags.AddUnique(FName(*TagStr));
                        }
                    }
                }
            }
        }

        // Add to index for O(1) lookup
        GetActorIndex().AddActor(NewActor);

        // Return the created actor's details
        return FEpicUnrealMCPCommonUtils::ActorToJsonObject(NewActor, true);
    }

    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create actor"));
}

TSharedPtr<FJsonObject> FEpicUnrealMCPEditorCommands::HandleDeleteActor(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    AActor* Actor = GetActorIndex().FindByName(FName(*ActorName));
    if (!Actor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    TSharedPtr<FJsonObject> ActorInfo = FEpicUnrealMCPCommonUtils::ActorToJsonObject(Actor);
    GetActorIndex().RemoveActor(Actor);

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Delete Actor")));
    Actor->Modify();
    Actor->Destroy();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetObjectField(TEXT("deleted_actor"), ActorInfo);
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPEditorCommands::HandleSetActorTransform(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    AActor* TargetActor = GetActorIndex().FindByName(FName(*ActorName));
    if (!TargetActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    // Get transform parameters
    FTransform NewTransform = TargetActor->GetTransform();

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Set Actor Transform")));
    TargetActor->Modify();

    FString ParamError;

    if (Params->HasField(TEXT("location")))
    {
        FVector NewLocation;
        if (!FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Params, TEXT("location"), NewLocation, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'location': %s"), *ParamError));
        }
        NewTransform.SetLocation(NewLocation);
    }
    if (Params->HasField(TEXT("rotation")))
    {
        FRotator NewRotation;
        if (!FEpicUnrealMCPCommonUtils::TryGetRotatorFromJson(Params, TEXT("rotation"), NewRotation, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'rotation': %s"), *ParamError));
        }
        NewTransform.SetRotation(FQuat(NewRotation));
    }
    if (Params->HasField(TEXT("scale")))
    {
        FVector NewScale;
        if (!FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Params, TEXT("scale"), NewScale, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'scale': %s"), *ParamError));
        }
        NewTransform.SetScale3D(NewScale);
    }

    // Set the new transform
    TargetActor->SetActorTransform(NewTransform);

    // Return updated actor info
    return FEpicUnrealMCPCommonUtils::ActorToJsonObject(TargetActor, true);
}

AActor* FEpicUnrealMCPEditorCommands::FindActorByMcpId(UWorld* World, const FString& McpId) const
{
    if (!World || McpId.IsEmpty())
    {
        return nullptr;
    }

    AActor* FoundActor = GetActorIndex().FindByMcpId(McpId);
    if (FoundActor)
    {
        return FoundActor;
    }

    // Fallback: linear scan for actors not yet in the index
    const FName TargetTag(*FString::Printf(TEXT("mcp_id:%s"), *McpId));
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(World, AActor::StaticClass(), AllActors);

    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->Tags.Contains(TargetTag))
        {
            if (FoundActor)
            {
                UE_LOG(LogTemp, Warning, TEXT("FindActorByMcpId: Multiple actors found with mcp_id '%s'"), *McpId);
                return FoundActor; // Return first found
            }
            FoundActor = Actor;
        }
    }

    return FoundActor;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPEditorCommands::HandleFindActorByMcpId(const TSharedPtr<FJsonObject>& Params)
{
    FString McpId;
    if (!Params->TryGetStringField(TEXT("mcp_id"), McpId) || McpId.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'mcp_id' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // O(1) lookup via index
    AActor* FoundActor = GetActorIndex().FindByMcpId(McpId);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    if (!FoundActor)
    {
        ResultObj->SetBoolField(TEXT("success"), true);
        ResultObj->SetStringField(TEXT("message"), TEXT("No actor found with the given mcp_id"));
        ResultObj->SetObjectField(TEXT("actor"), nullptr);
    }
    else
    {
        ResultObj->SetBoolField(TEXT("success"), true);
        TSharedPtr<FJsonValue> ActorJsonValue = FEpicUnrealMCPCommonUtils::ActorToJson(FoundActor);
        if (ActorJsonValue.IsValid() && ActorJsonValue->Type == EJson::Object)
        {
            ResultObj->SetObjectField(TEXT("actor"), ActorJsonValue->AsObject());
        }
    }
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPEditorCommands::HandleSetActorTransformByMcpId(const TSharedPtr<FJsonObject>& Params)
{
    FString McpId;
    if (!Params->TryGetStringField(TEXT("mcp_id"), McpId) || McpId.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'mcp_id' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    AActor* TargetActor = FindActorByMcpId(World, McpId);
    if (!TargetActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor with mcp_id '%s' not found"), *McpId));
    }

    FTransform NewTransform = TargetActor->GetTransform();

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Set Actor Transform By McpId")));
    TargetActor->Modify();

    FString ParamError;

    if (Params->HasField(TEXT("location")))
    {
        FVector NewLocation;
        if (!FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Params, TEXT("location"), NewLocation, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'location': %s"), *ParamError));
        }
        NewTransform.SetLocation(NewLocation);
    }
    if (Params->HasField(TEXT("rotation")))
    {
        FRotator NewRotation;
        if (!FEpicUnrealMCPCommonUtils::TryGetRotatorFromJson(Params, TEXT("rotation"), NewRotation, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'rotation': %s"), *ParamError));
        }
        NewTransform.SetRotation(FQuat(NewRotation));
    }
    if (Params->HasField(TEXT("scale")))
    {
        FVector NewScale;
        if (!FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(Params, TEXT("scale"), NewScale, ParamError))
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Invalid 'scale': %s"), *ParamError));
        }
        NewTransform.SetScale3D(NewScale);
    }

    TargetActor->SetActorTransform(NewTransform);

    return FEpicUnrealMCPCommonUtils::ActorToJsonObject(TargetActor, true);
}

TSharedPtr<FJsonObject> FEpicUnrealMCPEditorCommands::HandleDeleteActorByMcpId(const TSharedPtr<FJsonObject>& Params)
{
    FString McpId;
    if (!Params->TryGetStringField(TEXT("mcp_id"), McpId) || McpId.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'mcp_id' parameter"));
    }

    AActor* Actor = GetActorIndex().FindByMcpId(McpId);

    if (!Actor)
    {
        // Fallback linear scan for actors not in the index
        UWorld* World = GetEditorWorld();
        if (!World)
        {
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
        }
        const FName TargetTag(*FString::Printf(TEXT("mcp_id:%s"), *McpId));
        TArray<AActor*> AllActors;
        UGameplayStatics::GetAllActorsOfClass(World, AActor::StaticClass(), AllActors);
        for (AActor* A : AllActors)
        {
            if (A && A->Tags.Contains(TargetTag))
            {
                Actor = A;
                break;
            }
        }
    }

    if (!Actor)
    {
        TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
        ResultObj->SetBoolField(TEXT("success"), true);
        ResultObj->SetStringField(TEXT("message"), FString::Printf(TEXT("No actor with mcp_id '%s' found (already deleted)"), *McpId));
        ResultObj->SetBoolField(TEXT("deleted"), false);
        return ResultObj;
    }

    TSharedPtr<FJsonObject> ActorInfo = FEpicUnrealMCPCommonUtils::ActorToJsonObject(Actor);
    GetActorIndex().RemoveActor(Actor);

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Delete Actor By McpId")));
    Actor->Modify();
    Actor->Destroy();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetObjectField(TEXT("deleted_actor"), ActorInfo);
    ResultObj->SetBoolField(TEXT("deleted"), true);
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPEditorCommands::HandleSpawnBlueprintActor(const TSharedPtr<FJsonObject>& Params)
{
    // This function will now correctly call the implementation in BlueprintCommands
    FEpicUnrealMCPBlueprintCommands BlueprintCommands;
    return BlueprintCommands.HandleCommand(TEXT("spawn_blueprint_actor"), Params);
}
