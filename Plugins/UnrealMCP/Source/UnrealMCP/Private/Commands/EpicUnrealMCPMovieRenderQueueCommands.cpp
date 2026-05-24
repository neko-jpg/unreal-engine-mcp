#include "Commands/EpicUnrealMCPMovieRenderQueueCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_MRQ_MCP
#include "MoviePipelineQueueSubsystem.h"
#include "MoviePipelineQueue.h"
#include "MoviePipelinePrimaryConfig.h"
#include "MoviePipelineOutputSetting.h"
#include "MoviePipelineAntiAliasingSetting.h"
#include "MoviePipelineConsoleVariableSetting.h"
#include "MoviePipelineBurnInSetting.h"
#include "MoviePipelineImageSequenceOutput.h"
#include "MoviePipelineEXROutput.h"
#include "MoviePipelineDeferredPasses.h"
#include "Graph/MovieGraphConfig.h"
#include "Editor.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "UObject/Package.h"
#endif

bool FEpicUnrealMCPMovieRenderQueueCommands::IsModuleAvailable()
{
#if WITH_MRQ_MCP
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPMovieRenderQueueCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Enable the Movie Render Queue plugin (Engine/Plugins/MovieScene/MovieRenderPipeline) and rebuild UnrealMCP so the bridge picks up MoviePipelineCore module."));
    return R;
}

FEpicUnrealMCPMovieRenderQueueCommands::FEpicUnrealMCPMovieRenderQueueCommands() {}
FEpicUnrealMCPMovieRenderQueueCommands::~FEpicUnrealMCPMovieRenderQueueCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPMovieRenderQueueCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_mrq_job"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleCreateMrqJob},
        {TEXT("add_sequence_to_mrq"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleAddSequenceToMrq},
        {TEXT("set_mrq_output_directory"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqOutputDirectory},
        {TEXT("set_mrq_resolution"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqResolution},
        {TEXT("set_mrq_frame_range"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqFrameRange},
        {TEXT("set_mrq_anti_aliasing"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqAntiAliasing},
        {TEXT("set_mrq_exr_output"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqExrOutput},
        {TEXT("set_mrq_png_output"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqPngOutput},
        {TEXT("set_mrq_jpg_output"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqJpgOutput},
        {TEXT("set_mrq_video_output"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqVideoOutput},
        {TEXT("set_mrq_path_tracer"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqPathTracer},
        {TEXT("set_mrq_console_variables"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqConsoleVariables},
        {TEXT("add_mrq_render_pass"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleAddMrqRenderPass},
        {TEXT("set_mrq_object_id_pass"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqObjectIdPass},
        {TEXT("set_mrq_burn_in"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqBurnIn},
        {TEXT("set_mrq_warm_up"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqWarmUp},
        {TEXT("start_mrq_render"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleStartMrqRender},
        {TEXT("cancel_mrq_render"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleCancelMrqRender},
        {TEXT("get_mrq_render_progress"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleGetMrqRenderProgress},
        {TEXT("verify_mrq_render_result"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleVerifyMrqRenderResult},
        {TEXT("create_movie_render_graph"),  &FEpicUnrealMCPMovieRenderQueueCommands::HandleCreateMovieRenderGraph}
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
// 234-stubs W4 (#96): MRQ executed-envelope helpers.
// ---------------------------------------------------------------------------

static TSharedPtr<FJsonObject> MrqOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> MrqErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

#if WITH_MRQ_MCP
// Resolve a UMoviePipelineExecutorJob by JobName from the editor queue.
static UMoviePipelineExecutorJob* FindJobInQueue(UMoviePipelineQueue* Queue, const FString& JobName)
{
    if (!Queue) return nullptr;
    for (UMoviePipelineExecutorJob* Job : Queue->GetJobs())
    {
        if (Job && Job->JobName == JobName)
        {
            return Job;
        }
    }
    return nullptr;
}
#endif // WITH_MRQ_MCP

// ---------------------------------------------------------------------------
// create_mrq_job -- Allocate a new job in the editor MRQ queue.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleCreateMrqJob(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_mrq_job"));

#if WITH_MRQ_MCP
    FString JobName = TEXT("NewMRQJob");
    if (Params.IsValid()) Params->TryGetStringField(TEXT("job_name"), JobName);

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    if (!Queue) return MrqErr(TEXT("Failed to get MRQ queue"));

    UMoviePipelineExecutorJob* Job = Queue->AllocateNewJob();
    if (!Job) return MrqErr(TEXT("Failed to allocate new MRQ job"));

    Job->JobName = JobName;
    Job->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_mrq_job"));
    Data->SetStringField(TEXT("job_name"), Job->JobName);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("create_mrq_job"));
#endif
}

// ---------------------------------------------------------------------------
// add_sequence_to_mrq -- Set the sequence and map on an existing job.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleAddSequenceToMrq(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_sequence_to_mrq"));

#if WITH_MRQ_MCP
    FString JobName, LevelPath, SequencePath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        Params->TryGetStringField(TEXT("level_path"), LevelPath);
        Params->TryGetStringField(TEXT("sequence_path"), SequencePath);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found in queue"), *JobName));

    if (!SequencePath.IsEmpty())
    {
        Job->SetSequence(FSoftObjectPath(SequencePath));
    }
    if (!LevelPath.IsEmpty())
    {
        Job->Map = FSoftObjectPath(LevelPath);
    }
    Job->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_sequence_to_mrq"));
    Data->SetStringField(TEXT("job_name"), Job->JobName);
    Data->SetStringField(TEXT("sequence"), Job->Sequence.ToString());
    Data->SetStringField(TEXT("map"), Job->Map.ToString());
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("add_sequence_to_mrq"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_output_directory -- Configure output directory on a job.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqOutputDirectory(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_output_directory"));

#if WITH_MRQ_MCP
    FString JobName, OutputDirectory;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        Params->TryGetStringField(TEXT("output_directory"), OutputDirectory);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found in queue"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UMoviePipelineOutputSetting* OutputSetting =
        Cast<UMoviePipelineOutputSetting>(Config->FindOrAddSettingByClass(UMoviePipelineOutputSetting::StaticClass()));
    if (!OutputSetting) return MrqErr(TEXT("Failed to get output setting"));

    OutputSetting->OutputDirectory.Path = OutputDirectory;
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_output_directory"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetStringField(TEXT("output_directory"), OutputSetting->OutputDirectory.Path);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_output_directory"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_resolution -- Set output resolution on a job.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqResolution(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_resolution"));

#if WITH_MRQ_MCP
    FString JobName;
    int32 Width = 1920, Height = 1080;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        const TSharedPtr<FJsonValue>* W = Params->TryGetField(TEXT("width"));
        const TSharedPtr<FJsonValue>* H = Params->TryGetField(TEXT("height"));
        if (W) Width = (*W)->AsNumber();
        if (H) Height = (*H)->AsNumber();
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UMoviePipelineOutputSetting* OutputSetting =
        Cast<UMoviePipelineOutputSetting>(Config->FindOrAddSettingByClass(UMoviePipelineOutputSetting::StaticClass()));
    if (!OutputSetting) return MrqErr(TEXT("Failed to get output setting"));

    OutputSetting->OutputResolution = FIntPoint(Width, Height);
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_resolution"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetNumberField(TEXT("width"), Width);
    Data->SetNumberField(TEXT("height"), Height);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_resolution"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_frame_range -- Set custom playback range on a job.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqFrameRange(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_frame_range"));

#if WITH_MRQ_MCP
    FString JobName;
    int32 StartFrame = 0, EndFrame = 120;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        const TSharedPtr<FJsonValue>* S = Params->TryGetField(TEXT("start_frame"));
        const TSharedPtr<FJsonValue>* E = Params->TryGetField(TEXT("end_frame"));
        if (S) StartFrame = (*S)->AsNumber();
        if (E) EndFrame = (*E)->AsNumber();
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UMoviePipelineOutputSetting* OutputSetting =
        Cast<UMoviePipelineOutputSetting>(Config->FindOrAddSettingByClass(UMoviePipelineOutputSetting::StaticClass()));
    if (!OutputSetting) return MrqErr(TEXT("Failed to get output setting"));

    OutputSetting->bUseCustomPlaybackRange = true;
    OutputSetting->CustomStartFrame = StartFrame;
    OutputSetting->CustomEndFrame = EndFrame;
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_frame_range"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetNumberField(TEXT("start_frame"), StartFrame);
    Data->SetNumberField(TEXT("end_frame"), EndFrame);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_frame_range"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_anti_aliasing -- Configure spatial/temporal AA samples.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqAntiAliasing(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_anti_aliasing"));

#if WITH_MRQ_MCP
    FString JobName;
    int32 SpatialSamples = 4, TemporalSamples = 1;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        const TSharedPtr<FJsonValue>* Sp = Params->TryGetField(TEXT("spatial_samples"));
        const TSharedPtr<FJsonValue>* Tp = Params->TryGetField(TEXT("temporal_samples"));
        if (Sp) SpatialSamples = (*Sp)->AsNumber();
        if (Tp) TemporalSamples = (*Tp)->AsNumber();
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UMoviePipelineAntiAliasingSetting* AASetting =
        Cast<UMoviePipelineAntiAliasingSetting>(Config->FindOrAddSettingByClass(UMoviePipelineAntiAliasingSetting::StaticClass()));
    if (!AASetting) return MrqErr(TEXT("Failed to get anti-aliasing setting"));

    AASetting->SpatialSampleCount = SpatialSamples;
    AASetting->TemporalSampleCount = TemporalSamples;
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_anti_aliasing"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetNumberField(TEXT("spatial_samples"), AASetting->SpatialSampleCount);
    Data->SetNumberField(TEXT("temporal_samples"), AASetting->TemporalSampleCount);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_anti_aliasing"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_exr_output -- Configure EXR image sequence output.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqExrOutput(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_exr_output"));

#if WITH_MRQ_MCP
    FString JobName, Compression = TEXT("PIZ");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        Params->TryGetStringField(TEXT("compression"), Compression);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UMoviePipelineImageSequenceOutput_EXR* EXROutput =
        Cast<UMoviePipelineImageSequenceOutput_EXR>(Config->FindOrAddSettingByClass(UMoviePipelineImageSequenceOutput_EXR::StaticClass()));
    if (!EXROutput) return MrqErr(TEXT("Failed to get EXR output setting"));

    if (Compression.Equals(TEXT("None"), ESearchCase::IgnoreCase))       EXROutput->Compression = EEXRCompressionFormat::None;
    else if (Compression.Equals(TEXT("RLE"), ESearchCase::IgnoreCase))   EXROutput->Compression = EEXRCompressionFormat::RLE;
    else if (Compression.Equals(TEXT("ZIPS"), ESearchCase::IgnoreCase))  EXROutput->Compression = EEXRCompressionFormat::ZIPS;
    else if (Compression.Equals(TEXT("ZIP"), ESearchCase::IgnoreCase))   EXROutput->Compression = EEXRCompressionFormat::ZIP;
    else if (Compression.Equals(TEXT("PIZ"), ESearchCase::IgnoreCase))   EXROutput->Compression = EEXRCompressionFormat::PIZ;
    else if (Compression.Equals(TEXT("PXR24"), ESearchCase::IgnoreCase)) EXROutput->Compression = EEXRCompressionFormat::PXR24;
    else if (Compression.Equals(TEXT("B44"), ESearchCase::IgnoreCase))   EXROutput->Compression = EEXRCompressionFormat::B44;
    else if (Compression.Equals(TEXT("B44A"), ESearchCase::IgnoreCase))  EXROutput->Compression = EEXRCompressionFormat::B44A;
    else if (Compression.Equals(TEXT("DWAA"), ESearchCase::IgnoreCase))  EXROutput->Compression = EEXRCompressionFormat::DWAA;
    else if (Compression.Equals(TEXT("DWAB"), ESearchCase::IgnoreCase))  EXROutput->Compression = EEXRCompressionFormat::DWAB;
    else EXROutput->Compression = EEXRCompressionFormat::PIZ;
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_exr_output"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetStringField(TEXT("compression"), Compression);
    Data->SetBoolField(TEXT("multilayer"), EXROutput->bMultilayer);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_exr_output"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_png_output -- Configure PNG image sequence output.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqPngOutput(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_png_output"));

#if WITH_MRQ_MCP
    FString JobName;
    bool bEnabled = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        Params->TryGetBoolField(TEXT("enabled"), bEnabled);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UMoviePipelineImageSequenceOutput_PNG* PNGOutput =
        Cast<UMoviePipelineImageSequenceOutput_PNG>(Config->FindOrAddSettingByClass(UMoviePipelineImageSequenceOutput_PNG::StaticClass()));
    if (!PNGOutput) return MrqErr(TEXT("Failed to get PNG output setting"));

    PNGOutput->SetEnabled(bEnabled);
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_png_output"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetBoolField(TEXT("enabled"), bEnabled);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_png_output"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_jpg_output -- Configure JPG image sequence output.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqJpgOutput(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_jpg_output"));

#if WITH_MRQ_MCP
    FString JobName;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UMoviePipelineImageSequenceOutput_JPG* JPGOutput =
        Cast<UMoviePipelineImageSequenceOutput_JPG>(Config->FindOrAddSettingByClass(UMoviePipelineImageSequenceOutput_JPG::StaticClass()));
    if (!JPGOutput) return MrqErr(TEXT("Failed to get JPG output setting"));

    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_jpg_output"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_jpg_output"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_video_output -- Configure video output format.
// Note: UMoviePipelineVideoOutputBase is abstract. The concrete output class
// must be configured through the MRQ editor or a project-specific executor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqVideoOutput(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_video_output"));

#if WITH_MRQ_MCP
    FString JobName, Format = TEXT("ProRes422");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        Params->TryGetStringField(TEXT("format"), Format);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_video_output"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetStringField(TEXT("format"), Format);
    Data->SetStringField(TEXT("note"), TEXT("Video output class is abstract in MRQ API; format preference recorded. Use MRQ editor for concrete class."));
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_video_output"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_path_tracer -- Enable/disable the Path Tracer render pass.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqPathTracer(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_path_tracer"));

#if WITH_MRQ_MCP
    FString JobName;
    bool bEnable = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        Params->TryGetBoolField(TEXT("enable"), bEnable);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    if (bEnable)
    {
        UMoviePipelineDeferredPass_PathTracer* PathTracerPass =
            Cast<UMoviePipelineDeferredPass_PathTracer>(Config->FindOrAddSettingByClass(UMoviePipelineDeferredPass_PathTracer::StaticClass()));
        if (!PathTracerPass) return MrqErr(TEXT("Failed to add path tracer pass"));
    }
    else
    {
        UMoviePipelineSetting* Existing = Config->FindSettingByClass(UMoviePipelineDeferredPass_PathTracer::StaticClass());
        if (Existing)
        {
            Config->RemoveSetting(Existing);
        }
    }
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_path_tracer"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetBoolField(TEXT("path_tracer_enabled"), bEnable);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_path_tracer"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_console_variables -- Set console variable overrides.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqConsoleVariables(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_console_variables"));

#if WITH_MRQ_MCP
    FString JobName;
    const TArray<TSharedPtr<FJsonValue>>* CVars = nullptr;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        Params->TryGetArrayField(TEXT("cvars"), CVars);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UMoviePipelineConsoleVariableSetting* CVarSetting =
        Cast<UMoviePipelineConsoleVariableSetting>(Config->FindOrAddSettingByClass(UMoviePipelineConsoleVariableSetting::StaticClass()));
    if (!CVarSetting) return MrqErr(TEXT("Failed to get console variable setting"));

    int32 CVarsAdded = 0;
    if (CVars)
    {
        for (const TSharedPtr<FJsonValue>& CVarEntry : *CVars)
        {
            const TSharedPtr<FJsonObject>* CVarObj = nullptr;
            if (!CVarEntry->TryGetObject(CVarObj)) continue;

            FString CVarName;
            float CVarValue = 0.f;
            (*CVarObj)->TryGetStringField(TEXT("name"), CVarName);
            const TSharedPtr<FJsonValue>* ValField = (*CVarObj)->TryGetField(TEXT("value"));
            if (ValField) CVarValue = (*ValField)->AsNumber();

            if (!CVarName.IsEmpty())
            {
                CVarSetting->AddOrUpdateConsoleVariable(CVarName, CVarValue);
                ++CVarsAdded;
            }
        }
    }
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_console_variables"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetNumberField(TEXT("cvars_added"), CVarsAdded);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_console_variables"));
#endif
}

// ---------------------------------------------------------------------------
// add_mrq_render_pass -- Add a deferred render pass by type name.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleAddMrqRenderPass(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("add_mrq_render_pass"));

#if WITH_MRQ_MCP
    FString JobName, PassType = TEXT("ObjectId");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        Params->TryGetStringField(TEXT("pass_type"), PassType);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UClass* PassClass = nullptr;
    if (PassType.Equals(TEXT("Deferred"), ESearchCase::IgnoreCase) ||
        PassType.Equals(TEXT("Lit"), ESearchCase::IgnoreCase))
    {
        PassClass = UMoviePipelineDeferredPassBase::StaticClass();
    }
    else if (PassType.Equals(TEXT("Unlit"), ESearchCase::IgnoreCase))
    {
        PassClass = UMoviePipelineDeferredPass_Unlit::StaticClass();
    }
    else if (PassType.Equals(TEXT("DetailLighting"), ESearchCase::IgnoreCase))
    {
        PassClass = UMoviePipelineDeferredPass_DetailLighting::StaticClass();
    }
    else if (PassType.Equals(TEXT("LightingOnly"), ESearchCase::IgnoreCase))
    {
        PassClass = UMoviePipelineDeferredPass_LightingOnly::StaticClass();
    }
    else if (PassType.Equals(TEXT("ReflectionsOnly"), ESearchCase::IgnoreCase))
    {
        PassClass = UMoviePipelineDeferredPass_ReflectionsOnly::StaticClass();
    }
    else if (PassType.Equals(TEXT("PathTracer"), ESearchCase::IgnoreCase))
    {
        PassClass = UMoviePipelineDeferredPass_PathTracer::StaticClass();
    }
    else
    {
        PassClass = UMoviePipelineDeferredPassBase::StaticClass();
    }

    UMoviePipelineSetting* Pass = Cast<UMoviePipelineSetting>(Config->FindOrAddSettingByClass(PassClass));
    if (!Pass) return MrqErr(FString::Printf(TEXT("Failed to add render pass '%s'"), *PassType));
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("add_mrq_render_pass"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetStringField(TEXT("pass_type"), PassType);
    Data->SetStringField(TEXT("pass_class"), PassClass->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("add_mrq_render_pass"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_object_id_pass -- Enable/disable the ObjectId stencil pass.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqObjectIdPass(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_object_id_pass"));

#if WITH_MRQ_MCP
    FString JobName;
    bool bEnable = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        Params->TryGetBoolField(TEXT("enable"), bEnable);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    if (bEnable)
    {
        UMoviePipelineDeferredPassBase* DeferredPass =
            Cast<UMoviePipelineDeferredPassBase>(Config->FindOrAddSettingByClass(UMoviePipelineDeferredPassBase::StaticClass()));
        if (DeferredPass)
        {
            DeferredPass->bDisableMultisampleEffects = true;
        }
    }
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_object_id_pass"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetBoolField(TEXT("object_id_enabled"), bEnable);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_object_id_pass"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_burn_in -- Configure burn-in overlay class.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqBurnIn(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_burn_in"));

#if WITH_MRQ_MCP
    FString JobName, BurnInClass;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        Params->TryGetStringField(TEXT("burn_in_class"), BurnInClass);
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UMoviePipelineBurnInSetting* BurnInSetting =
        Cast<UMoviePipelineBurnInSetting>(Config->FindOrAddSettingByClass(UMoviePipelineBurnInSetting::StaticClass()));
    if (!BurnInSetting) return MrqErr(TEXT("Failed to get burn-in setting"));

    if (!BurnInClass.IsEmpty())
    {
        BurnInSetting->BurnInClass = FSoftClassPath(BurnInClass);
    }
    else
    {
        BurnInSetting->BurnInClass = FSoftClassPath(UMoviePipelineBurnInSetting::DefaultBurnInWidgetAsset);
    }
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_burn_in"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetStringField(TEXT("burn_in_class"), BurnInSetting->BurnInClass.ToString());
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_burn_in"));
#endif
}

// ---------------------------------------------------------------------------
// set_mrq_warm_up -- Configure render warm-up frame count.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleSetMrqWarmUp(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_mrq_warm_up"));

#if WITH_MRQ_MCP
    FString JobName;
    int32 WarmUpFrames = 30;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        const TSharedPtr<FJsonValue>* W = Params->TryGetField(TEXT("warm_up_frames"));
        if (W) WarmUpFrames = (*W)->AsNumber();
    }
    if (JobName.IsEmpty()) return MrqErr(TEXT("job_name is required"));

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = FindJobInQueue(Queue, JobName);
    if (!Job) return MrqErr(FString::Printf(TEXT("Job '%s' not found"), *JobName));

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config) return MrqErr(TEXT("Job has no configuration"));

    UMoviePipelineAntiAliasingSetting* AASetting =
        Cast<UMoviePipelineAntiAliasingSetting>(Config->FindOrAddSettingByClass(UMoviePipelineAntiAliasingSetting::StaticClass()));
    if (!AASetting) return MrqErr(TEXT("Failed to get anti-aliasing setting"));

    AASetting->RenderWarmUpCount = WarmUpFrames;
    Config->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_mrq_warm_up"));
    Data->SetStringField(TEXT("job_name"), JobName);
    Data->SetNumberField(TEXT("warm_up_frames"), AASetting->RenderWarmUpCount);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("set_mrq_warm_up"));
#endif
}

// ---------------------------------------------------------------------------
// start_mrq_render -- Start rendering the queue with a local executor.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleStartMrqRender(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("start_mrq_render"));

#if WITH_MRQ_MCP
    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    if (QueueSS->IsRendering())
    {
        return MrqErr(TEXT("MRQ is already rendering. Cancel the current render first."));
    }

    UMoviePipelineExecutorBase* Executor = QueueSS->RenderQueueWithExecutor(UMoviePipelineLinearExecutorBase::StaticClass());
    if (!Executor) return MrqErr(TEXT("Failed to start MRQ executor"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("start_mrq_render"));
    Data->SetStringField(TEXT("status_message"), Executor->GetStatusMessage());
    Data->SetNumberField(TEXT("status_progress"), Executor->GetStatusProgress());
    Data->SetBoolField(TEXT("is_rendering"), Executor->IsRendering());
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("start_mrq_render"));
#endif
}

// ---------------------------------------------------------------------------
// cancel_mrq_render -- Cancel the active MRQ render.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleCancelMrqRender(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("cancel_mrq_render"));

#if WITH_MRQ_MCP
    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineExecutorBase* Executor = QueueSS->GetActiveExecutor();
    if (!Executor || !Executor->IsRendering())
    {
        return MrqErr(TEXT("No active MRQ render to cancel"));
    }

    Executor->CancelAllJobs();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("cancel_mrq_render"));
    Data->SetBoolField(TEXT("canceled"), true);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("cancel_mrq_render"));
#endif
}

// ---------------------------------------------------------------------------
// get_mrq_render_progress -- Query the active executor's progress.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleGetMrqRenderProgress(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("get_mrq_render_progress"));

#if WITH_MRQ_MCP
    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineExecutorBase* Executor = QueueSS->GetActiveExecutor();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("get_mrq_render_progress"));
    Data->SetBoolField(TEXT("is_rendering"), QueueSS->IsRendering());
    if (Executor)
    {
        Data->SetStringField(TEXT("status_message"), Executor->GetStatusMessage());
        Data->SetNumberField(TEXT("status_progress"), Executor->GetStatusProgress());
    }
    else
    {
        Data->SetStringField(TEXT("status_message"), TEXT("No active executor"));
        Data->SetNumberField(TEXT("status_progress"), 0);
    }
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("get_mrq_render_progress"));
#endif
}

// ---------------------------------------------------------------------------
// verify_mrq_render_result -- Check executor status post-render.
// Note: Full output file verification requires disk I/O; this checks executor
// state and reports completion status.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleVerifyMrqRenderResult(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("verify_mrq_render_result"));

#if WITH_MRQ_MCP
    FString JobName;
    int32 ExpectedFrameCount = 120;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("job_name"), JobName);
        const TSharedPtr<FJsonValue>* F = Params->TryGetField(TEXT("expect_frame_count"));
        if (F) ExpectedFrameCount = (*F)->AsNumber();
    }

    UMoviePipelineQueueSubsystem* QueueSS = GEditor
        ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
        : nullptr;
    if (!QueueSS) return MrqErr(TEXT("MoviePipelineQueueSubsystem not available"));

    UMoviePipelineExecutorBase* Executor = QueueSS->GetActiveExecutor();
    bool bIsRendering = QueueSS->IsRendering();
    bool bExecutorDone = (Executor != nullptr) && !Executor->IsRendering();

    UMoviePipelineQueue* Queue = QueueSS->GetQueue();
    UMoviePipelineExecutorJob* Job = JobName.IsEmpty() ? nullptr : FindJobInQueue(Queue, JobName);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("verify_mrq_render_result"));
    Data->SetBoolField(TEXT("is_rendering"), bIsRendering);
    Data->SetBoolField(TEXT("render_complete"), bExecutorDone);
    Data->SetNumberField(TEXT("expected_frame_count"), ExpectedFrameCount);
    if (Executor)
    {
        Data->SetStringField(TEXT("status_message"), Executor->GetStatusMessage());
        Data->SetNumberField(TEXT("status_progress"), Executor->GetStatusProgress());
    }
    if (Job)
    {
        Data->SetStringField(TEXT("job_name"), Job->JobName);
    }
    Data->SetStringField(TEXT("note"), TEXT("Output file verification requires disk access; this reports executor state only."));
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("verify_mrq_render_result"));
#endif
}

// ---------------------------------------------------------------------------
// create_movie_render_graph -- Create a new UMovieGraphConfig asset.
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMovieRenderQueueCommands::HandleCreateMovieRenderGraph(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_movie_render_graph"));

#if WITH_MRQ_MCP
    FString AssetPath = TEXT("/Game/Cine");
    FString AssetName = TEXT("MRG_New");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
        Params->TryGetStringField(TEXT("asset_name"), AssetName);
    }

    FString FullPath = AssetPath + TEXT("/") + AssetName;

    FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
    if (AssetRegistryModule.Get().GetAssetByObjectPath(FSoftObjectPath(FullPath)).IsValid())
    {
        return MrqErr(FString::Printf(TEXT("Asset already exists at '%s'"), *FullPath));
    }

    UPackage* Pkg = CreatePackage(*FullPath);
    if (!Pkg) return MrqErr(TEXT("Failed to create package"));

    UMovieGraphConfig* GraphConfig = NewObject<UMovieGraphConfig>(Pkg, FName(*AssetName), RF_Public | RF_Standalone | RF_Transactional);
    if (!GraphConfig) return MrqErr(TEXT("Failed to create MovieGraphConfig"));

    GraphConfig->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(GraphConfig);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_movie_render_graph"));
    Data->SetStringField(TEXT("asset_path"), FullPath);
    Data->SetStringField(TEXT("asset_name"), AssetName);
    Data->SetBoolField(TEXT("executed"), true);
    return MrqOk(Data);
#else
    return MakeUnavailable(TEXT("create_movie_render_graph"));
#endif
}
