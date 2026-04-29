#pragma once

#include "CoreMinimal.h"
#include "HAL/Runnable.h"
#include "Sockets.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include "HAL/CriticalSection.h"
#include "MCPClientHandler.h"
#include <atomic>

class UEpicUnrealMCPBridge;

/**
 * Runnable class for the MCP server listener thread.
 * Accepts incoming connections and spawns a dedicated FMCPClientHandler
 * thread for each client.
 */
class FMCPServerRunnable : public FRunnable
{
public:
    FMCPServerRunnable(UEpicUnrealMCPBridge* InBridge, FSocket* InListenerSocket);
    virtual ~FMCPServerRunnable();

    // FRunnable interface
    virtual bool Init() override;
    virtual uint32 Run() override;
    virtual void Stop() override;
    virtual void Exit() override;

    /** Maximum number of concurrent client connections allowed. */
    static constexpr int32 MAX_CLIENT_CONNECTIONS = 16;

protected:
    /** Remove finished client handlers from the tracking arrays. */
    void CleanupFinishedHandlers();

private:
    UEpicUnrealMCPBridge* Bridge;
    FSocket* ListenerSocket;
    std::atomic<bool> bRunning;

    FCriticalSection HandlersLock;
    TArray<TUniquePtr<FMCPClientHandler>> ClientHandlers;
    TArray<FRunnableThread*> ClientThreads;
};
