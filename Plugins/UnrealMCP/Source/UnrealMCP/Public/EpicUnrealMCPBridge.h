#pragma once

#include "CoreMinimal.h"
#include "EditorSubsystem.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Http.h"
#include "Json.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "Interfaces/IPv4/IPv4Endpoint.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"
#include "Commands/EpicUnrealMCPRouter.h"
#include "MCPServerRunnable.h"
#include "EpicUnrealMCPBridge.generated.h"

/**
 * Editor subsystem for MCP Bridge
 *
 * Handles communication between external tools and the Unreal Editor
 * through a TCP socket connection. Commands are received as JSON and
 * routed to the appropriate command handler.
 *
 * Routing model (Phase 4 / Issue #32 registry refactor):
 *
 *   FEpicUnrealMCPRouter::RouteCommand(name)  ->  int32 RouteId
 *   CommandHandlerRegistry[RouteId]           ->  handler closure
 *
 * The legacy `switch (Route)` block in `ExecuteCommand` was replaced
 * with a runtime registry of TFunctions populated once during
 * construction (see `RegisterHandlers()` in `EpicUnrealMCPBridge.cpp`).
 *
 * To add a new handler class, only **one** location in
 * `EpicUnrealMCPBridge.cpp` needs to change: a single
 * `RegisterHandler<FEpicUnrealMCPXxxCommands>(<RouteId>);` line in
 * `RegisterHandlers()`.  The matching command-name -> RouteId mapping
 * still lives in `EpicUnrealMCPRouter.cpp`.
 */
#if WITH_EDITOR

UCLASS()
class UNREALMCP_API UEpicUnrealMCPBridge : public UEditorSubsystem
{
	GENERATED_BODY()

public:
	UEpicUnrealMCPBridge();
	virtual ~UEpicUnrealMCPBridge();

	// UEditorSubsystem implementation
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	// Server functions
	void StartServer();
	void StopServer();
	bool IsRunning() const { return bIsRunning; }
	FIPv4Address GetServerAddress() const { return ServerAddress; }
	uint16 GetServerPort() const { return Port; }

	// Lazy actor index initialization
	void EnsureActorIndexInitialized();

	// Command execution
	FString ExecuteCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

	// Actor index for O(1) lookup by name/mcp_id
	FActorIndex ActorIndex;

	/**
	 * Type alias for a single registered handler closure.  The closure
	 * receives the original JSON command name plus its params object,
	 * and returns the per-handler result payload (i.e. the inner
	 * `result` of the success envelope).
	 */
	using FCommandHandlerFn = TFunction<TSharedPtr<FJsonObject>(const FString&, const TSharedPtr<FJsonObject>&)>;

private:
	// Server state
	bool bIsRunning;
	FSocket* ListenerSocket;
	FSocket* ConnectionSocket;
	FRunnableThread* ServerThread;
	TUniquePtr<FMCPServerRunnable> Runnable;

	// Server configuration
	FIPv4Address ServerAddress;
	uint16 Port;

	/**
	 * Route id -> handler closure registry.
	 *
	 * Populated once in the constructor by `RegisterHandlers()`.  Each
	 * lambda owns a TSharedPtr to its handler instance, which keeps the
	 * handler alive for the lifetime of the registry (which is destroyed
	 * with the bridge).  Thread-safety: writes happen only at
	 * construction; reads are concurrent and the TMap is never mutated
	 * after `RegisterHandlers()` returns, so no extra locking is needed.
	 */
	TMap<int32, FCommandHandlerFn> CommandHandlerRegistry;

	/** Populates `CommandHandlerRegistry` with the full route table. */
	void RegisterHandlers();

	/**
	 * Helper: register a handler closure under `RouteId`.
	 * Each handler class is created and owned exclusively by the
	 * captured TSharedPtr inside the closure, so removing or replacing
	 * the entry here is the only place a handler needs to be touched
	 * inside `EpicUnrealMCPBridge.cpp`.
	 */
	template <typename HandlerType>
	void RegisterHandler(int32 RouteId);
};

#endif // WITH_EDITOR
