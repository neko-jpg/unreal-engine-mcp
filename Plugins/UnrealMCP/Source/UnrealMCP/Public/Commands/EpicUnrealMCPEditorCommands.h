#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Pre-parsed create parameters for batch scene delta processing.
 * Parsed once before entering the game-thread loop to reduce per-item overhead.
 */
struct FParsedCreateParams
{
    bool bValid = false;
    FString ErrorString;
    FString Name;
    FString Type;
    FString McpId;
    FString StaticMeshPath;
    FVector Location = FVector::ZeroVector;
    FRotator Rotation = FRotator::ZeroRotator;
    FVector Scale = FVector::OneVector;
    TArray<FString> Tags;
};

/**
 * Pre-parsed update parameters for batch scene delta processing.
 */
struct FParsedUpdateParams
{
    bool bValid = false;
    FString ErrorString;
    FString McpId;
    FVector Location = FVector::ZeroVector;
    FRotator Rotation = FRotator::ZeroRotator;
    FVector Scale = FVector::OneVector;
    bool bHasLocation = false;
    bool bHasRotation = false;
    bool bHasScale = false;
};

/**
 * Handler class for Editor-related MCP commands
 * Handles viewport control, actor manipulation, and level management
 */
class UNREALMCP_API FEpicUnrealMCPEditorCommands
{
public:
    	FEpicUnrealMCPEditorCommands();

    // Handle editor commands
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    UWorld* GetEditorWorld() const;

    // Actor manipulation commands
    TSharedPtr<FJsonObject> HandleGetActorsInLevel(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleFindActorsByName(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSpawnActor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleDeleteActor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetActorTransform(const TSharedPtr<FJsonObject>& Params);

    // MCP identity commands
    TSharedPtr<FJsonObject> HandleFindActorByMcpId(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetActorTransformByMcpId(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleDeleteActorByMcpId(const TSharedPtr<FJsonObject>& Params);

    // Helper
    AActor* FindActorByMcpId(UWorld* World, const FString& McpId) const;

    // P4.3: Pre-parse helpers for batch scene delta
    FParsedCreateParams ParseCreateParams(const TSharedPtr<FJsonObject>& Params) const;
    FParsedUpdateParams ParseUpdateParams(const TSharedPtr<FJsonObject>& Params) const;
    TSharedPtr<FJsonObject> ExecuteCreateActor(const FParsedCreateParams& Parsed);
    TSharedPtr<FJsonObject> ExecuteUpdateActor(const FParsedUpdateParams& Parsed);

    // Blueprint actor spawning
    TSharedPtr<FJsonObject> HandleSpawnBlueprintActor(const TSharedPtr<FJsonObject>& Params);

    // Batch scene delta (P4)
    TSharedPtr<FJsonObject> HandleApplySceneDelta(const TSharedPtr<FJsonObject>& Params);
}; 