#pragma once

#include "CoreMinimal.h"
#include "Json.h"

class UDataLayerAsset;
class UDataLayerInstance;
class AActor;
class UWorld;

/**
 * Shared helpers for the World Partition Data Layer subsystem.
 *
 * Used by:
 *   - FEpicUnrealMCPProjectEditorCommands (data_layer create/add/remove/enable handlers)
 *   - FEpicUnrealMCPProceduralCommands::HandleCreateDataLayerForGeneration
 *
 * These wrappers degrade gracefully to actor-tag mode when the level does
 * not have a World Partition setup (no UDataLayerEditorSubsystem), so
 * non-WP levels remain functional. Callers can inspect the returned
 * `method` field on the JSON response to know which mode was used.
 */
class UNREALMCP_API FEpicUnrealMCPDataLayerHelpers
{
public:
    /** Returns true when the editor / level supports real UDataLayerInstance. */
    static bool IsDataLayerSubsystemAvailable();

    /** Find or create the UDataLayerAsset for the given logical name. */
    static UDataLayerAsset* FindOrCreateDataLayerAsset(const FString& DataLayerName, FString* OutAssetPath = nullptr);

    /** Find or create the UDataLayerInstance for the given asset. Returns nullptr if WP is not available. */
    static UDataLayerInstance* FindOrCreateDataLayerInstance(const FString& DataLayerName, UDataLayerAsset* DataLayerAsset);

    /** Add a set of actors to the given data layer instance. Returns count actually modified. */
    static int32 AddActorsToInstance(const TArray<AActor*>& Actors, UDataLayerInstance* Instance);

    /** Apply an optional debug color (hex string "#RRGGBB" or "RRGGBB") to the instance. */
    static bool ApplyDebugColor(UDataLayerInstance* Instance, const FString& ColorHex);

    /** Apply an initial runtime state string ("Activated" / "Loaded" / "Unloaded") to the instance. */
    static bool ApplyInitialRuntimeState(UDataLayerInstance* Instance, const FString& StateName);
};
