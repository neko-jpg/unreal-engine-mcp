#pragma once

#include "CoreMinimal.h"
#include "HAL/Runnable.h"
#include "Sockets.h"
#include "Interfaces/IPv4/IPv4Address.h"
#include <atomic>

class UEpicUnrealMCPBridge;

/**
 * Runnable class for the MCP server thread
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

protected:
	void ProcessMessage(FSocket* Client, const FString& Message);

private:
	UEpicUnrealMCPBridge* Bridge;
	FSocket* ListenerSocket;
	std::atomic<FSocket*> ClientSocket{nullptr};
	std::atomic<bool> bRunning;
}; 
