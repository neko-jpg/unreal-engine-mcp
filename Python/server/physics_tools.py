"""Physics and Collision tools for the Unreal MCP server."""

import logging
from typing import Dict, Any, Optional, List

from server.core import mcp, get_unreal_connection
from server.validation import validate_string, ValidationError, make_validation_error_response_from_exception
from utils.responses import make_error_response

logger = logging.getLogger("UnrealMCP_Advanced")


@mcp.tool()
def set_actor_collision_preset(
    actor_name: str,
    preset: str,
) -> Dict[str, Any]:
    """Set the collision preset on an actor's root primitive component.

    actor_name: Name or label of the actor
    preset: Collision preset name (e.g. "BlockAll", "OverlapAll", "Pawn", "PhysicsActor")
    """
    try:
        validate_string(actor_name, "actor_name")
        validate_string(preset, "preset")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        response = unreal.send_command(
            "set_actor_collision_preset",
            {"actor_name": actor_name, "preset": preset},
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_actor_collision_preset error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def set_actor_physics(
    actor_name: str,
    simulate_physics: Optional[bool] = None,
    gravity_enabled: Optional[bool] = None,
    mass_scale: Optional[float] = None,
    linear_damping: Optional[float] = None,
    angular_damping: Optional[float] = None,
) -> Dict[str, Any]:
    """Set physics properties on an actor's root primitive component.

    actor_name: Name or label of the actor
    simulate_physics: Enable physics simulation
    gravity_enabled: Enable gravity
    mass_scale: Multiplier for mass
    linear_damping: Linear damping (0-1)
    angular_damping: Angular damping (0-1)
    """
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    params: Dict[str, Any] = {"actor_name": actor_name}
    if simulate_physics is not None:
        params["simulate_physics"] = simulate_physics
    if gravity_enabled is not None:
        params["gravity_enabled"] = gravity_enabled
    if mass_scale is not None:
        params["mass_scale"] = mass_scale
    if linear_damping is not None:
        params["linear_damping"] = linear_damping
    if angular_damping is not None:
        params["angular_damping"] = angular_damping

    try:
        response = unreal.send_command("set_actor_physics", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"set_actor_physics error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def create_physical_material(
    asset_path: str,
    friction: float = 0.7,
    restitution: float = 0.3,
) -> Dict[str, Any]:
    """Create a PhysicalMaterial asset.

    asset_path: Full asset path (e.g. /Game/Physics/PM_MyMaterial)
    friction: Surface friction (0-1)
    restitution: Bounciness (0-1)
    """
    try:
        validate_string(asset_path, "asset_path")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    try:
        response = unreal.send_command(
            "create_physical_material",
            {
                "asset_path": asset_path,
                "friction": friction,
                "restitution": restitution,
            },
        )
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"create_physical_material error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def spawn_radial_force(
    actor_name: str = "RadialForceActor",
    location: Optional[Dict[str, float]] = None,
    radius: float = 500.0,
    strength: float = 1000.0,
) -> Dict[str, Any]:
    """Spawn a RadialForceActor in the level.

    actor_name: Actor name
    location: {"x": 0, "y": 0, "z": 0}
    radius: Force radius in cm
    strength: Force strength
    """
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    params: Dict[str, Any] = {"actor_name": actor_name, "radius": radius, "strength": strength}
    if location is not None:
        params["location"] = location

    try:
        response = unreal.send_command("spawn_radial_force", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"spawn_radial_force error: {e}")
        return make_error_response(str(e))


@mcp.tool()
def spawn_physics_constraint(
    actor_name: str = "PhysicsConstraintActor",
    location: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Spawn a PhysicsConstraintActor in the level.

    actor_name: Actor name
    location: {"x": 0, "y": 0, "z": 0}
    """
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as e:
        return make_validation_error_response_from_exception(e)

    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")

    params: Dict[str, Any] = {"actor_name": actor_name}
    if location is not None:
        params["location"] = location

    try:
        response = unreal.send_command("spawn_physics_constraint", params)
        return response or make_error_response("No response from Unreal")
    except Exception as e:
        logger.error(f"spawn_physics_constraint error: {e}")
        return make_error_response(str(e))

# W1-B Physics residue (UE 5.7, non-Chaos)


@mcp.tool()
def set_actor_collision_response(
    actor_name: str,
    channel: str,
    response: str,
) -> Dict[str, Any]:
    """Set per-channel collision response on an actor's root primitive.

    actor_name: Editor-world actor name or label
    channel: Trace/object channel name. Supported aliases:
             WorldStatic / WorldDynamic / Pawn / Visibility / Camera /
             PhysicsBody / Vehicle / Destructible (or full ECC_* names)
    response: Block | Overlap | Ignore
    """
    try:
        validate_string(actor_name, "actor_name")
        validate_string(channel, "channel")
        validate_string(response, "response")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if response not in {"Block", "Overlap", "Ignore"}:
        return make_error_response("response must be one of: Block, Overlap, Ignore")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        resp = unreal.send_command(
            "set_actor_collision_response",
            {"actor_name": actor_name, "channel": channel, "response": response},
        )
        return resp or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"set_actor_collision_response error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def set_constraint_limits(
    actor_name: str,
    linear_x_motion: Optional[str] = None,
    linear_y_motion: Optional[str] = None,
    linear_z_motion: Optional[str] = None,
    linear_limit_size: Optional[float] = None,
    angular_swing1_motion: Optional[str] = None,
    angular_swing2_motion: Optional[str] = None,
    angular_twist_motion: Optional[str] = None,
    angular_swing1_limit_degrees: Optional[float] = None,
    angular_swing2_limit_degrees: Optional[float] = None,
    angular_twist_limit_degrees: Optional[float] = None,
) -> Dict[str, Any]:
    """Configure motion modes and limits on a PhysicsConstraintActor.

    Linear motion strings: Free | Limited | Locked
    Angular motion strings: Free | Limited | Locked
    Limit values are in cm (linear) or degrees (angular).
    """
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    motion_set = {"Free", "Limited", "Locked"}
    for name, v in [
        ("linear_x_motion", linear_x_motion),
        ("linear_y_motion", linear_y_motion),
        ("linear_z_motion", linear_z_motion),
        ("angular_swing1_motion", angular_swing1_motion),
        ("angular_swing2_motion", angular_swing2_motion),
        ("angular_twist_motion", angular_twist_motion),
    ]:
        if v is not None and v not in motion_set:
            return make_error_response(f"{name} must be one of: Free, Limited, Locked")
    for name, v in [
        ("linear_limit_size", linear_limit_size),
        ("angular_swing1_limit_degrees", angular_swing1_limit_degrees),
        ("angular_swing2_limit_degrees", angular_swing2_limit_degrees),
        ("angular_twist_limit_degrees", angular_twist_limit_degrees),
    ]:
        if v is not None and v < 0:
            return make_error_response(f"{name} must be >= 0")
    payload: Dict[str, Any] = {"actor_name": actor_name}
    for k, v in [
        ("linear_x_motion", linear_x_motion),
        ("linear_y_motion", linear_y_motion),
        ("linear_z_motion", linear_z_motion),
        ("linear_limit_size", linear_limit_size),
        ("angular_swing1_motion", angular_swing1_motion),
        ("angular_swing2_motion", angular_swing2_motion),
        ("angular_twist_motion", angular_twist_motion),
        ("angular_swing1_limit_degrees", angular_swing1_limit_degrees),
        ("angular_swing2_limit_degrees", angular_swing2_limit_degrees),
        ("angular_twist_limit_degrees", angular_twist_limit_degrees),
    ]:
        if v is not None:
            payload[k] = v
    if len(payload) == 1:
        return make_error_response("Provide at least one motion or limit field")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        resp = unreal.send_command("set_constraint_limits", payload)
        return resp or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"set_constraint_limits error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def set_constraint_motor(
    actor_name: str,
    linear_velocity_drive: Optional[bool] = None,
    linear_position_drive: Optional[bool] = None,
    linear_velocity_target: Optional[List[float]] = None,
    angular_orientation_drive: Optional[bool] = None,
    angular_velocity_drive: Optional[bool] = None,
) -> Dict[str, Any]:
    """Enable or disable motors on a PhysicsConstraintActor.

    Linear drives toggle on all 3 axes simultaneously.
    Angular drives use SLERP mode.
    """
    try:
        validate_string(actor_name, "actor_name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if linear_velocity_target is not None:
        if not isinstance(linear_velocity_target, list) or len(linear_velocity_target) < 3:
            return make_error_response("linear_velocity_target must be a [x, y, z] list")
    payload: Dict[str, Any] = {"actor_name": actor_name}
    if linear_velocity_drive is not None:
        payload["linear_velocity_drive"] = linear_velocity_drive
    if linear_position_drive is not None:
        payload["linear_position_drive"] = linear_position_drive
    if linear_velocity_target is not None:
        payload["linear_velocity_target"] = linear_velocity_target
    if angular_orientation_drive is not None:
        payload["angular_orientation_drive"] = angular_orientation_drive
    if angular_velocity_drive is not None:
        payload["angular_velocity_drive"] = angular_velocity_drive
    if len(payload) == 1:
        return make_error_response("Provide at least one motor field")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    try:
        resp = unreal.send_command("set_constraint_motor", payload)
        return resp or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"set_constraint_motor error: {exc}")
        return make_error_response(str(exc))


@mcp.tool()
def spawn_physics_volume(
    name: str,
    location: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
    terminal_velocity: Optional[float] = None,
    priority: Optional[float] = None,
    water_volume: Optional[bool] = None,
    fluid_friction: Optional[float] = None,
) -> Dict[str, Any]:
    """Spawn an APhysicsVolume in the editor world.

    Modulates physics behavior for actors inside the volume (e.g. water).
    """
    try:
        validate_string(name, "name")
    except ValidationError as exc:
        return make_validation_error_response_from_exception(exc)
    if terminal_velocity is not None and terminal_velocity < 0:
        return make_error_response("terminal_velocity must be >= 0")
    if fluid_friction is not None and fluid_friction < 0:
        return make_error_response("fluid_friction must be >= 0")
    unreal = get_unreal_connection()
    if not unreal:
        return make_error_response("Failed to connect to Unreal Engine")
    payload: Dict[str, Any] = {"name": name}
    if location is not None:
        payload["location"] = location
    if scale is not None:
        payload["scale"] = scale
    if terminal_velocity is not None:
        payload["terminal_velocity"] = terminal_velocity
    if priority is not None:
        payload["priority"] = priority
    if water_volume is not None:
        payload["water_volume"] = water_volume
    if fluid_friction is not None:
        payload["fluid_friction"] = fluid_friction
    try:
        resp = unreal.send_command("spawn_physics_volume", payload)
        return resp or make_error_response("No response from Unreal")
    except Exception as exc:
        logger.error(f"spawn_physics_volume error: {exc}")
        return make_error_response(str(exc))
