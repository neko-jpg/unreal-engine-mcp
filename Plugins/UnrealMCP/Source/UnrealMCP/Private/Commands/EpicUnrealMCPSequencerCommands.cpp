#include "Commands/EpicUnrealMCPSequencerCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"
#include "LevelSequence.h"
#include "MovieScene.h"
#include "Tracks/MovieScene3DTransformTrack.h"
#include "Sections/MovieScene3DTransformSection.h"
#include "Tracks/MovieSceneCameraCutTrack.h"
#include "Sections/MovieSceneCameraCutSection.h"
#include "Tracks/MovieSceneEventTrack.h"
#include "Sections/MovieSceneEventSection.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/Paths.h"
#include "Kismet/GameplayStatics.h"
#include "EngineUtils.h"
#include "Channels/MovieSceneChannel.h"
#include "Channels/MovieSceneChannelProxy.h"
#include "Channels/MovieSceneDoubleChannel.h"
#include "Channels/MovieSceneFloatChannel.h"
#include "Tracks/MovieSceneVisibilityTrack.h"
#include "Sections/MovieSceneVisibilitySection.h"
#include "Tracks/MovieSceneAudioTrack.h"
#include "Sections/MovieSceneAudioSection.h"
#include "Tracks/MovieSceneSkeletalAnimationTrack.h"
#include "Sections/MovieSceneSkeletalAnimationSection.h"
#include "Tracks/MovieSceneMaterialTrack.h"
#include "Tracks/MovieSceneCinematicShotTrack.h"
#include "Sections/MovieSceneCinematicShotSection.h"
#include "Tracks/MovieSceneSubTrack.h"
#include "Sections/MovieSceneSubSection.h"
#include "Animation/AnimSequence.h"
#include "Sound/SoundBase.h"

FEpicUnrealMCPSequencerCommands::FEpicUnrealMCPSequencerCommands()
{
}

FEpicUnrealMCPSequencerCommands::~FEpicUnrealMCPSequencerCommands()
{
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPSequencerCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_level_sequence"), &FEpicUnrealMCPSequencerCommands::HandleCreateLevelSequence},
        {TEXT("add_actor_binding"), &FEpicUnrealMCPSequencerCommands::HandleAddActorBinding},
        {TEXT("add_transform_track"), &FEpicUnrealMCPSequencerCommands::HandleAddTransformTrack},
        {TEXT("add_camera_cut_track"), &FEpicUnrealMCPSequencerCommands::HandleAddCameraCutTrack},
        {TEXT("add_event_track"), &FEpicUnrealMCPSequencerCommands::HandleAddEventTrack},
        {TEXT("add_keyframe"), &FEpicUnrealMCPSequencerCommands::HandleAddKeyframe},
        {TEXT("set_playback_range"), &FEpicUnrealMCPSequencerCommands::HandleSetPlaybackRange},
        {TEXT("set_frame_rate"), &FEpicUnrealMCPSequencerCommands::HandleSetFrameRate},
        {TEXT("add_visibility_track"), &FEpicUnrealMCPSequencerCommands::HandleAddVisibilityTrack},
        {TEXT("add_audio_track"), &FEpicUnrealMCPSequencerCommands::HandleAddAudioTrack},
        {TEXT("add_animation_track"), &FEpicUnrealMCPSequencerCommands::HandleAddAnimationTrack},
        {TEXT("add_material_parameter_track"), &FEpicUnrealMCPSequencerCommands::HandleAddMaterialParameterTrack},
        {TEXT("delete_keyframe"), &FEpicUnrealMCPSequencerCommands::HandleDeleteKeyframe},
        {TEXT("set_keyframe_interpolation"), &FEpicUnrealMCPSequencerCommands::HandleSetKeyframeInterpolation},
        {TEXT("add_subsequence"), &FEpicUnrealMCPSequencerCommands::HandleAddSubsequence},
    };

    const Handler* H = Dispatch.Find(CommandType);
    if (H)
    {
        return (this->*(*H))(Params);
    }

    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown sequencer command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleCreateLevelSequence(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    }

    int32 DurationFrames = 150;
    Params->TryGetNumberField(TEXT("duration_frames"), DurationFrames);

    int32 FrameRateNum = 30;
    Params->TryGetNumberField(TEXT("frame_rate_numerator"), FrameRateNum);
    int32 FrameRateDen = 1;
    Params->TryGetNumberField(TEXT("frame_rate_denominator"), FrameRateDen);

    FString SequenceName = FPaths::GetBaseFilename(SequencePath);
    UPackage* Package = CreatePackage(*SequencePath);
    if (!Package)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package for level sequence"));
    }

    ULevelSequence* Sequence = NewObject<ULevelSequence>(Package, FName(*SequenceName), RF_Public | RF_Standalone);
    if (!Sequence)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create LevelSequence object"));
    }

    Sequence->Initialize();
    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (MovieScene)
    {
        MovieScene->SetDisplayRate(FFrameRate(FrameRateNum, FrameRateDen));
        MovieScene->SetPlaybackRange(0, DurationFrames);
        MovieScene->SetWorkingRange(0.0f, static_cast<float>(DurationFrames) / static_cast<float>(FrameRateNum));
    }

    Package->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Sequence);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("sequence_name"), SequenceName);
    Result->SetNumberField(TEXT("duration_frames"), DurationFrames);
    Result->SetNumberField(TEXT("frame_rate"), static_cast<double>(FrameRateNum) / static_cast<double>(FrameRateDen));
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddActorBinding(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    }

    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'actor_name' parameter"));
    }

    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    }

    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    }

    // Find actor in current world
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No active editor world"));
    }

    AActor* Actor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetActorNameOrLabel().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            Actor = *It;
            break;
        }
    }

    if (!Actor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor '%s' not found in level"), *ActorName));
    }

    FGuid Binding = MovieScene->AddPossessable(Actor->GetActorNameOrLabel(), Actor->GetClass());
    Sequence->BindPossessableObject(Binding, *Actor, World);
    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    Result->SetStringField(TEXT("binding_guid"), Binding.ToString());
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddTransformTrack(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    }

    FString BindingGuidStr;
    if (!Params->TryGetStringField(TEXT("binding_guid"), BindingGuidStr) || BindingGuidStr.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'binding_guid' parameter"));
    }

    FGuid BindingGuid;
    if (!FGuid::Parse(BindingGuidStr, BindingGuid))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid 'binding_guid' format"));
    }

    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    }

    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    }

    UMovieScene3DTransformTrack* TransformTrack = MovieScene->AddTrack<UMovieScene3DTransformTrack>(BindingGuid);
    if (!TransformTrack)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add transform track"));
    }

    UMovieSceneSection* Section = TransformTrack->CreateNewSection();
    if (Section)
    {
        TransformTrack->AddSection(*Section);
    }

    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("binding_guid"), BindingGuidStr);
    Result->SetStringField(TEXT("track_type"), TEXT("transform"));
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddCameraCutTrack(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    }

    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    }

    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    }

    UMovieSceneCameraCutTrack* CameraCutTrack = Cast<UMovieSceneCameraCutTrack>(MovieScene->AddCameraCutTrack(UMovieSceneCameraCutTrack::StaticClass()));
    if (!CameraCutTrack)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add camera cut track"));
    }

    // Optionally add a section with a camera binding
    FString CameraBindingGuidStr;
    if (Params->TryGetStringField(TEXT("camera_binding_guid"), CameraBindingGuidStr) && !CameraBindingGuidStr.IsEmpty())
    {
        FGuid CameraGuid;
        if (FGuid::Parse(CameraBindingGuidStr, CameraGuid))
        {
            UMovieSceneCameraCutSection* CutSection = Cast<UMovieSceneCameraCutSection>(CameraCutTrack->CreateNewSection());
            if (CutSection)
            {
                CutSection->SetCameraGuid(CameraGuid);
                CameraCutTrack->AddSection(*CutSection);
            }
        }
    }

    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("track_type"), TEXT("camera_cut"));
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddEventTrack(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    }

    FString BindingGuidStr;
    if (!Params->TryGetStringField(TEXT("binding_guid"), BindingGuidStr) || BindingGuidStr.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'binding_guid' parameter"));
    }

    FGuid BindingGuid;
    if (!FGuid::Parse(BindingGuidStr, BindingGuid))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid 'binding_guid' format"));
    }

    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    }

    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    }

    UMovieSceneEventTrack* EventTrack = MovieScene->AddTrack<UMovieSceneEventTrack>(BindingGuid);
    if (!EventTrack)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add event track"));
    }

    UMovieSceneSection* Section = EventTrack->CreateNewSection();
    if (Section)
    {
        EventTrack->AddSection(*Section);
    }

    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("binding_guid"), BindingGuidStr);
    Result->SetStringField(TEXT("track_type"), TEXT("event"));
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddKeyframe(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    }

    FString BindingGuidStr;
    if (!Params->TryGetStringField(TEXT("binding_guid"), BindingGuidStr) || BindingGuidStr.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'binding_guid' parameter"));
    }

    FGuid BindingGuid;
    if (!FGuid::Parse(BindingGuidStr, BindingGuid))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid 'binding_guid' format"));
    }

    int32 Frame = 0;
    Params->TryGetNumberField(TEXT("frame"), Frame);

    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    }

    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    }

    // Find transform track for this binding
    UMovieScene3DTransformTrack* TransformTrack = nullptr;
    for (UMovieSceneTrack* Track : MovieScene->GetTracks())
    {
        if (Track->GetAllSections().Num() > 0 && Track->SupportsType(UMovieScene3DTransformSection::StaticClass()))
        {
            // Check if track belongs to this binding via the object binding ID
            if (Track->FindObjectBindingGuid() == BindingGuid)
            {
                TransformTrack = Cast<UMovieScene3DTransformTrack>(Track);
                break;
            }
        }
    }

    if (!TransformTrack)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No transform track found for binding"));
    }

    TArray<UMovieSceneSection*> Sections = TransformTrack->GetAllSections();
    if (Sections.Num() == 0)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Transform track has no sections"));
    }

    UMovieScene3DTransformSection* TransformSection = Cast<UMovieScene3DTransformSection>(Sections[0]);
    if (!TransformSection)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to cast section to transform section"));
    }

    // Parse optional location / rotation / scale values
    float LocX = 0.0f, LocY = 0.0f, LocZ = 0.0f;
    float RotX = 0.0f, RotY = 0.0f, RotZ = 0.0f;
    float ScaleX = 1.0f, ScaleY = 1.0f, ScaleZ = 1.0f;

    const TSharedPtr<FJsonObject>* LocationObj = nullptr;
    if (Params->TryGetObjectField(TEXT("location"), LocationObj) && LocationObj->IsValid())
    {
        (*LocationObj)->TryGetNumberField(TEXT("x"), LocX);
        (*LocationObj)->TryGetNumberField(TEXT("y"), LocY);
        (*LocationObj)->TryGetNumberField(TEXT("z"), LocZ);
    }

    const TSharedPtr<FJsonObject>* RotationObj = nullptr;
    if (Params->TryGetObjectField(TEXT("rotation"), RotationObj) && RotationObj->IsValid())
    {
        (*RotationObj)->TryGetNumberField(TEXT("x"), RotX);
        (*RotationObj)->TryGetNumberField(TEXT("y"), RotY);
        (*RotationObj)->TryGetNumberField(TEXT("z"), RotZ);
    }

    const TSharedPtr<FJsonObject>* ScaleObj = nullptr;
    if (Params->TryGetObjectField(TEXT("scale"), ScaleObj) && ScaleObj->IsValid())
    {
        (*ScaleObj)->TryGetNumberField(TEXT("x"), ScaleX);
        (*ScaleObj)->TryGetNumberField(TEXT("y"), ScaleY);
        (*ScaleObj)->TryGetNumberField(TEXT("z"), ScaleZ);
    }

    FFrameNumber KeyTime(Frame);

#if ENGINE_MAJOR_VERSION >= 5
    // UE5 uses double channels accessed via ChannelProxy.
    // Channel order on UMovieScene3DTransformSection: [Tx,Ty,Tz, Rx,Ry,Rz, Sx,Sy,Sz, ManualWeight].
    TArrayView<FMovieSceneDoubleChannel*> AllDoubleChannels =
        TransformSection->GetChannelProxy().GetChannels<FMovieSceneDoubleChannel>();
    if (AllDoubleChannels.Num() >= 9)
    {
        AllDoubleChannels[0]->AddCubicKey(KeyTime, static_cast<double>(LocX));
        AllDoubleChannels[1]->AddCubicKey(KeyTime, static_cast<double>(LocY));
        AllDoubleChannels[2]->AddCubicKey(KeyTime, static_cast<double>(LocZ));
        AllDoubleChannels[3]->AddCubicKey(KeyTime, static_cast<double>(RotX));
        AllDoubleChannels[4]->AddCubicKey(KeyTime, static_cast<double>(RotY));
        AllDoubleChannels[5]->AddCubicKey(KeyTime, static_cast<double>(RotZ));
        AllDoubleChannels[6]->AddCubicKey(KeyTime, static_cast<double>(ScaleX));
        AllDoubleChannels[7]->AddCubicKey(KeyTime, static_cast<double>(ScaleY));
        AllDoubleChannels[8]->AddCubicKey(KeyTime, static_cast<double>(ScaleZ));
    }
#else
    // UE4 uses float channels
    TArrayView<FMovieSceneFloatChannel*> TransChannels = TransformSection->GetTranslationChannel();
    if (TransChannels.Num() >= 3)
    {
        TransChannels[0]->AddKey(KeyTime, LocX);
        TransChannels[1]->AddKey(KeyTime, LocY);
        TransChannels[2]->AddKey(KeyTime, LocZ);
    }

    TArrayView<FMovieSceneFloatChannel*> RotChannels = TransformSection->GetRotationChannel();
    if (RotChannels.Num() >= 3)
    {
        RotChannels[0]->AddKey(KeyTime, RotX);
        RotChannels[1]->AddKey(KeyTime, RotY);
        RotChannels[2]->AddKey(KeyTime, RotZ);
    }

    TArrayView<FMovieSceneFloatChannel*> ScaleChannels = TransformSection->GetScaleChannel();
    if (ScaleChannels.Num() >= 3)
    {
        ScaleChannels[0]->AddKey(KeyTime, ScaleX);
        ScaleChannels[1]->AddKey(KeyTime, ScaleY);
        ScaleChannels[2]->AddKey(KeyTime, ScaleZ);
    }
#endif

    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("binding_guid"), BindingGuidStr);
    Result->SetNumberField(TEXT("frame"), Frame);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleSetPlaybackRange(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    }

    int32 StartFrame = 0;
    Params->TryGetNumberField(TEXT("start_frame"), StartFrame);
    int32 EndFrame = 150;
    Params->TryGetNumberField(TEXT("end_frame"), EndFrame);

    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    }

    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    }

    MovieScene->SetPlaybackRange(StartFrame, EndFrame - StartFrame);
    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetNumberField(TEXT("start_frame"), StartFrame);
    Result->SetNumberField(TEXT("end_frame"), EndFrame);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleSetFrameRate(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    }

    int32 Numerator = 30;
    Params->TryGetNumberField(TEXT("numerator"), Numerator);
    int32 Denominator = 1;
    Params->TryGetNumberField(TEXT("denominator"), Denominator);

    if (Denominator <= 0)
    {
        Denominator = 1;
    }

    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    }

    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    }

    MovieScene->SetDisplayRate(FFrameRate(Numerator, Denominator));
    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetNumberField(TEXT("numerator"), Numerator);
    Result->SetNumberField(TEXT("denominator"), Denominator);
    return Result;
}


// =============================================================================
// W1-4 Sequencer residue (UE 5.7)
// =============================================================================

namespace
{
    static ULevelSequence* LoadLevelSequenceChecked(const FString& SequencePath, TSharedPtr<FJsonObject>& OutError)
    {
        ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
        if (!Sequence)
        {
            OutError = FEpicUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
        }
        return Sequence;
    }
}

// W1-4_IMPL_BEGIN
// W1-4 Sequencer residue (UE 5.7): Visibility / Audio / Animation / Material
// parameter / Keyframe delete / Keyframe interpolation / Subsequence shot tracks

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddVisibilityTrack(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath, BindingGuidStr;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    if (!Params->TryGetStringField(TEXT("binding_guid"), BindingGuidStr) || BindingGuidStr.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'binding_guid' parameter"));
    FGuid BindingGuid;
    if (!FGuid::Parse(BindingGuidStr, BindingGuid))
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid 'binding_guid' format"));
    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    UMovieSceneVisibilityTrack* Track = MovieScene->AddTrack<UMovieSceneVisibilityTrack>(BindingGuid);
    if (!Track)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add visibility track"));
    Track->SetPropertyNameAndPath(FName(TEXT("bHidden")), TEXT("bHidden"));
    UMovieSceneSection* Section = Track->CreateNewSection();
    if (Section)
    {
        Section->SetRange(MovieScene->GetPlaybackRange());
        Track->AddSection(*Section);
    }
    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("binding_guid"), BindingGuidStr);
    Result->SetStringField(TEXT("track_type"), TEXT("visibility"));
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddAudioTrack(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    UMovieSceneAudioTrack* Track = MovieScene->AddTrack<UMovieSceneAudioTrack>();
    if (!Track)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add audio track"));

    FString SoundPath;
    int32 StartFrame = 0;
    Params->TryGetNumberField(TEXT("start_frame"), StartFrame);
    if (Params->TryGetStringField(TEXT("sound_path"), SoundPath) && !SoundPath.IsEmpty())
    {
        USoundBase* Sound = LoadObject<USoundBase>(nullptr, *SoundPath);
        if (Sound) Track->AddNewSound(Sound, FFrameNumber(StartFrame));
    }
    else
    {
        UMovieSceneSection* Section = Track->CreateNewSection();
        if (Section)
        {
            Section->SetRange(MovieScene->GetPlaybackRange());
            Track->AddSection(*Section);
        }
    }
    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("track_type"), TEXT("audio"));
    if (!SoundPath.IsEmpty()) Result->SetStringField(TEXT("sound_path"), SoundPath);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddAnimationTrack(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath, BindingGuidStr;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    if (!Params->TryGetStringField(TEXT("binding_guid"), BindingGuidStr) || BindingGuidStr.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'binding_guid' parameter"));
    FGuid BindingGuid;
    if (!FGuid::Parse(BindingGuidStr, BindingGuid))
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid 'binding_guid' format"));
    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    UMovieSceneSkeletalAnimationTrack* Track = MovieScene->AddTrack<UMovieSceneSkeletalAnimationTrack>(BindingGuid);
    if (!Track)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add animation track"));

    FString AnimPath;
    int32 StartFrame = 0;
    Params->TryGetNumberField(TEXT("start_frame"), StartFrame);
    UMovieSceneSkeletalAnimationSection* Section = Cast<UMovieSceneSkeletalAnimationSection>(Track->CreateNewSection());
    if (Section)
    {
        if (Params->TryGetStringField(TEXT("anim_sequence_path"), AnimPath) && !AnimPath.IsEmpty())
        {
            UAnimSequenceBase* Anim = LoadObject<UAnimSequenceBase>(nullptr, *AnimPath);
            if (Anim) Section->Params.Animation = Anim;
        }
        TRange<FFrameNumber> Range = MovieScene->GetPlaybackRange();
        if (StartFrame > 0)
        {
            const int32 Length = UE::MovieScene::DiscreteSize(Range);
            Range = TRange<FFrameNumber>(FFrameNumber(StartFrame), FFrameNumber(StartFrame + Length));
        }
        Section->SetRange(Range);
        Track->AddSection(*Section);
    }
    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("binding_guid"), BindingGuidStr);
    Result->SetStringField(TEXT("track_type"), TEXT("skeletal_animation"));
    if (!AnimPath.IsEmpty()) Result->SetStringField(TEXT("anim_sequence_path"), AnimPath);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddMaterialParameterTrack(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath, BindingGuidStr;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    if (!Params->TryGetStringField(TEXT("binding_guid"), BindingGuidStr) || BindingGuidStr.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'binding_guid' parameter"));
    FGuid BindingGuid;
    if (!FGuid::Parse(BindingGuidStr, BindingGuid))
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid 'binding_guid' format"));
    int32 MaterialIndex = 0;
    Params->TryGetNumberField(TEXT("material_index"), MaterialIndex);
    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));
    UMovieSceneComponentMaterialTrack* Track = MovieScene->AddTrack<UMovieSceneComponentMaterialTrack>(BindingGuid);
    if (!Track)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add material parameter track"));
#if ENGINE_MAJOR_VERSION >= 5 && ENGINE_MINOR_VERSION >= 4
    FComponentMaterialInfo MatInfo;
    MatInfo.MaterialSlotName = NAME_None;
    MatInfo.MaterialSlotIndex = MaterialIndex;
    MatInfo.MaterialType = EComponentMaterialType::IndexedMaterial;
    Track->SetMaterialInfo(MatInfo);
#else
    Track->SetMaterialIndex(MaterialIndex);
#endif
    UMovieSceneSection* Section = Track->CreateNewSection();
    if (Section)
    {
        Section->SetRange(MovieScene->GetPlaybackRange());
        Track->AddSection(*Section);
    }
    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("binding_guid"), BindingGuidStr);
    Result->SetStringField(TEXT("track_type"), TEXT("component_material_parameter"));
    Result->SetNumberField(TEXT("material_index"), MaterialIndex);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleDeleteKeyframe(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath, BindingGuidStr;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    if (!Params->TryGetStringField(TEXT("binding_guid"), BindingGuidStr) || BindingGuidStr.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'binding_guid' parameter"));
    FGuid BindingGuid;
    if (!FGuid::Parse(BindingGuidStr, BindingGuid))
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid 'binding_guid' format"));
    int32 Frame = 0;
    Params->TryGetNumberField(TEXT("frame"), Frame);
    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));

    int32 RemovedKeyCount = 0;
    const FFrameNumber Target(Frame);
    for (UMovieSceneTrack* Track : MovieScene->GetTracks())
    {
        if (!Track || Track->FindObjectBindingGuid() != BindingGuid) continue;
        for (UMovieSceneSection* Section : Track->GetAllSections())
        {
            if (!Section) continue;
            for (FMovieSceneDoubleChannel* Channel : Section->GetChannelProxy().GetChannels<FMovieSceneDoubleChannel>())
            {
                if (!Channel) continue;
                TArray<FKeyHandle> Handles;
                Channel->GetKeys(TRange<FFrameNumber>(Target, Target + 1), nullptr, &Handles);
                if (Handles.Num() > 0) { Channel->DeleteKeys(Handles); RemovedKeyCount += Handles.Num(); }
            }
            for (FMovieSceneFloatChannel* Channel : Section->GetChannelProxy().GetChannels<FMovieSceneFloatChannel>())
            {
                if (!Channel) continue;
                TArray<FKeyHandle> Handles;
                Channel->GetKeys(TRange<FFrameNumber>(Target, Target + 1), nullptr, &Handles);
                if (Handles.Num() > 0) { Channel->DeleteKeys(Handles); RemovedKeyCount += Handles.Num(); }
            }
        }
    }
    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("binding_guid"), BindingGuidStr);
    Result->SetNumberField(TEXT("frame"), Frame);
    Result->SetNumberField(TEXT("removed_keys"), RemovedKeyCount);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleSetKeyframeInterpolation(const TSharedPtr<FJsonObject>& Params)
{
    FString SequencePath, BindingGuidStr;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SequencePath) || SequencePath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    if (!Params->TryGetStringField(TEXT("binding_guid"), BindingGuidStr) || BindingGuidStr.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'binding_guid' parameter"));
    FGuid BindingGuid;
    if (!FGuid::Parse(BindingGuidStr, BindingGuid))
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid 'binding_guid' format"));
    FString InterpMode = TEXT("Cubic");
    Params->TryGetStringField(TEXT("interpolation"), InterpMode);
    ERichCurveInterpMode Mode = RCIM_Cubic;
    if (InterpMode.Equals(TEXT("Linear"), ESearchCase::IgnoreCase)) Mode = RCIM_Linear;
    else if (InterpMode.Equals(TEXT("Constant"), ESearchCase::IgnoreCase)) Mode = RCIM_Constant;
    else if (InterpMode.Equals(TEXT("None"), ESearchCase::IgnoreCase)) Mode = RCIM_None;
    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, *SequencePath);
    if (!Sequence)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("LevelSequence not found: %s"), *SequencePath));
    UMovieScene* MovieScene = Sequence->GetMovieScene();
    if (!MovieScene)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));

    int32 UpdatedKeyCount = 0;
    for (UMovieSceneTrack* Track : MovieScene->GetTracks())
    {
        if (!Track || Track->FindObjectBindingGuid() != BindingGuid) continue;
        for (UMovieSceneSection* Section : Track->GetAllSections())
        {
            if (!Section) continue;
            for (FMovieSceneDoubleChannel* Channel : Section->GetChannelProxy().GetChannels<FMovieSceneDoubleChannel>())
            {
                if (!Channel) continue;
                TArrayView<FMovieSceneDoubleValue> Values = Channel->GetData().GetValues();
                for (FMovieSceneDoubleValue& V : Values) { V.InterpMode = Mode; V.TangentMode = RCTM_Auto; ++UpdatedKeyCount; }
            }
            for (FMovieSceneFloatChannel* Channel : Section->GetChannelProxy().GetChannels<FMovieSceneFloatChannel>())
            {
                if (!Channel) continue;
                TArrayView<FMovieSceneFloatValue> Values = Channel->GetData().GetValues();
                for (FMovieSceneFloatValue& V : Values) { V.InterpMode = Mode; V.TangentMode = RCTM_Auto; ++UpdatedKeyCount; }
            }
        }
    }
    Sequence->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), SequencePath);
    Result->SetStringField(TEXT("binding_guid"), BindingGuidStr);
    Result->SetStringField(TEXT("interpolation"), InterpMode);
    Result->SetNumberField(TEXT("updated_keys"), UpdatedKeyCount);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPSequencerCommands::HandleAddSubsequence(const TSharedPtr<FJsonObject>& Params)
{
    FString OuterPath, InnerPath;
    if (!Params->TryGetStringField(TEXT("sequence_path"), OuterPath) || OuterPath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'sequence_path' parameter"));
    if (!Params->TryGetStringField(TEXT("inner_sequence_path"), InnerPath) || InnerPath.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'inner_sequence_path' parameter"));
    int32 StartFrame = 0, Duration = 150;
    Params->TryGetNumberField(TEXT("start_frame"), StartFrame);
    Params->TryGetNumberField(TEXT("duration_frames"), Duration);
    bool bAsShot = false;
    Params->TryGetBoolField(TEXT("as_shot"), bAsShot);

    ULevelSequence* Outer = LoadObject<ULevelSequence>(nullptr, *OuterPath);
    if (!Outer)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Outer LevelSequence not found: %s"), *OuterPath));
    ULevelSequence* Inner = LoadObject<ULevelSequence>(nullptr, *InnerPath);
    if (!Inner)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Inner LevelSequence not found: %s"), *InnerPath));
    UMovieScene* MS = Outer->GetMovieScene();
    if (!MS)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));

    UMovieSceneSubSection* SubSection = nullptr;
    FString TrackKind;
    if (bAsShot)
    {
        UMovieSceneCinematicShotTrack* Track = MS->FindTrack<UMovieSceneCinematicShotTrack>();
        if (!Track) Track = MS->AddTrack<UMovieSceneCinematicShotTrack>();
        if (!Track)
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add cinematic shot track"));
        SubSection = Cast<UMovieSceneSubSection>(Track->AddSequence(Inner, FFrameNumber(StartFrame), Duration));
        TrackKind = TEXT("cinematic_shot");
    }
    else
    {
        UMovieSceneSubTrack* Track = MS->FindTrack<UMovieSceneSubTrack>();
        if (!Track) Track = MS->AddTrack<UMovieSceneSubTrack>();
        if (!Track)
            return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add sub-sequence track"));
        SubSection = Track->AddSequence(Inner, FFrameNumber(StartFrame), Duration);
        TrackKind = TEXT("subsequence");
    }
    if (!SubSection)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add subsequence section"));
    Outer->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence_path"), OuterPath);
    Result->SetStringField(TEXT("inner_sequence_path"), InnerPath);
    Result->SetStringField(TEXT("track_type"), TrackKind);
    Result->SetNumberField(TEXT("start_frame"), StartFrame);
    Result->SetNumberField(TEXT("duration_frames"), Duration);
    return Result;
}
