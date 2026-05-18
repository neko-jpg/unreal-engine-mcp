"""Scene database tools for the Unreal MCP server.

This module is now split into domain-specific sub-modules. It re-exports all
functions for backward compatibility.
"""

# Re-export common helpers and shared dependencies
from server.scene_tools_common import (  # noqa: F401
    _scene_syncd_error_response,
    _scene_syncd_data,
    _extract_layout_kind,
    _object_to_draft_instance,
    _send_draft_proxy_replace,
    _unreal_envelope,
    call_scene_syncd,
    call_scene_syncd_get,
    get_unreal_connection,
)

# CRUD
from server.scene_crud_tools import (  # noqa: F401
    scene_create,
    scene_upsert_actor,
    scene_upsert_actors,
    scene_delete_actor,
    scene_list_objects,
    scene_list_scenes,
    scene_list_snapshots,
    scene_snapshot_create,
    scene_snapshot_restore,
    scene_create_wall,
    scene_create_pyramid,
    scene_health,
)

# Sync / InstanceSet
from server.scene_sync_tools import (  # noqa: F401
    scene_plan_sync,
    scene_sync,
    scene_get_instance_sets,
    scene_spawn_instance_set,
    scene_update_instance_set,
    scene_delete_instance_set,
    scene_get_instance_set_state,
    scene_list_instance_sets,
)

# Layout / DraftProxy
from server.scene_layout_tools import (  # noqa: F401
    scene_generate_layout_objects,
    scene_create_layout,
    scene_create_draft_proxy,
    scene_update_draft_proxy,
    scene_delete_draft_proxy,
    scene_show_draft_proxy,
    scene_update_layout_node,
    scene_preview_layout,
    scene_approve_layout,
    scene_realize_layout,
    scene_compile_preview,
)

# Procedural generation
from server.scene_procedural_tools import (  # noqa: F401
    scene_upsert_procedural_mesh,
    scene_create_sdf_mesh,
    scene_create_superformula_mesh,
    scene_create_lsystem_spline,
    scene_create_wfc_grid,
    scene_create_wfc_grid_unreal,
    scene_wfc_to_semantic_layout,
    scene_show_wfc_proxy,
    scene_spawn_procedural_actor_batch,
    scene_create_spline_mesh_from_segments,
    scene_create_data_layer_for_generation,
    scene_clear_generated_group,
)

# Async jobs
from server.scene_job_tools import (  # noqa: F401
    scene_procedural_job_submit,
    scene_procedural_job_status,
    scene_procedural_job_result,
    scene_procedural_job_cancel,
    scene_procedural_job_list,
)

# NavMesh / AI / Blueprint
from server.scene_nav_ai_tools import (  # noqa: F401
    scene_create_navmesh_volume,
    scene_create_patrol_route,
    scene_set_ai_behavior,
    scene_spawn_blueprint,
    scene_component_upsert,
)

# Validation / PIE
from server.scene_validate_tools import (  # noqa: F401
    scene_validate,
    scene_compile_plan,
    scene_compile_apply,
    scene_run_pie_test,
    scene_generate_fix_plan,
)
