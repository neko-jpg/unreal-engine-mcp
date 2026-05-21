// =====================================================================
// EpicUnrealMCPInstanceCommands
//
// Phase 4 (Issue #31) split from EpicUnrealMCPProceduralCommands.cpp.
// Owns the Draft Proxy visualisation handlers and the HISM/ISM
// InstanceSet CRUD handlers, plus their file-local static helpers.
//
// Routed under id 24.
// =====================================================================

#include "Commands/EpicUnrealMCPInstanceCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Editor.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"
#include "Engine/World.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "EditorAssetLibrary.h"
#include "ScopedTransaction.h"
#include "Engine/StaticMesh.h"
#include "RenderingThread.h"

// =====================================================================
// File-local static helpers (moved verbatim from
// EpicUnrealMCPProceduralCommands.cpp during the Phase 4 split).
// =====================================================================

static AActor* FindDraftProxyActor(UWorld* World, const FString& ProxyName)
{
    if (!World) return nullptr;
    FString McpIdTag = FString::Printf(TEXT("mcp_id:draft_%s"), *ProxyName);
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->Tags.Contains(FName(*McpIdTag)))
        {
            return *It;
        }
    }
    return nullptr;
}

static UMaterialInterface* LoadDraftMaterial(UObject* Outer, bool bUseDither)
{
    if (!Outer) return nullptr;

    // Try project-specific preset material first
    UMaterialInterface* Mat = Cast<UMaterialInterface>(
        UEditorAssetLibrary::LoadAsset(TEXT("/Game/Materials/M_DraftProxy"))
    );
    if (Mat) return Mat;

    // Fallback: try dither variant
    if (bUseDither)
    {
        Mat = Cast<UMaterialInterface>(
            UEditorAssetLibrary::LoadAsset(TEXT("/Game/Materials/M_DraftProxy_Dither"))
        );
        if (Mat) return Mat;
    }

    // Final fallback: use the engine default translucent material
    Mat = Cast<UMaterialInterface>(
        UEditorAssetLibrary::LoadAsset(TEXT("/Engine/BasicShapes/BasicShapeMaterial"))
    );
    return Mat;
}

static UHierarchicalInstancedStaticMeshComponent* GetOrCreateHismComponent(AActor* Actor)
{
    if (!Actor) return nullptr;
    UHierarchicalInstancedStaticMeshComponent* HISM = Actor->FindComponentByClass<UHierarchicalInstancedStaticMeshComponent>();
    if (!HISM)
    {
        HISM = NewObject<UHierarchicalInstancedStaticMeshComponent>(Actor, UHierarchicalInstancedStaticMeshComponent::StaticClass(), TEXT("DraftHISM"));
        HISM->RegisterComponent();
        if (Actor->GetRootComponent())
        {
            HISM->AttachToComponent(Actor->GetRootComponent(), FAttachmentTransformRules::KeepRelativeTransform);
        }
        else
        {
            Actor->SetRootComponent(HISM);
        }
    }
    return HISM;
}

static bool ParseInstanceEntry(const TSharedPtr<FJsonObject>& Obj, FVector& OutLocation, FVector& OutScale, FRotator& OutRotation)
{
    if (!Obj.IsValid()) return false;
    const TSharedPtr<FJsonObject>* LocPtr = nullptr;
    if (Obj->TryGetObjectField(TEXT("location"), LocPtr) && LocPtr)
    {
        double X = 0, Y = 0, Z = 0;
        (*LocPtr)->TryGetNumberField(TEXT("x"), X);
        (*LocPtr)->TryGetNumberField(TEXT("y"), Y);
        (*LocPtr)->TryGetNumberField(TEXT("z"), Z);
        OutLocation = FVector(X, Y, Z);
    }
    const TSharedPtr<FJsonObject>* ScalePtr = nullptr;
    if (Obj->TryGetObjectField(TEXT("scale"), ScalePtr) && ScalePtr)
    {
        double X = 1, Y = 1, Z = 1;
        (*ScalePtr)->TryGetNumberField(TEXT("x"), X);
        (*ScalePtr)->TryGetNumberField(TEXT("y"), Y);
        (*ScalePtr)->TryGetNumberField(TEXT("z"), Z);
        OutScale = FVector(X, Y, Z);
    }
    const TSharedPtr<FJsonObject>* RotPtr = nullptr;
    if (Obj->TryGetObjectField(TEXT("rotation"), RotPtr) && RotPtr)
    {
        double Pitch = 0, Yaw = 0, Roll = 0;
        (*RotPtr)->TryGetNumberField(TEXT("pitch"), Pitch);
        (*RotPtr)->TryGetNumberField(TEXT("yaw"), Yaw);
        (*RotPtr)->TryGetNumberField(TEXT("roll"), Roll);
        OutRotation = FRotator(Pitch, Yaw, Roll);
    }
    return true;
}

// =====================================================================
// Class members
// =====================================================================

FEpicUnrealMCPInstanceCommands::FEpicUnrealMCPInstanceCommands()
{
}

UWorld* FEpicUnrealMCPInstanceCommands::GetEditorWorld() const
{
    if (!GEditor)
    {
        return nullptr;
    }
    return GEditor->GetEditorWorldContext().World();
}

TSharedPtr<FJsonObject> FEpicUnrealMCPInstanceCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPInstanceCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        // Draft proxy (HISM visualization)
        {TEXT("create_draft_proxy"),     &FEpicUnrealMCPInstanceCommands::HandleCreateDraftProxy},
        {TEXT("update_draft_proxy"),     &FEpicUnrealMCPInstanceCommands::HandleUpdateDraftProxy},
        {TEXT("delete_draft_proxy"),     &FEpicUnrealMCPInstanceCommands::HandleDeleteDraftProxy},

        // InstanceSet commands (HISM/ISM bulk instancing)
        {TEXT("spawn_instance_set"),     &FEpicUnrealMCPInstanceCommands::HandleSpawnInstanceSet},
        {TEXT("update_instance_set"),    &FEpicUnrealMCPInstanceCommands::HandleUpdateInstanceSet},
        {TEXT("delete_instance_set"),    &FEpicUnrealMCPInstanceCommands::HandleDeleteInstanceSet},
        {TEXT("get_instance_set_state"), &FEpicUnrealMCPInstanceCommands::HandleGetInstanceSetState},
        {TEXT("list_instance_sets"),     &FEpicUnrealMCPInstanceCommands::HandleListInstanceSets},
    };

    const Handler* H = Dispatch.Find(CommandType);
    if (H)
    {
        return (this->*(*H))(Params);
    }

    return FEpicUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown instance command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FEpicUnrealMCPInstanceCommands::HandleCreateDraftProxy(const TSharedPtr<FJsonObject>& Params)
{
    FString ProxyName;
    if (!Params->TryGetStringField(TEXT("proxy_name"), ProxyName) || ProxyName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'proxy_name' parameter"));
    }

    FString MeshPath = TEXT("/Engine/BasicShapes/Cube.Cube");
    Params->TryGetStringField(TEXT("mesh_path"), MeshPath);

    FString MaterialPath;
    Params->TryGetStringField(TEXT("material_path"), MaterialPath);

    bool bUseDither = false;
    Params->TryGetBoolField(TEXT("use_dither"), bUseDither);

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // Prevent duplicate proxy names
    if (FindDraftProxyActor(World, ProxyName))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Draft proxy '%s' already exists. Use update_draft_proxy instead."), *ProxyName));
    }

    FScopedTransaction Transaction(FText::FromString(FString::Printf(TEXT("UnrealMCP: Create Draft Proxy %s"), *ProxyName)));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = *FString::Printf(TEXT("DraftProxy_%s"), *ProxyName);
    AActor* ProxyActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!ProxyActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn draft proxy actor"));
    }

    ProxyActor->SetActorLabel(*ProxyName);
    ProxyActor->Tags.AddUnique(FName(TEXT("managed_by_mcp")));
    ProxyActor->Tags.AddUnique(FName(*FString::Printf(TEXT("mcp_id:draft_%s"), *ProxyName)));

    UHierarchicalInstancedStaticMeshComponent* HISM = GetOrCreateHismComponent(ProxyActor);
    if (!HISM)
    {
        ProxyActor->Destroy();
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create HISM component"));
    }

    // Load static mesh
    UStaticMesh* Mesh = Cast<UStaticMesh>(UEditorAssetLibrary::LoadAsset(MeshPath));
    if (!Mesh)
    {
        ProxyActor->Destroy();
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Failed to load static mesh: %s"), *MeshPath));
    }
    FlushRenderingCommands();
    HISM->SetStaticMesh(Mesh);

    // Load material if provided, otherwise create a default Unlit translucent draft material
    UMaterialInterface* Material = nullptr;
    if (!MaterialPath.IsEmpty())
    {
        Material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(MaterialPath));
        if (!Material)
        {
            UE_LOG(LogTemp, Warning, TEXT("Could not load material at path: %s, falling back to default draft material"), *MaterialPath);
        }
    }
    if (!Material)
    {
        Material = LoadDraftMaterial(ProxyActor, bUseDither);
    }
    if (Material)
    {
        HISM->SetMaterial(0, Material);
    }

    // Disable collision and shadows for draft visualization
    HISM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    HISM->SetCastShadow(false);

    // Parse and add instances
    const TArray<TSharedPtr<FJsonValue>>* InstancesArray = nullptr;
    int32 InstanceCount = 0;
    if (Params->TryGetArrayField(TEXT("instances"), InstancesArray) && InstancesArray)
    {
        for (const TSharedPtr<FJsonValue>& Value : *InstancesArray)
        {
            if (!Value.IsValid() || Value->Type != EJson::Object) continue;
            FVector Location = FVector::ZeroVector;
            FVector Scale = FVector::OneVector;
            FRotator Rotation = FRotator::ZeroRotator;
            if (ParseInstanceEntry(Value->AsObject(), Location, Scale, Rotation))
            {
                FTransform InstanceTransform(Rotation, Location, Scale);
                HISM->AddInstance(InstanceTransform);
                InstanceCount++;
            }
        }
    }

    HISM->MarkRenderStateDirty();

    FEpicUnrealMCPCommonUtils::GetActorIndex().AddActor(ProxyActor);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("proxy_name"), ProxyName);
    ResultObj->SetStringField(TEXT("actor_name"), ProxyActor->GetName());
    ResultObj->SetNumberField(TEXT("instance_count"), InstanceCount);
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPInstanceCommands::HandleUpdateDraftProxy(const TSharedPtr<FJsonObject>& Params)
{
    FString ProxyName;
    if (!Params->TryGetStringField(TEXT("proxy_name"), ProxyName) || ProxyName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'proxy_name' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    AActor* ProxyActor = FindDraftProxyActor(World, ProxyName);
    if (!ProxyActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Draft proxy '%s' not found"), *ProxyName));
    }

    UHierarchicalInstancedStaticMeshComponent* HISM = GetOrCreateHismComponent(ProxyActor);
    if (!HISM)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get HISM component"));
    }

    // Clear existing instances and re-add
    FlushRenderingCommands();
    HISM->ClearInstances();

    FString MaterialPath;
    Params->TryGetStringField(TEXT("material_path"), MaterialPath);
    bool bUseDither = false;
    Params->TryGetBoolField(TEXT("use_dither"), bUseDither);

    UMaterialInterface* Material = nullptr;
    if (!MaterialPath.IsEmpty())
    {
        Material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(MaterialPath));
    }
    if (!Material)
    {
        Material = LoadDraftMaterial(ProxyActor, bUseDither);
    }
    if (Material)
    {
        HISM->SetMaterial(0, Material);
    }

    const TArray<TSharedPtr<FJsonValue>>* InstancesArray = nullptr;
    int32 InstanceCount = 0;
    if (Params->TryGetArrayField(TEXT("instances"), InstancesArray) && InstancesArray)
    {
        for (const TSharedPtr<FJsonValue>& Value : *InstancesArray)
        {
            if (!Value.IsValid() || Value->Type != EJson::Object) continue;
            FVector Location = FVector::ZeroVector;
            FVector Scale = FVector::OneVector;
            FRotator Rotation = FRotator::ZeroRotator;
            if (ParseInstanceEntry(Value->AsObject(), Location, Scale, Rotation))
            {
                FTransform InstanceTransform(Rotation, Location, Scale);
                HISM->AddInstance(InstanceTransform);
                InstanceCount++;
            }
        }
    }

    HISM->MarkRenderStateDirty();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("proxy_name"), ProxyName);
    ResultObj->SetNumberField(TEXT("instance_count"), InstanceCount);
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPInstanceCommands::HandleDeleteDraftProxy(const TSharedPtr<FJsonObject>& Params)
{
    FString ProxyName;
    if (!Params->TryGetStringField(TEXT("proxy_name"), ProxyName) || ProxyName.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'proxy_name' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    AActor* ProxyActor = FindDraftProxyActor(World, ProxyName);
    if (!ProxyActor)
    {
        TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
        ResultObj->SetBoolField(TEXT("success"), true);
        ResultObj->SetBoolField(TEXT("deleted"), false);
        ResultObj->SetStringField(TEXT("message"), FString::Printf(TEXT("Draft proxy '%s' not found (already deleted)"), *ProxyName));
        return ResultObj;
    }

    FEpicUnrealMCPCommonUtils::GetActorIndex().RemoveActor(ProxyActor);

    FScopedTransaction Transaction(FText::FromString(FString::Printf(TEXT("UnrealMCP: Delete Draft Proxy %s"), *ProxyName)));
    ProxyActor->Modify();
    ProxyActor->Destroy();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetBoolField(TEXT("deleted"), true);
    ResultObj->SetStringField(TEXT("proxy_name"), ProxyName);
    return ResultObj;
}

// ------------------------------------------------------------------
// InstanceSet commands (HISM/ISM bulk instancing)
// ------------------------------------------------------------------

static AActor* FindInstanceSetActor(UWorld* World, const FString& SetId)
{
    if (!World) return nullptr;
    FString McpIdTag = FString::Printf(TEXT("mcp_id:instance_set_%s"), *SetId);
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->Tags.Contains(FName(*McpIdTag)))
        {
            return *It;
        }
    }
    return nullptr;
}

static UInstancedStaticMeshComponent* GetOrCreateIsmComponent(AActor* Actor, bool bUseHism)
{
    if (!Actor) return nullptr;
    if (bUseHism)
    {
        UHierarchicalInstancedStaticMeshComponent* HISM = Actor->FindComponentByClass<UHierarchicalInstancedStaticMeshComponent>();
        if (!HISM)
        {
            HISM = NewObject<UHierarchicalInstancedStaticMeshComponent>(Actor, UHierarchicalInstancedStaticMeshComponent::StaticClass(), TEXT("InstanceSetHISM"));
            HISM->RegisterComponent();
            if (Actor->GetRootComponent())
            {
                HISM->AttachToComponent(Actor->GetRootComponent(), FAttachmentTransformRules::KeepRelativeTransform);
            }
            else
            {
                Actor->SetRootComponent(HISM);
            }
        }
        return HISM;
    }
    else
    {
        UInstancedStaticMeshComponent* ISM = Actor->FindComponentByClass<UInstancedStaticMeshComponent>();
        if (!ISM)
        {
            ISM = NewObject<UInstancedStaticMeshComponent>(Actor, UInstancedStaticMeshComponent::StaticClass(), TEXT("InstanceSetISM"));
            ISM->RegisterComponent();
            if (Actor->GetRootComponent())
            {
                ISM->AttachToComponent(Actor->GetRootComponent(), FAttachmentTransformRules::KeepRelativeTransform);
            }
            else
            {
                Actor->SetRootComponent(ISM);
            }
        }
        return ISM;
    }
}

static bool ParseTransformArrayEntry(const TSharedPtr<FJsonObject>& Obj, FVector& OutLocation, FVector& OutScale, FRotator& OutRotation)
{
    if (!Obj.IsValid()) return false;

    auto GetArrayDouble = [](const TArray<TSharedPtr<FJsonValue>>& Arr, int32 Index, double Default) -> double {
        if (!Arr.IsValidIndex(Index)) return Default;
        return Arr[Index]->AsNumber();
    };

    const TArray<TSharedPtr<FJsonValue>>* LocArray = nullptr;
    if (Obj->TryGetArrayField(TEXT("location"), LocArray) && LocArray && LocArray->Num() >= 3)
    {
        OutLocation = FVector(
            GetArrayDouble(*LocArray, 0, 0.0),
            GetArrayDouble(*LocArray, 1, 0.0),
            GetArrayDouble(*LocArray, 2, 0.0)
        );
    }
    else
    {
        OutLocation = FVector::ZeroVector;
    }

    const TArray<TSharedPtr<FJsonValue>>* ScaleArray = nullptr;
    if (Obj->TryGetArrayField(TEXT("scale"), ScaleArray) && ScaleArray && ScaleArray->Num() >= 3)
    {
        OutScale = FVector(
            GetArrayDouble(*ScaleArray, 0, 1.0),
            GetArrayDouble(*ScaleArray, 1, 1.0),
            GetArrayDouble(*ScaleArray, 2, 1.0)
        );
    }
    else
    {
        OutScale = FVector::OneVector;
    }

    const TArray<TSharedPtr<FJsonValue>>* RotArray = nullptr;
    if (Obj->TryGetArrayField(TEXT("rotation"), RotArray) && RotArray && RotArray->Num() >= 3)
    {
        OutRotation = FRotator(
            GetArrayDouble(*RotArray, 0, 0.0),
            GetArrayDouble(*RotArray, 1, 0.0),
            GetArrayDouble(*RotArray, 2, 0.0)
        );
    }
    else
    {
        OutRotation = FRotator::ZeroRotator;
    }

    return true;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPInstanceCommands::HandleSpawnInstanceSet(const TSharedPtr<FJsonObject>& Params)
{
    FString SetId;
    if (!Params->TryGetStringField(TEXT("set_id"), SetId) || SetId.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'set_id' parameter"));
    }

    FString MeshPath;
    if (!Params->TryGetStringField(TEXT("mesh_path"), MeshPath) || MeshPath.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'mesh_path' parameter"));
    }

    FString MaterialPath;
    Params->TryGetStringField(TEXT("material_path"), MaterialPath);

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    if (FindInstanceSetActor(World, SetId))
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Instance set '%s' already exists. Use update_instance_set instead."), *SetId));
    }

    const TArray<TSharedPtr<FJsonValue>>* TransformsArray = nullptr;
    int32 InstanceCount = 0;
    if (Params->TryGetArrayField(TEXT("transforms"), TransformsArray) && TransformsArray)
    {
        InstanceCount = TransformsArray->Num();
    }

    bool bUseHism = InstanceCount > 100;

    FScopedTransaction Transaction(FText::FromString(FString::Printf(TEXT("UnrealMCP: Spawn Instance Set %s"), *SetId)));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = *FString::Printf(TEXT("InstanceSet_%s"), *SetId);
    AActor* SetActor = World->SpawnActor<AActor>(AActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, SpawnParams);
    if (!SetActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn instance set actor"));
    }

    SetActor->SetActorLabel(*SetId);
    SetActor->Tags.AddUnique(FName(TEXT("managed_by_mcp")));
    SetActor->Tags.AddUnique(FName(*FString::Printf(TEXT("mcp_id:instance_set_%s"), *SetId)));

    UInstancedStaticMeshComponent* ISM = GetOrCreateIsmComponent(SetActor, bUseHism);
    if (!ISM)
    {
        SetActor->Destroy();
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create ISM/HISM component"));
    }

    UStaticMesh* Mesh = Cast<UStaticMesh>(UEditorAssetLibrary::LoadAsset(MeshPath));
    if (!Mesh)
    {
        SetActor->Destroy();
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Failed to load static mesh: %s"), *MeshPath));
    }
    FlushRenderingCommands();
    ISM->SetStaticMesh(Mesh);

    if (!MaterialPath.IsEmpty())
    {
        UMaterialInterface* Material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(MaterialPath));
        if (Material)
        {
            ISM->SetMaterial(0, Material);
        }
    }

    if (TransformsArray)
    {
        for (const TSharedPtr<FJsonValue>& Value : *TransformsArray)
        {
            if (!Value.IsValid() || Value->Type != EJson::Object) continue;
            FVector Location = FVector::ZeroVector;
            FVector Scale = FVector::OneVector;
            FRotator Rotation = FRotator::ZeroRotator;
            if (ParseTransformArrayEntry(Value->AsObject(), Location, Scale, Rotation))
            {
                FTransform InstanceTransform(Rotation, Location, Scale);
                ISM->AddInstance(InstanceTransform);
            }
        }
    }

    ISM->MarkRenderStateDirty();
    FEpicUnrealMCPCommonUtils::GetActorIndex().AddActor(SetActor);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("set_id"), SetId);
    ResultObj->SetStringField(TEXT("actor_name"), SetActor->GetName());
    ResultObj->SetNumberField(TEXT("instance_count"), InstanceCount);
    ResultObj->SetBoolField(TEXT("use_hism"), bUseHism);
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPInstanceCommands::HandleUpdateInstanceSet(const TSharedPtr<FJsonObject>& Params)
{
    FString SetId;
    if (!Params->TryGetStringField(TEXT("set_id"), SetId) || SetId.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'set_id' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    AActor* SetActor = FindInstanceSetActor(World, SetId);
    if (!SetActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Instance set '%s' not found"), *SetId));
    }

    UInstancedStaticMeshComponent* ISM = SetActor->FindComponentByClass<UInstancedStaticMeshComponent>();
    if (!ISM)
    {
        ISM = SetActor->FindComponentByClass<UHierarchicalInstancedStaticMeshComponent>();
    }
    if (!ISM)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to find ISM/HISM component on instance set actor"));
    }

    FlushRenderingCommands();
    ISM->ClearInstances();

    FString MaterialPath;
    Params->TryGetStringField(TEXT("material_path"), MaterialPath);
    if (!MaterialPath.IsEmpty())
    {
        UMaterialInterface* Material = Cast<UMaterialInterface>(UEditorAssetLibrary::LoadAsset(MaterialPath));
        if (Material)
        {
            ISM->SetMaterial(0, Material);
        }
    }

    const TArray<TSharedPtr<FJsonValue>>* TransformsArray = nullptr;
    int32 InstanceCount = 0;
    if (Params->TryGetArrayField(TEXT("transforms"), TransformsArray) && TransformsArray)
    {
        for (const TSharedPtr<FJsonValue>& Value : *TransformsArray)
        {
            if (!Value.IsValid() || Value->Type != EJson::Object) continue;
            FVector Location = FVector::ZeroVector;
            FVector Scale = FVector::OneVector;
            FRotator Rotation = FRotator::ZeroRotator;
            if (ParseTransformArrayEntry(Value->AsObject(), Location, Scale, Rotation))
            {
                FTransform InstanceTransform(Rotation, Location, Scale);
                ISM->AddInstance(InstanceTransform);
                InstanceCount++;
            }
        }
    }

    ISM->MarkRenderStateDirty();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("set_id"), SetId);
    ResultObj->SetNumberField(TEXT("instance_count"), InstanceCount);
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPInstanceCommands::HandleDeleteInstanceSet(const TSharedPtr<FJsonObject>& Params)
{
    FString SetId;
    if (!Params->TryGetStringField(TEXT("set_id"), SetId) || SetId.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'set_id' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    AActor* SetActor = FindInstanceSetActor(World, SetId);
    if (!SetActor)
    {
        TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
        ResultObj->SetBoolField(TEXT("success"), true);
        ResultObj->SetBoolField(TEXT("deleted"), false);
        ResultObj->SetStringField(TEXT("message"), FString::Printf(TEXT("Instance set '%s' not found (already deleted)"), *SetId));
        return ResultObj;
    }

    FEpicUnrealMCPCommonUtils::GetActorIndex().RemoveActor(SetActor);

    FScopedTransaction Transaction(FText::FromString(FString::Printf(TEXT("UnrealMCP: Delete Instance Set %s"), *SetId)));
    SetActor->Modify();
    SetActor->Destroy();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetBoolField(TEXT("deleted"), true);
    ResultObj->SetStringField(TEXT("set_id"), SetId);
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPInstanceCommands::HandleGetInstanceSetState(const TSharedPtr<FJsonObject>& Params)
{
    FString SetId;
    if (!Params->TryGetStringField(TEXT("set_id"), SetId) || SetId.IsEmpty())
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'set_id' parameter"));
    }

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    AActor* SetActor = FindInstanceSetActor(World, SetId);
    if (!SetActor)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Instance set '%s' not found"), *SetId));
    }

    UInstancedStaticMeshComponent* ISM = SetActor->FindComponentByClass<UInstancedStaticMeshComponent>();
    bool bIsHism = false;
    if (!ISM)
    {
        ISM = SetActor->FindComponentByClass<UHierarchicalInstancedStaticMeshComponent>();
        bIsHism = (ISM != nullptr);
    }

    int32 InstanceCount = ISM ? ISM->GetInstanceCount() : 0;
    FString MeshPath;
    FString MaterialPath;
    if (ISM && ISM->GetStaticMesh())
    {
        MeshPath = ISM->GetStaticMesh()->GetPathName();
    }
    if (ISM && ISM->GetMaterial(0))
    {
        MaterialPath = ISM->GetMaterial(0)->GetPathName();
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("set_id"), SetId);
    ResultObj->SetStringField(TEXT("actor_name"), SetActor->GetName());
    ResultObj->SetNumberField(TEXT("instance_count"), InstanceCount);
    ResultObj->SetBoolField(TEXT("use_hism"), bIsHism);
    if (!MeshPath.IsEmpty())
    {
        ResultObj->SetStringField(TEXT("mesh_path"), MeshPath);
    }
    if (!MaterialPath.IsEmpty())
    {
        ResultObj->SetStringField(TEXT("material_path"), MaterialPath);
    }

    TSharedPtr<FJsonObject> StateObj = MakeShared<FJsonObject>();
    StateObj->SetStringField(TEXT("set_id"), SetId);
    StateObj->SetStringField(TEXT("actor_name"), SetActor->GetName());
    StateObj->SetNumberField(TEXT("instance_count"), InstanceCount);
    StateObj->SetBoolField(TEXT("use_hism"), bIsHism);
    if (!MeshPath.IsEmpty())
    {
        StateObj->SetStringField(TEXT("mesh_path"), MeshPath);
    }
    if (!MaterialPath.IsEmpty())
    {
        StateObj->SetStringField(TEXT("material_path"), MaterialPath);
    }
    ResultObj->SetObjectField(TEXT("state"), StateObj);
    return ResultObj;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPInstanceCommands::HandleListInstanceSets(const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FEpicUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    TArray<TSharedPtr<FJsonValue>> SetArray;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!Actor || !Actor->Tags.Contains(FName(TEXT("managed_by_mcp"))))
        {
            continue;
        }
        FString SetId;
        for (const FName& Tag : Actor->Tags)
        {
            FString TagStr = Tag.ToString();
            if (TagStr.StartsWith(TEXT("mcp_id:instance_set_")))
            {
                SetId = TagStr.RightChop(FCString::Strlen(TEXT("mcp_id:instance_set_")));
                break;
            }
        }
        if (SetId.IsEmpty())
        {
            continue;
        }

        UInstancedStaticMeshComponent* ISM = Actor->FindComponentByClass<UInstancedStaticMeshComponent>();
        bool bIsHism = false;
        if (!ISM)
        {
            ISM = Actor->FindComponentByClass<UHierarchicalInstancedStaticMeshComponent>();
            bIsHism = (ISM != nullptr);
        }

        int32 InstanceCount = ISM ? ISM->GetInstanceCount() : 0;
        FString MeshPath;
        FString MaterialPath;
        if (ISM && ISM->GetStaticMesh())
        {
            MeshPath = ISM->GetStaticMesh()->GetPathName();
        }
        if (ISM && ISM->GetMaterial(0))
        {
            MaterialPath = ISM->GetMaterial(0)->GetPathName();
        }

        TSharedPtr<FJsonObject> SetObj = MakeShared<FJsonObject>();
        SetObj->SetStringField(TEXT("set_id"), SetId);
        SetObj->SetStringField(TEXT("actor_name"), Actor->GetName());
        SetObj->SetNumberField(TEXT("instance_count"), InstanceCount);
        SetObj->SetBoolField(TEXT("use_hism"), bIsHism);
        if (!MeshPath.IsEmpty())
        {
            SetObj->SetStringField(TEXT("mesh_path"), MeshPath);
        }
        if (!MaterialPath.IsEmpty())
        {
            SetObj->SetStringField(TEXT("material_path"), MaterialPath);
        }
        SetArray.Add(MakeShared<FJsonValueObject>(SetObj));
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetNumberField(TEXT("count"), SetArray.Num());
    ResultObj->SetArrayField(TEXT("sets"), SetArray);
    return ResultObj;
}

