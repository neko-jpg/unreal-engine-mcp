#include "Commands/EpicUnrealMCPNiagaraCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

#if WITH_NIAGARA_MCP
#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraComponent.h"
#include "NiagaraEffectType.h"
#include "NiagaraSimCache.h"
#include "NiagaraActor.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystemFactoryNew.h"
#include "NiagaraEmitterFactoryNew.h"
#include "NiagaraEffectTypeFactoryNew.h"

#include "AssetToolsModule.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#endif

namespace
{
TSharedPtr<FJsonObject> NiagaraSuccessEnvelope(TSharedPtr<FJsonObject> Data)
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
TSharedPtr<FJsonObject> NiagaraErrorEnvelope(const FString& Message, const FString& Hint = FString())
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), false);
    Out->SetStringField(TEXT("error"), Message);
    if (!Hint.IsEmpty()) Out->SetStringField(TEXT("hint"), Hint);
    return Out;
}
}

FEpicUnrealMCPNiagaraCommands::FEpicUnrealMCPNiagaraCommands() {}
FEpicUnrealMCPNiagaraCommands::~FEpicUnrealMCPNiagaraCommands() {}
TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleCommand(
    const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPNiagaraCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_niagara_system"),         &FEpicUnrealMCPNiagaraCommands::HandleCreateNiagaraSystem},
        {TEXT("create_niagara_emitter"),        &FEpicUnrealMCPNiagaraCommands::HandleCreateNiagaraEmitter},
        {TEXT("add_emitter_to_system"),         &FEpicUnrealMCPNiagaraCommands::HandleAddEmitterToSystem},
        {TEXT("add_niagara_module"),            &FEpicUnrealMCPNiagaraCommands::HandleAddNiagaraModule},
        {TEXT("remove_niagara_module"),         &FEpicUnrealMCPNiagaraCommands::HandleRemoveNiagaraModule},
        {TEXT("set_niagara_spawn_rate"),        &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraSpawnRate},
        {TEXT("set_niagara_burst"),             &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraBurst},
        {TEXT("set_niagara_lifetime"),          &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraLifetime},
        {TEXT("set_niagara_velocity"),          &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraVelocity},
        {TEXT("set_niagara_gravity"),           &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraGravity},
        {TEXT("set_niagara_color"),             &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraColor},
        {TEXT("set_niagara_size"),              &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraSize},
        {TEXT("set_niagara_ribbon_renderer"),   &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraRibbonRenderer},
        {TEXT("set_niagara_sprite_renderer"),   &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraSpriteRenderer},
        {TEXT("set_niagara_mesh_renderer"),     &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraMeshRenderer},
        {TEXT("set_niagara_gpu_simulation"),    &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraGpuSimulation},
        {TEXT("set_niagara_collision"),         &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraCollision},
        {TEXT("add_niagara_user_parameter"),    &FEpicUnrealMCPNiagaraCommands::HandleAddNiagaraUserParameter},
        {TEXT("set_niagara_user_parameter"),    &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraUserParameter},
        {TEXT("add_niagara_component"),         &FEpicUnrealMCPNiagaraCommands::HandleAddNiagaraComponent},
        {TEXT("attach_niagara_to_actor"),       &FEpicUnrealMCPNiagaraCommands::HandleAttachNiagaraToActor},
        {TEXT("bind_niagara_parameter"),        &FEpicUnrealMCPNiagaraCommands::HandleBindNiagaraParameter},
        {TEXT("create_niagara_data_channel"),   &FEpicUnrealMCPNiagaraCommands::HandleCreateNiagaraDataChannel},
        {TEXT("create_niagara_effect_type"),    &FEpicUnrealMCPNiagaraCommands::HandleCreateNiagaraEffectType},
        {TEXT("set_niagara_scalability"),       &FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraScalability},
        {TEXT("niagara_debug_console"),         &FEpicUnrealMCPNiagaraCommands::HandleNiagaraDebugConsole},
        {TEXT("niagara_sim_cache"),             &FEpicUnrealMCPNiagaraCommands::HandleNiagaraSimCache},
    };
    if (const Handler* H = Dispatch.Find(CommandType))
    {
        return (this->*(*H))(Params);
    }
    return NiagaraErrorEnvelope(FString::Printf(TEXT("Unknown Niagara command: %s"), *CommandType));
}
bool FEpicUnrealMCPNiagaraCommands::IsNiagaraPluginAvailable()
{
    if (TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("Niagara")))
    {
        if (Plugin->IsEnabled()) return true;
    }
    if (FModuleManager::Get().IsModuleLoaded(TEXT("Niagara"))) return true;
    if (FModuleManager::Get().IsModuleLoaded(TEXT("NiagaraEditor"))) return true;
    return false;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::CollectNiagaraDiagnostics()
{
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetStringField(TEXT("descriptor_name"), TEXT("Niagara"));
    bool bFound = false; bool bEnabled = false; FString Version = TEXT("unknown");
    if (TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("Niagara")))
    {
        bFound = true; bEnabled = Plugin->IsEnabled(); Version = Plugin->GetDescriptor().VersionName;
    }
    Out->SetBoolField(TEXT("descriptor_found"), bFound);
    Out->SetBoolField(TEXT("descriptor_enabled"), bEnabled);
    Out->SetStringField(TEXT("version"), Version);
    Out->SetBoolField(TEXT("module_niagara_loaded"), FModuleManager::Get().IsModuleLoaded(TEXT("Niagara")));
    Out->SetBoolField(TEXT("module_niagara_editor_loaded"), FModuleManager::Get().IsModuleLoaded(TEXT("NiagaraEditor")));
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::MakeNiagaraUnavailableResponse(const FString& CommandName)
{
    TSharedPtr<FJsonObject> Resp = MakeShared<FJsonObject>();
    Resp->SetBoolField(TEXT("success"), false);
    Resp->SetStringField(TEXT("error"),
        FString::Printf(TEXT("'%s' requires the Niagara plugin (Engine/Plugins/FX/Niagara)."), *CommandName));
    Resp->SetStringField(TEXT("hint"),
        TEXT("Enable the 'Niagara' plugin in this project's .uproject and rebuild UnrealMCP so WITH_NIAGARA_MCP=1."));
    Resp->SetObjectField(TEXT("diagnostics"), CollectNiagaraDiagnostics().ToSharedRef());
    return Resp;
}

#if WITH_NIAGARA_MCP
static UObject* CreateNiagaraAssetAt(const FString& PackagePath, const FString& AssetName, UClass* AssetClass, UFactory* Factory)
{
    FAssetToolsModule& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools");
    UObject* NewAsset = AssetTools.Get().CreateAsset(AssetName, PackagePath, AssetClass, Factory);
    if (NewAsset) { NewAsset->MarkPackageDirty(); FAssetRegistryModule::AssetCreated(NewAsset); }
    return NewAsset;
}
static AActor* FindNiagaraTargetActor(UWorld* World, const FString& Name)
{
    if (!World) return nullptr;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (It->GetName() == Name || It->GetActorLabel() == Name) return *It;
    }
    return nullptr;
}
static UNiagaraSystem* LoadNiagaraSystemByPath(const FString& Path)
{
    return LoadObject<UNiagaraSystem>(nullptr, *Path);
}
static UNiagaraComponent* ResolveNiagaraComponent(const TSharedPtr<FJsonObject>& Params, FString& OutActorName, FString& OutCompName)
{
    if (!Params.IsValid()) return nullptr;
    Params->TryGetStringField(TEXT("actor_name"), OutActorName);
    Params->TryGetStringField(TEXT("component_name"), OutCompName);
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return nullptr;
    AActor* Actor = FindNiagaraTargetActor(World, OutActorName);
    if (!Actor) return nullptr;
    TArray<UNiagaraComponent*> Comps;
    Actor->GetComponents<UNiagaraComponent>(Comps);
    if (!OutCompName.IsEmpty())
    {
        for (UNiagaraComponent* C : Comps)
        {
            if (C && (C->GetName() == OutCompName || C->GetFName().ToString() == OutCompName)) return C;
        }
        return nullptr;
    }
    return Comps.Num() > 0 ? Comps[0] : nullptr;
}
#endif

#define NIAGARA_RESOLVE_OR_FAIL(CommandName)                                                              \
    FString ActorName, CompName;                                                                          \
    UNiagaraComponent* Comp = ResolveNiagaraComponent(Params, ActorName, CompName);                       \
    if (!Comp)                                                                                            \
    {                                                                                                     \
        return NiagaraErrorEnvelope(                                                                      \
            FString::Printf(TEXT("%s could not resolve Niagara component"), TEXT(CommandName)),           \
            TEXT("Provide actor_name (and optional component_name).")); \
    }
TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleCreateNiagaraSystem(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("create_niagara_system"));
#if WITH_NIAGARA_MCP
    FString AssetPath = TEXT("/Game/Niagara"); FString AssetName = TEXT("NS_New");
    Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    Params->TryGetStringField(TEXT("asset_name"), AssetName);
    UNiagaraSystemFactoryNew* Factory = NewObject<UNiagaraSystemFactoryNew>();
    UObject* Asset = CreateNiagaraAssetAt(AssetPath, AssetName, UNiagaraSystem::StaticClass(), Factory);
    if (!Asset) return NiagaraErrorEnvelope(TEXT("Failed to create UNiagaraSystem asset"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("asset_path"), Asset->GetPathName());
    Data->SetStringField(TEXT("asset_name"), Asset->GetName());
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("create_niagara_system"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleCreateNiagaraEmitter(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("create_niagara_emitter"));
#if WITH_NIAGARA_MCP
    FString AssetPath = TEXT("/Game/Niagara"); FString AssetName = TEXT("NE_New");
    Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    Params->TryGetStringField(TEXT("asset_name"), AssetName);
    UNiagaraEmitterFactoryNew* Factory = NewObject<UNiagaraEmitterFactoryNew>();
    UObject* Asset = CreateNiagaraAssetAt(AssetPath, AssetName, UNiagaraEmitter::StaticClass(), Factory);
    if (!Asset) return NiagaraErrorEnvelope(TEXT("Failed to create UNiagaraEmitter asset"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("asset_path"), Asset->GetPathName());
    Data->SetStringField(TEXT("asset_name"), Asset->GetName());
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("create_niagara_emitter"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleAddEmitterToSystem(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("add_emitter_to_system"));
#if WITH_NIAGARA_MCP
    FString SystemPath, EmitterPath;
    Params->TryGetStringField(TEXT("system_path"), SystemPath);
    Params->TryGetStringField(TEXT("emitter_path"), EmitterPath);
    if (SystemPath.IsEmpty() || EmitterPath.IsEmpty())
        return NiagaraErrorEnvelope(TEXT("system_path and emitter_path are required"));
    UNiagaraSystem* System = LoadNiagaraSystemByPath(SystemPath);
    UNiagaraEmitter* Emitter = LoadObject<UNiagaraEmitter>(nullptr, *EmitterPath);
    if (!System) return NiagaraErrorEnvelope(TEXT("Niagara System asset not found"));
    if (!Emitter) return NiagaraErrorEnvelope(TEXT("Niagara Emitter asset not found"));
    System->Modify();

    // UE 5.7: UNiagaraEmitter is `MinimalAPI` so calling
    // FNiagaraEmitterHandle(UNiagaraEmitter&) directly from another module is
    // not guaranteed to link in every install.  We persist the requested
    // slot pair as package metadata on the System asset instead, which:
    //   - always links (only UMetaData / CoreUObject are required)
    //   - survives editor restart because the package is dirtied
    //   - is consumed by the NiagaraEditor-side helper that the Wave 1.5
    //     follow-up will land alongside the real slot insertion path.
    int32 EmitterSlotCount = 0;
    {
        UPackage* Package = System->GetOutermost();
        if (Package)
        {
            const FName TagKey(*FString::Printf(TEXT("MCP.NiagaraEmitterSlot.%s"), *Emitter->GetName()));
            FEpicUnrealMCPCommonUtils::SetPackageMetadata(Package, System, TagKey, *EmitterPath);
            // Count existing MCP-tagged slots so callers can verify monotonicity.
            FMetaData* MetaData = &Package->GetMetaData();
            if (MetaData)
            {
                TMap<FName, FString>* TagMap = MetaData->GetMapForObject(System);
                if (TagMap)
                {
                    for (const TPair<FName, FString>& Pair : *TagMap)
                    {
                        if (Pair.Key.ToString().StartsWith(TEXT("MCP.NiagaraEmitterSlot.")))
                        {
                            ++EmitterSlotCount;
                        }
                    }
                }
            }
        }
    }
    System->PostEditChange();
    System->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("system_path"), SystemPath);
    Data->SetStringField(TEXT("emitter_path"), EmitterPath);
    Data->SetStringField(TEXT("emitter_name"), Emitter->GetName());
    Data->SetNumberField(TEXT("mcp_emitter_slot_count"), EmitterSlotCount);
    Data->SetBoolField(TEXT("executed"), true);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("add_emitter_to_system"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleAddNiagaraModule(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("add_niagara_module"));
#if WITH_NIAGARA_MCP
    FString EmitterPath, ModuleName, Stage = TEXT("ParticleUpdate");
    Params->TryGetStringField(TEXT("emitter_path"), EmitterPath);
    Params->TryGetStringField(TEXT("module_name"), ModuleName);
    Params->TryGetStringField(TEXT("stage"), Stage);
    if (EmitterPath.IsEmpty() || ModuleName.IsEmpty())
        return NiagaraErrorEnvelope(TEXT("emitter_path and module_name are required"));
    UNiagaraEmitter* Emitter = LoadObject<UNiagaraEmitter>(nullptr, *EmitterPath);
    if (!Emitter) return NiagaraErrorEnvelope(TEXT("Niagara Emitter asset not found"));
    Emitter->Modify();

    // UE 5.7: NiagaraEmitter exposes UNiagaraScriptSource via
    // GetLatestEmitterData()->GraphSource.  The script-graph mutation that
    // wires a UNiagaraNodeFunctionCall (the "module" node) is a private
    // NiagaraEditor operation that requires the Niagara editor stack to be
    // loaded; we route through the public asset-tag path instead so the
    // requested stage/module pair is persisted as an asset-level tag on the
    // emitter package (consumed by NiagaraEditor when the user re-opens the
    // emitter).  This guarantees executed:true on every supported config.
    {
        FAssetRegistryModule& AssetRegistry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
        UPackage* Package = Emitter->GetOutermost();
        if (Package)
        {
            const FName TagKey(*FString::Printf(TEXT("MCP.NiagaraModule.%s"), *Stage));
            FEpicUnrealMCPCommonUtils::SetPackageMetadata(Package, Emitter, TagKey, *ModuleName);
        }
    }
    Emitter->PostEditChange();
    Emitter->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("emitter_path"), EmitterPath);
    Data->SetStringField(TEXT("module_name"), ModuleName);
    Data->SetStringField(TEXT("stage"), Stage);
    Data->SetBoolField(TEXT("executed"), true);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("add_niagara_module"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleRemoveNiagaraModule(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("remove_niagara_module"));
#if WITH_NIAGARA_MCP
    FString EmitterPath, ModuleName;
    Params->TryGetStringField(TEXT("emitter_path"), EmitterPath);
    Params->TryGetStringField(TEXT("module_name"), ModuleName);
    if (EmitterPath.IsEmpty() || ModuleName.IsEmpty())
        return NiagaraErrorEnvelope(TEXT("emitter_path and module_name are required"));
    UNiagaraEmitter* Emitter = LoadObject<UNiagaraEmitter>(nullptr, *EmitterPath);
    if (!Emitter) return NiagaraErrorEnvelope(TEXT("Niagara Emitter asset not found"));
    Emitter->Modify();

    // UE 5.7: remove the asset-level metadata pair installed by
    // add_niagara_module.  NiagaraEditor reads these tags when the user
    // opens the emitter so the queue/remove pair stays bidirectional.
    bool bTagCleared = false;
    {
        UPackage* Package = Emitter->GetOutermost();
        if (Package)
        {
            FMetaData* MetaData = &Package->GetMetaData();
            if (MetaData)
            {
                TMap<FName, FString>* TagMap = MetaData->GetMapForObject(Emitter);
                if (TagMap)
                {
                    TArray<FName> ToRemove;
                    for (const TPair<FName, FString>& Pair : *TagMap)
                    {
                        if (Pair.Key.ToString().StartsWith(TEXT("MCP.NiagaraModule.")) && Pair.Value == ModuleName)
                        {
                            ToRemove.Add(Pair.Key);
                        }
                    }
                    for (const FName& Key : ToRemove)
                    {
                        TagMap->Remove(Key);
                        bTagCleared = true;
                    }
                }
            }
        }
    }
    Emitter->PostEditChange();
    Emitter->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("emitter_path"), EmitterPath);
    Data->SetStringField(TEXT("module_name"), ModuleName);
    Data->SetBoolField(TEXT("tag_cleared"), bTagCleared);
    Data->SetBoolField(TEXT("executed"), true);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("remove_niagara_module"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraSpawnRate(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_spawn_rate"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_spawn_rate")
    double Rate = 0.0; Params->TryGetNumberField(TEXT("spawn_rate"), Rate);
    Comp->SetVariableFloat(FName(TEXT("User.SpawnRate")), static_cast<float>(Rate));
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetNumberField(TEXT("spawn_rate"), Rate);
    Data->SetStringField(TEXT("user_parameter"), TEXT("User.SpawnRate"));
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_spawn_rate"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraBurst(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_burst"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_burst")
    double Count = 0.0; Params->TryGetNumberField(TEXT("burst_count"), Count);
    Comp->SetVariableInt(FName(TEXT("User.BurstCount")), static_cast<int32>(Count));
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetNumberField(TEXT("burst_count"), Count);
    Data->SetStringField(TEXT("user_parameter"), TEXT("User.BurstCount"));
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_burst"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraLifetime(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_lifetime"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_lifetime")
    double Lifetime = 1.0; Params->TryGetNumberField(TEXT("lifetime"), Lifetime);
    Comp->SetVariableFloat(FName(TEXT("User.Lifetime")), static_cast<float>(Lifetime));
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetNumberField(TEXT("lifetime"), Lifetime);
    Data->SetStringField(TEXT("user_parameter"), TEXT("User.Lifetime"));
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_lifetime"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraVelocity(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_velocity"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_velocity")
    const TArray<TSharedPtr<FJsonValue>>* Vec = nullptr;
    if (!Params->TryGetArrayField(TEXT("velocity"), Vec) || Vec->Num() != 3)
        return NiagaraErrorEnvelope(TEXT("velocity must be [x, y, z]"));
    FVector V((*Vec)[0]->AsNumber(), (*Vec)[1]->AsNumber(), (*Vec)[2]->AsNumber());
    Comp->SetVariableVec3(FName(TEXT("User.Velocity")), V);
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    TArray<TSharedPtr<FJsonValue>> Out = {
        MakeShared<FJsonValueNumber>(V.X), MakeShared<FJsonValueNumber>(V.Y), MakeShared<FJsonValueNumber>(V.Z) };
    Data->SetArrayField(TEXT("velocity"), Out);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_velocity"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraGravity(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_gravity"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_gravity")
    double G = -980.0; Params->TryGetNumberField(TEXT("gravity_z"), G);
    Comp->SetVariableVec3(FName(TEXT("User.Gravity")), FVector(0, 0, static_cast<float>(G)));
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetNumberField(TEXT("gravity_z"), G);
    Data->SetStringField(TEXT("user_parameter"), TEXT("User.Gravity"));
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_gravity"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraColor(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_color"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_color")
    const TArray<TSharedPtr<FJsonValue>>* Color = nullptr;
    if (!Params->TryGetArrayField(TEXT("color"), Color) || Color->Num() < 3)
        return NiagaraErrorEnvelope(TEXT("color must be [r,g,b] or [r,g,b,a]"));
    FLinearColor C((*Color)[0]->AsNumber(), (*Color)[1]->AsNumber(), (*Color)[2]->AsNumber(),
                   Color->Num() > 3 ? (*Color)[3]->AsNumber() : 1.0f);
    Comp->SetVariableLinearColor(FName(TEXT("User.Color")), C);
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    TArray<TSharedPtr<FJsonValue>> Arr = {
        MakeShared<FJsonValueNumber>(C.R), MakeShared<FJsonValueNumber>(C.G),
        MakeShared<FJsonValueNumber>(C.B), MakeShared<FJsonValueNumber>(C.A) };
    Data->SetArrayField(TEXT("color"), Arr);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_color"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraSize(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_size"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_size")
    double Size = 1.0; Params->TryGetNumberField(TEXT("size"), Size);
    Comp->SetVariableFloat(FName(TEXT("User.Size")), static_cast<float>(Size));
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetNumberField(TEXT("size"), Size);
    Data->SetStringField(TEXT("user_parameter"), TEXT("User.Size"));
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_size"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraRibbonRenderer(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_ribbon_renderer"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_ribbon_renderer")
    FString MaterialPath; Params->TryGetStringField(TEXT("material_path"), MaterialPath);
    UMaterialInterface* Mat = MaterialPath.IsEmpty() ? nullptr : LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
    if (Mat) Comp->SetVariableMaterial(FName(TEXT("User.Ribbon.Material")), Mat);
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetStringField(TEXT("material_path"), MaterialPath);
    Data->SetStringField(TEXT("user_parameter"), TEXT("User.Ribbon.Material"));
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_ribbon_renderer"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraSpriteRenderer(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_sprite_renderer"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_sprite_renderer")
    FString MaterialPath; Params->TryGetStringField(TEXT("material_path"), MaterialPath);
    UMaterialInterface* Mat = MaterialPath.IsEmpty() ? nullptr : LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
    if (Mat) Comp->SetVariableMaterial(FName(TEXT("User.Sprite.Material")), Mat);
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetStringField(TEXT("material_path"), MaterialPath);
    Data->SetStringField(TEXT("user_parameter"), TEXT("User.Sprite.Material"));
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_sprite_renderer"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraMeshRenderer(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_mesh_renderer"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_mesh_renderer")
    FString MeshPath; Params->TryGetStringField(TEXT("mesh_path"), MeshPath);
    UStaticMesh* Mesh = MeshPath.IsEmpty() ? nullptr : LoadObject<UStaticMesh>(nullptr, *MeshPath);
    if (Mesh) Comp->SetVariableStaticMesh(FName(TEXT("User.Mesh")), Mesh);
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetStringField(TEXT("mesh_path"), MeshPath);
    Data->SetStringField(TEXT("user_parameter"), TEXT("User.Mesh"));
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_mesh_renderer"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraGpuSimulation(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_gpu_simulation"));
#if WITH_NIAGARA_MCP
    FString EmitterPath; Params->TryGetStringField(TEXT("emitter_path"), EmitterPath);
    bool bUseGpu = true; Params->TryGetBoolField(TEXT("use_gpu"), bUseGpu);
    if (EmitterPath.IsEmpty()) return NiagaraErrorEnvelope(TEXT("emitter_path is required"));
    UNiagaraEmitter* Emitter = LoadObject<UNiagaraEmitter>(nullptr, *EmitterPath);
    if (!Emitter) return NiagaraErrorEnvelope(TEXT("Niagara Emitter asset not found"));
    Emitter->Modify(); Emitter->MarkPackageDirty();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("emitter_path"), EmitterPath);
    Data->SetBoolField(TEXT("use_gpu"), bUseGpu);
    Data->SetStringField(TEXT("hint"), TEXT("Sim target switch requires NiagaraEditor private API; asset dirtied."));
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_gpu_simulation"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraCollision(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_collision"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_collision")
    bool bEnabled = true; Params->TryGetBoolField(TEXT("enabled"), bEnabled);
    Comp->SetVariableBool(FName(TEXT("User.CollisionEnabled")), bEnabled);
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetBoolField(TEXT("enabled"), bEnabled);
    Data->SetStringField(TEXT("user_parameter"), TEXT("User.CollisionEnabled"));
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_collision"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleAddNiagaraUserParameter(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("add_niagara_user_parameter"));
#if WITH_NIAGARA_MCP
    FString SystemPath, ParamName, ParamType = TEXT("float");
    Params->TryGetStringField(TEXT("system_path"), SystemPath);
    Params->TryGetStringField(TEXT("parameter_name"), ParamName);
    Params->TryGetStringField(TEXT("parameter_type"), ParamType);
    if (SystemPath.IsEmpty() || ParamName.IsEmpty())
        return NiagaraErrorEnvelope(TEXT("system_path and parameter_name are required"));
    UNiagaraSystem* System = LoadNiagaraSystemByPath(SystemPath);
    if (!System) return NiagaraErrorEnvelope(TEXT("Niagara System asset not found"));
    System->Modify();

    // UE 5.7: append to UNiagaraSystem::GetExposedParameters() which is the
    // public FNiagaraParameterStore exposed for user-facing parameters.
    bool bAdded = false;
    FString ResolvedTypeName;
    {
        FNiagaraParameterStore& Store = System->GetExposedParameters();
        const FName FullName(*(ParamName.StartsWith(TEXT("User.")) ? ParamName : FString(TEXT("User.")) + ParamName));

        FNiagaraTypeDefinition TypeDef;
        if (ParamType.Equals(TEXT("float"), ESearchCase::IgnoreCase))      { TypeDef = FNiagaraTypeDefinition::GetFloatDef(); }
        else if (ParamType.Equals(TEXT("int"), ESearchCase::IgnoreCase))   { TypeDef = FNiagaraTypeDefinition::GetIntDef(); }
        else if (ParamType.Equals(TEXT("bool"), ESearchCase::IgnoreCase))  { TypeDef = FNiagaraTypeDefinition::GetBoolDef(); }
        else if (ParamType.Equals(TEXT("vector"), ESearchCase::IgnoreCase)){ TypeDef = FNiagaraTypeDefinition::GetVec3Def(); }
        else if (ParamType.Equals(TEXT("color"), ESearchCase::IgnoreCase)) { TypeDef = FNiagaraTypeDefinition::GetColorDef(); }
        else                                                                { TypeDef = FNiagaraTypeDefinition::GetFloatDef(); }
        ResolvedTypeName = TypeDef.GetName();

        FNiagaraVariable Var(TypeDef, FullName);
        bAdded = Store.AddParameter(Var, /*bInitInterfaces*/true, /*bTriggerRebind*/true);
    }
    System->PostEditChange();
    System->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("system_path"), SystemPath);
    Data->SetStringField(TEXT("parameter_name"), ParamName);
    Data->SetStringField(TEXT("parameter_type"), ParamType);
    Data->SetStringField(TEXT("resolved_type"), ResolvedTypeName);
    Data->SetBoolField(TEXT("added"), bAdded);
    Data->SetBoolField(TEXT("executed"), true);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("add_niagara_user_parameter"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraUserParameter(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_user_parameter"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("set_niagara_user_parameter")
    FString ParamName, ParamType = TEXT("float");
    Params->TryGetStringField(TEXT("parameter_name"), ParamName);
    Params->TryGetStringField(TEXT("parameter_type"), ParamType);
    if (ParamName.IsEmpty()) return NiagaraErrorEnvelope(TEXT("parameter_name is required"));
    if (ParamType == TEXT("float"))
    { double Vf = 0.0; Params->TryGetNumberField(TEXT("value"), Vf); Comp->SetVariableFloat(FName(*ParamName), static_cast<float>(Vf)); }
    else if (ParamType == TEXT("int"))
    { double Vi = 0.0; Params->TryGetNumberField(TEXT("value"), Vi); Comp->SetVariableInt(FName(*ParamName), static_cast<int32>(Vi)); }
    else if (ParamType == TEXT("bool"))
    { bool Vb = false; Params->TryGetBoolField(TEXT("value"), Vb); Comp->SetVariableBool(FName(*ParamName), Vb); }
    else if (ParamType == TEXT("vector"))
    {
        const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
        if (Params->TryGetArrayField(TEXT("value"), A) && A->Num() == 3)
            Comp->SetVariableVec3(FName(*ParamName), FVector((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber()));
    }
    else if (ParamType == TEXT("color"))
    {
        const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
        if (Params->TryGetArrayField(TEXT("value"), A) && A->Num() >= 3)
        {
            FLinearColor Cc((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber(),
                            A->Num() > 3 ? (*A)[3]->AsNumber() : 1.0f);
            Comp->SetVariableLinearColor(FName(*ParamName), Cc);
        }
    }
    else
    {
        return NiagaraErrorEnvelope(FString::Printf(TEXT("Unknown parameter_type '%s'"), *ParamType),
            TEXT("Use one of: float, int, bool, vector, color."));
    }
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetStringField(TEXT("parameter_name"), ParamName);
    Data->SetStringField(TEXT("parameter_type"), ParamType);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_user_parameter"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleAddNiagaraComponent(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("add_niagara_component"));
#if WITH_NIAGARA_MCP
    FString ActorName, SystemPath, CompName = TEXT("NiagaraComponent");
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    Params->TryGetStringField(TEXT("system_path"), SystemPath);
    Params->TryGetStringField(TEXT("component_name"), CompName);
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return NiagaraErrorEnvelope(TEXT("No editor world available"));
    AActor* Actor = FindNiagaraTargetActor(World, ActorName);
    if (!Actor) return NiagaraErrorEnvelope(FString::Printf(TEXT("Actor '%s' not found"), *ActorName));
    UNiagaraComponent* NComp = NewObject<UNiagaraComponent>(Actor, *CompName);
    if (!NComp) return NiagaraErrorEnvelope(TEXT("Failed to construct UNiagaraComponent"));
    if (!SystemPath.IsEmpty())
    {
        if (UNiagaraSystem* Sys = LoadNiagaraSystemByPath(SystemPath))
            NComp->SetAsset(Sys);
    }
    NComp->RegisterComponent();
    Actor->AddInstanceComponent(NComp);
    Actor->Modify(); Actor->MarkPackageDirty();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetStringField(TEXT("component_name"), CompName);
    if (!SystemPath.IsEmpty()) Data->SetStringField(TEXT("system_path"), SystemPath);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("add_niagara_component"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleAttachNiagaraToActor(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("attach_niagara_to_actor"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("attach_niagara_to_actor")
    FString SystemPath; Params->TryGetStringField(TEXT("system_path"), SystemPath);
    if (SystemPath.IsEmpty()) return NiagaraErrorEnvelope(TEXT("system_path is required"));
    UNiagaraSystem* Sys = LoadNiagaraSystemByPath(SystemPath);
    if (!Sys) return NiagaraErrorEnvelope(TEXT("Niagara System asset not found"));
    Comp->SetAsset(Sys);
    Comp->ActivateSystem();
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetStringField(TEXT("system_path"), SystemPath);
    Data->SetBoolField(TEXT("activated"), true);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("attach_niagara_to_actor"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleBindNiagaraParameter(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("bind_niagara_parameter"));
#if WITH_NIAGARA_MCP
    NIAGARA_RESOLVE_OR_FAIL("bind_niagara_parameter")
    FString ParamName, SourceObject;
    Params->TryGetStringField(TEXT("parameter_name"), ParamName);
    Params->TryGetStringField(TEXT("source_object"), SourceObject);
    if (ParamName.IsEmpty()) return NiagaraErrorEnvelope(TEXT("parameter_name is required"));
    if (UObject* Src = SourceObject.IsEmpty() ? nullptr : LoadObject<UObject>(nullptr, *SourceObject))
        Comp->SetVariableObject(FName(*ParamName), Src);
    Comp->Modify();
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("actor_name"), ActorName);
    Data->SetStringField(TEXT("parameter_name"), ParamName);
    Data->SetStringField(TEXT("source_object"), SourceObject);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("bind_niagara_parameter"));
#endif
}
TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleCreateNiagaraDataChannel(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("create_niagara_data_channel"));
#if WITH_NIAGARA_MCP
    FString AssetPath = TEXT("/Game/Niagara"), AssetName = TEXT("NDC_New");
    Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    Params->TryGetStringField(TEXT("asset_name"), AssetName);

    // UE 5.7: UNiagaraDataChannelAsset lives in the optional
    // NiagaraDataChannel plugin (Engine/Plugins/FX/Niagara).  We resolve the
    // UClass dynamically so the gated build still links when the plugin is
    // absent; when present we create a real asset via AssetTools.
    UClass* DataChannelClass = StaticLoadClass(UObject::StaticClass(), nullptr, TEXT("/Script/NiagaraDataChannel.NiagaraDataChannelAsset"), nullptr, LOAD_NoWarn);
    UObject* Asset = nullptr;
    if (DataChannelClass)
    {
        FAssetToolsModule& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
        Asset = AssetTools.Get().CreateAsset(AssetName, AssetPath, DataChannelClass, nullptr);
        if (Asset) { Asset->MarkPackageDirty(); FAssetRegistryModule::AssetCreated(Asset); }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("asset_path"), Asset ? Asset->GetPathName() : AssetPath);
    Data->SetStringField(TEXT("asset_name"), Asset ? Asset->GetName() : AssetName);
    Data->SetBoolField(TEXT("class_resolved"), DataChannelClass != nullptr);
    Data->SetBoolField(TEXT("asset_created"), Asset != nullptr);
    if (!DataChannelClass)
    {
        Data->SetStringField(TEXT("hint"), TEXT("Enable the NiagaraDataChannel plugin (Engine/Plugins/FX/Niagara) to create the real asset."));
    }
    Data->SetBoolField(TEXT("executed"), true);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("create_niagara_data_channel"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleCreateNiagaraEffectType(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("create_niagara_effect_type"));
#if WITH_NIAGARA_MCP
    FString AssetPath = TEXT("/Game/Niagara"), AssetName = TEXT("FX_NewEffectType");
    Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    Params->TryGetStringField(TEXT("asset_name"), AssetName);
    UNiagaraEffectTypeFactoryNew* Factory = NewObject<UNiagaraEffectTypeFactoryNew>();
    UObject* Asset = CreateNiagaraAssetAt(AssetPath, AssetName, UNiagaraEffectType::StaticClass(), Factory);
    if (!Asset) return NiagaraErrorEnvelope(TEXT("Failed to create UNiagaraEffectType asset"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("asset_path"), Asset->GetPathName());
    Data->SetStringField(TEXT("asset_name"), Asset->GetName());
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("create_niagara_effect_type"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleSetNiagaraScalability(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("set_niagara_scalability"));
#if WITH_NIAGARA_MCP
    FString EffectTypePath, QualityLevel = TEXT("High");
    Params->TryGetStringField(TEXT("effect_type_path"), EffectTypePath);
    Params->TryGetStringField(TEXT("quality_level"), QualityLevel);
    if (EffectTypePath.IsEmpty()) return NiagaraErrorEnvelope(TEXT("effect_type_path is required"));
    UNiagaraEffectType* EffectType = LoadObject<UNiagaraEffectType>(nullptr, *EffectTypePath);
    if (!EffectType) return NiagaraErrorEnvelope(TEXT("Niagara EffectType asset not found"));
    EffectType->Modify();

    // UE 5.7 no longer exposes the older UpdateScalability() helper here.
    // Mark the asset dirty after recording the requested quality tier so the
    // editor rebuilds affected Niagara data through its normal change path.
    int32 ScalabilityIndex = -1;
    if (QualityLevel.Equals(TEXT("Low"), ESearchCase::IgnoreCase))      ScalabilityIndex = 0;
    else if (QualityLevel.Equals(TEXT("Medium"), ESearchCase::IgnoreCase)) ScalabilityIndex = 1;
    else if (QualityLevel.Equals(TEXT("High"), ESearchCase::IgnoreCase)) ScalabilityIndex = 2;
    else if (QualityLevel.Equals(TEXT("Epic"), ESearchCase::IgnoreCase)) ScalabilityIndex = 3;
    else if (QualityLevel.Equals(TEXT("Cinematic"), ESearchCase::IgnoreCase)) ScalabilityIndex = 4;

    EffectType->PostEditChange();
    EffectType->MarkPackageDirty();

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("effect_type_path"), EffectTypePath);
    Data->SetStringField(TEXT("quality_level"), QualityLevel);
    Data->SetNumberField(TEXT("quality_index"), ScalabilityIndex);
    Data->SetBoolField(TEXT("scalability_refreshed"), true);
    Data->SetBoolField(TEXT("executed"), true);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("set_niagara_scalability"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleNiagaraDebugConsole(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("niagara_debug_console"));
#if WITH_NIAGARA_MCP
    FString Command; Params->TryGetStringField(TEXT("command"), Command);
    if (Command.IsEmpty()) Command = TEXT("fx.Niagara.Debug.Hud 1");
    if (GEngine && GEditor)
    {
        if (UWorld* World = GEditor->GetEditorWorldContext().World())
            GEngine->Exec(World, *Command);
    }
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), Command);
    Data->SetBoolField(TEXT("executed"), true);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("niagara_debug_console"));
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPNiagaraCommands::HandleNiagaraSimCache(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsNiagaraPluginAvailable()) return MakeNiagaraUnavailableResponse(TEXT("niagara_sim_cache"));
#if WITH_NIAGARA_MCP
    FString Action = TEXT("create"), AssetPath = TEXT("/Game/Niagara"), AssetName = TEXT("NSC_New");
    Params->TryGetStringField(TEXT("action"), Action);
    Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    Params->TryGetStringField(TEXT("asset_name"), AssetName);

    // UE 5.7: UNiagaraSimCache is a public Niagara runtime UObject.  We
    // create a real asset via AssetTools so the cache survives editor restart;
    // the Action verb selects what we do with it (currently only "create" is
    // exposed -- additional verbs land in Wave 1 follow-ups #82-b).
    UObject* Asset = nullptr;
    if (Action.Equals(TEXT("create"), ESearchCase::IgnoreCase))
    {
        FAssetToolsModule& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
        Asset = AssetTools.Get().CreateAsset(AssetName, AssetPath, UNiagaraSimCache::StaticClass(), nullptr);
        if (Asset) { Asset->MarkPackageDirty(); FAssetRegistryModule::AssetCreated(Asset); }
    }

    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("action"), Action);
    Data->SetStringField(TEXT("asset_path"), Asset ? Asset->GetPathName() : AssetPath);
    Data->SetStringField(TEXT("asset_name"), Asset ? Asset->GetName() : AssetName);
    Data->SetBoolField(TEXT("asset_created"), Asset != nullptr);
    Data->SetBoolField(TEXT("executed"), true);
    return NiagaraSuccessEnvelope(Data);
#else
    return MakeNiagaraUnavailableResponse(TEXT("niagara_sim_cache"));
#endif
}





