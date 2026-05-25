#include "Commands/EpicUnrealMCPSequencerExtensionCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#include "Engine/World.h"
#include "LevelSequence.h"
#include "LevelSequenceActor.h"
#include "LevelSequencePlayer.h"
#include "MovieScene.h"
#include "MovieSceneTrack.h"
#include "MovieSceneSection.h"
#include "Sections/MovieSceneSpawnSection.h"
#include "Tracks/MovieSceneSpawnTrack.h"
#include "Tracks/MovieSceneSkeletalAnimationTrack.h"
#include "Evaluation/MovieSceneSequenceTransform.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "CineCameraActor.h"
#include "CineCameraComponent.h"
#include "Components/SplineComponent.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "UObject/Package.h"
#include "UObject/MetaData.h"

bool FEpicUnrealMCPSequencerExtensionCommands::IsModuleAvailable()
{
#if 1
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerExtensionCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPSequencerExtensionCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("CinematicCamera + TakeRecorder + ControlRig + Sequencer modules ship with UE 5.7."));
    return R;
}

FEpicUnrealMCPSequencerExtensionCommands::FEpicUnrealMCPSequencerExtensionCommands() {}
FEpicUnrealMCPSequencerExtensionCommands::~FEpicUnrealMCPSequencerExtensionCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerExtensionCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPSequencerExtensionCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("spawn_camera_rail"),  &FEpicUnrealMCPSequencerExtensionCommands::HandleSpawnCameraRail},
        {TEXT("spawn_camera_crane"),  &FEpicUnrealMCPSequencerExtensionCommands::HandleSpawnCameraCrane},
        {TEXT("sequencer_render_preview"),  &FEpicUnrealMCPSequencerExtensionCommands::HandleSequencerRenderPreview},
        {TEXT("register_take_recorder_source"),  &FEpicUnrealMCPSequencerExtensionCommands::HandleRegisterTakeRecorderSource},
        {TEXT("add_control_rig_track"),  &FEpicUnrealMCPSequencerExtensionCommands::HandleAddControlRigTrack},
        {TEXT("spawn_level_sequence_actor"),  &FEpicUnrealMCPSequencerExtensionCommands::HandleSpawnLevelSequenceActor}
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
// 234-stubs W2 (#87): Sequencer executed-envelope helpers.
//
// SequencerMetaPersist: resolve a UObject (typically ALevelSequenceActor or
// ULevelSequence), open an FMCPScopedTransaction, persist MCP metadata, return
// the canonical executed envelope.
// ---------------------------------------------------------------------------
static TSharedPtr<FJsonObject> SequencerOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> SequencerErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

static ULevelSequence* ResolveLevelSequence(const FString& Path)
{
    if (Path.IsEmpty()) return nullptr;
    return LoadObject<ULevelSequence>(nullptr, *Path);
}

static ALevelSequenceActor* FindOrCreateSequenceActor(UWorld* World, ULevelSequence* Sequence, const FString& ActorName)
{
    if (!World || !Sequence) return nullptr;

    // Look for an existing actor linked to this sequence
    for (TActorIterator<ALevelSequenceActor> It(World); It; ++It)
    {
        ALevelSequenceActor* Existing = *It;
        if (Existing && Existing->GetSequence() == Sequence)
        {
            return Existing;
        }
    }

    // Spawn a new one
    FActorSpawnParameters SP;
    SP.Name = *ActorName;
    ALevelSequenceActor* Actor = World->SpawnActor<ALevelSequenceActor>(ALevelSequenceActor::StaticClass(), FTransform::Identity, SP);
    if (Actor)
    {
        Actor->SetSequence(Sequence);
        Actor->Modify();
        Actor->MarkPackageDirty();
    }
    return Actor;
}

// ---------------------------------------------------------------------------
// spawn_camera_rail — Spawn a spline-based camera rail actor and persist
//                      metadata about the spline points for Sequencer binding.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerExtensionCommands::HandleSpawnCameraRail(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_camera_rail"));

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return SequencerErr(TEXT("No editor world available"));

    FString ActorName = TEXT("CameraRail");
    if (Params.IsValid()) Params->TryGetStringField(TEXT("actor_name"), ActorName);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_camera_rail"));

    FActorSpawnParameters SP;
    SP.Name = *ActorName;
    AActor* RailActor = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, SP);
    if (!RailActor) return SequencerErr(TEXT("Failed to spawn camera rail actor"));

    USplineComponent* Spline = NewObject<USplineComponent>(RailActor, TEXT("RailSpline"));
    Spline->RegisterComponent();
    RailActor->AddInstanceComponent(Spline);
    RailActor->SetRootComponent(Spline);

    // Parse spline points from params
    if (Params.IsValid())
    {
        const TArray<TSharedPtr<FJsonValue>>* Points;
        if (Params->TryGetArrayField(TEXT("rail_spline_points"), Points))
        {
            for (int32 i = 0; i < Points->Num(); ++i)
            {
                const TSharedPtr<FJsonObject>* PtObj;
                if ((*Points)[i]->TryGetObject(PtObj))
                {
                    double X = 0, Y = 0, Z = 0;
                    PtObj->Get()->TryGetNumberField(TEXT("x"), X);
                    PtObj->Get()->TryGetNumberField(TEXT("y"), Y);
                    PtObj->Get()->TryGetNumberField(TEXT("z"), Z);
                    Spline->AddSplinePoint(FVector(X, Y, Z), ESplineCoordinateSpace::World);
                }
            }
        }
    }

    RailActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_camera_rail"));
    Data->SetStringField(TEXT("actor_name"), RailActor->GetName());
    Data->SetNumberField(TEXT("spline_points"), Spline->GetNumberOfSplinePoints());
    Data->SetBoolField(TEXT("executed"), true);
    return SequencerOk(Data);
}

// ---------------------------------------------------------------------------
// spawn_camera_crane — Spawn a crane rig actor with a height parameter.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerExtensionCommands::HandleSpawnCameraCrane(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_camera_crane"));

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return SequencerErr(TEXT("No editor world available"));

    FString ActorName = TEXT("CameraCrane");
    double Height = 300.0;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetNumberField(TEXT("height"), Height);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_camera_crane"));

    FActorSpawnParameters SP;
    SP.Name = *ActorName;
    ACineCameraActor* CraneActor = World->SpawnActor<ACineCameraActor>(ACineCameraActor::StaticClass(), FTransform::Identity, SP);
    if (!CraneActor) return SequencerErr(TEXT("Failed to spawn camera crane actor"));

    // Set crane height via actor transform
    FTransform T = CraneActor->GetActorTransform();
    T.SetLocation(T.GetLocation() + FVector(0, 0, Height));
    CraneActor->SetActorTransform(T);

    CraneActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_camera_crane"));
    Data->SetStringField(TEXT("actor_name"), CraneActor->GetName());
    Data->SetNumberField(TEXT("height"), Height);
    Data->SetStringField(TEXT("camera_class"), TEXT("ACineCameraActor"));
    Data->SetBoolField(TEXT("executed"), true);
    return SequencerOk(Data);
}

// ---------------------------------------------------------------------------
// sequencer_render_preview — Persist metadata on a LevelSequence indicating
//                           a render-preview pass was requested.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerExtensionCommands::HandleSequencerRenderPreview(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("sequencer_render_preview"));

    FString SequencePath;
    if (Params.IsValid()) Params->TryGetStringField(TEXT("level_sequence_path"), SequencePath);

    ULevelSequence* Seq = ResolveLevelSequence(SequencePath);
    if (!Seq)
    {
        return SequencerErr(FString::Printf(
            TEXT("sequencer_render_preview: could not load LevelSequence at '%s'."), *SequencePath));
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: sequencer_render_preview"));
    Seq->Modify();

    UPackage* Pkg = Seq->GetOutermost();
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Seq, FName(TEXT("MCP.sequencer_render_preview.requested")), TEXT("true"));
        Pkg->MarkPackageDirty();
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("sequencer_render_preview"));
    Data->SetStringField(TEXT("level_sequence_path"), Seq->GetPathName());
    Data->SetStringField(TEXT("status"), TEXT("render_preview_requested"));
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), 1);
    Data->SetBoolField(TEXT("executed"), true);
    return SequencerOk(Data);
}

// ---------------------------------------------------------------------------
// register_take_recorder_source — Persist metadata indicating an actor/class
//                                 should be registered as a Take Recorder source.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerExtensionCommands::HandleRegisterTakeRecorderSource(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("register_take_recorder_source"));

    FString SourceClass = TEXT("ActorRecorder");
    FString TargetActor;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("source_class"), SourceClass);
        Params->TryGetStringField(TEXT("target_actor"), TargetActor);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return SequencerErr(TEXT("No editor world available"));

    // Resolve target actor if provided
    AActor* Target = nullptr;
    if (!TargetActor.IsEmpty())
    {
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            if (It->GetName().Equals(TargetActor, ESearchCase::IgnoreCase) ||
                It->GetActorLabel().Equals(TargetActor, ESearchCase::IgnoreCase))
            {
                Target = *It;
                break;
            }
        }
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: register_take_recorder_source"));

    int32 KeysPersisted = 0;
    if (Target)
    {
        Target->Modify();
        UPackage* Pkg = Target->GetOutermost();
        if (Pkg)
        {
            FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Target, FName(TEXT("MCP.take_recorder.source_class")), *SourceClass);
            FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Target, FName(TEXT("MCP.take_recorder.enabled")), TEXT("true"));
            Pkg->MarkPackageDirty();
            KeysPersisted = 2;
        }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("register_take_recorder_source"));
    Data->SetStringField(TEXT("source_class"), SourceClass);
    Data->SetStringField(TEXT("target_actor_resolved"), Target ? Target->GetName() : TEXT("none"));
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return SequencerOk(Data);
}

// ---------------------------------------------------------------------------
// add_control_rig_track — Persist metadata on a LevelSequence indicating a
//                         ControlRig track should be added to a binding.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerExtensionCommands::HandleAddControlRigTrack(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_control_rig_track"));

    FString SequencePath;
    FString BindingId;
    FString ControlRigPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("level_sequence_path"), SequencePath);
        Params->TryGetStringField(TEXT("binding_id"), BindingId);
        Params->TryGetStringField(TEXT("control_rig_path"), ControlRigPath);
    }

    ULevelSequence* Seq = ResolveLevelSequence(SequencePath);
    if (!Seq)
    {
        return SequencerErr(FString::Printf(
            TEXT("add_control_rig_track: could not load LevelSequence at '%s'."), *SequencePath));
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: add_control_rig_track"));
    Seq->Modify();

    UPackage* Pkg = Seq->GetOutermost();
    int32 KeysPersisted = 0;
    if (Pkg)
    {
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Seq, FName(TEXT("MCP.add_control_rig_track.binding_id")), *BindingId);
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Seq, FName(TEXT("MCP.add_control_rig_track.control_rig_path")), *ControlRigPath);
        FEpicUnrealMCPCommonUtils::SetPackageMetadata(Pkg, Seq, FName(TEXT("MCP.add_control_rig_track.status")), TEXT("track_noted"));
        Pkg->MarkPackageDirty();
        KeysPersisted = 3;
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_control_rig_track"));
    Data->SetStringField(TEXT("level_sequence_path"), Seq->GetPathName());
    Data->SetStringField(TEXT("binding_id"), BindingId);
    Data->SetStringField(TEXT("control_rig_path"), ControlRigPath);
    Data->SetNumberField(TEXT("mcp_metadata_keys_persisted"), KeysPersisted);
    Data->SetBoolField(TEXT("executed"), true);
    return SequencerOk(Data);
}

// ---------------------------------------------------------------------------
// spawn_level_sequence_actor — Place a LevelSequenceActor in the world and
//                              link it to a LevelSequence asset.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerExtensionCommands::HandleSpawnLevelSequenceActor(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_level_sequence_actor"));

    FString SequencePath;
    FString ActorName = TEXT("LevelSequenceActor");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("level_sequence_path"), SequencePath);
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
    }

    ULevelSequence* Seq = ResolveLevelSequence(SequencePath);
    if (!Seq)
    {
        return SequencerErr(FString::Printf(
            TEXT("spawn_level_sequence_actor: could not load LevelSequence at '%s'."), *SequencePath));
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return SequencerErr(TEXT("No editor world available"));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_level_sequence_actor"));

    ALevelSequenceActor* Actor = FindOrCreateSequenceActor(World, Seq, ActorName);
    if (!Actor) return SequencerErr(TEXT("Failed to spawn LevelSequenceActor"));

    Actor->Modify();
    Actor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_level_sequence_actor"));
    Data->SetStringField(TEXT("actor_name"), Actor->GetName());
    Data->SetStringField(TEXT("level_sequence_path"), Seq->GetPathName());
    Data->SetBoolField(TEXT("auto_play"), Actor->PlaybackSettings.bAutoPlay);
    Data->SetBoolField(TEXT("executed"), true);
    return SequencerOk(Data);
}
