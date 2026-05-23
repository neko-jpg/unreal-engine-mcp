#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Handler class for Niagara / VFX MCP commands.
 *
 * UE 5.7 Notes:
 * - Niagara is shipped as an engine plugin under Engine/Plugins/FX/Niagara.
 *   Verified header paths: Engine/Plugins/FX/Niagara/Source/Niagara/Classes/{NiagaraSystem.h,NiagaraEmitter.h,NiagaraEffectType.h,NiagaraSimCache.h},
 *   Public/NiagaraComponent.h, NiagaraEditor/Public/NiagaraSystemFactoryNew.h /
 *   NiagaraEmitterFactoryNew.h / NiagaraEffectTypeFactoryNew.h.
 * - Build.cs probes for `Niagara.uplugin`. When found it adds the `Niagara` and
 *   `NiagaraEditor` modules as private dependencies and defines `WITH_NIAGARA_MCP=1`.
 *   When the plugin is missing the handler still builds and every command returns
 *   a structured "plugin missing" envelope with an actionable hint.
 *
 * The 27 commands map 1:1 to tasks.md / Niagara section items (issue #49).
 */
class FEpicUnrealMCPNiagaraCommands
{
public:
    FEpicUnrealMCPNiagaraCommands();
    ~FEpicUnrealMCPNiagaraCommands();

    /** Dispatch a single Niagara command. */
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    // ----- Asset creation --------------------------------------------------
    TSharedPtr<FJsonObject> HandleCreateNiagaraSystem(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateNiagaraEmitter(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddEmitterToSystem(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddNiagaraModule(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRemoveNiagaraModule(const TSharedPtr<FJsonObject>& Params);

    // ----- Spawn / lifecycle ----------------------------------------------
    TSharedPtr<FJsonObject> HandleSetNiagaraSpawnRate(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraBurst(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraLifetime(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraVelocity(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraGravity(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraColor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraSize(const TSharedPtr<FJsonObject>& Params);

    // ----- Renderers -------------------------------------------------------
    TSharedPtr<FJsonObject> HandleSetNiagaraRibbonRenderer(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraSpriteRenderer(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraMeshRenderer(const TSharedPtr<FJsonObject>& Params);

    // ----- Simulation ------------------------------------------------------
    TSharedPtr<FJsonObject> HandleSetNiagaraGpuSimulation(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraCollision(const TSharedPtr<FJsonObject>& Params);

    // ----- Parameters ------------------------------------------------------
    TSharedPtr<FJsonObject> HandleAddNiagaraUserParameter(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraUserParameter(const TSharedPtr<FJsonObject>& Params);

    // ----- Placement -------------------------------------------------------
    TSharedPtr<FJsonObject> HandleAddNiagaraComponent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAttachNiagaraToActor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleBindNiagaraParameter(const TSharedPtr<FJsonObject>& Params);

    // ----- Effect / Scalability / Debug -----------------------------------
    TSharedPtr<FJsonObject> HandleCreateNiagaraDataChannel(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateNiagaraEffectType(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNiagaraScalability(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleNiagaraDebugConsole(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleNiagaraSimCache(const TSharedPtr<FJsonObject>& Params);

    // ----- Helpers ---------------------------------------------------------
    static bool IsNiagaraPluginAvailable();
    static TSharedPtr<FJsonObject> MakeNiagaraUnavailableResponse(const FString& CommandName);
    static TSharedPtr<FJsonObject> CollectNiagaraDiagnostics();
};
