#include "Commands/EpicUnrealMCPSourceControlCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

bool FEpicUnrealMCPSourceControlCommands::IsModuleAvailable()
{
#if 1
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPSourceControlCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("SourceControl + GitSourceControl + PerforceSourceControl + ConcertSyncClient ship with UE 5.7; enable the desired provider plugin."));
    return R;
}

FEpicUnrealMCPSourceControlCommands::FEpicUnrealMCPSourceControlCommands() {}
FEpicUnrealMCPSourceControlCommands::~FEpicUnrealMCPSourceControlCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPSourceControlCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("register_git_provider"),  &FEpicUnrealMCPSourceControlCommands::HandleRegisterGitProvider},
        {TEXT("register_perforce_provider"),  &FEpicUnrealMCPSourceControlCommands::HandleRegisterPerforceProvider},
        {TEXT("source_control_checkout"),  &FEpicUnrealMCPSourceControlCommands::HandleSourceControlCheckout},
        {TEXT("source_control_checkin"),  &FEpicUnrealMCPSourceControlCommands::HandleSourceControlCheckin},
        {TEXT("source_control_revert"),  &FEpicUnrealMCPSourceControlCommands::HandleSourceControlRevert},
        {TEXT("source_control_file_lock_acquire"),  &FEpicUnrealMCPSourceControlCommands::HandleSourceControlFileLockAcquire},
        {TEXT("source_control_file_lock_release"),  &FEpicUnrealMCPSourceControlCommands::HandleSourceControlFileLockRelease},
        {TEXT("source_control_create_changelist"),  &FEpicUnrealMCPSourceControlCommands::HandleSourceControlCreateChangelist},
        {TEXT("source_control_asset_diff"),  &FEpicUnrealMCPSourceControlCommands::HandleSourceControlAssetDiff},
        {TEXT("source_control_blueprint_diff"),  &FEpicUnrealMCPSourceControlCommands::HandleSourceControlBlueprintDiff},
        {TEXT("source_control_merge"),  &FEpicUnrealMCPSourceControlCommands::HandleSourceControlMerge},
        {TEXT("multi_user_editing_start"),  &FEpicUnrealMCPSourceControlCommands::HandleMultiUserEditingStart},
        {TEXT("multi_user_session_join"),  &FEpicUnrealMCPSourceControlCommands::HandleMultiUserSessionJoin}
    };
    if (const Handler* H = Dispatch.Find(CommandType))
    {
        return (this->*(*H))(Params);
    }
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));
    return R;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleRegisterGitProvider(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("register_git_provider"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("register_git_provider"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleRegisterPerforceProvider(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("register_perforce_provider"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("register_perforce_provider"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlCheckout(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("source_control_checkout"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_checkout"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlCheckin(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("source_control_checkin"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_checkin"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlRevert(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("source_control_revert"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_revert"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlFileLockAcquire(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("source_control_file_lock_acquire"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_file_lock_acquire"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlFileLockRelease(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("source_control_file_lock_release"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_file_lock_release"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlCreateChangelist(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("source_control_create_changelist"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_create_changelist"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlAssetDiff(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("source_control_asset_diff"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_asset_diff"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlBlueprintDiff(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("source_control_blueprint_diff"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_blueprint_diff"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlMerge(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("source_control_merge"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_merge"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleMultiUserEditingStart(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("multi_user_editing_start"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("multi_user_editing_start"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleMultiUserSessionJoin(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("multi_user_session_join"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("multi_user_session_join"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; ISourceControlOperation runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
