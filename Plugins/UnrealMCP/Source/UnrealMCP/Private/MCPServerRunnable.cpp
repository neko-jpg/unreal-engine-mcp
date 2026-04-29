#include "MCPServerRunnable.h"
#include "EpicUnrealMCPBridge.h"
#include "UnrealMCPSettings.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "HAL/PlatformTime.h"

FMCPServerRunnable::FMCPServerRunnable(UEpicUnrealMCPBridge* InBridge, FSocket* InListenerSocket)
    : Bridge(InBridge)
    , ListenerSocket(InListenerSocket)
    , bRunning(true)
{
    UE_LOG(LogTemp, Log, TEXT("MCPServerRunnable: Created server runnable"));
}

FMCPServerRunnable::~FMCPServerRunnable()
{
}

bool FMCPServerRunnable::Init()
{
    return true;
}

uint32 FMCPServerRunnable::Run()
{
    UE_LOG(LogTemp, Log, TEXT("MCPServerRunnable: Server thread starting..."));

    while (bRunning)
    {
        bool bPending = false;
        if (ListenerSocket && ListenerSocket->HasPendingConnection(bPending) && bPending)
        {
            FSocket* NewClientSocket = ListenerSocket->Accept(TEXT("MCPClient"));
            if (NewClientSocket)
            {
                FScopeLock Lock(&HandlersLock);
                if (ClientHandlers.Num() >= MAX_CLIENT_CONNECTIONS)
                {
                    UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Max client connections (%d) reached; rejecting new client"), MAX_CLIENT_CONNECTIONS);
                    NewClientSocket->Close();
                    if (ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM))
                    {
                        SocketSubsystem->DestroySocket(NewClientSocket);
                    }
                }
                else
                {
                    auto Handler = MakeUnique<FMCPClientHandler>(Bridge, NewClientSocket);
                    FRunnableThread* Thread = FRunnableThread::Create(
                        Handler.Get(),
                        TEXT("MCPClientHandler"),
                        0, TPri_Normal);

                    if (Thread)
                    {
                        ClientHandlers.Add(MoveTemp(Handler));
                        ClientThreads.Add(Thread);
                        UE_LOG(LogTemp, Log, TEXT("MCPServerRunnable: Spawned client handler (total: %d)"), ClientHandlers.Num());
                    }
                    else
                    {
                        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to create client thread"));
                        NewClientSocket->Close();
                        if (ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM))
                        {
                            SocketSubsystem->DestroySocket(NewClientSocket);
                        }
                    }
                }
            }
            else
            {
                UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to accept client connection"));
            }
        }

        // Periodic cleanup of finished handlers to prevent unbounded growth
        CleanupFinishedHandlers();

        if (ListenerSocket)
        {
            ListenerSocket->Wait(ESocketWaitConditions::WaitForRead, FTimespan::FromMilliseconds(250));
        }
    }

    UE_LOG(LogTemp, Log, TEXT("MCPServerRunnable: Server thread stopping"));
    return 0;
}

void FMCPServerRunnable::Stop()
{
    bRunning = false;
    FScopeLock Lock(&HandlersLock);
    for (auto& Handler : ClientHandlers)
    {
        if (Handler.IsValid())
        {
            Handler->Stop();
        }
    }
}

void FMCPServerRunnable::Exit()
{
    FScopeLock Lock(&HandlersLock);
    for (FRunnableThread* Thread : ClientThreads)
    {
        if (Thread)
        {
            Thread->WaitForCompletion();
            delete Thread;
        }
    }
    ClientThreads.Empty();
    ClientHandlers.Empty();
}

void FMCPServerRunnable::CleanupFinishedHandlers()
{
    FScopeLock Lock(&HandlersLock);
    for (int32 i = ClientHandlers.Num() - 1; i >= 0; --i)
    {
        if (ClientHandlers[i].IsValid() && ClientHandlers[i]->IsFinished())
        {
            if (ClientThreads.IsValidIndex(i) && ClientThreads[i])
            {
                // Wait for the thread to finish (should be quick since IsFinished is true)
                ClientThreads[i]->WaitForCompletion();
                delete ClientThreads[i];
            }
            ClientThreads.RemoveAt(i);
            ClientHandlers.RemoveAt(i);
        }
    }
}
