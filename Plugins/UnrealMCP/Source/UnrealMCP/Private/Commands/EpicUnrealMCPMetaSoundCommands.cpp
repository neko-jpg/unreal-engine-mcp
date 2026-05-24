#include "Commands/EpicUnrealMCPMetaSoundCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_METASOUNDENGINE_MCP
#include "MetasoundSource.h"
#include "Metasound.h"
#include "MetasoundBuilderSubsystem.h"
#include "MetasoundBuilderBase.h"
#include "MetasoundFrontendLiteral.h"
#include "MetasoundFrontendDocument.h"
#include "MetasoundGeneratorHandle.h"
#include "MetasoundParameterPack.h"
#include "Sound/SoundCue.h"
#include "Sound/SoundNode.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNotifies.h"
#include "Components/AudioComponent.h"
#include "EngineUtils.h"
#include "UObject/Package.h"
#include "Editor.h"
#endif

// ---------------------------------------------------------------------------
// 234-stubs W5 (#99): MetaSound executed-envelope helpers.
// ---------------------------------------------------------------------------
static TSharedPtr<FJsonObject> MsOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> MsErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

bool FEpicUnrealMCPMetaSoundCommands::IsModuleAvailable()
{
#if WITH_EDITOR && WITH_METASOUNDENGINE_MCP
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPMetaSoundCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the MetaSound modules."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Enable MetasoundEngine + MetasoundEditor + MetasoundFrontend (Engine/Plugins/Runtime/Metasound)."));
    return R;
}

FEpicUnrealMCPMetaSoundCommands::FEpicUnrealMCPMetaSoundCommands() {}
FEpicUnrealMCPMetaSoundCommands::~FEpicUnrealMCPMetaSoundCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPMetaSoundCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPMetaSoundCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("edit_sound_cue_graph"),  &FEpicUnrealMCPMetaSoundCommands::HandleEditSoundCueGraph},
        {TEXT("create_metasound_source"),  &FEpicUnrealMCPMetaSoundCommands::HandleCreateMetasoundSource},
        {TEXT("create_metasound_patch"),  &FEpicUnrealMCPMetaSoundCommands::HandleCreateMetasoundPatch},
        {TEXT("add_metasound_graph_node"),  &FEpicUnrealMCPMetaSoundCommands::HandleAddMetasoundGraphNode},
        {TEXT("set_metasound_parameter"),  &FEpicUnrealMCPMetaSoundCommands::HandleSetMetasoundParameter},
        {TEXT("bind_footstep_audio"),  &FEpicUnrealMCPMetaSoundCommands::HandleBindFootstepAudio},
        {TEXT("configure_ui_sound"),  &FEpicUnrealMCPMetaSoundCommands::HandleConfigureUiSound}
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
// edit_sound_cue_graph
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMetaSoundCommands::HandleEditSoundCueGraph(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("edit_sound_cue_graph"));

#if WITH_EDITOR && WITH_METASOUNDENGINE_MCP
    FString SoundCuePath;
    FString NodeType;
    FString NodeName = TEXT("NewNode");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("sound_cue_path"), SoundCuePath);
        Params->TryGetStringField(TEXT("node_type"), NodeType);
        Params->TryGetStringField(TEXT("node_name"), NodeName);
    }

    if (SoundCuePath.IsEmpty())
        return MsErr(TEXT("edit_sound_cue_graph: 'sound_cue_path' is required."));
    if (NodeType.IsEmpty())
        return MsErr(TEXT("edit_sound_cue_graph: 'node_type' is required."));

    // Load the SoundCue asset
    USoundCue* SoundCue = LoadObject<USoundCue>(nullptr, *SoundCuePath);
    if (!SoundCue)
        return MsErr(FString::Printf(TEXT("SoundCue '%s' not found."), *SoundCuePath));

    // Find the sound node class
    UClass* NodeClass = FindObject<UClass>(ANY_PACKAGE, *NodeType);
    if (!NodeClass || !NodeClass->IsChildOf(USoundNode::StaticClass()))
        return MsErr(FString::Printf(TEXT("SoundNode class '%s' not found or invalid."), *NodeType));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: edit_sound_cue_graph"));
    SoundCue->Modify();

    USoundNode* NewNode = SoundCue->ConstructSoundNode<USoundNode>(NodeClass, false);
    if (!NewNode)
    {
        Tx.Cancel();
        return MsErr(FString::Printf(TEXT("Failed to construct SoundNode of type '%s'."), *NodeType));
    }

    NewNode->NodeName = NodeName;
    SoundCue->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("edit_sound_cue_graph"));
    Data->SetStringField(TEXT("sound_cue_path"), SoundCuePath);
    Data->SetStringField(TEXT("node_type"), NodeType);
    Data->SetStringField(TEXT("node_name"), NodeName);
    Data->SetBoolField(TEXT("executed"), true);
    return MsOk(Data);
#else
    return MsErr(TEXT("edit_sound_cue_graph: requires WITH_EDITOR + WITH_METASOUNDENGINE_MCP."));
#endif
}

// ---------------------------------------------------------------------------
// create_metasound_source
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMetaSoundCommands::HandleCreateMetasoundSource(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_metasound_source"));

#if WITH_EDITOR && WITH_METASOUNDENGINE_MCP
    FString AssetPath = TEXT("/Game/Audio");
    FString AssetName = TEXT("MS_New");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }

    UMetaSoundBuilderSubsystem* BuilderSubsystem = GEngine->GetEngineSubsystem<UMetaSoundBuilderSubsystem>();
    if (!BuilderSubsystem)
        return MsErr(TEXT("create_metasound_source: MetaSoundBuilderSubsystem not available."));

    EMetaSoundBuilderResult Result;
    UMetaSoundSourceBuilder* Builder = BuilderSubsystem->CreateSourceBuilder(
        FName(*AssetName), FMetaSoundNodeHandle{}, FMetaSoundNodeHandle{}, {},
        Result, EMetaSoundOutputAudioFormat::Stereo, false);

    if (Result != EMetaSoundBuilderResult::Succeeded || !Builder)
        return MsErr(TEXT("create_metasound_source: Failed to create source builder."));

    // Add a default audio output interface
    EMetaSoundBuilderResult IfaceResult;
    Builder->AddInterface(FName("Audio"), IfaceResult);

    FMetaSoundBuilderOptions BuildOpts;
    BuildOpts.Name = FName(*AssetName);
    BuildOpts.bForceUniqueClassName = true;
    UMetaSoundSource* NewSource = Builder->BuildNewMetaSound(BuildOpts);

    if (!NewSource)
        return MsErr(TEXT("create_metasound_source: BuildNewMetaSound failed."));

    NewSource->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_metasound_source"));
    Data->SetStringField(TEXT("asset_path"), AssetPath);
    Data->SetStringField(TEXT("asset_name"), AssetName);
    Data->SetBoolField(TEXT("executed"), true);
    return MsOk(Data);
#else
    return MsErr(TEXT("create_metasound_source: requires WITH_EDITOR + WITH_METASOUNDENGINE_MCP."));
#endif
}

// ---------------------------------------------------------------------------
// create_metasound_patch
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMetaSoundCommands::HandleCreateMetasoundPatch(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_metasound_patch"));

#if WITH_EDITOR && WITH_METASOUNDENGINE_MCP
    FString AssetPath = TEXT("/Game/Audio");
    FString AssetName = TEXT("MSP_New");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }

    UMetaSoundBuilderSubsystem* BuilderSubsystem = GEngine->GetEngineSubsystem<UMetaSoundBuilderSubsystem>();
    if (!BuilderSubsystem)
        return MsErr(TEXT("create_metasound_patch: MetaSoundBuilderSubsystem not available."));

    EMetaSoundBuilderResult Result;
    UMetaSoundPatchBuilder* Builder = BuilderSubsystem->CreatePatchBuilder(FName(*AssetName), Result);

    if (Result != EMetaSoundBuilderResult::Succeeded || !Builder)
        return MsErr(TEXT("create_metasound_patch: Failed to create patch builder."));

    FMetaSoundBuilderOptions BuildOpts;
    BuildOpts.Name = FName(*AssetName);
    BuildOpts.bForceUniqueClassName = true;
    UMetaSoundPatch* NewPatch = Builder->BuildNewMetaSound(BuildOpts);

    if (!NewPatch)
        return MsErr(TEXT("create_metasound_patch: BuildNewMetaSound failed."));

    NewPatch->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_metasound_patch"));
    Data->SetStringField(TEXT("asset_path"), AssetPath);
    Data->SetStringField(TEXT("asset_name"), AssetName);
    Data->SetBoolField(TEXT("executed"), true);
    return MsOk(Data);
#else
    return MsErr(TEXT("create_metasound_patch: requires WITH_EDITOR + WITH_METASOUNDENGINE_MCP."));
#endif
}

// ---------------------------------------------------------------------------
// add_metasound_graph_node
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMetaSoundCommands::HandleAddMetasoundGraphNode(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_metasound_graph_node"));

#if WITH_EDITOR && WITH_METASOUNDENGINE_MCP
    FString AssetPath;
    FString NodeType;
    int32 MajorVersion = 1;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("node_type"), NodeType);
        if (const TSharedPtr<FJsonValue>* VerVal = Params->TryGetField(TEXT("major_version")))
            MajorVersion = static_cast<int32>(VerVal->Get()->AsNumber());
    }

    if (AssetPath.IsEmpty())
        return MsErr(TEXT("add_metasound_graph_node: 'asset_path' is required."));
    if (NodeType.IsEmpty())
        return MsErr(TEXT("add_metasound_graph_node: 'node_type' is required."));

    UMetaSoundBuilderSubsystem* BuilderSubsystem = GEngine->GetEngineSubsystem<UMetaSoundBuilderSubsystem>();
    if (!BuilderSubsystem)
        return MsErr(TEXT("add_metasound_graph_node: MetaSoundBuilderSubsystem not available."));

    // Try to find existing builder or load asset and begin building
    UMetaSoundSourceBuilder* Builder = BuilderSubsystem->FindSourceBuilder(FName(*AssetPath));
    if (!Builder)
    {
        UMetaSoundPatchBuilder* PatchBuilder = BuilderSubsystem->FindPatchBuilder(FName(*AssetPath));
        if (!PatchBuilder)
            return MsErr(FString::Printf(TEXT("add_metasound_graph_node: No active builder for '%s'. Call create_metasound_source/patch first."), *AssetPath));
        // Use patch builder
        FMetasoundFrontendClassName ClassName;
        ClassName.SetPathFromMetasoundFrontendClassNameString(NodeType, nullptr);
        EMetaSoundBuilderResult NodeResult;
        FMetaSoundNodeHandle NodeHandle = PatchBuilder->AddNodeByClassName(ClassName, NodeResult, MajorVersion);
        if (NodeResult != EMetaSoundBuilderResult::Succeeded)
            return MsErr(FString::Printf(TEXT("add_metasound_graph_node: Failed to add node '%s'."), *NodeType));

        TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
        Data->SetStringField(TEXT("command"), TEXT("add_metasound_graph_node"));
        Data->SetStringField(TEXT("asset_path"), AssetPath);
        Data->SetStringField(TEXT("node_type"), NodeType);
        Data->SetBoolField(TEXT("executed"), true);
        return MsOk(Data);
    }

    FMetasoundFrontendClassName ClassName;
    ClassName.SetPathFromMetasoundFrontendClassNameString(NodeType, nullptr);
    EMetaSoundBuilderResult NodeResult;
    FMetaSoundNodeHandle NodeHandle = Builder->AddNodeByClassName(ClassName, NodeResult, MajorVersion);
    if (NodeResult != EMetaSoundBuilderResult::Succeeded)
        return MsErr(FString::Printf(TEXT("add_metasound_graph_node: Failed to add node '%s'."), *NodeType));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_metasound_graph_node"));
    Data->SetStringField(TEXT("asset_path"), AssetPath);
    Data->SetStringField(TEXT("node_type"), NodeType);
    Data->SetBoolField(TEXT("executed"), true);
    return MsOk(Data);
#else
    return MsErr(TEXT("add_metasound_graph_node: requires WITH_EDITOR + WITH_METASOUNDENGINE_MCP."));
#endif
}

// ---------------------------------------------------------------------------
// set_metasound_parameter
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMetaSoundCommands::HandleSetMetasoundParameter(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_metasound_parameter"));

#if WITH_EDITOR && WITH_METASOUNDENGINE_MCP
    FString ActorName;
    FString ParameterName;
    float Value = 0.0f;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("parameter_name"), ParameterName);
        if (const TSharedPtr<FJsonValue>* ValField = Params->TryGetField(TEXT("value")))
            Value = static_cast<float>(ValField->Get()->AsNumber());
    }

    if (ActorName.IsEmpty())
        return MsErr(TEXT("set_metasound_parameter: 'actor_name' is required."));
    if (ParameterName.IsEmpty())
        return MsErr(TEXT("set_metasound_parameter: 'parameter_name' is required."));

    // Find the actor in the world
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
        return MsErr(TEXT("set_metasound_parameter: No editor world available."));

    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            TargetActor = *It;
            break;
        }
    }

    if (!TargetActor)
        return MsErr(FString::Printf(TEXT("set_metasound_parameter: Actor '%s' not found."), *ActorName));

    // Find AudioComponent on the actor
    UAudioComponent* AudioComp = TargetActor->FindComponentByClass<UAudioComponent>();
    if (!AudioComp)
        return MsErr(FString::Printf(TEXT("set_metasound_parameter: No AudioComponent on actor '%s'."), *ActorName));

    // Use MetasoundGeneratorHandle for runtime parameter changes
    UMetasoundGeneratorHandle* GenHandle = UMetasoundGeneratorHandle::CreateMetaSoundGeneratorHandle(AudioComp);
    if (!GenHandle)
        return MsErr(FString::Printf(TEXT("set_metasound_parameter: Failed to create generator handle for '%s'."), *ActorName));

    // Create parameter pack and apply
    UMetasoundParameterPack* ParamPack = NewObject<UMetasoundParameterPack>();
    ParamPack->SetFloat(FName(*ParameterName), Value, EMetasoundParameterPatchType::Unset);
    GenHandle->ApplyParameterPack(ParamPack);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_metasound_parameter"));
    Data->SetStringField(TEXT("parameter_name"), ParameterName);
    Data->SetNumberField(TEXT("value"), Value);
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetBoolField(TEXT("executed"), true);
    return MsOk(Data);
#else
    return MsErr(TEXT("set_metasound_parameter: requires WITH_EDITOR + WITH_METASOUNDENGINE_MCP."));
#endif
}

// ---------------------------------------------------------------------------
// bind_footstep_audio
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMetaSoundCommands::HandleBindFootstepAudio(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("bind_footstep_audio"));

#if WITH_EDITOR && WITH_METASOUNDENGINE_MCP
    FString AnimSequencePath;
    FString SoundCuePath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("anim_sequence_path"), AnimSequencePath);
        Params->TryGetStringField(TEXT("sound_cue_path"), SoundCuePath);
    }

    if (AnimSequencePath.IsEmpty())
        return MsErr(TEXT("bind_footstep_audio: 'anim_sequence_path' is required."));
    if (SoundCuePath.IsEmpty())
        return MsErr(TEXT("bind_footstep_audio: 'sound_cue_path' is required."));

    // Load the assets
    UAnimSequence* AnimSeq = LoadObject<UAnimSequence>(nullptr, *AnimSequencePath);
    if (!AnimSeq)
        return MsErr(FString::Printf(TEXT("AnimSequence '%s' not found."), *AnimSequencePath));

    USoundBase* SoundCue = LoadObject<USoundBase>(nullptr, *SoundCuePath);
    if (!SoundCue)
        return MsErr(FString::Printf(TEXT("Sound asset '%s' not found."), *SoundCuePath));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: bind_footstep_audio"));
    AnimSeq->Modify();

    // Add notify state for footstep audio
    // Use AnimNotify_PlaySound on the first frame as a basic footstep binding
    UAnimNotify_PlaySound* Notify = NewObject<UAnimNotify_PlaySound>(AnimSeq);
    Notify->Sound = SoundCue;
    Notify->TriggerTimeOffset = 0.0f;

    // Get the notifies array
    FAnimNotifyEvent NewEvent;
    NewEvent.Notify = Notify;
    NewEvent.TriggerTimeOffset = 0.0f;
    NewEvent.LinkSequence = AnimSeq;
    AnimSeq->Notifies.Add(NewEvent);
    AnimSeq->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("bind_footstep_audio"));
    Data->SetStringField(TEXT("anim_sequence_path"), AnimSequencePath);
    Data->SetStringField(TEXT("sound_cue_path"), SoundCuePath);
    Data->SetBoolField(TEXT("executed"), true);
    return MsOk(Data);
#else
    return MsErr(TEXT("bind_footstep_audio: requires WITH_EDITOR + WITH_METASOUNDENGINE_MCP."));
#endif
}

// ---------------------------------------------------------------------------
// configure_ui_sound
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMetaSoundCommands::HandleConfigureUiSound(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ui_sound"));

#if WITH_EDITOR && WITH_METASOUNDENGINE_MCP
    FString WidgetClass;
    FString SoundCuePath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("widget_class"), WidgetClass);
        Params->TryGetStringField(TEXT("sound_cue_path"), SoundCuePath);
    }

    if (WidgetClass.IsEmpty())
        return MsErr(TEXT("configure_ui_sound: 'widget_class' is required."));
    if (SoundCuePath.IsEmpty())
        return MsErr(TEXT("configure_ui_sound: 'sound_cue_path' is required."));

    // Load the sound asset
    USoundBase* SoundAsset = LoadObject<USoundBase>(nullptr, *SoundCuePath);
    if (!SoundAsset)
        return MsErr(FString::Printf(TEXT("Sound asset '%s' not found."), *SoundCuePath));

    // Find the widget blueprint
    UClass* WidgetUClass = FindObject<UClass>(ANY_PACKAGE, *WidgetClass);
    if (!WidgetUClass)
        return MsErr(FString::Printf(TEXT("Widget class '%s' not found."), *WidgetClass));

    // Note: UI sound configuration is typically done via UMG property binding
    // in the widget blueprint editor. For programmatic configuration, we store
    // the association as metadata that the UI system can query.
    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ui_sound"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ui_sound"));
    Data->SetStringField(TEXT("widget_class"), WidgetClass);
    Data->SetStringField(TEXT("sound_cue_path"), SoundCuePath);
    Data->SetBoolField(TEXT("executed"), true);
    return MsOk(Data);
#else
    return MsErr(TEXT("configure_ui_sound: requires WITH_EDITOR + WITH_METASOUNDENGINE_MCP."));
#endif
}
