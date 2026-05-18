// =====================================================================
// EpicUnrealMCPPhysicsCommands
//
// Phase 4 (Issue #31) split from EpicUnrealMCPProceduralCommands.cpp.
// Owns:
//   - set_actor_collision_preset
//   - set_actor_physics
//   - create_physical_material
//   - spawn_radial_force
//   - spawn_physics_constraint
//
// Routed under id 22.
// =====================================================================

#include "Commands/EpicUnrealMCPPhysicsCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Editor.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"
#include "Engine/World.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "PhysicsEngine/RadialForceComponent.h"
#include "PhysicsEngine/RadialForceActor.h"
#include "PhysicsEngine/PhysicsConstraintActor.h"
#include "PhysicsEngine/PhysicsConstraintComponent.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "EditorAssetLibrary.h"
#include "ScopedTransaction.h"
#include "UObject/Package.h"
#include "Misc/Paths.h"

FEpicUnrealMCPPhysicsCommands::FEpicUnrealMCPPhysicsCommands()
{
}

UWorld* FEpicUnrealMCPPhysicsCommands::GetEditorWorld() const
{
    if (!GEditor)
    {
        return nullptr;
    }
    return GEditor->GetEditorWorldContext().World();
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPPhysicsCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("set_actor_collision_preset"), &FEpicUnrealMCPPhysicsCommands::HandleSetActorCollisionPreset},
        {TEXT("set_actor_physics"),          &FEpicUnrealMCPPhysicsCommands::HandleSetActorPhysics},
        {TEXT("create_physical_material"),   &FEpicUnrealMCPPhysicsCommands::HandleCreatePhysicalMaterial},
        {TEXT("spawn_radial_force"),         &FEpicUnrealMCPPhysicsCommands::HandleSpawnRadialForce},
        {TEXT("spawn_physics_constraint"),   &FEpicUnrealMCPPhysicsCommands::HandleSpawnPhysicsConstraint},
    };

    const Handler* H = Dispatch.Find(CommandType);
    if (H)
    {
        return (this->*(*H))(Params);
    }

    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown physics command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSetActorCollisionPreset(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'actor_name' parameter"));
    }

    FString PresetName;
    if (!Params->TryGetStringField(TEXT("preset"), PresetName) || PresetName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'preset' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    AActor* Actor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName || It->GetActorLabel() == ActorName)
        {
            Actor = *It;
            break;
        }
    }

    if (!Actor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor '%s' not found"), *ActorName));
    }

    UPrimitiveComponent* RootComp = Cast<UPrimitiveComponent>(Actor->GetRootComponent());
    if (!RootComp)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Actor does not have a primitive root component"));
    }

    FScopedTransaction Transaction(FText::FromString(FString::Printf(TEXT("UnrealMCP: Set Collision Preset %s"), *ActorName)));
    Actor->Modify();
    RootComp->Modify();
    RootComp->SetCollisionProfileName(FName(*PresetName));

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    Result->SetStringField(TEXT("preset"), PresetName);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSetActorPhysics(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'actor_name' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    AActor* Actor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName || It->GetActorLabel() == ActorName)
        {
            Actor = *It;
            break;
        }
    }

    if (!Actor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor '%s' not found"), *ActorName));
    }

    UPrimitiveComponent* RootComp = Cast<UPrimitiveComponent>(Actor->GetRootComponent());
    if (!RootComp)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Actor does not have a primitive root component"));
    }

    FScopedTransaction Transaction(FText::FromString(FString::Printf(TEXT("UnrealMCP: Set Actor Physics %s"), *ActorName)));
    Actor->Modify();
    RootComp->Modify();

    bool bSimulatePhysics = false;
    if (Params->TryGetBoolField(TEXT("simulate_physics"), bSimulatePhysics))
    {
        RootComp->SetSimulatePhysics(bSimulatePhysics);
    }

    bool bGravityEnabled = true;
    if (Params->TryGetBoolField(TEXT("gravity_enabled"), bGravityEnabled))
    {
        RootComp->SetEnableGravity(bGravityEnabled);
    }

    double MassScale = 1.0;
    if (Params->TryGetNumberField(TEXT("mass_scale"), MassScale))
    {
        RootComp->SetMassScale(NAME_None, static_cast<float>(MassScale));
    }

    double LinearDamping = 0.01;
    if (Params->TryGetNumberField(TEXT("linear_damping"), LinearDamping))
    {
        RootComp->SetLinearDamping(static_cast<float>(LinearDamping));
    }

    double AngularDamping = 0.0;
    if (Params->TryGetNumberField(TEXT("angular_damping"), AngularDamping))
    {
        RootComp->SetAngularDamping(static_cast<float>(AngularDamping));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    Result->SetBoolField(TEXT("simulate_physics"), RootComp->IsSimulatingPhysics());
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleCreatePhysicalMaterial(const TSharedPtr<FJsonObject>& Params)
{
    FString AssetPath;
    if (!Params->TryGetStringField(TEXT("asset_path"), AssetPath) || AssetPath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or empty 'asset_path' parameter"));
    }

    FString AssetName = FPaths::GetBaseFilename(AssetPath);
    UPackage* Package = CreatePackage(*AssetPath);
    if (!Package)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create package for physical material"));
    }

    UPhysicalMaterial* PhysMat = NewObject<UPhysicalMaterial>(Package, FName(*AssetName), RF_Public | RF_Standalone);
    if (!PhysMat)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create PhysicalMaterial object"));
    }

    double Friction = 0.7;
    if (Params->TryGetNumberField(TEXT("friction"), Friction))
    {
        PhysMat->Friction = static_cast<float>(Friction);
    }

    double Restitution = 0.3;
    if (Params->TryGetNumberField(TEXT("restitution"), Restitution))
    {
        PhysMat->Restitution = static_cast<float>(Restitution);
    }

    double Density = 1.0;
    if (Params->TryGetNumberField(TEXT("density"), Density))
    {
        // Density is not a direct property on UPhysicalMaterial in newer UE versions;
        // it is typically part of the body setup or physical material mask.
        // We skip setting it here to avoid compilation issues.
    }

    Package->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(PhysMat);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("asset_path"), AssetPath);
    Result->SetStringField(TEXT("asset_name"), AssetName);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSpawnRadialForce(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName = TEXT("RadialForceActor");
    Params->TryGetStringField(TEXT("actor_name"), ActorName);

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FVector Location = FVector::ZeroVector;
    const TSharedPtr<FJsonObject>* LocObj = nullptr;
    if (Params->TryGetObjectField(TEXT("location"), LocObj) && LocObj)
    {
        double X = 0, Y = 0, Z = 0;
        (*LocObj)->TryGetNumberField(TEXT("x"), X);
        (*LocObj)->TryGetNumberField(TEXT("y"), Y);
        (*LocObj)->TryGetNumberField(TEXT("z"), Z);
        Location = FVector(X, Y, Z);
    }

    FScopedTransaction Transaction(FText::FromString(FString::Printf(TEXT("UnrealMCP: Spawn Radial Force %s"), *ActorName)));

    ARadialForceActor* ForceActor = World->SpawnActor<ARadialForceActor>(ARadialForceActor::StaticClass(), Location, FRotator::ZeroRotator);
    if (!ForceActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn RadialForceActor"));
    }

    ForceActor->SetActorLabel(*ActorName);
    ForceActor->Tags.AddUnique(FName(TEXT("managed_by_mcp")));

    double Radius = 500.0;
    if (Params->TryGetNumberField(TEXT("radius"), Radius))
    {
        if (ForceActor->GetForceComponent())
        {
            ForceActor->GetForceComponent()->Radius = static_cast<float>(Radius);
        }
    }

    double Strength = 1000.0;
    if (Params->TryGetNumberField(TEXT("strength"), Strength))
    {
        if (ForceActor->GetForceComponent())
        {
            ForceActor->GetForceComponent()->ForceStrength = static_cast<float>(Strength);
        }
    }

    FEpicUnrealMCPCommonUtils::GetActorIndex().AddActor(ForceActor);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ForceActor->GetName());
    Result->SetNumberField(TEXT("radius"), Radius);
    Result->SetNumberField(TEXT("strength"), Strength);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSpawnPhysicsConstraint(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName = TEXT("PhysicsConstraintActor");
    Params->TryGetStringField(TEXT("actor_name"), ActorName);

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FVector Location = FVector::ZeroVector;
    const TSharedPtr<FJsonObject>* LocObj = nullptr;
    if (Params->TryGetObjectField(TEXT("location"), LocObj) && LocObj)
    {
        double X = 0, Y = 0, Z = 0;
        (*LocObj)->TryGetNumberField(TEXT("x"), X);
        (*LocObj)->TryGetNumberField(TEXT("y"), Y);
        (*LocObj)->TryGetNumberField(TEXT("z"), Z);
        Location = FVector(X, Y, Z);
    }

    FScopedTransaction Transaction(FText::FromString(FString::Printf(TEXT("UnrealMCP: Spawn Physics Constraint %s"), *ActorName)));

    APhysicsConstraintActor* ConstraintActor = World->SpawnActor<APhysicsConstraintActor>(APhysicsConstraintActor::StaticClass(), Location, FRotator::ZeroRotator);
    if (!ConstraintActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn PhysicsConstraintActor"));
    }

    ConstraintActor->SetActorLabel(*ActorName);
    ConstraintActor->Tags.AddUnique(FName(TEXT("managed_by_mcp")));

    FEpicUnrealMCPCommonUtils::GetActorIndex().AddActor(ConstraintActor);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ConstraintActor->GetName());
    return Result;
}


