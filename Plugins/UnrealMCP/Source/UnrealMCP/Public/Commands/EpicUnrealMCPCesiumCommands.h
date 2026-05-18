#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Handler class for Cesium for Unreal MCP commands.
 *
 * UE 5.7 Notes:
 * - Cesium for Unreal v2.18 and later officially ship Unreal Engine 5.7
 *   binaries (see https://github.com/CesiumGS/cesium-unreal/releases).
 * - All editor operations run on GameThread via AsyncTask from EpicUnrealMCPBridge.
 *
 * Detection Strategy:
 * - Check IPluginManager for CesiumForUnreal plugin descriptor.
 * - Check FModuleManager for CesiumRuntime module load state.
 * - When unavailable, every command returns success=false with an actionable
 *   `error` and `hint` that tells the AI exactly what to do next.
 *
 * Build.cs probes for `CesiumForUnreal.uplugin`. When found it adds
 * `CesiumRuntime` as a Private dependency and defines `WITH_CESIUM=1` so the
 * implementations below compile against the real Cesium types. The plugin
 * still builds when Cesium is not installed; in that mode every command
 * returns an actionable "plugin missing" envelope from
 * MakeCesiumUnavailableResponse.
 */
class UNREALMCP_API FEpicUnrealMCPCesiumCommands
{
public:
	FEpicUnrealMCPCesiumCommands();

	/** Dispatch a single Cesium command. */
	TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
	// ----- Always-on handlers (work without Cesium installed) -------------
	TSharedPtr<FJsonObject> HandleCesiumCheckPlugin(const TSharedPtr<FJsonObject>& Params);

	// ----- Implemented handlers (require WITH_CESIUM=1 to do real work) --
	TSharedPtr<FJsonObject> HandleCesiumSetupGeoreference(const TSharedPtr<FJsonObject>& Params);
	TSharedPtr<FJsonObject> HandleCesiumAddTileset(const TSharedPtr<FJsonObject>& Params);
	TSharedPtr<FJsonObject> HandleCesiumPlaceActorAtGeolocation(const TSharedPtr<FJsonObject>& Params);

	// ----- Helpers --------------------------------------------------------

	/** True when the CesiumForUnreal plugin descriptor is found and enabled. */
	static bool IsCesiumPluginAvailable();

	/** Resolve plugin display name + version + enabled state for diagnostics. */
	static TSharedPtr<FJsonObject> CollectCesiumDiagnostics();

	/** Build a standard "Cesium plugin missing" failure response with actionable hint. */
	static TSharedPtr<FJsonObject> MakeCesiumUnavailableResponse(const FString& CommandName);

	/** Build a standard "feature not yet wired" envelope (plugin present but PoC depth limited). */
	static TSharedPtr<FJsonObject> MakeCesiumNotImplementedResponse(const FString& CommandName);
};
