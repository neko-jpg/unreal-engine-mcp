#include "MCPServerRunnable.h"
#include "EpicUnrealMCPBridge.h"
#include "UnrealMCPSettings.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "HAL/PlatformTime.h"

FMCPServerRunnable::FMCPServerRunnable(UEpicUnrealMCPBridge* InBridge, FSocket* InListenerSocket)
    : Bridge(InBridge)
    , ListenerSocket(InListenerSocket)
    , ClientSocket(nullptr)
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
            ClientSocket = ListenerSocket->Accept(TEXT("MCPClient"));
            if (ClientSocket)
            {
                ClientSocket->SetNonBlocking(true);
                ClientSocket->SetNoDelay(true);
                int32 SocketBufferSize = 65536;
                ClientSocket->SetSendBufferSize(SocketBufferSize, SocketBufferSize);
                ClientSocket->SetReceiveBufferSize(SocketBufferSize, SocketBufferSize);

                // Receive loop with newline-delimited framing
                const int32 ChunkSize = 65536;
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
                            ClientSocket->Wait(ESocketWaitConditions::WaitForRead, FTimespan::FromMilliseconds(50));
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

                ClientSocket->Close();
                if (ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM))
                {
                    SocketSubsystem->DestroySocket(ClientSocket);
                }
                ClientSocket = nullptr;
            }
            else
            {
                UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to accept client connection"));
            }
        }

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
}

void FMCPServerRunnable::Exit()
{
}

void FMCPServerRunnable::ProcessMessage(FSocket* Client, const FString& Message)
{
    auto SendJsonError = [Client](const FString& ErrorCode, const FString& ErrorMessage) {
        if (!Client)
        {
            return;
        }

        TSharedPtr<FJsonObject> ErrorObj = MakeShared<FJsonObject>();
        ErrorObj->SetBoolField(TEXT("success"), false);
        ErrorObj->SetStringField(TEXT("error_code"), ErrorCode);
        ErrorObj->SetStringField(TEXT("error"), ErrorMessage);
        FString ErrorStr;
        TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
            TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&ErrorStr);
        FJsonSerializer::Serialize(ErrorObj.ToSharedRef(), Writer);
        ErrorStr.AppendChar('\n');
        FTCHARToUTF8 UTF8Error(*ErrorStr);
        const uint8* Data = (const uint8*)UTF8Error.Get();
        int32 TotalSize = UTF8Error.Length();
        int32 Sent = 0;
        while (Sent < TotalSize)
        {
            int32 ChunkSent = 0;
            if (!Client->Send(Data + Sent, TotalSize - Sent, ChunkSent))
            {
                return;
            }
            Sent += ChunkSent;
        }
    };

    TSharedPtr<FJsonObject> JsonMessage;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);

    if (!FJsonSerializer::Deserialize(Reader, JsonMessage) || !JsonMessage.IsValid())
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Failed to parse JSON message"));
        SendJsonError(TEXT("INVALID_JSON"), TEXT("Failed to parse request as valid JSON"));
        return;
    }

    FString CommandType;
    if (!JsonMessage->TryGetStringField(TEXT("command"), CommandType))
    {
        UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Missing 'command' field"));
        SendJsonError(TEXT("MISSING_COMMAND"), TEXT("Request must include a 'command' field"));
        return;
    }

    const UUnrealMCPSettings* Settings = GetDefault<UUnrealMCPSettings>();
    if (Settings && !Settings->AuthToken.IsEmpty())
    {
        FString ProvidedToken;
        if (!JsonMessage->TryGetStringField(TEXT("auth_token"), ProvidedToken) || ProvidedToken != Settings->AuthToken)
        {
            UE_LOG(LogTemp, Warning, TEXT("MCPServerRunnable: Authentication failed for command '%s'"), *CommandType);
            SendJsonError(TEXT("AUTH_FAILED"), TEXT("Invalid or missing auth_token"));
            return;
        }
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
