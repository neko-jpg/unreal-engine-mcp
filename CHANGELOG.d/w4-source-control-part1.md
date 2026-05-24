feat(234-stubs W4 #97): promote 13 Source Control handlers to executed envelope

Promote all 13 Source Control handlers from stub (queued: true) to
executed envelope with real UE 5.7 API calls:
register_git_provider, register_perforce_provider,
source_control_checkout, source_control_checkin, source_control_revert,
source_control_file_lock_acquire, source_control_file_lock_release,
source_control_create_changelist, source_control_asset_diff,
source_control_blueprint_diff, source_control_merge,
multi_user_editing_start, multi_user_session_join.

UE 5.7 APIs used:
- ISourceControlModule::Get().SetProvider() (provider registration)
- ISourceControlProvider::Execute(FCheckOut/FCheckIn/FRevert/FNewChangelist/FResolve)
- ISourceControlProvider::GetState() + ISourceControlState/Revision (diff queries)
- FModuleManager::LoadModule("ConcertSyncClient") (multi-user editing)
- GConfig persistence (Perforce/Git settings)
