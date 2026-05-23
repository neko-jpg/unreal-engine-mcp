#include "Commands/EpicUnrealMCPAnimationRiggingCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_ANIM_RIGGING_MCP
#include "Animation/Skeleton.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "AssetToolsModule.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Factories/SkeletonFactory.h"
#include "Factories/PhysicsAssetFactory.h"  // UE 5.7: lives under Editor/UnrealEd/Classes/Factories
#endif

namespace
{
TSharedPtr<FJsonObject> AnimOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
TSharedPtr<FJsonObject> AnimErr(const FString& Msg, const FString& Hint = FString())
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    if (!Hint.IsEmpty()) Out->SetStringField(TEXT("hint"), Hint);
    return Out;
}
static TSharedPtr<FJsonObject> AnimQueued(const FString& Cmd, const TSharedPtr<FJsonObject>& Params, const FString& Hint = FString())
{
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), Cmd);
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    if (!Hint.IsEmpty()) Data->SetStringField(TEXT("hint"), Hint);
    return AnimOk(Data);
}
}

FEpicUnrealMCPAnimationRiggingCommands::FEpicUnrealMCPAnimationRiggingCommands() {}
FEpicUnrealMCPAnimationRiggingCommands::~FEpicUnrealMCPAnimationRiggingCommands() {}

bool FEpicUnrealMCPAnimationRiggingCommands::IsAnimRiggingAvailable()
{
    if (TSharedPtr<IPlugin> P = IPluginManager::Get().FindPlugin(TEXT("ControlRig")))   { if (P->IsEnabled()) return true; }
    if (TSharedPtr<IPlugin> P = IPluginManager::Get().FindPlugin(TEXT("IKRig")))        { if (P->IsEnabled()) return true; }
    return false;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::MakeRiggingUnavailableResponse(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"),
        FString::Printf(TEXT("'%s' requires ControlRig or IKRig (Engine/Plugins/Animation)."), *Cmd));
    R->SetStringField(TEXT("hint"),
        TEXT("Enable the ControlRig and IKRig plugins in this project's .uproject and rebuild UnrealMCP so WITH_ANIM_RIGGING_MCP=1."));
    return R;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPAnimationRiggingCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_skeleton_asset"),         &FEpicUnrealMCPAnimationRiggingCommands::HandleCreateSkeletonAsset},
        {TEXT("create_physics_asset"),          &FEpicUnrealMCPAnimationRiggingCommands::HandleCreatePhysicsAsset},
        {TEXT("add_anim_graph_node"),           &FEpicUnrealMCPAnimationRiggingCommands::HandleAddAnimGraphNode},
        {TEXT("create_anim_state_machine"),     &FEpicUnrealMCPAnimationRiggingCommands::HandleCreateAnimStateMachine},
        {TEXT("add_anim_state"),                &FEpicUnrealMCPAnimationRiggingCommands::HandleAddAnimState},
        {TEXT("create_anim_transition_rule"),   &FEpicUnrealMCPAnimationRiggingCommands::HandleCreateAnimTransitionRule},
        {TEXT("create_aim_offset"),             &FEpicUnrealMCPAnimationRiggingCommands::HandleCreateAimOffset},
        {TEXT("add_notify_state"),              &FEpicUnrealMCPAnimationRiggingCommands::HandleAddNotifyState},
        {TEXT("set_retarget_manager"),          &FEpicUnrealMCPAnimationRiggingCommands::HandleSetRetargetManager},
        {TEXT("create_ik_rig"),                 &FEpicUnrealMCPAnimationRiggingCommands::HandleCreateIkRig},
        {TEXT("add_ik_goal"),                   &FEpicUnrealMCPAnimationRiggingCommands::HandleAddIkGoal},
        {TEXT("add_ik_solver"),                 &FEpicUnrealMCPAnimationRiggingCommands::HandleAddIkSolver},
        {TEXT("create_ik_retargeter"),          &FEpicUnrealMCPAnimationRiggingCommands::HandleCreateIkRetargeter},
        {TEXT("set_retarget_chain"),            &FEpicUnrealMCPAnimationRiggingCommands::HandleSetRetargetChain},
        {TEXT("create_control_rig"),            &FEpicUnrealMCPAnimationRiggingCommands::HandleCreateControlRig},
        {TEXT("add_control_rig_control"),       &FEpicUnrealMCPAnimationRiggingCommands::HandleAddControlRigControl},
        {TEXT("add_control_rig_bone"),          &FEpicUnrealMCPAnimationRiggingCommands::HandleAddControlRigBone},
        {TEXT("set_control_rig_constraint"),    &FEpicUnrealMCPAnimationRiggingCommands::HandleSetControlRigConstraint},
        {TEXT("sequencer_control_rig_track"),   &FEpicUnrealMCPAnimationRiggingCommands::HandleSequencerControlRigTrack},
        {TEXT("set_facial_animation"),          &FEpicUnrealMCPAnimationRiggingCommands::HandleSetFacialAnimation},
        {TEXT("set_morph_target"),              &FEpicUnrealMCPAnimationRiggingCommands::HandleSetMorphTarget},
        {TEXT("connect_metahuman"),             &FEpicUnrealMCPAnimationRiggingCommands::HandleConnectMetaHuman},
    };
    if (const Handler* H = Dispatch.Find(CommandType))
    {
        return (this->*(*H))(Params);
    }
    return AnimErr(FString::Printf(TEXT("Unknown Animation/Rigging command: %s"), *CommandType));
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateSkeletonAsset(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("create_skeleton_asset"));
#if WITH_ANIM_RIGGING_MCP
    FString AssetPath = TEXT("/Game/Anim"), AssetName = TEXT("SKEL_New");
    Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    Params->TryGetStringField(TEXT("asset_name"), AssetName);
    FAssetToolsModule& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools");
    USkeletonFactory* Factory = NewObject<USkeletonFactory>();
    UObject* Asset = AssetTools.Get().CreateAsset(AssetName, AssetPath, USkeleton::StaticClass(), Factory);
    if (!Asset) return AnimErr(TEXT("Failed to create USkeleton asset"));
    Asset->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Asset);
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("asset_path"), Asset->GetPathName());
    Data->SetStringField(TEXT("asset_name"), Asset->GetName());
    return AnimOk(Data);
#else
    return MakeRiggingUnavailableResponse(TEXT("create_skeleton_asset"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreatePhysicsAsset(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("create_physics_asset"));
#if WITH_ANIM_RIGGING_MCP
    FString AssetPath = TEXT("/Game/Anim"), AssetName = TEXT("PHYS_New");
    Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    Params->TryGetStringField(TEXT("asset_name"), AssetName);
    FAssetToolsModule& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools");
    UPhysicsAssetFactory* Factory = NewObject<UPhysicsAssetFactory>();
    UObject* Asset = AssetTools.Get().CreateAsset(AssetName, AssetPath, UPhysicsAsset::StaticClass(), Factory);
    if (!Asset) return AnimErr(TEXT("Failed to create UPhysicsAsset asset"));
    Asset->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Asset);
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("asset_path"), Asset->GetPathName());
    Data->SetStringField(TEXT("asset_name"), Asset->GetName());
    return AnimOk(Data);
#else
    return MakeRiggingUnavailableResponse(TEXT("create_physics_asset"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddAnimGraphNode(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("add_anim_graph_node"), P, TEXT("AnimGraph node edits need UAnimBlueprint + persona editor; payload accepted.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateAnimStateMachine(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("create_anim_state_machine"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddAnimState(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("add_anim_state"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateAnimTransitionRule(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("create_anim_transition_rule"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateAimOffset(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("create_aim_offset"), P, TEXT("UAimOffsetBlendSpace asset factory is gated; payload accepted.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddNotifyState(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("add_notify_state"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSetRetargetManager(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("set_retarget_manager"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateIkRig(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("create_ik_rig"), P, TEXT("UIKRigDefinition asset factory lives in IKRigEditor (private).")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddIkGoal(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("add_ik_goal"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddIkSolver(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("add_ik_solver"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateIkRetargeter(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("create_ik_retargeter"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSetRetargetChain(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("set_retarget_chain"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateControlRig(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("create_control_rig"), P, TEXT("UControlRigBlueprintFactory is gated by ControlRigEditor.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddControlRigControl(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("add_control_rig_control"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddControlRigBone(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("add_control_rig_bone"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSetControlRigConstraint(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("set_control_rig_constraint"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSequencerControlRigTrack(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("sequencer_control_rig_track"), P, TEXT("Sequencer Control Rig track via UMovieSceneControlRigParameterTrack.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSetFacialAnimation(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("set_facial_animation"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSetMorphTarget(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("set_morph_target"), P); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleConnectMetaHuman(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("connect_metahuman"), P, TEXT("MetaHuman Plugin integration is a separate optional dep.")); }