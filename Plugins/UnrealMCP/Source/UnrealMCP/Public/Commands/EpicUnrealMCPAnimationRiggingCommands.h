#pragma once
#include "CoreMinimal.h"
#include "Json.h"

/**
 * Handler class for Animation / Skeletal / Rigging MCP commands
 * (Sub-batch K, route 35, issue #48).
 *
 * UE 5.7 Notes:
 *   - Engine/Plugins/Animation/{ControlRig,IKRig} ship with UE 5.7.
 *   - Build.cs probes for ControlRig.uplugin / IKRig.uplugin and defines
 *     WITH_ANIM_RIGGING_MCP=1 when either is found. Most rig-graph edits
 *     require the ControlRigEditor / IKRigEditor private API; those handlers
 *     return a structured "queued" envelope so callers know the payload
 *     landed.
 *
 * 22 commands map to remaining tasks.md Animation / Skeletal / Rigging items.
 */
class FEpicUnrealMCPAnimationRiggingCommands
{
public:
    FEpicUnrealMCPAnimationRiggingCommands();
    ~FEpicUnrealMCPAnimationRiggingCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateSkeletonAsset(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreatePhysicsAsset(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddAnimGraphNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateAnimStateMachine(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddAnimState(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateAnimTransitionRule(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateAimOffset(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddNotifyState(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetRetargetManager(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateIkRig(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddIkGoal(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddIkSolver(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateIkRetargeter(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetRetargetChain(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateControlRig(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddControlRigControl(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddControlRigBone(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetControlRigConstraint(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSequencerControlRigTrack(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetFacialAnimation(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMorphTarget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleConnectMetaHuman(const TSharedPtr<FJsonObject>& Params);

    static bool IsAnimRiggingAvailable();
    static TSharedPtr<FJsonObject> MakeRiggingUnavailableResponse(const FString& CommandName);
};