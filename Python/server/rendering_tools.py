"""Rendering and lighting settings tools for the Unreal MCP server."""

import logging
from typing import Dict, Any, List, Optional

from server.core import mcp, get_unreal_connection
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")


@mcp.tool()
def set_global_illumination(method: str) -> Dict[str, Any]:
    """Set the global illumination method.

    Supported methods: Off, Lumen, ScreenSpace, RayTraced
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {"method": method}
        response = unreal.send_command("set_global_illumination", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_global_illumination error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_lumen_enabled(enabled: bool) -> Dict[str, Any]:
    """Enable or disable Lumen global illumination and reflections."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {"enabled": enabled}
        response = unreal.send_command("set_lumen_enabled", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_lumen_enabled error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_lumen_scene_detail(
    card_refresh_fraction: float = -1.0,
    radiosity_iterations: int = -1
) -> Dict[str, Any]:
    """Set Lumen scene detail parameters.

    card_refresh_fraction: 0.0-1.0 (fraction of cards updated per frame)
    radiosity_iterations: number of propagation iterations
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params: Dict[str, Any] = {}
        if card_refresh_fraction >= 0.0:
            params["card_refresh_fraction"] = card_refresh_fraction
        if radiosity_iterations >= 0:
            params["radiosity_iterations"] = radiosity_iterations
        response = unreal.send_command("set_lumen_scene_detail", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_lumen_scene_detail error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_lumen_reflection_quality(
    max_bounces: int = -1,
    screen_trace_iterations: int = -1
) -> Dict[str, Any]:
    """Set Lumen reflection quality parameters."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params: Dict[str, Any] = {}
        if max_bounces >= 0:
            params["max_bounces"] = max_bounces
        if screen_trace_iterations >= 0:
            params["screen_trace_iterations"] = screen_trace_iterations
        response = unreal.send_command("set_lumen_reflection_quality", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_lumen_reflection_quality error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_hardware_ray_tracing(enabled: bool) -> Dict[str, Any]:
    """Enable or disable hardware ray tracing (requires compatible GPU)."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {"enabled": enabled}
        response = unreal.send_command("set_hardware_ray_tracing", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_hardware_ray_tracing error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_path_tracing(
    enabled: bool = True,
    max_bounces: int = -1
) -> Dict[str, Any]:
    """Enable or disable path tracing and set max bounces."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params: Dict[str, Any] = {"enabled": enabled}
        if max_bounces >= 0:
            params["max_bounces"] = max_bounces
        response = unreal.send_command("set_path_tracing", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_path_tracing error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_virtual_shadow_maps(
    enabled: bool = True,
    resolution_lod_bias: float = 0.0
) -> Dict[str, Any]:
    """Enable or disable virtual shadow maps (VSM)."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {
            "enabled": enabled,
            "resolution_lod_bias": resolution_lod_bias,
        }
        response = unreal.send_command("set_virtual_shadow_maps", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_virtual_shadow_maps error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_shadow_quality(
    max_cascades: int = -1,
    distance_scale: float = -1.0
) -> Dict[str, Any]:
    """Set shadow quality parameters for CSM shadows."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params: Dict[str, Any] = {}
        if max_cascades >= 0:
            params["max_cascades"] = max_cascades
        if distance_scale > 0.0:
            params["distance_scale"] = distance_scale
        response = unreal.send_command("set_shadow_quality", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_shadow_quality error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_anti_aliasing(method: str) -> Dict[str, Any]:
    """Set the anti-aliasing method.

    Supported methods: None, FXAA, TAA, TSR, MSAA
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {"method": method}
        response = unreal.send_command("set_anti_aliasing", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_anti_aliasing error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_tsr_settings(
    algorithm: str = "",
    history_screen_percentage: float = -1.0
) -> Dict[str, Any]:
    """Set Temporal Super Resolution (TSR) settings.

    algorithm: Gen4 or Gen5
    history_screen_percentage: percentage for history buffer resolution
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params: Dict[str, Any] = {}
        if algorithm:
            params["algorithm"] = algorithm
        if history_screen_percentage >= 0.0:
            params["history_screen_percentage"] = history_screen_percentage
        response = unreal.send_command("set_tsr_settings", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_tsr_settings error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_upscaler(upscaler: str, enabled: bool) -> Dict[str, Any]:
    """Enable or disable an upscaling technology.

    Supported upscalers: DLSS, FSR, XeSS, NIS
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {
            "upscaler": upscaler,
            "enabled": enabled,
        }
        response = unreal.send_command("set_upscaler", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_upscaler error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_nanite_visualization(mode: str) -> Dict[str, Any]:
    """Set Nanite visualization mode.

    Supported modes: Off, Clusters, Triangles
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params = {"mode": mode}
        response = unreal.send_command("set_nanite_visualization", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_nanite_visualization error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def get_shader_compile_status() -> Dict[str, Any]:
    """Get the current shader compilation status."""
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        response = unreal.send_command("get_shader_compile_status", {})
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"get_shader_compile_status error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def spawn_camera_actor(
    name: str,
    location: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Spawn a CameraActor in the editor world.

    name: Unique actor name
    location: [x, y, z]
    rotation: [pitch, yaw, roll]
    """
    try:
        validate_string(name, "name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    params: Dict[str, Any] = {"name": name}
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    response = unreal.send_command("spawn_camera_actor", params)
    return response or make_error_response("No response from Unreal")


@mcp.tool()
def spawn_cine_camera_actor(
    name: str,
    location: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    focal_length: Optional[float] = None,
    aperture: Optional[float] = None,
    focus_distance: Optional[float] = None,
) -> Dict[str, Any]:
    """Spawn a CineCameraActor in the editor world.

    name: Unique actor name
    location: [x, y, z]
    rotation: [pitch, yaw, roll]
    focal_length: Lens focal length in mm
    aperture: f-stop value
    focus_distance: Focus distance in cm
    """
    try:
        validate_string(name, "name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    params: Dict[str, Any] = {"name": name}
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if focal_length is not None:
        params["focal_length"] = focal_length
    if aperture is not None:
        params["aperture"] = aperture
    if focus_distance is not None:
        params["focus_distance"] = focus_distance
    response = unreal.send_command("spawn_cine_camera_actor", params)
    return response or make_error_response("No response from Unreal")


@mcp.tool()
def set_camera_properties(
    name: str,
    focal_length: Optional[float] = None,
    aperture: Optional[float] = None,
    focus_distance: Optional[float] = None,
) -> Dict[str, Any]:
    """Set focal length, aperture, and focus distance on an existing CineCameraActor.

    name: Name of the existing CineCameraActor
    focal_length: Lens focal length in mm
    aperture: f-stop value
    focus_distance: Focus distance in cm
    """
    try:
        validate_string(name, "name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    params: Dict[str, Any] = {"name": name}
    if focal_length is not None:
        params["focal_length"] = focal_length
    if aperture is not None:
        params["aperture"] = aperture
    if focus_distance is not None:
        params["focus_distance"] = focus_distance
    response = unreal.send_command("set_camera_properties", params)
    return response or make_error_response("No response from Unreal")


@mcp.tool()
def set_post_process_volume(
    volume_name: str,
    exposure_method: str = "",
    exposure_bias: float = 0.0,
    bloom_intensity: float = 0.0,
    bloom_threshold: float = 0.0,
    dof_enabled: bool = False,
    dof_focal_distance: float = 0.0,
    dof_aperture: float = 0.0,
    color_temperature: float = 0.0,
    color_tint: float = 0.0,
    motion_blur_amount: float = 0.0,
    ao_intensity: float = 0.0,
    ao_radius: float = 0.0,
    vignette_intensity: float = 0.0,
    film_grain_intensity: float = 0.0,
    chromatic_aberration: float = 0.0,
    lens_flare_intensity: float = 0.0,
) -> Dict[str, Any]:
    """Configure an existing PostProcessVolume.

    exposure_method: Manual, AutoHistogram, AutoBasic
    exposure_bias: exposure compensation in EV
    bloom_intensity: bloom strength (0 = off)
    bloom_threshold: minimum brightness for bloom
    dof_enabled: toggle depth of field
    dof_focal_distance: focus distance in cm
    dof_aperture: f-stop value (lower = more blur)
    color_temperature: white balance temperature in Kelvin (6500 = neutral)
    color_tint: white balance tint (-1 to 1)
    motion_blur_amount: motion blur strength (0 = off)
    ao_intensity: ambient occlusion intensity
    ao_radius: ambient occlusion radius
    vignette_intensity: vignette strength (0 = off)
    film_grain_intensity: film grain strength (0 = off)
    chromatic_aberration: chromatic aberration intensity (0 = off)
    lens_flare_intensity: lens flare intensity (0 = off)
    """
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        params: Dict[str, Any] = {"volume_name": volume_name}
        if exposure_method:
            params["exposure_method"] = exposure_method
        if exposure_bias != 0.0:
            params["exposure_bias"] = exposure_bias
        if bloom_intensity != 0.0:
            params["bloom_intensity"] = bloom_intensity
        if bloom_threshold != 0.0:
            params["bloom_threshold"] = bloom_threshold
        if dof_enabled:
            params["dof_enabled"] = True
        if dof_focal_distance != 0.0:
            params["dof_focal_distance"] = dof_focal_distance
        if dof_aperture != 0.0:
            params["dof_aperture"] = dof_aperture
        if color_temperature != 0.0:
            params["color_temperature"] = color_temperature
        if color_tint != 0.0:
            params["color_tint"] = color_tint
        if motion_blur_amount != 0.0:
            params["motion_blur_amount"] = motion_blur_amount
        if ao_intensity != 0.0:
            params["ao_intensity"] = ao_intensity
        if ao_radius != 0.0:
            params["ao_radius"] = ao_radius
        if vignette_intensity != 0.0:
            params["vignette_intensity"] = vignette_intensity
        if film_grain_intensity != 0.0:
            params["film_grain_intensity"] = film_grain_intensity
        if chromatic_aberration != 0.0:
            params["chromatic_aberration"] = chromatic_aberration
        if lens_flare_intensity != 0.0:
            params["lens_flare_intensity"] = lens_flare_intensity

        response = unreal.send_command("set_post_process_volume", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_post_process_volume error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def spawn_post_process_volume(
    name: str,
    location: Optional[List[float]] = None,
    extent: Optional[List[float]] = None,
    infinite_extent: bool = False,
) -> Dict[str, Any]:
    """Spawn a PostProcessVolume in the editor world.

    name: Unique actor name
    location: [x, y, z]
    extent: [x, y, z] box extent in cm (default 500x500x500)
    infinite_extent: If True, volume affects the entire world (bUnbound)
    """
    try:
        validate_string(name, "name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    params: Dict[str, Any] = {"name": name}
    if location is not None:
        params["location"] = location
    if extent is not None:
        params["extent"] = extent
    if infinite_extent:
        params["infinite_extent"] = infinite_extent

    response = unreal.send_command("spawn_post_process_volume", params)
    return response or make_error_response("No response from Unreal")

# W1-7 Post Process / Camera residue (UE 5.7)


@mcp.tool()
def spawn_camera_shake_source(
    name: str,
    location: Optional[List[float]] = None,
    shake_class_path: Optional[str] = None,
    attenuation_inner_radius: float = 100.0,
    attenuation_outer_radius: float = 1000.0,
) -> Dict[str, Any]:
    """Spawn an actor with a UCameraShakeSourceComponent that drives nearby cameras.

    name: Unique actor name
    location: [x, y, z] world location
    shake_class_path: Optional /Script-path to a UCameraShakeBase-derived class
    attenuation_inner_radius: Inner radius (full intensity)
    attenuation_outer_radius: Outer radius (zero intensity)
    """
    try:
        validate_string(name, "name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {
        "name": name,
        "attenuation_inner_radius": attenuation_inner_radius,
        "attenuation_outer_radius": attenuation_outer_radius,
    }
    if location is not None:
        payload["location"] = location
    if shake_class_path:
        payload["shake_class_path"] = shake_class_path
    response = unreal.send_command("spawn_camera_shake_source", payload)
    return response or make_error_response("No response from Unreal")


@mcp.tool()
def spawn_camera_rig_rail(
    name: str,
    location: Optional[List[float]] = None,
    current_position: float = 0.0,
    lock_orientation_to_rail: bool = False,
) -> Dict[str, Any]:
    """Spawn an ACameraRig_Rail (spline-driven camera dolly).

    name: Unique actor name
    location: [x, y, z] world location
    current_position: Normalized rail position 0..1
    lock_orientation_to_rail: If True, mount orientation follows the rail
    """
    try:
        validate_string(name, "name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if not 0.0 <= current_position <= 1.0:
        return make_error_response("current_position must be within [0, 1]")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {
        "name": name,
        "current_position": current_position,
        "lock_orientation_to_rail": lock_orientation_to_rail,
    }
    if location is not None:
        payload["location"] = location
    response = unreal.send_command("spawn_camera_rig_rail", payload)
    return response or make_error_response("No response from Unreal")


@mcp.tool()
def spawn_camera_rig_crane(
    name: str,
    location: Optional[List[float]] = None,
    crane_pitch: float = 0.0,
    crane_yaw: float = 0.0,
    crane_arm_length: float = 250.0,
    lock_mount_pitch: bool = False,
    lock_mount_yaw: bool = False,
) -> Dict[str, Any]:
    """Spawn an ACameraRig_Crane for cinematic crane-like camera moves.

    name: Unique actor name
    location: [x, y, z] world location
    crane_pitch: Pitch angle (deg)
    crane_yaw: Yaw angle (deg)
    crane_arm_length: Arm length (cm), clamped to >= 0
    lock_mount_pitch: Lock the mount pitch to the crane arm direction
    lock_mount_yaw: Lock the mount yaw to the crane arm direction
    """
    try:
        validate_string(name, "name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if crane_arm_length < 0:
        return make_error_response("crane_arm_length must be >= 0")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {
        "name": name,
        "crane_pitch": crane_pitch,
        "crane_yaw": crane_yaw,
        "crane_arm_length": crane_arm_length,
        "lock_mount_pitch": lock_mount_pitch,
        "lock_mount_yaw": lock_mount_yaw,
    }
    if location is not None:
        payload["location"] = location
    response = unreal.send_command("spawn_camera_rig_crane", payload)
    return response or make_error_response("No response from Unreal")


@mcp.tool()
def set_post_process_override(
    volume_name: str,
    gi_method: Optional[str] = None,
    reflection_method: Optional[str] = None,
) -> Dict[str, Any]:
    """Override the Global Illumination / Reflection method on a PostProcessVolume.

    volume_name: Existing APostProcessVolume actor name
    gi_method: "Lumen" | "ScreenSpace" | "Plugin" | "None"
    reflection_method: "Lumen" | "ScreenSpace" | "None"

    At least one of gi_method or reflection_method must be provided.
    """
    try:
        validate_string(volume_name, "volume_name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if gi_method is None and reflection_method is None:
        return make_error_response("provide at least one of gi_method or reflection_method")
    gi_allowed = {"Lumen", "ScreenSpace", "Plugin", "None"}
    ref_allowed = {"Lumen", "ScreenSpace", "None"}
    if gi_method is not None and gi_method not in gi_allowed:
        return make_error_response(
            f"gi_method must be one of {sorted(gi_allowed)}, got: {gi_method}"
        )
    if reflection_method is not None and reflection_method not in ref_allowed:
        return make_error_response(
            f"reflection_method must be one of {sorted(ref_allowed)}, got: {reflection_method}"
        )
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {"volume_name": volume_name}
    if gi_method is not None:
        payload["gi_method"] = gi_method
    if reflection_method is not None:
        payload["reflection_method"] = reflection_method
    response = unreal.send_command("set_post_process_override", payload)
    return response or make_error_response("No response from Unreal")
