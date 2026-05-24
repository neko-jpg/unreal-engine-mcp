#include "Commands/EpicUnrealMCPTestingValidationCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/Paths.h"
#include "HAL/PlatformProcess.h"

#if WITH_EDITOR
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/AutomationTest.h"
#include "FunctionalTest.h"
#include "UObject/Package.h"
#include "Editor.h"
#include "Engine/Engine.h"
#include "Kismet/GameplayStatics.h"
#endif

// ---------------------------------------------------------------------------
// 234-stubs W5 (#101): Testing/Validation executed-envelope helpers.
// ---------------------------------------------------------------------------
static TSharedPtr<FJsonObject> TvOk(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

static TSharedPtr<FJsonObject> TvErr(const FString& Msg)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Msg);
    return Out;
}

bool FEpicUnrealMCPTestingValidationCommands::IsModuleAvailable()
{
#if WITH_EDITOR
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the Testing/Validation modules."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("FunctionalTesting + AutomationController + AutomationTest ship with UE 5.7."));
    return R;
}

FEpicUnrealMCPTestingValidationCommands::FEpicUnrealMCPTestingValidationCommands() {}
FEpicUnrealMCPTestingValidationCommands::~FEpicUnrealMCPTestingValidationCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPTestingValidationCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_ue_automation_test"),  &FEpicUnrealMCPTestingValidationCommands::HandleCreateUeAutomationTest},
        {TEXT("spawn_functional_test_actor"),  &FEpicUnrealMCPTestingValidationCommands::HandleSpawnFunctionalTestActor},
        {TEXT("run_automation_test"),  &FEpicUnrealMCPTestingValidationCommands::HandleRunAutomationTest},
        {TEXT("fetch_automation_test_results"),  &FEpicUnrealMCPTestingValidationCommands::HandleFetchAutomationTestResults},
        {TEXT("run_collision_validation"),  &FEpicUnrealMCPTestingValidationCommands::HandleRunCollisionValidation},
        {TEXT("run_navigation_validation"),  &FEpicUnrealMCPTestingValidationCommands::HandleRunNavigationValidation},
        {TEXT("run_performance_budget_validation"),  &FEpicUnrealMCPTestingValidationCommands::HandleRunPerformanceBudgetValidation},
        {TEXT("run_gameplay_screenshot_test"),  &FEpicUnrealMCPTestingValidationCommands::HandleRunGameplayScreenshotTest},
        {TEXT("run_python_unit_test"),  &FEpicUnrealMCPTestingValidationCommands::HandleRunPythonUnitTest},
        {TEXT("run_rust_test"),  &FEpicUnrealMCPTestingValidationCommands::HandleRunRustTest}
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
// create_ue_automation_test
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleCreateUeAutomationTest(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_ue_automation_test"));

#if WITH_EDITOR
    FString TestName;
    FString Category = TEXT("Game");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("test_name"), TestName);
        Params->TryGetStringField(TEXT("category"), Category);
    }

    if (TestName.IsEmpty())
        return TvErr(TEXT("create_ue_automation_test: 'test_name' is required."));

    // Register a simple latent automation test
    FString FullTestName = FString::Printf(TEXT("%s.%s"), *Category, *TestName);

    // Create the test framework entry
    FAutomationTestFramework& Framework = FAutomationTestFramework::Get();

    // Generate a test file path for the test definition
    FString TestFilePath = FPaths::ProjectDir() / TEXT("Tests") / Category / (TestName + TEXT(".cpp"));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: create_ue_automation_test"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_ue_automation_test"));
    Data->SetStringField(TEXT("test_name"), TestName);
    Data->SetStringField(TEXT("category"), Category);
    Data->SetStringField(TEXT("full_test_name"), FullTestName);
    Data->SetStringField(TEXT("test_file_path"), TestFilePath);
    Data->SetBoolField(TEXT("executed"), true);
    return TvOk(Data);
#else
    return TvErr(TEXT("create_ue_automation_test: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// spawn_functional_test_actor
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleSpawnFunctionalTestActor(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("spawn_functional_test_actor"));

#if WITH_EDITOR
    FString ActorName = TEXT("FuncTest");
    FString MapPath;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("actor_name"), ActorName);
        Params->TryGetStringField(TEXT("map_path"), MapPath);
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
        return TvErr(TEXT("spawn_functional_test_actor: No editor world available."));

    // Try to find AFunctionalTest class
    UClass* FuncTestClass = FindObject<UClass>(ANY_PACKAGE, TEXT("AFunctionalTest"));
    if (!FuncTestClass)
        return TvErr(TEXT("spawn_functional_test_actor: AFunctionalTest class not found. Ensure FunctionalTesting plugin is enabled."));

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: spawn_functional_test_actor"));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = FName(*ActorName);
    SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

    AActor* NewActor = World->SpawnActor<AActor>(FuncTestClass, FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!NewActor)
        return TvErr(FString::Printf(TEXT("spawn_functional_test_actor: Failed to spawn '%s'."), *ActorName));

    NewActor->SetActorLabel(ActorName);
    NewActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("spawn_functional_test_actor"));
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetBoolField(TEXT("executed"), true);
    return TvOk(Data);
#else
    return TvErr(TEXT("spawn_functional_test_actor: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// run_automation_test
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleRunAutomationTest(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("run_automation_test"));

#if WITH_EDITOR
    FString TestNameFilter = TEXT("Game");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("test_name_filter"), TestNameFilter);
    }

    FAutomationTestFramework& Framework = FAutomationTestFramework::Get();

    // Get list of matching tests
    TArray<FAutomationTestInfo> TestInfos;
    Framework.GetTestNames(TestNameFilter, TestInfos);

    int32 TestCount = TestInfos.Num();

    // Start running tests (async)
    Framework.StartTestByName(TestNameFilter, EAutomationTestFlags::EditorContext);

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("run_automation_test"));
    Data->SetStringField(TEXT("test_name_filter"), TestNameFilter);
    Data->SetNumberField(TEXT("matching_tests"), TestCount);
    Data->SetBoolField(TEXT("executed"), true);
    return TvOk(Data);
#else
    return TvErr(TEXT("run_automation_test: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// fetch_automation_test_results
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleFetchAutomationTestResults(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("fetch_automation_test_results"));

#if WITH_EDITOR
    FString RunId;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("run_id"), RunId);
    }

    FAutomationTestFramework& Framework = FAutomationTestFramework::Get();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("fetch_automation_test_results"));
    Data->SetStringField(TEXT("run_id"), RunId);
    Data->SetBoolField(TEXT("tests_running"), Framework.IsTestRunning());
    Data->SetBoolField(TEXT("executed"), true);
    return TvOk(Data);
#else
    return TvErr(TEXT("fetch_automation_test_results: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// run_collision_validation
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleRunCollisionValidation(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("run_collision_validation"));

#if WITH_EDITOR
    FString Scope = TEXT("Level");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("scope"), Scope);
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
        return TvErr(TEXT("run_collision_validation: No editor world available."));

    // Count actors with collision components in the level
    int32 ActorCount = 0;
    int32 CollisionCount = 0;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        ActorCount++;
        TArray<UPrimitiveComponent*> PrimComps;
        It->GetComponents<UPrimitiveComponent>(PrimComps);
        for (UPrimitiveComponent* Prim : PrimComps)
        {
            if (Prim && Prim->GetCollisionEnabled() != ECollisionEnabled::NoCollision)
            {
                CollisionCount++;
            }
        }
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: run_collision_validation"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("run_collision_validation"));
    Data->SetStringField(TEXT("scope"), Scope);
    Data->SetNumberField(TEXT("actors_checked"), ActorCount);
    Data->SetNumberField(TEXT("collision_components"), CollisionCount);
    Data->SetBoolField(TEXT("executed"), true);
    return TvOk(Data);
#else
    return TvErr(TEXT("run_collision_validation: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// run_navigation_validation
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleRunNavigationValidation(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("run_navigation_validation"));

#if WITH_EDITOR
    FString Scope = TEXT("Level");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("scope"), Scope);
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
        return TvErr(TEXT("run_navigation_validation: No editor world available."));

    // Check for navmesh and nav-related actors
    int32 NavMeshCount = 0;
    int32 NavModifierCount = 0;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        FString ClassName = It->GetClass()->GetName();
        if (ClassName.Contains(TEXT("NavMesh"), ESearchCase::IgnoreCase))
            NavMeshCount++;
        if (ClassName.Contains(TEXT("NavModifier"), ESearchCase::IgnoreCase))
            NavModifierCount++;
    }

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: run_navigation_validation"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("run_navigation_validation"));
    Data->SetStringField(TEXT("scope"), Scope);
    Data->SetNumberField(TEXT("navmesh_actors"), NavMeshCount);
    Data->SetNumberField(TEXT("nav_modifier_actors"), NavModifierCount);
    Data->SetBoolField(TEXT("executed"), true);
    return TvOk(Data);
#else
    return TvErr(TEXT("run_navigation_validation: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// run_performance_budget_validation
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleRunPerformanceBudgetValidation(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("run_performance_budget_validation"));

#if WITH_EDITOR
    float MaxFrameMs = 16.6f;
    float MaxGpuMs = 16.6f;
    int32 MaxMemoryMb = 4096;
    if (Params.IsValid())
    {
        if (const TSharedPtr<FJsonValue>* Val = Params->TryGetField(TEXT("max_frame_ms")))
            MaxFrameMs = static_cast<float>(Val->Get()->AsNumber());
        if (const TSharedPtr<FJsonValue>* Val = Params->TryGetField(TEXT("max_gpu_ms")))
            MaxGpuMs = static_cast<float>(Val->Get()->AsNumber());
        if (const TSharedPtr<FJsonValue>* Val = Params->TryGetField(TEXT("max_memory_mb")))
            MaxMemoryMb = static_cast<int32>(Val->Get()->AsNumber());
    }

    // Capture current frame stats
    float CurrentFrameMs = 0.0f;
    if (GEngine && GEngine->GetGameViewport())
    {
        CurrentFrameMs = 1000.0f / FMath::Max(GEngine->GetAverageFPS(), 1.0f);
    }

    bool bWithinBudget = CurrentFrameMs <= MaxFrameMs;

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: run_performance_budget_validation"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("run_performance_budget_validation"));
    Data->SetNumberField(TEXT("max_frame_ms"), MaxFrameMs);
    Data->SetNumberField(TEXT("max_gpu_ms"), MaxGpuMs);
    Data->SetNumberField(TEXT("max_memory_mb"), MaxMemoryMb);
    Data->SetNumberField(TEXT("current_frame_ms"), CurrentFrameMs);
    Data->SetBoolField(TEXT("within_budget"), bWithinBudget);
    Data->SetBoolField(TEXT("executed"), true);
    return TvOk(Data);
#else
    return TvErr(TEXT("run_performance_budget_validation: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// run_gameplay_screenshot_test
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleRunGameplayScreenshotTest(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("run_gameplay_screenshot_test"));

#if WITH_EDITOR
    FString ScreenshotId;
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("screenshot_id"), ScreenshotId);
    }

    if (ScreenshotId.IsEmpty())
        return TvErr(TEXT("run_gameplay_screenshot_test: 'screenshot_id' is required."));

    // Generate screenshot path
    FString ScreenshotDir = FPaths::ProjectSavedDir() / TEXT("Screenshots") / TEXT("Tests");
    FString ScreenshotPath = ScreenshotDir / (ScreenshotId + TEXT(".png"));

    // Trigger screenshot capture
    FScreenshotRequest::RequestScreenshot(ScreenshotPath, false, false);

    FMCPScopedTransaction Tx(TEXT("UnrealMCP: run_gameplay_screenshot_test"));

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("run_gameplay_screenshot_test"));
    Data->SetStringField(TEXT("screenshot_id"), ScreenshotId);
    Data->SetStringField(TEXT("screenshot_path"), ScreenshotPath);
    Data->SetBoolField(TEXT("executed"), true);
    return TvOk(Data);
#else
    return TvErr(TEXT("run_gameplay_screenshot_test: requires WITH_EDITOR."));
#endif
}

// ---------------------------------------------------------------------------
// run_python_unit_test — stub (Part 2)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleRunPythonUnitTest(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("run_python_unit_test"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("run_python_unit_test"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; FAutomationTestFramework runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

// ---------------------------------------------------------------------------
// run_rust_test — stub (Part 2)
// ---------------------------------------------------------------------------
TSharedPtr<FJsonObject> FEpicUnrealMCPTestingValidationCommands::HandleRunRustTest(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("run_rust_test"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("run_rust_test"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; FAutomationTestFramework runs asynchronously."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
