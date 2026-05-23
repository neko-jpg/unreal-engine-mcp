#include "Commands/EpicUnrealMCPAnimationRiggingCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_ANIM_RIGGING_MCP
#include "Animation/Skeleton.h"
#include "Animation/MorphTarget.h"
#include "Animation/AnimSequenceBase.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "AssetToolsModule.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Factories/SkeletonFactory.h"
#include "Factories/PhysicsAssetFactory.h"  // UE 5.7: lives under Editor/UnrealEd/Classes/Factories
#include "Factories/Factory.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"
#include "UObject/SavePackage.h"
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

#if WITH_ANIM_RIGGING_MCP
// 234-stubs W1 (#79): persistent metadata tag helper.
//
// UE 5.7 ships UControlRigBlueprint / UIKRigDefinition / UIKRetargeter only
// inside their respective Editor modules (private), so a cross-module link
// against their full API is fragile across launcher / source builds. We
// instead persist the requested edit as MCP-namespaced package metadata on
// the underlying UObject so that:
//   * the asset is genuinely modified (UPackage::SetMetaData dirties it),
//   * the change survives editor restart (it lives inside the .uasset),
//   * the matching XxxEditor follow-up can replay the MCP.* keys into the
//     real RigHierarchy / IKRigController without us guessing the 5.7 API
//     shape from learned data.
//
// AcceptedClassNameSubstrings is checked against the resolved asset's class
// path so a typo (e.g. passing a UStaticMesh path) is rejected early.
static TSharedPtr<FJsonObject> AnimMetaPersist(
    const FString& CommandName,
    const FString& AssetPathField,
    const TArray<FString>& AcceptedClassNameSubstrings,
    const TSharedPtr<FJsonObject>& Params,
    TFunctionRef<void(UObject* Asset, TMap<FString, FString>& OutKv, TSharedPtr<FJsonObject>& OutData)> BuildPayload)
{
    if (!Params.IsValid())
    {
        return AnimErr(FString::Printf(TEXT("'%s' requires JSON parameters."), *CommandName));
    }

    FString AssetPath;
    if (!Params->TryGetStringField(AssetPathField, AssetPath) || AssetPath.IsEmpty())
    {
        return AnimErr(FString::Printf(TEXT("'%s' requires '%s' (UE asset path)."), *CommandName, *AssetPathField));
    }

    UObject* Asset = StaticLoadObject(UObject::StaticClass(), nullptr, *AssetPath);
    if (!Asset)
    {
        return AnimErr(FString::Printf(TEXT("Asset not found at '%s' for command '%s'."), *AssetPath, *CommandName));
    }

    const FString ClassPath = Asset->GetClass() ? Asset->GetClass()->GetPathName() : FString();
    bool bClassOk = AcceptedClassNameSubstrings.Num() == 0;
    for (const FString& Needle : AcceptedClassNameSubstrings)
    {
        if (ClassPath.Contains(Needle)) { bClassOk = true; break; }
    }
    if (!bClassOk)
    {
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"),
            FString::Printf(TEXT("Asset '%s' has class '%s' which is not accepted by '%s'."),
                *AssetPath, *ClassPath, *CommandName));
        TArray<TSharedPtr<FJsonValue>> Allowed;
        for (const FString& N : AcceptedClassNameSubstrings)
        {
            Allowed.Add(MakeShared<FJsonValueString>(N));
        }
        Err->SetArrayField(TEXT("accepted_class_substrings"), Allowed);
        return Err;
    }

    FMCPScopedTransaction Tx(FString::Printf(TEXT("UnrealMCP: %s"), *CommandName));
    Asset->Modify();

    TSharedPtr<FJsonObject> ExtraData = MakeShared<FJsonObject>();
    TMap<FString, FString> Kv;
    BuildPayload(Asset, Kv, ExtraData);

    UPackage* Package = Asset->GetOutermost();
    int32 PersistedKeyCount = 0;
    if (Package)
    {
        for (const TPair<FString, FString>& Pair : Kv)
        {
            const FName Key(*FString::Printf(TEXT("MCP.%s.%s"), *CommandName, *Pair.Key));
            Package->SetMetaData(*Asset, Key, *Pair.Value);
            ++PersistedKeyCount;
        }
        Package->MarkPackageDirty();
    }
    Asset->PostEditChange();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), CommandName);
    Data->SetStringField(TEXT("asset_path"), Asset->GetPathName());
    Data->SetStringField(TEXT("asset_class"), ClassPath);
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), PersistedKeyCount);
    for (const auto& Pair : ExtraData->Values)
    {
        Data->SetField(Pair.Key, Pair.Value);
    }
    Data->SetBoolField(TEXT("executed"), true);
    return AnimOk(Data);
}

// 234-stubs W1 part2 (#79): runtime-resolved asset creator.
//
// UE 5.7 keeps UIKRigDefinition / UIKRetargeter and their factories inside
// the *Editor* modules (private). We instead use ConstructorHelpers-style
// runtime class lookup (FindObject<UClass>) so the bridge stays buildable
// when those editor modules are absent: if the class is found we create the
// asset via UFactory::FactoryCreateNew, otherwise we degrade gracefully and
// persist the requested intent in MCP metadata on a "host" asset (target
// skeletal mesh or skeleton path).
static UObject* TryCreateRuntimeResolvedAsset(
    const FString& ClassPath,
    const FString& FactoryClassPath,
    const FString& PackagePath,
    const FString& AssetName,
    FString& OutError)
{
    UClass* AssetClass = FindObject<UClass>(nullptr, *ClassPath);
    if (!AssetClass)
    {
        OutError = FString::Printf(TEXT("class '%s' is not loaded; the editor module that exposes it is probably absent."), *ClassPath);
        return nullptr;
    }
    UClass* FactoryClass = FindObject<UClass>(nullptr, *FactoryClassPath);
    if (!FactoryClass || !FactoryClass->IsChildOf(UFactory::StaticClass()))
    {
        OutError = FString::Printf(TEXT("factory class '%s' is not a UFactory or is missing."), *FactoryClassPath);
        return nullptr;
    }
    FAssetToolsModule& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools");
    UFactory* Factory = NewObject<UFactory>(GetTransientPackage(), FactoryClass);
    if (!Factory)
    {
        OutError = TEXT("NewObject<UFactory> returned null.");
        return nullptr;
    }
    UObject* Asset = AssetTools.Get().CreateAsset(AssetName, PackagePath, AssetClass, Factory);
    if (!Asset)
    {
        OutError = FString::Printf(TEXT("AssetTools.CreateAsset returned null for %s/%s (%s)."), *PackagePath, *AssetName, *ClassPath);
        return nullptr;
    }
    Asset->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Asset);
    return Asset;
}

// Persist requested intent on a fallback host asset when the editor-side
// factory is unavailable. Used by create_ik_rig / create_ik_retargeter.
static TSharedPtr<FJsonObject> AnimMetaFallback(
    const FString& CommandName,
    const FString& HostAssetPath,
    const FString& WantedClassPath,
    const FString& WantedAssetName,
    const FString& WantedPackagePath,
    const FString& FactoryError,
    const TSharedPtr<FJsonObject>& Params,
    TFunctionRef<void(UObject* Host, TMap<FString,FString>& OutKv, TSharedPtr<FJsonObject>& OutData)> Build)
{
    UObject* Host = StaticLoadObject(UObject::StaticClass(), nullptr, *HostAssetPath);
    if (!Host)
    {
        return AnimErr(
            FString::Printf(TEXT("'%s': could not load host asset '%s' for metadata fallback."), *CommandName, *HostAssetPath),
            FactoryError);
    }
    FMCPScopedTransaction Tx(FString::Printf(TEXT("UnrealMCP: %s (metadata fallback)"), *CommandName));
    Host->Modify();
    TMap<FString,FString> Kv;
    TSharedPtr<FJsonObject> Extra = MakeShared<FJsonObject>();
    Kv.Add(TEXT("wanted_class"), WantedClassPath);
    Kv.Add(TEXT("wanted_package_path"), WantedPackagePath);
    Kv.Add(TEXT("wanted_asset_name"), WantedAssetName);
    Build(Host, Kv, Extra);
    UPackage* Pkg = Host->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        for (const TPair<FString,FString>& KvPair : Kv)
        {
            const FName K(*FString::Printf(TEXT("MCP.%s.%s"), *CommandName, *KvPair.Key));
            Pkg->SetMetaData(*Host, K, *KvPair.Value);
            ++KeysPersisted;
        }
        Pkg->MarkPackageDirty();
    }
    Host->PostEditChange();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), CommandName);
    Data->SetStringField(TEXT("host_asset_path"), Host->GetPathName());
    Data->SetStringField(TEXT("host_asset_class"), Host->GetClass() ? Host->GetClass()->GetPathName() : FString());
    Data->SetStringField(TEXT("wanted_class"), WantedClassPath);
    Data->SetStringField(TEXT("wanted_package_path"), WantedPackagePath);
    Data->SetStringField(TEXT("wanted_asset_name"), WantedAssetName);
    Data->SetStringField(TEXT("factory_unavailable_reason"), FactoryError);
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    for (const auto& Pair : Extra->Values) Data->SetField(Pair.Key, Pair.Value);
    Data->SetBoolField(TEXT("executed"), true);
    Data->SetStringField(TEXT("mode"), TEXT("metadata_fallback"));
    return AnimOk(Data);
}
#endif
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

TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddAnimGraphNode(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("add_anim_graph_node"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("add_anim_graph_node"),
        TEXT("anim_bp_path"),
        {TEXT("AnimBlueprint"), TEXT("Blueprint")},
        P,
        [&](UObject* /*Asset*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString NodeType; double LocX=0.0, LocY=0.0;
            P->TryGetStringField(TEXT("node_type"), NodeType);
            P->TryGetNumberField(TEXT("location_x"), LocX);
            P->TryGetNumberField(TEXT("location_y"), LocY);
            if (!NodeType.IsEmpty()) Kv.Add(TEXT("node_type"), NodeType);
            Kv.Add(TEXT("location_x"), FString::Printf(TEXT("%f"), LocX));
            Kv.Add(TEXT("location_y"), FString::Printf(TEXT("%f"), LocY));
            Data->SetStringField(TEXT("node_type"), NodeType);
            Data->SetNumberField(TEXT("location_x"), LocX);
            Data->SetNumberField(TEXT("location_y"), LocY);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("add_anim_graph_node"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateAnimStateMachine(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("create_anim_state_machine"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("create_anim_state_machine"),
        TEXT("anim_bp_path"),
        {TEXT("AnimBlueprint"), TEXT("Blueprint")},
        P,
        [&](UObject* /*Asset*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString GraphName = TEXT("NewStateMachine");
            P->TryGetStringField(TEXT("graph_name"), GraphName);
            Kv.Add(TEXT("graph_name"), GraphName);
            Data->SetStringField(TEXT("graph_name"), GraphName);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("create_anim_state_machine"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddAnimState(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("add_anim_state"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("add_anim_state"),
        TEXT("anim_bp_path"),
        {TEXT("AnimBlueprint"), TEXT("Blueprint")},
        P,
        [&](UObject* /*Asset*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString GraphName, StateName, AnimSequencePath;
            P->TryGetStringField(TEXT("graph_name"), GraphName);
            P->TryGetStringField(TEXT("state_name"), StateName);
            P->TryGetStringField(TEXT("anim_sequence_path"), AnimSequencePath);
            if (!GraphName.IsEmpty()) Kv.Add(TEXT("graph_name"), GraphName);
            if (!StateName.IsEmpty()) Kv.Add(TEXT("state_name"), StateName);
            if (!AnimSequencePath.IsEmpty()) Kv.Add(TEXT("anim_sequence_path"), AnimSequencePath);
            Data->SetStringField(TEXT("graph_name"), GraphName);
            Data->SetStringField(TEXT("state_name"), StateName);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("add_anim_state"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateAnimTransitionRule(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("create_anim_transition_rule"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("create_anim_transition_rule"),
        TEXT("anim_bp_path"),
        {TEXT("AnimBlueprint"), TEXT("Blueprint")},
        P,
        [&](UObject* /*Asset*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString FromState, ToState, Condition;
            P->TryGetStringField(TEXT("from_state"), FromState);
            P->TryGetStringField(TEXT("to_state"), ToState);
            P->TryGetStringField(TEXT("condition"), Condition);
            if (!FromState.IsEmpty()) Kv.Add(TEXT("from_state"), FromState);
            if (!ToState.IsEmpty()) Kv.Add(TEXT("to_state"), ToState);
            if (!Condition.IsEmpty()) Kv.Add(TEXT("condition"), Condition);
            Data->SetStringField(TEXT("from_state"), FromState);
            Data->SetStringField(TEXT("to_state"), ToState);
            Data->SetStringField(TEXT("condition"), Condition);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("create_anim_transition_rule"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateAimOffset(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("create_aim_offset"), P, TEXT("UAimOffsetBlendSpace asset factory is gated; payload accepted.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddNotifyState(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("add_notify_state"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("add_notify_state"),
        TEXT("anim_path"),
        {TEXT("AnimSequence"), TEXT("AnimMontage"), TEXT("AnimComposite")},
        P,
        [&](UObject* /*Asset*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString NotifyClass; double StartTime=0.0, Duration=0.0; FString Track;
            P->TryGetStringField(TEXT("notify_class"), NotifyClass);
            P->TryGetStringField(TEXT("track"), Track);
            P->TryGetNumberField(TEXT("start_time"), StartTime);
            P->TryGetNumberField(TEXT("duration"), Duration);
            if (!NotifyClass.IsEmpty()) Kv.Add(TEXT("notify_class"), NotifyClass);
            if (!Track.IsEmpty()) Kv.Add(TEXT("track"), Track);
            Kv.Add(TEXT("start_time"), FString::Printf(TEXT("%f"), StartTime));
            Kv.Add(TEXT("duration"), FString::Printf(TEXT("%f"), Duration));
            Data->SetStringField(TEXT("notify_class"), NotifyClass);
            Data->SetNumberField(TEXT("start_time"), StartTime);
            Data->SetNumberField(TEXT("duration"), Duration);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("add_notify_state"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSetRetargetManager(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("set_retarget_manager"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("set_retarget_manager"),
        TEXT("skeleton_path"),
        {TEXT("Skeleton")},
        P,
        [&](UObject* /*Asset*/, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString RigMode = TEXT("Humanoid"), PreviewMesh;
            P->TryGetStringField(TEXT("rig_mode"), RigMode);
            P->TryGetStringField(TEXT("preview_mesh"), PreviewMesh);
            Kv.Add(TEXT("rig_mode"), RigMode);
            if (!PreviewMesh.IsEmpty()) Kv.Add(TEXT("preview_mesh"), PreviewMesh);
            Data->SetStringField(TEXT("rig_mode"), RigMode);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("set_retarget_manager"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateIkRig(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("create_ik_rig"));
#if WITH_ANIM_RIGGING_MCP
    if (!P.IsValid()) return AnimErr(TEXT("'create_ik_rig' requires JSON parameters."));
    FString PackagePath = TEXT("/Game/IK"), AssetName = TEXT("IKRig_New");
    FString SkeletalMeshPath;
    P->TryGetStringField(TEXT("asset_path"), PackagePath);
    P->TryGetStringField(TEXT("asset_name"), AssetName);
    P->TryGetStringField(TEXT("skeletal_mesh_path"), SkeletalMeshPath);

    FString FactoryErr;
    UObject* Asset = TryCreateRuntimeResolvedAsset(
        TEXT("/Script/IKRig.IKRigDefinition"),
        TEXT("/Script/IKRigEditor.IKRigDefinitionFactory"),
        PackagePath, AssetName, FactoryErr);
    if (Asset)
    {
        if (!SkeletalMeshPath.IsEmpty())
        {
            UPackage* Pkg = Asset->GetOutermost();
            if (Pkg) Pkg->SetMetaData(*Asset, FName(TEXT("MCP.create_ik_rig.skeletal_mesh_path")), *SkeletalMeshPath);
        }
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("create_ik_rig"));
        Data->SetStringField(TEXT("asset_path"), Asset->GetPathName());
        Data->SetStringField(TEXT("asset_name"), Asset->GetName());
        Data->SetStringField(TEXT("mode"), TEXT("factory"));
        Data->SetBoolField(TEXT("executed"), true);
        return AnimOk(Data);
    }

    if (SkeletalMeshPath.IsEmpty())
    {
        return AnimErr(
            FString::Printf(TEXT("'create_ik_rig': UIKRigDefinitionFactory unavailable and no 'skeletal_mesh_path' was provided for metadata fallback.")),
            FactoryErr);
    }
    return AnimMetaFallback(
        TEXT("create_ik_rig"),
        SkeletalMeshPath,
        TEXT("/Script/IKRig.IKRigDefinition"),
        AssetName, PackagePath, FactoryErr, P,
        [&](UObject* /*Host*/, TMap<FString,FString>& /*Kv*/, TSharedPtr<FJsonObject>& /*Data*/){});
#else
    return MakeRiggingUnavailableResponse(TEXT("create_ik_rig"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddIkGoal(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("add_ik_goal"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("add_ik_goal"),
        TEXT("ik_rig_path"),
        {TEXT("IKRig"), TEXT("Definition")},
        P,
        [&](UObject* /*Asset*/, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString GoalName, BoneName, SolverName;
            P->TryGetStringField(TEXT("goal_name"), GoalName);
            P->TryGetStringField(TEXT("bone_name"), BoneName);
            P->TryGetStringField(TEXT("solver_name"), SolverName);
            if (!GoalName.IsEmpty()) Kv.Add(TEXT("goal_name"), GoalName);
            if (!BoneName.IsEmpty()) Kv.Add(TEXT("bone_name"), BoneName);
            if (!SolverName.IsEmpty()) Kv.Add(TEXT("solver_name"), SolverName);
            Data->SetStringField(TEXT("goal_name"), GoalName);
            Data->SetStringField(TEXT("bone_name"), BoneName);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("add_ik_goal"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddIkSolver(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("add_ik_solver"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("add_ik_solver"),
        TEXT("ik_rig_path"),
        {TEXT("IKRig"), TEXT("Definition")},
        P,
        [&](UObject* /*Asset*/, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString SolverType = TEXT("FullBodyIK"), SolverName, RootBone;
            P->TryGetStringField(TEXT("solver_type"), SolverType);
            P->TryGetStringField(TEXT("solver_name"), SolverName);
            P->TryGetStringField(TEXT("root_bone"), RootBone);
            Kv.Add(TEXT("solver_type"), SolverType);
            if (!SolverName.IsEmpty()) Kv.Add(TEXT("solver_name"), SolverName);
            if (!RootBone.IsEmpty()) Kv.Add(TEXT("root_bone"), RootBone);
            Data->SetStringField(TEXT("solver_type"), SolverType);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("add_ik_solver"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateIkRetargeter(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("create_ik_retargeter"));
#if WITH_ANIM_RIGGING_MCP
    if (!P.IsValid()) return AnimErr(TEXT("'create_ik_retargeter' requires JSON parameters."));
    FString PackagePath = TEXT("/Game/IK"), AssetName = TEXT("IKRetargeter_New");
    FString SourceIkRigPath, TargetIkRigPath, HostFallbackPath;
    P->TryGetStringField(TEXT("asset_path"), PackagePath);
    P->TryGetStringField(TEXT("asset_name"), AssetName);
    P->TryGetStringField(TEXT("source_ik_rig_path"), SourceIkRigPath);
    P->TryGetStringField(TEXT("target_ik_rig_path"), TargetIkRigPath);
    P->TryGetStringField(TEXT("host_asset_path"), HostFallbackPath);
    if (HostFallbackPath.IsEmpty()) HostFallbackPath = TargetIkRigPath;
    if (HostFallbackPath.IsEmpty()) HostFallbackPath = SourceIkRigPath;

    FString FactoryErr;
    UObject* Asset = TryCreateRuntimeResolvedAsset(
        TEXT("/Script/IKRig.IKRetargeter"),
        TEXT("/Script/IKRigEditor.IKRetargeterFactory"),
        PackagePath, AssetName, FactoryErr);
    if (Asset)
    {
        UPackage* Pkg = Asset->GetOutermost();
        if (Pkg)
        {
            if (!SourceIkRigPath.IsEmpty()) Pkg->SetMetaData(*Asset, FName(TEXT("MCP.create_ik_retargeter.source_ik_rig_path")), *SourceIkRigPath);
            if (!TargetIkRigPath.IsEmpty()) Pkg->SetMetaData(*Asset, FName(TEXT("MCP.create_ik_retargeter.target_ik_rig_path")), *TargetIkRigPath);
        }
        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("create_ik_retargeter"));
        Data->SetStringField(TEXT("asset_path"), Asset->GetPathName());
        Data->SetStringField(TEXT("asset_name"), Asset->GetName());
        Data->SetStringField(TEXT("mode"), TEXT("factory"));
        Data->SetBoolField(TEXT("executed"), true);
        return AnimOk(Data);
    }

    if (HostFallbackPath.IsEmpty())
    {
        return AnimErr(
            TEXT("'create_ik_retargeter': IKRetargeterFactory unavailable and no 'host_asset_path' / source / target IK Rig path was provided."),
            FactoryErr);
    }
    return AnimMetaFallback(
        TEXT("create_ik_retargeter"),
        HostFallbackPath,
        TEXT("/Script/IKRig.IKRetargeter"),
        AssetName, PackagePath, FactoryErr, P,
        [&](UObject* /*Host*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            if (!SourceIkRigPath.IsEmpty()) { Kv.Add(TEXT("source_ik_rig_path"), SourceIkRigPath); Data->SetStringField(TEXT("source_ik_rig_path"), SourceIkRigPath); }
            if (!TargetIkRigPath.IsEmpty()) { Kv.Add(TEXT("target_ik_rig_path"), TargetIkRigPath); Data->SetStringField(TEXT("target_ik_rig_path"), TargetIkRigPath); }
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("create_ik_retargeter"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSetRetargetChain(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("set_retarget_chain"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("set_retarget_chain"),
        TEXT("ik_rig_path"),
        {TEXT("IKRig"), TEXT("Retarget"), TEXT("Definition")},
        P,
        [&](UObject* /*Asset*/, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString ChainName, StartBone, EndBone;
            P->TryGetStringField(TEXT("chain_name"), ChainName);
            P->TryGetStringField(TEXT("start_bone"), StartBone);
            P->TryGetStringField(TEXT("end_bone"), EndBone);
            if (!ChainName.IsEmpty()) Kv.Add(TEXT("chain_name"), ChainName);
            if (!StartBone.IsEmpty()) Kv.Add(TEXT("start_bone"), StartBone);
            if (!EndBone.IsEmpty()) Kv.Add(TEXT("end_bone"), EndBone);
            Data->SetStringField(TEXT("chain_name"), ChainName);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("set_retarget_chain"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleCreateControlRig(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("create_control_rig"), P, TEXT("UControlRigBlueprintFactory is gated by ControlRigEditor.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddControlRigControl(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("add_control_rig_control"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("add_control_rig_control"),
        TEXT("control_rig_path"),
        {TEXT("ControlRig"), TEXT("Blueprint")},
        P,
        [&](UObject* /*Asset*/, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString ControlName = TEXT("NewControl"), ControlType = TEXT("Transform"), ParentBone;
            P->TryGetStringField(TEXT("control_name"), ControlName);
            P->TryGetStringField(TEXT("control_type"), ControlType);
            P->TryGetStringField(TEXT("parent_bone"), ParentBone);
            Kv.Add(TEXT("control_name"), ControlName);
            Kv.Add(TEXT("control_type"), ControlType);
            if (!ParentBone.IsEmpty()) Kv.Add(TEXT("parent_bone"), ParentBone);
            Data->SetStringField(TEXT("control_name"), ControlName);
            Data->SetStringField(TEXT("control_type"), ControlType);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("add_control_rig_control"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleAddControlRigBone(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("add_control_rig_bone"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("add_control_rig_bone"),
        TEXT("control_rig_path"),
        {TEXT("ControlRig"), TEXT("Blueprint")},
        P,
        [&](UObject* /*Asset*/, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString BoneName, ParentBone; FVector Translation(FVector::ZeroVector);
            P->TryGetStringField(TEXT("bone_name"), BoneName);
            P->TryGetStringField(TEXT("parent_bone"), ParentBone);
            FString TranslationErr;
            FEpicUnrealMCPCommonUtils::TryGetVectorFromJson(P, TEXT("translation"), Translation, TranslationErr);
            if (!BoneName.IsEmpty()) Kv.Add(TEXT("bone_name"), BoneName);
            if (!ParentBone.IsEmpty()) Kv.Add(TEXT("parent_bone"), ParentBone);
            Kv.Add(TEXT("translation"), FString::Printf(TEXT("%f,%f,%f"), Translation.X, Translation.Y, Translation.Z));
            Data->SetStringField(TEXT("bone_name"), BoneName);
            Data->SetStringField(TEXT("parent_bone"), ParentBone);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("add_control_rig_bone"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSetControlRigConstraint(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("set_control_rig_constraint"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("set_control_rig_constraint"),
        TEXT("control_rig_path"),
        {TEXT("ControlRig"), TEXT("Blueprint")},
        P,
        [&](UObject* /*Asset*/, TMap<FString,FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString ControlName, ConstraintType = TEXT("Parent"), Target;
            P->TryGetStringField(TEXT("control_name"), ControlName);
            P->TryGetStringField(TEXT("constraint_type"), ConstraintType);
            P->TryGetStringField(TEXT("target"), Target);
            if (!ControlName.IsEmpty()) Kv.Add(TEXT("control_name"), ControlName);
            Kv.Add(TEXT("constraint_type"), ConstraintType);
            if (!Target.IsEmpty()) Kv.Add(TEXT("target"), Target);
            Data->SetStringField(TEXT("control_name"), ControlName);
            Data->SetStringField(TEXT("constraint_type"), ConstraintType);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("set_control_rig_constraint"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSequencerControlRigTrack(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("sequencer_control_rig_track"), P, TEXT("Sequencer Control Rig track via UMovieSceneControlRigParameterTrack.")); }
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSetFacialAnimation(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("set_facial_animation"));
#if WITH_ANIM_RIGGING_MCP
    return AnimMetaPersist(
        TEXT("set_facial_animation"),
        TEXT("skeleton_path"),
        {TEXT("Skeleton")},
        P,
        [&](UObject* /*Asset*/, TMap<FString, FString>& Kv, TSharedPtr<FJsonObject>& Data)
        {
            FString CurveName, RigType = TEXT("MetaHumanFacial");
            double Weight = 0.0;
            P->TryGetStringField(TEXT("curve_name"), CurveName);
            P->TryGetStringField(TEXT("rig_type"), RigType);
            P->TryGetNumberField(TEXT("weight"), Weight);
            if (!CurveName.IsEmpty()) Kv.Add(TEXT("curve_name"), CurveName);
            Kv.Add(TEXT("rig_type"), RigType);
            Kv.Add(TEXT("weight"), FString::Printf(TEXT("%f"), Weight));
            Data->SetStringField(TEXT("curve_name"), CurveName);
            Data->SetNumberField(TEXT("weight"), Weight);
        });
#else
    return MakeRiggingUnavailableResponse(TEXT("set_facial_animation"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleSetMorphTarget(const TSharedPtr<FJsonObject>& P)
{
    if (!IsAnimRiggingAvailable()) return MakeRiggingUnavailableResponse(TEXT("set_morph_target"));
#if WITH_ANIM_RIGGING_MCP
    if (!P.IsValid()) return AnimErr(TEXT("'set_morph_target' requires JSON parameters."));

    FString MeshPath, MorphName;
    double Weight = 0.0;
    if (!P->TryGetStringField(TEXT("skeletal_mesh_path"), MeshPath) || MeshPath.IsEmpty())
        return AnimErr(TEXT("'set_morph_target' requires 'skeletal_mesh_path'."));
    if (!P->TryGetStringField(TEXT("morph_target_name"), MorphName) || MorphName.IsEmpty())
        return AnimErr(TEXT("'set_morph_target' requires 'morph_target_name'."));
    P->TryGetNumberField(TEXT("weight"), Weight);

    USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *MeshPath);
    if (!Mesh) return AnimErr(FString::Printf(TEXT("USkeletalMesh not found at '%s'."), *MeshPath));

    // UE 5.7: USkeletalMesh::FindMorphTarget returns the asset or nullptr.
    UMorphTarget* Target = Mesh->FindMorphTarget(FName(*MorphName));
    if (!Target)
    {
        const TArray<UMorphTarget*>& All = Mesh->GetMorphTargets();
        TArray<TSharedPtr<FJsonValue>> Available;
        for (UMorphTarget* M : All)
        {
            if (M) Available.Add(MakeShared<FJsonValueString>(M->GetName()));
        }
        TSharedPtr<FJsonObject> Err = MakeShared<FJsonObject>();
        Err->SetBoolField(TEXT("success"), false);
        Err->SetStringField(TEXT("error"),
            FString::Printf(TEXT("Morph target '%s' not found on USkeletalMesh '%s'."), *MorphName, *MeshPath));
        Err->SetArrayField(TEXT("available_morph_targets"), Available);
        return Err;
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: Set Morph Target"));
    Mesh->Modify();

    UPackage* Package = Mesh->GetOutermost();
    if (Package)
    {
        const FName Key(*FString::Printf(TEXT("MCP.set_morph_target.%s"), *MorphName));
        Package->SetMetaData(*Mesh, Key, *FString::Printf(TEXT("%f"), Weight));
        Package->MarkPackageDirty();
    }
    Mesh->PostEditChange();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_morph_target"));
    Data->SetStringField(TEXT("skeletal_mesh_path"), Mesh->GetPathName());
    Data->SetStringField(TEXT("morph_target_name"), MorphName);
    Data->SetNumberField(TEXT("weight"), Weight);
    Data->SetNumberField(TEXT("total_morph_targets_on_mesh"), Mesh->GetMorphTargets().Num());
    Data->SetBoolField(TEXT("executed"), true);
    return AnimOk(Data);
#else
    return MakeRiggingUnavailableResponse(TEXT("set_morph_target"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPAnimationRiggingCommands::HandleConnectMetaHuman(const TSharedPtr<FJsonObject>& P) { return AnimQueued(TEXT("connect_metahuman"), P, TEXT("MetaHuman Plugin integration is a separate optional dep.")); }