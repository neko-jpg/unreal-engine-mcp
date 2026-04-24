#include "MCPServerRunnable.h"
#include "EpicUnrealMCPBridge.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "HAL/PlatformTime.h"

FMCPServerRunnable::FMCPServerRunnable(UEpicUnrealMCPBridge* InBridge, TSharedPtr<FSocket> InListenerSocket)
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
        if (ListenerSocket->HasPendingConnection(bPending) && bPending)
        {
                ClientSocket = MakeShareable(ListenerSocket->Accept(TEXT("MCPClient")));
            if (ClientSocket.IsValid())
            {
                ClientSocket->SetNonBlocking(true);
                ClientSocket->SetNoDelay(true);
                int32 SocketBufferSize = 65536;
                ClientSocket->SetSendBufferSize(SocketBufferSize, SocketBufferSize);
                ClientSocket->SetReceiveBufferSize(SocketBufferSize, SocketBufferSize);

                // Receive loop with newline-delimited framing
                const int32 ChunkSize = 4096;
                uint8 Buffer[ChunkSize];
                FString Accumulator;

                while (bRunning)
                {
                    int32 BytesRead = 0;
                    if (!ClientSocket->Recv(Buffer, ChunkSize - 1, BytesRead))
                    {
                        int32 LastError = (int32)ISocketSubsystem::Get()->GetLastErrorCode();
                        if (LastError == SE_EWOULDBLOCK)
                        {
                            FPlatformProcess::Sleep(0.01f);
                            continue;
                        }
                        else if (LastError == SE_EINTR)
                        {
                            UE_LOG(LogTemp, Verbose, TEXT("MCPServerRunnable: Recv interrupted, continuing..."));
                            continue;
                        }
                        else
                        {
                            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Client disconnected or error. Code: %d"), LastError);
                            break;
                        }
                    }

                    if (BytesRead == 0)
                    {
                        UE_LOG(LogTemp, Log, TEXT("MCPServerRunnable: Client disconnected (zero bytes)"));
                        break;
                    }

                    Buffer[BytesRead] = '\0';
                    Accumulator.Append(UTF8_TO_TCHAR(Buffer));

                    int32 NewlineIndex;
                    while (Accumulator.FindChar('\n', NewlineIndex))
                    {
                        FString Line = Accumulator.Left(NewlineIndex);
                        Accumulator.RemoveAt(0, NewlineIndex + 1);

                        Line.TrimStartAndEndInline();
                        if (!Line.IsEmpty())
                        {
                            ProcessMessage(ClientSocket, Line);
                        }
                    }

                    // Prevent unbounded growth of accumulator from malformed input
                    if (Accumulator.Len() > 65536)
                    {
                        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Accumulator exceeded 64KB without newline; dropping buffer."));
                        Accumulator.Empty();
                    }
                }
            }
            else
            {
                UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to accept client connection"));
            }
        }

        FPlatformProcess::Sleep(0.1f);
    }

    UE_LOG(LogTemp, Log, TEXT("MCPServerRunnable: Server thread stopping"));
    return 0;
}

void FMCPServerRunnable::Stop()
{
    bRunning = false;
}

void FMCPServerRunnable::Exit()
{
}

void FMCPServerRunnable::ProcessMessage(TSharedPtr<FSocket> Client, const FString& Message)
{
    TSharedPtr<FJsonObject> JsonMessage;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);

    if (!FJsonSerializer::Deserialize(Reader, JsonMessage) || !JsonMessage.IsValid())
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to parse JSON message"));
        return;
    }

    FString CommandType;
    if (!JsonMessage->TryGetStringField(TEXT("command"), CommandType))
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Missing 'command' field"));
        return;
    }

    TSharedPtr<FJsonObject> Params;
    const TSharedPtr<FJsonObject>* ParamsPtr = nullptr;
    if (JsonMessage->TryGetObjectField(TEXT("params"), ParamsPtr))
    {
        Params = *ParamsPtr;
    }
    else
    {
        Params = MakeShareable(new FJsonObject());
    }

    FString Response = Bridge->ExecuteCommand(CommandType, Params);
    Response.AppendChar('\n');

    FTCHARToUTF8 UTF8Response(*Response);
    const uint8* DataToSend = (const uint8*)UTF8Response.Get();
    int32 TotalDataSize = UTF8Response.Length();
    int32 TotalBytesSent = 0;

    while (TotalBytesSent < TotalDataSize)
    {
        int32 BytesSent = 0;
        if (!Client->Send(DataToSend + TotalBytesSent, TotalDataSize - TotalBytesSent, BytesSent))
        {
            UE_LOG(LogTemp, Error, TEXT("MCPServerRunnable: Failed to send response after %d/%d bytes"), TotalBytesSent, TotalDataSize);
            return;
        }
        TotalBytesSent += BytesSent;
    }
}
