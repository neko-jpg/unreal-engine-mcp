#include "Commands/EpicUnrealMCPMobileXrCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/ConfigCacheIni.h"
#include "HAL/IConsoleManager.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/DefaultPawn.h"
#include "Camera/CameraActor.h"
#include "Components/MotionControllerComponent.h"
#include "Components/CameraComponent.h"
#include "Subsystems/EditorActorSubsystem.h"
#include "UObject/SoftObjectPath.h"

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
    R->SetStringField(TEXT("hint"), TEXT("Enable OpenXR / AndroidRuntimeSettings / IOSRuntimeSettings depending on the platform; settings persist via TryUpdateDefaultConfigFile()."));
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
        if (const TSharedPtr<FJsonValue>* Val = Params->TryGetField(TEXT("min_sdk")))
            MinSdk = static_cast<int32>(Val->Get()->AsNumber());
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_android_settings"));

    // Persist to AndroidRuntimeSettings in DefaultEngine.ini
    GConfig->SetString(TEXT("/Script/AndroidRuntimeSettings.AndroidRuntimeSettings"), TEXT("PackageName"), *PackageName, GEngineIni);
    GConfig->SetInt(TEXT("/Script/AndroidRuntimeSettings.AndroidRuntimeSettings"), TEXT("MinSDKVersion"), MinSdk, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    TryUpdateDefaultConfigFile(GEngineIni);

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
    TryUpdateDefaultConfigFile(GEngineIni);

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
    TryUpdateDefaultConfigFile(GEngineIni);

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
    TryUpdateDefaultConfigFile(GEngineIni);

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
    TryUpdateDefaultConfigFile(GEngineIni);

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
    TryUpdateDefaultConfigFile(GEngineIni);

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
    TryUpdateDefaultConfigFile(GEngineIni);

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
    TryUpdateDefaultConfigFile(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_openxr"));
    Data->SetStringField(TEXT("session_mode"), SessionMode);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// spawn_vr_pawn
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleSpawnVrPawn(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_vr_pawn"));

    FString ActorName = TEXT("VRPawn");
    FString AssetPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    }

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return XrErr(TEXT("No editor world available"));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_vr_pawn"));

    UClass* SpawnClass = ADefaultPawn::StaticClass();
    if (!AssetPath.IsEmpty())
    {
        FSoftObjectPath Path(AssetPath);
        UClass* Loaded = Cast<UClass>(Path.TryLoad());
        if (Loaded && Loaded->IsChildOf(APawn::StaticClass()))
        {
            SpawnClass = Loaded;
        }
    }

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = *ActorName;
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    APawn* NewPawn = World->SpawnActor<APawn>(SpawnClass, FTransform::Identity, SpawnParams);
    if (!NewPawn) return XrErr(TEXT("Failed to spawn VR pawn"));

    NewPawn->SetActorLabel(*ActorName);
    NewPawn->AddToRoot();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_vr_pawn"));
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetStringField(TEXT("class"), SpawnClass->GetName());
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// configure_motion_controller
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureMotionController(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_motion_controller"));

    FString ActorName;
    FString Hand = TEXT("Right");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("hand"), Hand);
    }

    if (ActorName.IsEmpty()) return XrErr(TEXT("actor_name is required"));

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return XrErr(TEXT("No editor world available"));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_motion_controller"));

    // Find target actor by label
    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetActorLabel() == ActorName)
        {
            TargetActor = *It;
            break;
        }
    }
    if (!TargetActor) return XrErr(FString::Printf(TEXT("Actor '%s' not found"), *ActorName));

    // Create and attach motion controller component
    EControllerHand HandEnum = (Hand == TEXT("Left")) ? EControllerHand::Left : EControllerHand::Right;
    UMotionControllerComponent* MC = NewObject<UMotionControllerComponent>(TargetActor);
    MC->SetTrackingMotionSource(FName(*Hand));
    MC->SetAssociatedPlayerIndex(0);
    MC->RegisterComponent();
    MC->AttachToComponent(TargetActor->GetRootComponent(), FAttachmentTransformRules::KeepRelativeTransform);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_motion_controller"));
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetStringField(TEXT("hand"), Hand);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// configure_hmd_camera
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureHmdCamera(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_hmd_camera"));

    FString ActorName;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
    }

    if (ActorName.IsEmpty()) return XrErr(TEXT("actor_name is required"));

    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return XrErr(TEXT("No editor world available"));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_hmd_camera"));

    // Find target actor by label
    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetActorLabel() == ActorName)
        {
            TargetActor = *It;
            break;
        }
    }
    if (!TargetActor) return XrErr(FString::Printf(TEXT("Actor '%s' not found"), *ActorName));

    // Create and attach a camera component for HMD tracking
    UCameraComponent* Cam = NewObject<UCameraComponent>(TargetActor);
    Cam->bLockToHmd = true;
    Cam->bUsePawnControlRotation = false;
    Cam->RegisterComponent();
    Cam->AttachToComponent(TargetActor->GetRootComponent(), FAttachmentTransformRules::KeepRelativeTransform);

    // Persist HMD camera setting
    GConfig->SetBool(TEXT("/Script/Engine.XRTrackingSystem"), TEXT("bLockToHMD"), true, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    TryUpdateDefaultConfigFile(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_hmd_camera"));
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// configure_ar_session
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureArSession(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ar_session"));

    FString WorldAlignment = TEXT("Gravity");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("world_alignment"), WorldAlignment);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ar_session"));

    const FString Section = TEXT("/Script/ARSessionConfig.ARSessionConfig");
    GConfig->SetString(*Section, TEXT("WorldAlignmentMode"), *WorldAlignment, GEngineIni);
    GConfig->SetBool(*Section, TEXT("bEnableAutoStartARSession"), true, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    TryUpdateDefaultConfigFile(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ar_session"));
    Data->SetStringField(TEXT("world_alignment"), WorldAlignment);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// configure_ar_plane_detection
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandleConfigureArPlaneDetection(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_ar_plane_detection"));

    bool bHorizontal = true;
    bool bVertical = false;
    if (Params.IsValid())
    {
        Params->TryGetBoolField(TEXT("horizontal"), bHorizontal);
        Params->TryGetBoolField(TEXT("vertical"), bVertical);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: configure_ar_plane_detection"));

    const FString Section = TEXT("/Script/ARSessionConfig.ARSessionConfig");
    int32 Flags = 0;
    if (bHorizontal) Flags |= 1;  // EARPlaneDetectionFlags::Horizontal
    if (bVertical)   Flags |= 2;  // EARPlaneDetectionFlags::Vertical
    GConfig->SetInt(*Section, TEXT("PlaneDetectionMode"), Flags, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    TryUpdateDefaultConfigFile(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_ar_plane_detection"));
    Data->SetBoolField(TEXT("horizontal"), bHorizontal);
    Data->SetBoolField(TEXT("vertical"), bVertical);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}

// ---------------------------------------------------------------------------
// platform_specific_packaging
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPMobileXrCommands::HandlePlatformSpecificPackaging(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("platform_specific_packaging"));

    FString Platform = TEXT("Android");
    FString BuildConfiguration = TEXT("Shipping");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("platform"), Platform);
        Params->TryGetStringField(TEXT("build_configuration"), BuildConfiguration);
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: platform_specific_packaging"));

    // Map platform to UE ini section
    FString PlatformSection;
    if (Platform == TEXT("Android"))
        PlatformSection = TEXT("/Script/AndroidRuntimeSettings.AndroidRuntimeSettings");
    else if (Platform == TEXT("IOS"))
        PlatformSection = TEXT("/Script/IOSRuntimeSettings.IOSRuntimeSettings");
    else
        PlatformSection = FString::Printf(TEXT("/Script/%sPlatformSettings.%sPlatformSettings"), *Platform, *Platform);

    GConfig->SetString(*PlatformSection, TEXT("BuildConfiguration"), *BuildConfiguration, GEngineIni);
    GConfig->Flush(false, GEngineIni);
    TryUpdateDefaultConfigFile(GEngineIni);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("platform_specific_packaging"));
    Data->SetStringField(TEXT("platform"), Platform);
    Data->SetStringField(TEXT("build_configuration"), BuildConfiguration);
    Data->SetStringField(TEXT("section"), PlatformSection);
    Data->SetBoolField(TEXT("executed"), true);
    return XrOk(Data);
}
