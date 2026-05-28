#include "Commands/EpicUnrealMCPMobileXrCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/ConfigCacheIni.h"
#include "HAL/IConsoleManager.h"

#if WITH_EDITOR
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Components/SceneComponent.h"
#include "MotionControllerComponent.h"
#include "Camera/CameraComponent.h"
#include "UObject/Package.h"
#include "Editor.h"
#endif

// ---------------------------------------------------------------------------
// 234-stubs W5 (#100): Mobile/XR executed-envelope helpers.
// ---------------------------------------------------------------------------
static TSharedPtr<FJsonObject> XrOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> XrErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

bool FEpicUnrealMCPMobileXrCommands::IsModuleAvailable()
{
#if WITH_EDITOR
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the Mobile/XR modules."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Enable OpenXR / AndroidRuntimeSettings / IOSRuntimeSettings depending on the platform; settings persist via FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe()."));
    return R;
}

FEpicUnrealMCPMobileXrCommands::FEpicUnrealMCPMobileXrCommands() {}
FEpicUnrealMCPMobileXrCommands::~FEpicUnrealMCPMobileXrCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPMobileXrCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("configure_android_settings"),  &FEpicUnrealMCPMobileXrCommands::HandleConfigureAndroidSettings},
        {TEXT("configure_ios_settings"),  &FEpicUnrealMCPMobileXrCommands::HandleConfigureIosSettings},
        {TEXT("configure_mobile_rendering"),  &FEpicUnrealMCPMobileXrCommands::HandleConfigureMobileRendering},
        {TEXT("configure_touch_input"),  &FEpicUnrealMCPMobileXrCommands::HandleConfigureTouchInput},
        {TEXT("set_device_profile"),  &FEpicUnrealMCPMobileXrCommands::HandleSetDeviceProfile},
        {TEXT("create_scalability_profile"),  &FEpicUnrealMCPMobileXrCommands::HandleCreateScalabilityProfile},
        {TEXT("enable_xr_plugin"),  &FEpicUnrealMCPMobileXrCommands::HandleEnableXrPlugin},
        {TEXT("configure_openxr"),  &FEpicUnrealMCPMobileXrCommands::HandleConfigureOpenxr},
        {TEXT("spawn_vr_pawn"),  &FEpicUnrealMCPMobileXrCommands::HandleSpawnVrPawn},
        {TEXT("configure_motion_controller"),  &FEpicUnrealMCPMobileXrCommands::HandleConfigureMotionController},
        {TEXT("configure_hmd_camera"),  &FEpicUnrealMCPMobileXrCommands::HandleConfigureHmdCamera},
        {TEXT("configure_ar_session"),  &FEpicUnrealMCPMobileXrCommands::HandleConfigureArSession},
        {TEXT("configure_ar_plane_detection"),  &FEpicUnrealMCPMobileXrCommands::HandleConfigureArPlaneDetection},
        {TEXT("platform_specific_packaging"),  &FEpicUnrealMCPMobileXrCommands::HandlePlatformSpecificPackaging}
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
// configure_android_settings
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureAndroidSettings(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_android_settings"));

    FString PackageName = TEXT("com.company.project");
    int32 MinSdk = 26;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("package_name"), PackageName);
        if (TSharedPtr<FJsonValue> Val = Params->TryGetField(TEXT("min_sdk")))
            MinSdk = static_cast<int32>(Val->AsNumber());
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_android_settings"));

    // Persist to AndroidRuntimeSettings in DefaultEngine.ini
    GConfig->SetString(TEXT("/Script/AndroidRuntimeSettings.AndroidRuntimeSettings"), TEXT("PackageName"), *PackageName, GEngineIni);
    GConfig->SetInt(TEXT("/Script/AndroidRuntimeSettings.AndroidRuntimeSettings"), TEXT("MinSDKVersion"), MinSdk, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_android_settings"));
    Data->SetStringField(TEXT("package_name"), PackageName);
    Data->SetNumberField(TEXT("min_sdk"), MinSdk);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// configure_ios_settings
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureIosSettings(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ios_settings"));

    FString BundleId = TEXT("com.company.project");
    FString MinimumIos = TEXT("15.0");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("bundle_id"), BundleId);
        Params->TryGetStringField(TEXT("minimum_ios"), MinimumIos);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ios_settings"));

    GConfig->SetString(TEXT("/Script/IOSRuntimeSettings.IOSRuntimeSettings"), TEXT("BundleIdentifier"), *BundleId, GEngineIni);
    GConfig->SetString(TEXT("/Script/IOSRuntimeSettings.IOSRuntimeSettings"), TEXT("MinimumiOSVersion"), *MinimumIos, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ios_settings"));
    Data->SetStringField(TEXT("bundle_id"), BundleId);
    Data->SetStringField(TEXT("minimum_ios"), MinimumIos);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// configure_mobile_rendering
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureMobileRendering(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_mobile_rendering"));

    FString FeatureLevel = TEXT("ES3_1");
    bool bForwardShading = true;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("feature_level"), FeatureLevel);
        Params->TryGetBoolField(TEXT("forward_shading"), bForwardShading);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_mobile_rendering"));

    GConfig->SetString(TEXT("/Script/Engine.RendererSettings"), TEXT("MobileFeatureLevel"), *FeatureLevel, GEngineIni);
    GConfig->SetBool(TEXT("/Script/Engine.RendererSettings"), TEXT("bForwardShading"), bForwardShading, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_mobile_rendering"));
    Data->SetStringField(TEXT("feature_level"), FeatureLevel);
    Data->SetBoolField(TEXT("forward_shading"), bForwardShading);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// configure_touch_input
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureTouchInput(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_touch_input"));

    bool bEnable = true;
    bool bPinchZoom = false;
    if (Params.IsValid())
    {
        Params->TryGetBoolField(TEXT("enable"), bEnable);
        Params->TryGetBoolField(TEXT("pinch_zoom"), bPinchZoom);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_touch_input"));

    GConfig->SetBool(TEXT("/Script/Engine.InputSettings"), TEXT("bUseTouchForTouchInterface"), bEnable, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_touch_input"));
    Data->SetBoolField(TEXT("enable"), bEnable);
    Data->SetBoolField(TEXT("pinch_zoom"), bPinchZoom);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// set_device_profile
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleSetDeviceProfile(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_device_profile"));

    FString ProfileName = TEXT("Android_High");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("profile_name"), ProfileName);
    }

    // Use console variable to set active device profile
    IConsoleVariable* ProfileVar = IConsoleManager::Get().FindConsoleVariable(TEXT("deviceprofile.ProfileToUse"));
    if (ProfileVar)
    {
        ProfileVar->Set(*ProfileName, ECVF_SetByCode);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: set_device_profile"));

    GConfig->SetString(TEXT("DeviceProfiles"), TEXT("ActiveProfileName"), *ProfileName, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_device_profile"));
    Data->SetStringField(TEXT("profile_name"), ProfileName);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// create_scalability_profile
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleCreateScalabilityProfile(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_scalability_profile"));

    FString ProfileName = TEXT("High");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("profile_name"), ProfileName);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_scalability_profile"));

    // Create scalability group section
    const FString Section = FString::Printf(TEXT("Scalability_%s"), *ProfileName);
    GConfig->SetInt(*Section, TEXT("sg.ResolutionQuality"), 100, GEngineIni);
    GConfig->SetInt(*Section, TEXT("sg.ViewDistanceQuality"), 3, GEngineIni);
    GConfig->SetInt(*Section, TEXT("sg.AntiAliasingQuality"), 3, GEngineIni);
    GConfig->SetInt(*Section, TEXT("sg.ShadowQuality"), 3, GEngineIni);
    GConfig->SetInt(*Section, TEXT("sg.GlobalIlluminationQuality"), 3, GEngineIni);
    GConfig->SetInt(*Section, TEXT("sg.PostProcessQuality"), 3, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_scalability_profile"));
    Data->SetStringField(TEXT("profile_name"), ProfileName);
    Data->SetStringField(TEXT("section"), Section);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// enable_xr_plugin
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleEnableXrPlugin(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("enable_xr_plugin"));

    FString PluginName = TEXT("OpenXR");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("plugin_name"), PluginName);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: enable_xr_plugin"));

    // Enable the XR plugin in project settings
    const FString Section = TEXT("/Script/Engine.XRPluginManager");
    GConfig->SetBool(*Section, *FString::Printf(TEXT("bEnable%s"), *PluginName), true, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("enable_xr_plugin"));
    Data->SetStringField(TEXT("plugin_name"), PluginName);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// configure_openxr
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureOpenxr(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_openxr"));

    FString SessionMode = TEXT("Stereo");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("session_mode"), SessionMode);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_openxr"));

    const FString Section = TEXT("/Script/OpenXRHMD.OpenXRHMDSettings");
    GConfig->SetString(*Section, TEXT("SessionMode"), *SessionMode, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_openxr"));
    Data->SetStringField(TEXT("session_mode"), SessionMode);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// spawn_vr_pawn — stub (Part 2)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleSpawnVrPawn(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_vr_pawn"));

#if WITH_EDITOR
    FString ActorName = TEXT("VRPawn");
    FString AssetPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
        return XrErr(TEXT("spawn_vr_pawn: No editor world available."));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_vr_pawn"));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*ActorName);
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    APawn* NewPawn = World->SpawnActor<APawn>(APawn::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!NewPawn)
        return XrErr(FString::Printf(TEXT("spawn_vr_pawn: Failed to spawn actor '%s'."), *ActorName));

    NewPawn->SetActorLabel(ActorName);

    USceneComponent* VRRoot = NewObject<USceneComponent>(NewPawn, TEXT("VRRoot"));
    VRRoot->SetupAttachment(NewPawn->GetRootComponent());
    VRRoot->RegisterComponent();
    NewPawn->SetRootComponent(VRRoot);
    NewPawn->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_vr_pawn"));
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
#else
    return XrErr(TEXT("spawn_vr_pawn: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// configure_motion_controller — stub (Part 2)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureMotionController(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_motion_controller"));

#if WITH_EDITOR
    FString ActorName;
    FString Hand = TEXT("Right");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("hand"), Hand);
    }

    if (ActorName.IsEmpty())
        return XrErr(TEXT("configure_motion_controller: 'actor_name' is required."));

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
        return XrErr(TEXT("configure_motion_controller: No editor world available."));

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
        return XrErr(FString::Printf(TEXT("configure_motion_controller: Actor '%s' not found."), *ActorName));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_motion_controller"));
    TargetActor->Modify();

    UMotionControllerComponent* MC = NewObject<UMotionControllerComponent>(TargetActor, TEXT("MotionController"));
    MC->SetTrackingMotionSource(FName(Hand));
    MC->SetupAttachment(TargetActor->GetRootComponent());
    MC->RegisterComponent();
    TargetActor->AddInstanceComponent(MC);
    TargetActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_motion_controller"));
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetStringField(TEXT("hand"), Hand);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
#else
    return XrErr(TEXT("configure_motion_controller: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// configure_hmd_camera — stub (Part 2)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureHmdCamera(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_hmd_camera"));

#if WITH_EDITOR
    FString ActorName;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
    }

    if (ActorName.IsEmpty())
        return XrErr(TEXT("configure_hmd_camera: 'actor_name' is required."));

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
        return XrErr(TEXT("configure_hmd_camera: No editor world available."));

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
        return XrErr(FString::Printf(TEXT("configure_hmd_camera: Actor '%s' not found."), *ActorName));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_hmd_camera"));
    TargetActor->Modify();

    UCameraComponent* HmdCamera = NewObject<UCameraComponent>(TargetActor, TEXT("HMD_Camera"));
    HmdCamera->SetupAttachment(TargetActor->GetRootComponent());
    HmdCamera->RegisterComponent();
    TargetActor->AddInstanceComponent(HmdCamera);
    TargetActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_hmd_camera"));
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
#else
    return XrErr(TEXT("configure_hmd_camera: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// configure_ar_session — stub (Part 2)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureArSession(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ar_session"));

#if WITH_EDITOR
    FString WorldAlignment = TEXT("Gravity");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("world_alignment"), WorldAlignment);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ar_session"));

    const FString Section = TEXT("/Script/ARSessionConfig.ARSessionConfig");
    GConfig->SetString(*Section, TEXT("WorldAlignment"), *WorldAlignment, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ar_session"));
    Data->SetStringField(TEXT("world_alignment"), WorldAlignment);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
#else
    return XrErr(TEXT("configure_ar_session: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// configure_ar_plane_detection — stub (Part 2)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureArPlaneDetection(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ar_plane_detection"));

#if WITH_EDITOR
    bool bHorizontal = true;
    bool bVertical = false;
    if (Params.IsValid())
    {
        Params->TryGetBoolField(TEXT("horizontal"), bHorizontal);
        Params->TryGetBoolField(TEXT("vertical"), bVertical);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ar_plane_detection"));

    const FString Section = TEXT("/Script/ARSessionConfig.ARSessionConfig");
    GConfig->SetBool(*Section, TEXT("bHorizontalPlaneDetection"), bHorizontal, GEngineIni);
    GConfig->SetBool(*Section, TEXT("bVerticalPlaneDetection"), bVertical, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ar_plane_detection"));
    Data->SetBoolField(TEXT("horizontal"), bHorizontal);
    Data->SetBoolField(TEXT("vertical"), bVertical);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
#else
    return XrErr(TEXT("configure_ar_plane_detection: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// platform_specific_packaging — stub (Part 2)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandlePlatformSpecificPackaging(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("platform_specific_packaging"));

#if WITH_EDITOR
    FString Platform = TEXT("Android");
    FString BuildConfiguration = TEXT("Shipping");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("platform"), Platform);
        Params->TryGetStringField(TEXT("build_configuration"), BuildConfiguration);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: platform_specific_packaging"));

    const FString Section = FString::Printf(TEXT("/Script/%s.%sRuntimeSettings"), *Platform, *Platform);
    GConfig->SetString(*Section, TEXT("BuildConfiguration"), *BuildConfiguration, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    FEpicUnrealMCPCommonUtils::TryUpdateDefaultConfigFileSafe(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("platform_specific_packaging"));
    Data->SetStringField(TEXT("platform"), Platform);
    Data->SetStringField(TEXT("build_configuration"), BuildConfiguration);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
#else
    return XrErr(TEXT("platform_specific_packaging: requires WITH_EDITOR."));
#endif
}
