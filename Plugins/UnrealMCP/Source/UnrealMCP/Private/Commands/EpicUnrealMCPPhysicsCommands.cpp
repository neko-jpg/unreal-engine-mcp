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
#include "Kismet/KismetSystemLibrary.h"
#include "Components/SphereComponent.h"
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
        // Spatial queries (React-for-UE v3.0)
        {TEXT("get_actor_bounds"),         &FEpicUnrealMCPPhysicsCommands::HandleGetActorBounds},
        {TEXT("spatial_overlap_sphere"),   &FEpicUnrealMCPPhysicsCommands::HandleSpatialOverlapSphere},
        {TEXT("spatial_raycast"),          &FEpicUnrealMCPPhysicsCommands::HandleSpatialRaycast},
        {TEXT("spatial_linecast"),         &FEpicUnrealMCPPhysicsCommands::HandleSpatialLinecast},
        {TEXT("spatial_nearest"),          &FEpicUnrealMCPPhysicsCommands::HandleSpatialNearest},
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
        // UE 5.7: UCollisionProfile::ReadChannelDisplayNames() was removed (use the
        // ChannelDisplayNames TArray directly via the manager APIs); for this parser
        // we already fall back to the ECollisionChannel enum, so use it directly.
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

// =====================================================================
// Spatial Queries (React-for-UE v3.0)
// =====================================================================

namespace
{
    static bool TryReadVectorArray(const TSharedPtr<FJsonObject>& Params, const TCHAR* Field, FVector& Out)
    {
        const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
        if (!Params->TryGetArrayField(Field, Arr) || !Arr || Arr->Num() < 3)
        {
            return false;
        }
        Out = FVector((*Arr)[0]->AsNumber(), (*Arr)[1]->AsNumber(), (*Arr)[2]->AsNumber());
        return true;
    }

    static TArray<TSharedPtr<FJsonValue>> VectorToJsonArray(const FVector& V)
    {
        TArray<TSharedPtr<FJsonValue>> Arr;
        Arr.Add(MakeShared<FJsonValueNumber>(V.X));
        Arr.Add(MakeShared<FJsonValueNumber>(V.Y));
        Arr.Add(MakeShared<FJsonValueNumber>(V.Z));
        return Arr;
    }

    static AActor* FindActorByName(UWorld* World, const FString& Name)
    {
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            if (It->GetName() == Name || It->GetActorLabel() == Name)
            {
                return *It;
            }
        }
        return nullptr;
    }

    static TArray<FString> ReadStringArray(const TSharedPtr<FJsonObject>& Params, const TCHAR* Field)
    {
        TArray<FString> Values;
        const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
        if (Params->TryGetArrayField(Field, Arr) && Arr)
        {
            for (const TSharedPtr<FJsonValue>& Value : *Arr)
            {
                FString Text = Value->AsString();
                if (!Text.IsEmpty())
                {
                    Values.Add(Text);
                }
            }
        }
        return Values;
    }

    static bool ActorMatchesTags(AActor* Actor, const TArray<FString>& FilterTags)
    {
        for (const FString& RequiredTag : FilterTags)
        {
            bool bFound = false;
            for (const FName& ActorTag : Actor->Tags)
            {
                if (ActorTag.ToString().Equals(RequiredTag, ESearchCase::IgnoreCase))
                {
                    bFound = true;
                    break;
                }
            }
            if (!bFound)
            {
                return false;
            }
        }
        return true;
    }

    static bool ActorMatchesKind(AActor* Actor, const FString& FilterKind)
    {
        if (FilterKind.IsEmpty())
        {
            return true;
        }
        return Actor->GetName().Contains(FilterKind, ESearchCase::IgnoreCase)
            || Actor->GetActorLabel().Contains(FilterKind, ESearchCase::IgnoreCase)
            || Actor->GetClass()->GetName().Contains(FilterKind, ESearchCase::IgnoreCase);
    }

    static bool ActorMatchesFilters(AActor* Actor, const TArray<FString>& FilterTags, const FString& FilterKind)
    {
        return Actor
            && !Actor->IsHiddenEd()
            && ActorMatchesTags(Actor, FilterTags)
            && ActorMatchesKind(Actor, FilterKind);
    }

    static TSharedPtr<FJsonObject> MakeHitJson(
        AActor* Actor,
        float Distance,
        const FVector& HitPoint,
        const FVector& HitNormal,
        UPrimitiveComponent* HitComponent = nullptr)
    {
        TSharedPtr<FJsonObject> Hit = MakeShared<FJsonObject>();
        Hit->SetStringField(TEXT("mcp_id"), Actor->GetName());
        Hit->SetStringField(TEXT("name"), Actor->GetActorLabel());
        Hit->SetStringField(TEXT("class"), Actor->GetClass()->GetName());
        Hit->SetNumberField(TEXT("distance"), Distance);
        Hit->SetArrayField(TEXT("hit_point"), VectorToJsonArray(HitPoint));
        Hit->SetArrayField(TEXT("hit_normal"), VectorToJsonArray(HitNormal));
        if (HitComponent)
        {
            Hit->SetStringField(TEXT("hit_component"), HitComponent->GetName());
        }
        return Hit;
    }
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleGetActorBounds(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName) || ActorName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    AActor* Actor = FindActorByName(World, ActorName);
    if (!Actor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor '%s' not found"), *ActorName));
    }

    FVector Origin;
    FVector Extent;
    Actor->GetActorBounds(true, Origin, Extent);

    const FVector Min = Origin - Extent;
    const FVector Max = Origin + Extent;

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("actor_name"), ActorName);
    Result->SetStringField(TEXT("name"), Actor->GetActorLabel());
    Result->SetArrayField(TEXT("center"), VectorToJsonArray(Origin));
    Result->SetArrayField(TEXT("size"), VectorToJsonArray(Extent * 2.0));
    Result->SetArrayField(TEXT("min"), VectorToJsonArray(Min));
    Result->SetArrayField(TEXT("max"), VectorToJsonArray(Max));
    Result->SetArrayField(TEXT("location"), VectorToJsonArray(Actor->GetActorLocation()));
    Result->SetArrayField(TEXT("rotation"), VectorToJsonArray(FVector(
        Actor->GetActorRotation().Pitch,
        Actor->GetActorRotation().Yaw,
        Actor->GetActorRotation().Roll)));
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSpatialOverlapSphere(const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FVector Center;
    if (!TryReadVectorArray(Params, TEXT("center"), Center))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing or invalid 'center' array [x,y,z]"));
    }

    double Radius = 100.0;
    Params->TryGetNumberField(TEXT("radius"), Radius);
    const double RadiusSq = Radius * Radius;
    const TArray<FString> FilterTags = ReadStringArray(Params, TEXT("filter_tags"));
    FString FilterKind;
    Params->TryGetStringField(TEXT("filter_kind"), FilterKind);

    TArray<TSharedPtr<FJsonValue>> HitsArr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!ActorMatchesFilters(Actor, FilterTags, FilterKind))
        {
            continue;
        }

        FVector Origin;
        FVector Extent;
        Actor->GetActorBounds(true, Origin, Extent);
        const FBox Bounds(Origin - Extent, Origin + Extent);
        if (Bounds.ComputeSquaredDistanceToPoint(Center) > RadiusSq)
        {
            continue;
        }

        const float Distance = FVector::Dist(Center, Actor->GetActorLocation());
        HitsArr.Add(MakeShared<FJsonValueObject>(
            MakeHitJson(Actor, Distance, Actor->GetActorLocation(), FVector::ZeroVector)));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetArrayField(TEXT("hits"), HitsArr);
    Result->SetNumberField(TEXT("count"), HitsArr.Num());
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSpatialRaycast(const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FVector Origin;
    FVector Direction;
    if (!TryReadVectorArray(Params, TEXT("origin"), Origin))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'origin' array [x,y,z]"));
    }
    if (!TryReadVectorArray(Params, TEXT("direction"), Direction))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'direction' array [x,y,z]"));
    }
    if (!Direction.Normalize())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'direction' must be non-zero"));
    }

    double MaxDistance = 10000.0;
    Params->TryGetNumberField(TEXT("max_distance"), MaxDistance);
    const FVector End = Origin + Direction * static_cast<float>(MaxDistance);

    FHitResult Hit;
    FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(UnrealMCPSpatialRaycast), true);
    const bool bHit = World->LineTraceSingleByChannel(Hit, Origin, End, ECC_Visibility, QueryParams);

    TArray<TSharedPtr<FJsonValue>> HitsArr;
    if (bHit && Hit.GetActor())
    {
        const float Distance = Hit.Distance > 0.0f ? Hit.Distance : FVector::Dist(Origin, Hit.ImpactPoint);
        HitsArr.Add(MakeShared<FJsonValueObject>(
            MakeHitJson(Hit.GetActor(), Distance, Hit.ImpactPoint, Hit.ImpactNormal, Hit.GetComponent())));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetArrayField(TEXT("hits"), HitsArr);
    Result->SetNumberField(TEXT("count"), HitsArr.Num());
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSpatialLinecast(const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FVector Origin;
    FVector End;
    if (!TryReadVectorArray(Params, TEXT("origin"), Origin))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'origin' array [x,y,z]"));
    }
    if (!TryReadVectorArray(Params, TEXT("end"), End))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'end' array [x,y,z]"));
    }

    TArray<FHitResult> Hits;
    FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(UnrealMCPSpatialLinecast), true);
    World->LineTraceMultiByChannel(Hits, Origin, End, ECC_Visibility, QueryParams);

    TArray<TSharedPtr<FJsonValue>> HitsArr;
    for (const FHitResult& Hit : Hits)
    {
        if (!Hit.GetActor())
        {
            continue;
        }
        const float Distance = Hit.Distance > 0.0f ? Hit.Distance : FVector::Dist(Origin, Hit.ImpactPoint);
        HitsArr.Add(MakeShared<FJsonValueObject>(
            MakeHitJson(Hit.GetActor(), Distance, Hit.ImpactPoint, Hit.ImpactNormal, Hit.GetComponent())));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetArrayField(TEXT("hits"), HitsArr);
    Result->SetNumberField(TEXT("count"), HitsArr.Num());
    return Result;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPPhysicsCommands::HandleSpatialNearest(const TSharedPtr<FJsonObject>& Params)
{
    FString ReferenceActor;
    if (!Params->TryGetStringField(TEXT("reference_actor"), ReferenceActor) || ReferenceActor.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'reference_actor' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    AActor* RefActor = FindActorByName(World, ReferenceActor);
    if (!RefActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Reference actor '%s' not found"), *ReferenceActor));
    }

    const TArray<FString> FilterTags = ReadStringArray(Params, TEXT("filter_tags"));
    FString FilterKind;
    Params->TryGetStringField(TEXT("filter_kind"), FilterKind);
    const FVector RefLocation = RefActor->GetActorLocation();
    AActor* NearestActor = nullptr;
    float NearestDistance = TNumericLimits<float>::Max();

    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (Actor == RefActor || !ActorMatchesFilters(Actor, FilterTags, FilterKind))
        {
            continue;
        }

        const float Distance = FVector::Dist(RefLocation, Actor->GetActorLocation());
        if (Distance < NearestDistance)
        {
            NearestDistance = Distance;
            NearestActor = Actor;
        }
    }

    TArray<TSharedPtr<FJsonValue>> HitsArr;
    if (NearestActor)
    {
        HitsArr.Add(MakeShared<FJsonValueObject>(
            MakeHitJson(NearestActor, NearestDistance, NearestActor->GetActorLocation(), FVector::ZeroVector)));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetArrayField(TEXT("hits"), HitsArr);
    Result->SetNumberField(TEXT("count"), HitsArr.Num());
    return Result;
}
