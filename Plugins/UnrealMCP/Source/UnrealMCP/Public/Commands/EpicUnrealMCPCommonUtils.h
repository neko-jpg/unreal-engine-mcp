#pragma once

#include "CoreMinimal.h"
#include "Json.h"

// Forward declarations
class AActor;
class UBlueprint;
class UPackage;
class UWorld;
class UEdGraph;
class UEdGraphNode;
class UEdGraphPin;
class UK2Node_Event;
class UK2Node_CallFunction;
class UK2Node_VariableGet;
class UK2Node_VariableSet;
class UK2Node_InputAction;
class UK2Node_Self;
class UFunction;
class UEpicUnrealMCPBridge;

/**
 * In-memory index for O(1) actor lookup by name and mcp_id.
 * Updated on spawn/delete to avoid GetAllActorsOfClass linear scans.
 */
struct UNREALMCP_API FActorIndex
{
    TMap<FName, TWeakObjectPtr<AActor>> NameIndex;
    TMap<FString, TWeakObjectPtr<AActor>> McpIdIndex;

    void AddActor(AActor* Actor);
    void RemoveActor(AActor* Actor);
    AActor* FindByName(const FName& Name);
    AActor* FindByMcpId(const FString& McpId);
    void RebuildFromWorld(UWorld* World);
    void Clear();
};

/**
 * Common utilities for EpicUnrealMCP commands
 */
class UNREALMCP_API FEpicUnrealMCPCommonUtils
{
public:
    // JSON utilities
    static TSharedPtr<FJsonObject> CreateErrorResponse(const FString& Message);
    static TSharedPtr<FJsonObject> CreateSuccessResponse(const TSharedPtr<FJsonObject>& Data = nullptr);
    static void GetIntArrayFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName, TArray<int32>& OutArray);
    static void GetFloatArrayFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName, TArray<float>& OutArray);
    static FVector2D GetVector2DFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName);
    static FVector GetVectorFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName);
    static bool TryGetVectorFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName, FVector& OutVector, FString& OutError);
    static FRotator GetRotatorFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName);
    static bool TryGetRotatorFromJson(const TSharedPtr<FJsonObject>& JsonObject, const FString& FieldName, FRotator& OutRotator, FString& OutError);
    
    // Actor utilities
    static TSharedPtr<FJsonValue> ActorToJson(AActor* Actor);
    static TSharedPtr<FJsonObject> ActorToJsonObject(AActor* Actor, bool bDetailed = false);
    
    // Blueprint utilities
    static UBlueprint* FindBlueprint(const FString& BlueprintName);
    static UBlueprint* FindBlueprintByName(const FString& BlueprintName);
    static UEdGraph* FindOrCreateEventGraph(UBlueprint* Blueprint);
    
    // Blueprint node utilities
    static UK2Node_Event* CreateEventNode(UEdGraph* Graph, const FString& EventName, const FVector2D& Position);
    static UK2Node_CallFunction* CreateFunctionCallNode(UEdGraph* Graph, UFunction* Function, const FVector2D& Position);
    static UK2Node_VariableGet* CreateVariableGetNode(UEdGraph* Graph, UBlueprint* Blueprint, const FString& VariableName, const FVector2D& Position);
    static UK2Node_VariableSet* CreateVariableSetNode(UEdGraph* Graph, UBlueprint* Blueprint, const FString& VariableName, const FVector2D& Position);
    static UK2Node_InputAction* CreateInputActionNode(UEdGraph* Graph, const FString& ActionName, const FVector2D& Position);
    static UK2Node_Self* CreateSelfReferenceNode(UEdGraph* Graph, const FVector2D& Position);
    static bool ConnectGraphNodes(UEdGraph* Graph, UEdGraphNode* SourceNode, const FString& SourcePinName, 
                                UEdGraphNode* TargetNode, const FString& TargetPinName);
    static UEdGraphPin* FindPin(UEdGraphNode* Node, const FString& PinName, EEdGraphPinDirection Direction = EGPD_MAX);
    static UK2Node_Event* FindExistingEventNode(UEdGraph* Graph, const FString& EventName);

    // Property utilities
    static bool SetObjectProperty(UObject* Object, const FString& PropertyName,
                                 const TSharedPtr<FJsonValue>& Value, FString& OutErrorMessage);
    static bool SetPackageMetadata(UPackage* Package, const UObject* Object, FName Key, const TCHAR* Value);

    // Tag / actor lookup helpers (moved from EpicUnrealMCPEditorCommands.cpp)
    static void ApplyMcpIdAndTags(AActor* Actor, const FString& McpId, const TArray<FString>& ExtraTags);
    static TArray<FString> ReadStringArrayField(const TSharedPtr<FJsonObject>& Object, const FString& FieldName);
    static AActor* FindActorByMcpIdTag(UWorld* World, const FString& McpId);

    // Bridge index accessor (used by command handlers for O(1) actor lookup)
    static FActorIndex& GetActorIndex();

    // ---- 234-stubs Wave 0 (#71): UE 5.7 ini-persistence + executed envelope helpers ----
    /**
     * Persist any modifications on an editor-mutated UObject (typically a CDO)
     * into its Default*.ini config file. UE 5.7 deprecates UpdateDefaultConfigFile();
     * this is the only sanctioned path. Failures are downgraded to a structured
     * warning written to *OutHint so command handlers never throw.
     */
    static bool TryUpdateDefaultConfigFileSafe(UObject* Object, FString* OutHint = nullptr);

    /** Build a { success:true, data:{ executed:true, ...payload } } envelope. */
    static TSharedPtr<FJsonObject> MakeExecutedEnvelope(const TSharedPtr<FJsonObject>& Payload = nullptr);

    /** True when Response has success=true *and* data.executed=true. */
    static bool ResponseIsExecuted(const TSharedPtr<FJsonObject>& Response);

    /** Build an MCP-422 "queued regression" error wrapping the offending response. */
    static TSharedPtr<FJsonObject> MakeQueuedRegressionError(const FString& CommandType, const TSharedPtr<FJsonObject>& OffendingResponse);
}; 

// ---- 234-stubs Wave 0 (#71): RAII wrapper around FScopedTransaction ----
// Forward declared to avoid pulling ScopedTransaction.h into a public header.
class FScopedTransaction;

/**
 * Minimal RAII wrapper around FScopedTransaction so MCP command handlers can
 * write a single line at the top of any mutating block. In non-editor /
 * commandlet contexts the wrapper is a no-op so it stays safe to use in
 * shared command code.
 */
class UNREALMCP_API FMCPScopedTransaction
{
public:
    explicit FMCPScopedTransaction(const FString& Context);
    ~FMCPScopedTransaction();

    FMCPScopedTransaction(const FMCPScopedTransaction&) = delete;
    FMCPScopedTransaction& operator=(const FMCPScopedTransaction&) = delete;

    /** Cancel the transaction before its scope ends. */
    void Cancel();

private:
    FScopedTransaction* Inner = nullptr;
};
