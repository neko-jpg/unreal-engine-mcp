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
#include "GameFramework/PhysicsVolume.h"
#include "Components/BrushComponent.h"
#include "Engine/CollisionProfile.h"

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
        {TEXT("set_actor_collision_response"), &FEpicUnrealMCPPhysicsCommands::HandleSetActorCollisionResponse},  // W1-B
        {TEXT("set_constraint_limits"), &FEpicUnrealMCPPhysicsCommands::HandleSetConstraintLimits},  // W1-B
        {TEXT("set_constraint_motor"), &FEpicUnrealMCPPhysicsCommands::HandleSetConstraintMotor},  // W1-B
        {TEXT("spawn_physics_volume"), &FEpicUnrealMCPPhysicsCommands::HandleSpawnPhysicsVolume},  // W1-B
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

// W1-B_PHYSICS_BEGIN
// W1-B Physics residue (UE 5.7, non-Chaos)

namespace
{
    static ECollisionResponse ParseCollisionResponse(const FString& Name)
    {
        if (Name.Equals(TEXT("Ignore"), ESearchCase::IgnoreCase)) return ECR_Ignore;
        if (Name.Equals(TEXT("Overlap"), ESearchCase::IgnoreCase)) return ECR_Overlap;
        return ECR_Block;
    }

    static ECollisionChannel ParseCollisionChannel(const FString& Name)
    {
        // Use the official collision channel mapping from CollisionProfile.
        FCollisionResponseTemplate Tmp;
        if (UCollisionProfile::Get()->ReadChannelDisplayNames())
        {
            // Fallback to enum string lookup.
        }
        const UEnum* EnumDef = StaticEnum<ECollisionChannel>();
        if (EnumDef)
        {
            int32 Idx = EnumDef->GetIndexByNameString(FString::Printf(TEXT("ECC_%s"), *Name));
            if (Idx != INDEX_NONE)
            {
                return static_cast<ECollisionChannel>(EnumDef->GetValueByIndex(Idx));
            }
        }
        // Try common aliases
        if (Name.Equals(TEXT("WorldStatic"), ESearchCase::IgnoreCase)) return ECC_WorldStatic;
        if (Name.Equals(TEXT("WorldDynamic"), ESearchCase::IgnoreCase)) return ECC_WorldDynamic;
        if (Name.Equals(TEXT("Pawn"), ESearchCase::IgnoreCase)) return ECC_Pawn;
        if (Name.Equals(TEXT("Visibility"), ESearchCase::IgnoreCase)) return ECC_Visibility;
        if (Name.Equals(TEXT("Camera"), ESearchCase::IgnoreCase)) return ECC_Camera;
        if (Name.Equals(TEXT("PhysicsBody"), ESearchCase::IgnoreCase)) return ECC_PhysicsBody;
        if (Name.Equals(TEXT("Vehicle"), ESearchCase::IgnoreCase)) return ECC_Vehicle;
        if (Name.Equals(TEXT("Destructible"), ESearchCase::IgnoreCase)) return ECC_Destructible;
        return ECC_MAX;
    }

    static EAngularConstraintMotion ParseAngularMotion(const FString& Name)
    {
        if (Name.Equals(TEXT("Free"), ESearchCase::IgnoreCase)) return ACM_Free;
        if (Name.Equals(TEXT("Locked"), ESearchCase::IgnoreCase)) return ACM_Locked;
        return ACM_Limited;
    }

    static ELinearConstraintMotion ParseLinearMotion(const FString& Name)
    {
        if (Name.Equals(TEXT("Free"), ESearchCase::IgnoreCase)) return LCM_Free;
        if (Name.Equals(TEXT("Locked"), ESearchCase::IgnoreCase)) return LCM_Locked;
        return LCM_Limited;
    }
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSetActorCollisionResponse(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));
    FString ChannelName;
    if (!Params->TryGetStringField(TEXT("channel"), ChannelName) || ChannelName.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'channel' parameter (e.g. WorldStatic, Pawn)"));
    FString ResponseStr;
    if (!Params->TryGetStringField(TEXT("response"), ResponseStr) || ResponseStr.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'response' parameter (Block / Overlap / Ignore)"));

    UWorld* World = GetEditorWorld();
    if (!World)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));

    AActor* TargetActor = nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName || It->GetActorLabel() == ActorName)
        {
            TargetActor = *It;
            break;
        }
    }
    if (!TargetActor)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));

    UPrimitiveComponent* Prim = Cast<UPrimitiveComponent>(TargetActor->GetRootComponent());
    if (!Prim)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Actor root has no UPrimitiveComponent"));

    ECollisionChannel Channel = ParseCollisionChannel(ChannelName);
    if (Channel == ECC_MAX)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown collision channel: %s"), *ChannelName));

    ECollisionResponse Response = ParseCollisionResponse(ResponseStr);

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Set Collision Response")));
    Prim->Modify();
    Prim->SetCollisionResponseToChannel(Channel, Response);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    Result->SetStringField(TEXT("channel"), ChannelName);
    Result->SetStringField(TEXT("response"), ResponseStr);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSetConstraintLimits(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));

    UWorld* World = GetEditorWorld();
    if (!World)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));

    APhysicsConstraintActor* ConstraintActor = nullptr;
    for (TActorIterator<APhysicsConstraintActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName || It->GetActorLabel() == ActorName)
        {
            ConstraintActor = *It;
            break;
        }
    }
    if (!ConstraintActor || !ConstraintActor->GetConstraintComp())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("PhysicsConstraintActor not found: %s"), *ActorName));

    UPhysicsConstraintComponent* Comp = ConstraintActor->GetConstraintComp();
    FConstraintInstance& Inst = Comp->ConstraintInstance;

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Set Constraint Limits")));
    Comp->Modify();

    // Linear limits
    FString LinearXMotion, LinearYMotion, LinearZMotion;
    if (Params->TryGetStringField(TEXT("linear_x_motion"), LinearXMotion))
        Inst.SetLinearXMotion(ParseLinearMotion(LinearXMotion));
    if (Params->TryGetStringField(TEXT("linear_y_motion"), LinearYMotion))
        Inst.SetLinearYMotion(ParseLinearMotion(LinearYMotion));
    if (Params->TryGetStringField(TEXT("linear_z_motion"), LinearZMotion))
        Inst.SetLinearZMotion(ParseLinearMotion(LinearZMotion));

    double LinearLimit = -1.0;
    if (Params->TryGetNumberField(TEXT("linear_limit_size"), LinearLimit) && LinearLimit >= 0.0)
        Inst.SetLinearLimitSize(static_cast<float>(LinearLimit));

    // Angular limits
    FString Swing1, Swing2, Twist;
    if (Params->TryGetStringField(TEXT("angular_swing1_motion"), Swing1))
        Inst.SetAngularSwing1Motion(ParseAngularMotion(Swing1));
    if (Params->TryGetStringField(TEXT("angular_swing2_motion"), Swing2))
        Inst.SetAngularSwing2Motion(ParseAngularMotion(Swing2));
    if (Params->TryGetStringField(TEXT("angular_twist_motion"), Twist))
        Inst.SetAngularTwistMotion(ParseAngularMotion(Twist));

    double Swing1Limit = -1.0, Swing2Limit = -1.0, TwistLimit = -1.0;
    if (Params->TryGetNumberField(TEXT("angular_swing1_limit_degrees"), Swing1Limit) && Swing1Limit >= 0.0)
        Inst.SetAngularSwing1Limit(ACM_Limited, static_cast<float>(Swing1Limit));
    if (Params->TryGetNumberField(TEXT("angular_swing2_limit_degrees"), Swing2Limit) && Swing2Limit >= 0.0)
        Inst.SetAngularSwing2Limit(ACM_Limited, static_cast<float>(Swing2Limit));
    if (Params->TryGetNumberField(TEXT("angular_twist_limit_degrees"), TwistLimit) && TwistLimit >= 0.0)
        Inst.SetAngularTwistLimit(ACM_Limited, static_cast<float>(TwistLimit));

    ConstraintActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSetConstraintMotor(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));

    UWorld* World = GetEditorWorld();
    if (!World)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));

    APhysicsConstraintActor* ConstraintActor = nullptr;
    for (TActorIterator<APhysicsConstraintActor> It(World); It; ++It)
    {
        if (It->GetName() == ActorName || It->GetActorLabel() == ActorName)
        {
            ConstraintActor = *It;
            break;
        }
    }
    if (!ConstraintActor || !ConstraintActor->GetConstraintComp())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("PhysicsConstraintActor not found: %s"), *ActorName));

    UPhysicsConstraintComponent* Comp = ConstraintActor->GetConstraintComp();
    FConstraintInstance& Inst = Comp->ConstraintInstance;

    FScopedTransaction Transaction(FText::FromString(TEXT("UnrealMCP: Set Constraint Motor")));
    Comp->Modify();

    bool bEnableLinearVel = false, bEnableLinearPos = false;
    if (Params->TryGetBoolField(TEXT("linear_velocity_drive"), bEnableLinearVel))
    {
        // Drive all 3 axes together for simplicity.
        Inst.SetLinearVelocityDrive(bEnableLinearVel, bEnableLinearVel, bEnableLinearVel);
    }
    if (Params->TryGetBoolField(TEXT("linear_position_drive"), bEnableLinearPos))
    {
        Inst.SetLinearPositionDrive(bEnableLinearPos, bEnableLinearPos, bEnableLinearPos);
    }

    const TArray<TSharedPtr<FJsonValue>>* TargetVelArr = nullptr;
    if (Params->TryGetArrayField(TEXT("linear_velocity_target"), TargetVelArr) && TargetVelArr && TargetVelArr->Num() >= 3)
    {
        FVector TargetVel(
            (*TargetVelArr)[0]->AsNumber(),
            (*TargetVelArr)[1]->AsNumber(),
            (*TargetVelArr)[2]->AsNumber());
        Inst.SetLinearVelocityTarget(TargetVel);
    }

    bool bEnableAngularSLERP = false, bEnableAngularVel = false;
    if (Params->TryGetBoolField(TEXT("angular_orientation_drive"), bEnableAngularSLERP))
    {
        Inst.SetOrientationDriveSLERP(bEnableAngularSLERP);
    }
    if (Params->TryGetBoolField(TEXT("angular_velocity_drive"), bEnableAngularVel))
    {
        Inst.SetAngularVelocityDriveSLERP(bEnableAngularVel);
    }

    ConstraintActor->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSpawnPhysicsVolume(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName) || ActorName.IsEmpty())
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    UWorld* World = GetEditorWorld();
    if (!World)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));

    FVector Location(0, 0, 0);
    const TArray<TSharedPtr<FJsonValue>>* LocArr = nullptr;
    if (Params->TryGetArrayField(TEXT("location"), LocArr) && LocArr && LocArr->Num() >= 3)
    {
        Location.X = (*LocArr)[0]->AsNumber();
        Location.Y = (*LocArr)[1]->AsNumber();
        Location.Z = (*LocArr)[2]->AsNumber();
    }

    FActorSpawnParameters Spawn;
    Spawn.Name = FName(*ActorName);
    Spawn.NameMode = FActorSpawnParameters::ESpawnActorNameMode::Requested;
    APhysicsVolume* Volume = World->SpawnActor<APhysicsVolume>(APhysicsVolume::StaticClass(), Location, FRotator::ZeroRotator, Spawn);
    if (!Volume)
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn APhysicsVolume"));
    Volume->SetActorLabel(ActorName);

    double TerminalVelocity = -1.0;
    if (Params->TryGetNumberField(TEXT("terminal_velocity"), TerminalVelocity) && TerminalVelocity >= 0.0)
        Volume->TerminalVelocity = static_cast<float>(TerminalVelocity);
    double Priority = -999999.0;
    if (Params->TryGetNumberField(TEXT("priority"), Priority))
        Volume->Priority = static_cast<float>(Priority);
    bool bWaterVolume = false;
    if (Params->TryGetBoolField(TEXT("water_volume"), bWaterVolume))
        Volume->bWaterVolume = bWaterVolume;
    double FluidFriction = -1.0;
    if (Params->TryGetNumberField(TEXT("fluid_friction"), FluidFriction) && FluidFriction >= 0.0)
        Volume->FluidFriction = static_cast<float>(FluidFriction);

    // Optional brush scale (volume size as multiplier of default 200x200x200)
    const TArray<TSharedPtr<FJsonValue>>* ScaleArr = nullptr;
    if (Params->TryGetArrayField(TEXT("scale"), ScaleArr) && ScaleArr && ScaleArr->Num() >= 3)
    {
        FVector Scale(
            (*ScaleArr)[0]->AsNumber(),
            (*ScaleArr)[1]->AsNumber(),
            (*ScaleArr)[2]->AsNumber());
        Volume->SetActorRelativeScale3D(Scale);
    }

    Volume->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    Result->SetNumberField(TEXT("terminal_velocity"), Volume->TerminalVelocity);
    Result->SetNumberField(TEXT("priority"), Volume->Priority);
    Result->SetBoolField(TEXT("water_volume"), Volume->bWaterVolume);
    Result->SetNumberField(TEXT("fluid_friction"), Volume->FluidFriction);
    return Result;
}
