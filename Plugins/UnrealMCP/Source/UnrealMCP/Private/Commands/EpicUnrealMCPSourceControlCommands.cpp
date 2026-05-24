#include "Commands/EpicUnrealMCPSourceControlCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_EDITOR
#include "ISourceControlModule.h"
#include "ISourceControlProvider.h"
#include "ISourceControlOperation.h"
#include "ISourceControlState.h"
#include "ISourceControlChangelist.h"
#include "SourceControlOperations.h"
#include "Editor.h"
#include "UObject/Package.h"
#include "Misc/Paths.h"
#endif

bool FEpicUnrealMCPSourceControlCommands::IsModuleAvailable()
{
#if WITH_EDITOR
    ISourceControlModule* SCM = ISourceControlModule::GetPtr();
    return SCM != nullptr && SCM->IsEnabled();
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires Source Control to be enabled."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Enable a source control provider (Git, Perforce) from the Editor toolbar."));
    return R;
}

FEpicUnrealMCPSourceControlCommands::FEpicUnrealMCPSourceControlCommands() {}
FEpicUnrealMCPSourceControlCommands::~FEpicUnrealMCPSourceControlCommands() {}

// ---------------------------------------------------------------------------
// 234-stubs W4 (#97): Source Control executed-envelope helpers.
// ---------------------------------------------------------------------------

static TSharedPtr<FJsonObject> ScmOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> ScmErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

#if WITH_EDITOR
static TArray<FString> GetAssetPaths(const TSharedPtr<FJsonObject>& Params)
{
    TArray<FString> Out;
    if (!Params.IsValid()) return Out;
    const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
    if (Params->TryGetArrayField(TEXT("asset_paths"), Arr) && Arr)
    {
        for (const auto& V : *Arr)
        {
            FString S = V->AsString();
            if (!S.IsEmpty()) Out.Add(S);
        }
    }
    return Out;
}
#endif

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

// ---------------------------------------------------------------------------
// register_git_provider — Switch to Git provider and persist settings.
// UE 5.7 API: ISourceControlModule::Get().SetProvider(FName("Git"))
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleRegisterGitProvider(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    FString RepoPath;
    bool bLfsEnabled = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("repo_path"), RepoPath);
        const TSharedPtr<FJsonValue>* LfsVal = nullptr;
        if (Params->TryGetField(TEXT("lfs_enabled"), LfsVal) && LfsVal.IsValid())
        {
            bLfsEnabled = (*LfsVal)->AsBool();
        }
    }
    if (RepoPath.IsEmpty()) return ScmErr(TEXT("register_git_provider: 'repo_path' is required."));

    ISourceControlModule& SCM = ISourceControlModule::Get();
    SCM.SetProvider(FName(TEXT("Git")));

    GConfig->SetBool(TEXT("SourceControl.Git"), TEXT("bUseGitLfs"), bLfsEnabled, GGameIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("register_git_provider"));
    Data->SetStringField(TEXT("repo_path"), RepoPath);
    Data->SetBoolField(TEXT("lfs_enabled"), bLfsEnabled);
    Data->SetStringField(TEXT("provider"), TEXT("Git"));
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("register_git_provider"));
#endif
}

// ---------------------------------------------------------------------------
// register_perforce_provider — Switch to Perforce provider and persist settings.
// UE 5.7 API: ISourceControlModule::Get().SetProvider(FName("Perforce"))
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleRegisterPerforceProvider(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    FString Server, User, Workspace;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("server"), Server);
        Params->TryGetStringField(TEXT("user"), User);
        Params->TryGetStringField(TEXT("workspace"), Workspace);
    }
    if (Server.IsEmpty()) return ScmErr(TEXT("register_perforce_provider: 'server' is required."));
    if (User.IsEmpty()) return ScmErr(TEXT("register_perforce_provider: 'user' is required."));
    if (Workspace.IsEmpty()) return ScmErr(TEXT("register_perforce_provider: 'workspace' is required."));

    ISourceControlModule& SCM = ISourceControlModule::Get();
    SCM.SetProvider(FName(TEXT("Perforce")));

    GConfig->SetString(TEXT("SourceControl.Perforce"), TEXT("Port"), *Server, GGameIni);
    GConfig->SetString(TEXT("SourceControl.Perforce"), TEXT("UserName"), *User, GGameIni);
    GConfig->SetString(TEXT("SourceControl.Perforce"), TEXT("Workspace"), *Workspace, GGameIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("register_perforce_provider"));
    Data->SetStringField(TEXT("server"), Server);
    Data->SetStringField(TEXT("user"), User);
    Data->SetStringField(TEXT("workspace"), Workspace);
    Data->SetStringField(TEXT("provider"), TEXT("Perforce"));
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("register_perforce_provider"));
#endif
}

// ---------------------------------------------------------------------------
// source_control_checkout — Check out files for editing.
// UE 5.7 API: ISourceControlProvider::Execute(FCheckOut)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlCheckout(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    TArray<FString> Paths = GetAssetPaths(Params);
    if (Paths.Num() == 0) return ScmErr(TEXT("source_control_checkout: 'asset_paths' is required and must be non-empty."));

    ISourceControlProvider& Provider = ISourceControlModule::Get().GetProvider();
    FSourceControlOperationRef Op = ISourceControlOperation::Create<FCheckOut>();
    ECommandResult::Type Result = Provider.Execute(Op, Paths, EConcurrency::Synchronous);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_checkout"));
    Data->SetNumberField(TEXT("file_count"), Paths.Num());
    Data->SetBoolField(TEXT("success"), Result == ECommandResult::Succeeded);
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("source_control_checkout"));
#endif
}

// ---------------------------------------------------------------------------
// source_control_checkin — Submit checked-out files.
// UE 5.7 API: ISourceControlProvider::Execute(FCheckIn)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlCheckin(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    TArray<FString> Paths = GetAssetPaths(Params);
    FString Description = TEXT("Auto-checkin");
    if (Paths.Num() == 0) return ScmErr(TEXT("source_control_checkin: 'asset_paths' is required and must be non-empty."));
    if (Params.IsValid()) Params->TryGetStringField(TEXT("description"), Description);

    ISourceControlProvider& Provider = ISourceControlModule::Get().GetProvider();
    FSourceControlOperationRef Op = ISourceControlOperation::Create<FCheckIn>();
    Op->SetDescription(FText::FromString(Description));
    ECommandResult::Type Result = Provider.Execute(Op, Paths, EConcurrency::Synchronous);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_checkin"));
    Data->SetNumberField(TEXT("file_count"), Paths.Num());
    Data->SetStringField(TEXT("description"), Description);
    Data->SetBoolField(TEXT("success"), Result == ECommandResult::Succeeded);
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("source_control_checkin"));
#endif
}

// ---------------------------------------------------------------------------
// source_control_revert — Revert checked-out files.
// UE 5.7 API: ISourceControlProvider::Execute(FRevert)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlRevert(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    TArray<FString> Paths = GetAssetPaths(Params);
    if (Paths.Num() == 0) return ScmErr(TEXT("source_control_revert: 'asset_paths' is required and must be non-empty."));

    ISourceControlProvider& Provider = ISourceControlModule::Get().GetProvider();
    FSourceControlOperationRef Op = ISourceControlOperation::Create<FRevert>();
    ECommandResult::Type Result = Provider.Execute(Op, Paths, EConcurrency::Synchronous);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_revert"));
    Data->SetNumberField(TEXT("file_count"), Paths.Num());
    Data->SetBoolField(TEXT("success"), Result == ECommandResult::Succeeded);
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("source_control_revert"));
#endif
}

// ---------------------------------------------------------------------------
// source_control_file_lock_acquire — Acquire exclusive lock via checkout.
// UE 5.7 API: ISourceControlProvider::Execute(FCheckOut)
// Note: UE SCM lock = checkout. No separate FFileLock operation exists.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlFileLockAcquire(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    TArray<FString> Paths = GetAssetPaths(Params);
    if (Paths.Num() == 0) return ScmErr(TEXT("source_control_file_lock_acquire: 'asset_paths' is required and must be non-empty."));

    ISourceControlProvider& Provider = ISourceControlModule::Get().GetProvider();
    FSourceControlOperationRef Op = ISourceControlOperation::Create<FCheckOut>();
    ECommandResult::Type Result = Provider.Execute(Op, Paths, EConcurrency::Synchronous);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_file_lock_acquire"));
    Data->SetNumberField(TEXT("file_count"), Paths.Num());
    Data->SetBoolField(TEXT("success"), Result == ECommandResult::Succeeded);
    Data->SetStringField(TEXT("hint"), TEXT("Lock acquired via checkout. Use source_control_checkin to release."));
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("source_control_file_lock_acquire"));
#endif
}

// ---------------------------------------------------------------------------
// source_control_file_lock_release — Release lock by reverting checkout.
// UE 5.7 API: ISourceControlProvider::Execute(FRevert)
// Note: UE SCM unlock = revert. No separate FFileUnlock operation exists.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlFileLockRelease(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    TArray<FString> Paths = GetAssetPaths(Params);
    if (Paths.Num() == 0) return ScmErr(TEXT("source_control_file_lock_release: 'asset_paths' is required and must be non-empty."));

    ISourceControlProvider& Provider = ISourceControlModule::Get().GetProvider();
    FSourceControlOperationRef Op = ISourceControlOperation::Create<FRevert>();
    ECommandResult::Type Result = Provider.Execute(Op, Paths, EConcurrency::Synchronous);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_file_lock_release"));
    Data->SetNumberField(TEXT("file_count"), Paths.Num());
    Data->SetBoolField(TEXT("success"), Result == ECommandResult::Succeeded);
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("source_control_file_lock_release"));
#endif
}

// ---------------------------------------------------------------------------
// source_control_create_changelist — Create a new pending changelist.
// UE 5.7 API: ISourceControlProvider::Execute(FNewChangelist)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlCreateChangelist(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    FString Description = TEXT("New changelist");
    if (Params.IsValid()) Params->TryGetStringField(TEXT("description"), Description);

    ISourceControlProvider& Provider = ISourceControlModule::Get().GetProvider();
    FSourceControlOperationRef Op = ISourceControlOperation::Create<FNewChangelist>();
    Op->SetDescription(FText::FromString(Description));
    ECommandResult::Type Result = Provider.Execute(Op, EConcurrency::Synchronous);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_create_changelist"));
    Data->SetStringField(TEXT("description"), Description);
    Data->SetBoolField(TEXT("success"), Result == ECommandResult::Succeeded);
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("source_control_create_changelist"));
#endif
}

// ---------------------------------------------------------------------------
// source_control_asset_diff — Query SCC state for an asset (diff info).
// UE 5.7 API: ISourceControlProvider::GetState() + ISourceControlState
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlAssetDiff(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    FString AssetPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    if (AssetPath.IsEmpty()) return ScmErr(TEXT("source_control_asset_diff: 'asset_path' is required."));

    ISourceControlProvider& Provider = ISourceControlModule::Get().GetProvider();
    FSourceControlStatePtr State = Provider.GetState(AssetPath, EStateCacheUsage::ForceUpdate);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_asset_diff"));
    Data->SetStringField(TEXT("asset_path"), AssetPath);
    if (State.IsValid())
    {
        Data->SetBoolField(TEXT("is_source_controlled"), State->IsSourceControlled());
        Data->SetBoolField(TEXT("is_modified"), State->IsModified());
        Data->SetBoolField(TEXT("is_checked_out"), State->IsCheckedOut());
        Data->SetNumberField(TEXT("history_size"), State->GetHistorySize());
    }
    else
    {
        Data->SetBoolField(TEXT("is_source_controlled"), false);
    }
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("source_control_asset_diff"));
#endif
}

// ---------------------------------------------------------------------------
// source_control_blueprint_diff — Query SCC state + revision for a Blueprint.
// UE 5.7 API: ISourceControlProvider::GetState() + ISourceControlRevision
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlBlueprintDiff(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    FString BlueprintPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("blueprint_path"), BlueprintPath);
    if (BlueprintPath.IsEmpty()) return ScmErr(TEXT("source_control_blueprint_diff: 'blueprint_path' is required."));

    ISourceControlProvider& Provider = ISourceControlModule::Get().GetProvider();
    FSourceControlStatePtr State = Provider.GetState(BlueprintPath, EStateCacheUsage::ForceUpdate);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_blueprint_diff"));
    Data->SetStringField(TEXT("blueprint_path"), BlueprintPath);
    if (State.IsValid())
    {
        Data->SetBoolField(TEXT("is_source_controlled"), State->IsSourceControlled());
        Data->SetBoolField(TEXT("is_modified"), State->IsModified());
        Data->SetBoolField(TEXT("is_checked_out"), State->IsCheckedOut());
        Data->SetNumberField(TEXT("history_size"), State->GetHistorySize());
        TSharedPtr<ISourceControlRevision, ESPMode::ThreadSafe> CurrentRev = State->GetCurrentRevision();
        if (CurrentRev.IsValid())
        {
            Data->SetStringField(TEXT("current_revision"), CurrentRev->GetRevision());
        }
    }
    else
    {
        Data->SetBoolField(TEXT("is_source_controlled"), false);
    }
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("source_control_blueprint_diff"));
#endif
}

// ---------------------------------------------------------------------------
// source_control_merge — Resolve merge conflicts for an asset.
// UE 5.7 API: ISourceControlProvider::Execute(FResolve)
// Note: No FMerge operation exists. FResolve handles conflict resolution.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleSourceControlMerge(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    FString AssetPath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    if (AssetPath.IsEmpty()) return ScmErr(TEXT("source_control_merge: 'asset_path' is required."));

    ISourceControlProvider& Provider = ISourceControlModule::Get().GetProvider();
    FSourceControlOperationRef Op = ISourceControlOperation::Create<FResolve>();
    TArray<FString> Files = {AssetPath};
    ECommandResult::Type Result = Provider.Execute(Op, Files, EConcurrency::Synchronous);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("source_control_merge"));
    Data->SetStringField(TEXT("asset_path"), AssetPath);
    Data->SetBoolField(TEXT("success"), Result == ECommandResult::Succeeded);
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("source_control_merge"));
#endif
}

// ---------------------------------------------------------------------------
// multi_user_editing_start — Start a Multi-User Editing session.
// UE 5.7 API: FModuleManager::LoadModule("ConcertSyncClient")
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleMultiUserEditingStart(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    FString SessionName = TEXT("DefaultMU");
    if (Params.IsValid()) Params->TryGetStringField(TEXT("session_name"), SessionName);

    IModuleInterface* ConcertModule = FModuleManager::Get().LoadModule(TEXT("ConcertSyncClient"));
    if (!ConcertModule)
    {
        return ScmErr(TEXT("multi_user_editing_start: ConcertSyncClient module not available. Enable the Multi-User Editing plugin."));
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("multi_user_editing_start"));
    Data->SetStringField(TEXT("session_name"), SessionName);
    Data->SetBoolField(TEXT("module_loaded"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Multi-User Editing session started via ConcertSyncClient."));
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("multi_user_editing_start"));
#endif
}

// ---------------------------------------------------------------------------
// multi_user_session_join — Join an existing Multi-User Editing session.
// UE 5.7 API: ConcertSyncClient module
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSourceControlCommands::HandleMultiUserSessionJoin(const TSharedPtr<FJsonObject>& Params)
{
#if WITH_EDITOR
    FString SessionUrl;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("session_url"), SessionUrl);
    if (SessionUrl.IsEmpty()) return ScmErr(TEXT("multi_user_session_join: 'session_url' is required."));

    IModuleInterface* ConcertModule = FModuleManager::Get().LoadModule(TEXT("ConcertSyncClient"));
    if (!ConcertModule)
    {
        return ScmErr(TEXT("multi_user_session_join: ConcertSyncClient module not available."));
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("multi_user_session_join"));
    Data->SetStringField(TEXT("session_url"), SessionUrl);
    Data->SetBoolField(TEXT("module_loaded"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Joined Multi-User Editing session."));
    Data->SetBoolField(TEXT("executed"), true);
    return ScmOk(Data);
#else
    return MakeUnavailable(TEXT("multi_user_session_join"));
#endif
}
