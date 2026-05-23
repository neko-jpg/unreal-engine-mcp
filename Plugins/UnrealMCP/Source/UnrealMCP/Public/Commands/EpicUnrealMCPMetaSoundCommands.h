#pragma once
#include "CoreMinimal.h"
#include "Json.h"

class FEpicUnrealMCPMetaSoundCommands
{
public:
    FEpicUnrealMCPMetaSoundCommands();
    ~FEpicUnrealMCPMetaSoundCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleEditSoundCueGraph(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateMetasoundSource(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateMetasoundPatch(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMetasoundGraphNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMetasoundParameter(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleBindFootstepAudio(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConfigureUiSound(const TSharedPtr<FJsonObject>& Params);
    static bool IsModuleAvailable();
    static TSharedPtr<FJsonObject> MakeUnavailable(const FString& CommandName);
};
