use axum::extract::State;
use axum::Json;
use axum::Router;
use axum::routing::{get, post};
use crate::api::common::{AppState, success_response};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::error::AppError;

#[derive(Debug, Deserialize)]
pub struct CreateProceduralMeshRequest {
    pub vertex_count: u32,
    pub index_count: u32,
    pub positions: Vec<[f32; 3]>,
    pub normals: Vec<[f32; 3]>,
    pub indices: Vec<u32>,
    #[serde(default)]
    pub uvs: Vec<[f32; 2]>,
    #[serde(default)]
    pub colors: Vec<[u8; 4]>,
    #[serde(default)]
    pub mcp_id: Option<String>,
    #[serde(default)]
    pub flags: u32,
    #[serde(default = "default_actor_name")]
    pub actor_name: String,
    #[serde(default)]
    pub material_path: String,
    #[serde(default)]
    pub location: Option<[f32; 3]>,
    #[serde(default)]
    pub rotation: Option<[f32; 3]>,
    #[serde(default)]
    pub scale: Option<[f32; 3]>,
    #[serde(default = "default_focus_viewport")]
    pub focus_viewport: bool,
}

fn default_actor_name() -> String {
    "ProceduralMesh".to_string()
}

fn default_focus_viewport() -> bool {
    true
}

pub async fn create_procedural_mesh_route(
    State(state): State<AppState>,
    Json(req): Json<CreateProceduralMeshRequest>,
) -> Result<Json<Value>, AppError> {
    use crate::procedural::mesh_buffer::ProceduralMeshPayload;

    let mcp_id = req.mcp_id.clone().unwrap_or_else(|| req.actor_name.clone());
    let request_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64;

    let uvs = if req.uvs.is_empty() {
        None
    } else {
        Some(req.uvs)
    };
    let colors = if req.colors.is_empty() {
        None
    } else {
        Some(req.colors)
    };

    let payload = match ProceduralMeshPayload::new(
        &mcp_id,
        request_id,
        req.positions,
        req.normals,
        uvs,
        None, // tangents not supported via JSON API yet
        colors,
        None, // material_ids not supported via JSON API yet
        req.indices,
    ) {
        Ok(p) => p,
        Err(e) => return Err(AppError::Validation(format!("Invalid mesh data: {}", e))),
    };
    payload
        .validate_size()
        .map_err(|e| AppError::Validation(format!("Invalid mesh data: {}", e)))?;

    let start = std::time::Instant::now();
    let location = req.location.unwrap_or([0.0, 0.0, 0.0]);
    let rotation = req.rotation.unwrap_or([0.0, 0.0, 0.0]);
    let scale = req.scale.unwrap_or([1.0, 1.0, 1.0]);

    let result = state
        .unreal_client
        .upsert_procedural_mesh(
            &mcp_id,
            &req.actor_name,
            if req.material_path.is_empty() {
                None
            } else {
                Some(&req.material_path)
            },
            [location[0] as f64, location[1] as f64, location[2] as f64],
            [rotation[0] as f64, rotation[1] as f64, rotation[2] as f64],
            [scale[0] as f64, scale[1] as f64, scale[2] as f64],
            req.focus_viewport,
            payload,
        )
        .await;
    let elapsed = start.elapsed();

    match result {
        Ok(resp) => {
            tracing::info!("Procedural mesh created in {:?}", elapsed);
            Ok(Json(success_response(json!({
                "unreal_response": resp,
                "elapsed_ms": elapsed.as_millis() as u64,
            }))))
        }
        Err(e) => {
            tracing::error!("Failed to create procedural mesh: {}", e);
            Err(e)
        }
    }
}

// -- Phase 1: SDF -> Marching Cubes mesh ------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct SdfMeshRequest {
    pub sdf: SdfTreeDesc,
    #[serde(default = "default_sdf_resolution")]
    pub resolution: u32,
    #[serde(default)]
    pub bounds: Option<SdfBoundsDesc>,
    #[serde(default = "default_bounds_padding")]
    pub bounds_padding: f32,
    #[serde(default)]
    pub mcp_id: Option<String>,
    #[serde(default = "default_actor_name_sdf")]
    pub actor_name: String,
    #[serde(default)]
    pub material_path: String,
    #[serde(default)]
    pub location: Option<[f32; 3]>,
    #[serde(default)]
    pub rotation: Option<[f32; 3]>,
    #[serde(default)]
    pub scale: Option<[f32; 3]>,
    #[serde(default = "default_focus_viewport")]
    pub focus_viewport: bool,
}

#[derive(Debug, Deserialize)]
pub struct SdfTreeDesc {
    #[serde(rename = "type")]
    pub sdf_type: String,
    #[serde(default)]
    pub center: [f32; 3],
    #[serde(default = "default_radius")]
    pub radius: f32,
    #[serde(default)]
    pub min: [f32; 3],
    #[serde(default = "default_one")]
    pub max: [f32; 3],
    #[serde(default = "default_major_radius")]
    pub major_radius: f32,
    #[serde(default = "default_minor_radius")]
    pub minor_radius: f32,
    #[serde(default = "default_frequency")]
    pub frequency: f32,
    #[serde(default = "default_thickness")]
    pub thickness: f32,
    #[serde(default)]
    pub smoothness: f32,
    #[serde(default)]
    pub left: Option<Box<SdfTreeDesc>>,
    #[serde(default)]
    pub right: Option<Box<SdfTreeDesc>>,
    #[serde(default)]
    pub a: Option<Box<SdfTreeDesc>>,
    #[serde(default)]
    pub b: Option<Box<SdfTreeDesc>>,
    #[serde(default)]
    pub child: Option<Box<SdfTreeDesc>>,
    #[serde(default)]
    pub children: Vec<SdfTreeDesc>,
    #[serde(default)]
    pub matrix: Option<[f32; 16]>,
}

#[derive(Debug, Deserialize)]
pub struct SdfBoundsDesc {
    pub min: [f32; 3],
    pub max: [f32; 3],
}

fn default_sdf_resolution() -> u32 {
    32
}
fn default_bounds_padding() -> f32 {
    0.0
}
fn default_actor_name_sdf() -> String {
    "SdfMesh".to_string()
}
fn default_radius() -> f32 {
    1.0
}
fn default_one() -> [f32; 3] {
    [1.0, 1.0, 1.0]
}
fn default_major_radius() -> f32 {
    1.0
}
fn default_minor_radius() -> f32 {
    0.3
}
fn default_frequency() -> f32 {
    1.0
}
fn default_thickness() -> f32 {
    0.1
}

fn identity_matrix() -> [f32; 16] {
    [
        1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0,
    ]
}

fn collect_sdf_children(desc: &SdfTreeDesc) -> Vec<&SdfTreeDesc> {
    let mut children = Vec::new();
    if let Some(left) = desc.left.as_deref().or(desc.a.as_deref()) {
        children.push(left);
    }
    if let Some(right) = desc.right.as_deref().or(desc.b.as_deref()) {
        children.push(right);
    }
    children.extend(desc.children.iter());
    children
}

fn build_folded_sdf_tree<F>(
    desc: &SdfTreeDesc,
    op_name: &str,
    make_node: F,
) -> Result<crate::procedural::sdf::SdfTree, String>
where
    F: Fn(
        crate::procedural::sdf::SdfTree,
        crate::procedural::sdf::SdfTree,
        f32,
    ) -> crate::procedural::sdf::SdfTree,
{
    let children = collect_sdf_children(desc);
    if children.len() < 2 {
        return Err(format!("{op_name} requires at least 2 children"));
    }

    let mut iter = children.into_iter();
    let first = build_sdf_tree(iter.next().expect("checked child count"))?;
    iter.try_fold(first, |acc, child| {
        Ok(make_node(acc, build_sdf_tree(child)?, desc.smoothness))
    })
}

fn build_sdf_tree(desc: &SdfTreeDesc) -> Result<crate::procedural::sdf::SdfTree, String> {
    use crate::procedural::sdf::{SdfPrimitive, SdfTree};
    match desc.sdf_type.to_ascii_lowercase().as_str() {
        "sphere" => Ok(SdfTree::Primitive(SdfPrimitive::Sphere {
            center: desc.center,
            radius: desc.radius,
        })),
        "box" => Ok(SdfTree::Primitive(SdfPrimitive::Box {
            min: desc.min,
            max: desc.max,
        })),
        "torus" => Ok(SdfTree::Primitive(SdfPrimitive::Torus {
            center: desc.center,
            major_radius: desc.major_radius,
            minor_radius: desc.minor_radius,
        })),
        "gyroid" => Ok(SdfTree::Primitive(SdfPrimitive::Gyroid {
            frequency: desc.frequency,
            thickness: desc.thickness,
        })),
        "scherk" => Ok(SdfTree::Primitive(SdfPrimitive::Scherk {
            frequency: desc.frequency,
        })),
        "union" => build_folded_sdf_tree(desc, "union", |a, b, s| {
            SdfTree::Union(Box::new(a), Box::new(b), s)
        }),
        "difference" | "subtract" => build_folded_sdf_tree(desc, "difference", |a, b, s| {
            SdfTree::Difference(Box::new(a), Box::new(b), s)
        }),
        "intersection" | "intersect" => build_folded_sdf_tree(desc, "intersection", |a, b, s| {
            SdfTree::Intersection(Box::new(a), Box::new(b), s)
        }),
        "transform" => {
            let child = desc
                .child
                .as_deref()
                .or_else(|| desc.children.first())
                .ok_or_else(|| "transform requires a child".to_string())?;
            Ok(SdfTree::Transform(
                Box::new(build_sdf_tree(child)?),
                desc.matrix.unwrap_or_else(identity_matrix),
            ))
        }
        other => Err(format!("unsupported SDF node type '{other}'")),
    }
}

pub async fn sdf_mesh_route(
    State(state): State<AppState>,
    Json(req): Json<SdfMeshRequest>,
) -> Result<Json<Value>, AppError> {
    use crate::procedural::mesh_gen::{auto_bounds_with_padding, sdf_to_mesh_payload};
    use crate::procedural::sdf::SdfBounds;
    use glam::Vec3;

    let sdf = build_sdf_tree(&req.sdf)
        .map_err(|e| AppError::Validation(format!("Invalid SDF tree: {e}")))?;
    let default_bounds = SdfBounds::new(Vec3::new(-5.0, -5.0, -5.0), Vec3::new(5.0, 5.0, 5.0));
    let bounds = match req.bounds {
        Some(b) => SdfBounds::new(Vec3::from(b.min), Vec3::from(b.max)),
        None => auto_bounds_with_padding(&sdf, default_bounds, req.bounds_padding),
    };

    let mcp_id = req.mcp_id.clone().unwrap_or_else(|| req.actor_name.clone());
    let request_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64;

    let payload = sdf_to_mesh_payload(&mcp_id, request_id, &sdf, bounds, req.resolution)
        .map_err(|e| AppError::Validation(format!("SDF mesh generation failed: {}", e)))?;
    payload
        .validate_size()
        .map_err(|e| AppError::Validation(format!("Invalid mesh data: {}", e)))?;

    let location = req.location.unwrap_or([0.0, 0.0, 0.0]);
    let rotation = req.rotation.unwrap_or([0.0, 0.0, 0.0]);
    let scale = req.scale.unwrap_or([1.0, 1.0, 1.0]);

    let start = std::time::Instant::now();
    let result = state
        .unreal_client
        .upsert_procedural_mesh(
            &mcp_id,
            &req.actor_name,
            if req.material_path.is_empty() {
                None
            } else {
                Some(&req.material_path)
            },
            [location[0] as f64, location[1] as f64, location[2] as f64],
            [rotation[0] as f64, rotation[1] as f64, rotation[2] as f64],
            [scale[0] as f64, scale[1] as f64, scale[2] as f64],
            req.focus_viewport,
            payload,
        )
        .await;
    let elapsed = start.elapsed();

    match result {
        Ok(resp) => Ok(Json(success_response(json!({
            "unreal_response": resp,
            "elapsed_ms": elapsed.as_millis() as u64,
        })))),
        Err(e) => Err(e),
    }
}

// 笏笏 Phase 1: Superformula mesh 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

#[derive(Debug, Deserialize)]
pub struct SuperformulaMeshRequest {
    #[serde(default = "default_sf_m")]
    pub m1: f32,
    #[serde(default = "default_sf_n")]
    pub n1_1: f32,
    #[serde(default = "default_sf_n")]
    pub n2_1: f32,
    #[serde(default = "default_sf_n")]
    pub n3_1: f32,
    #[serde(default = "default_sf_one")]
    pub a1: f32,
    #[serde(default = "default_sf_one")]
    pub b1: f32,
    #[serde(default = "default_sf_m")]
    pub m2: f32,
    #[serde(default = "default_sf_n")]
    pub n1_2: f32,
    #[serde(default = "default_sf_n")]
    pub n2_2: f32,
    #[serde(default = "default_sf_n")]
    pub n3_2: f32,
    #[serde(default = "default_sf_one")]
    pub a2: f32,
    #[serde(default = "default_sf_one")]
    pub b2: f32,
    #[serde(default = "default_sf_resolution")]
    pub resolution: u32,
    #[serde(default = "default_sf_scale")]
    pub scale: f32,
    #[serde(default)]
    pub mcp_id: Option<String>,
    #[serde(default = "default_actor_name_sf")]
    pub actor_name: String,
    #[serde(default)]
    pub material_path: String,
    #[serde(default)]
    pub location: Option<[f32; 3]>,
    #[serde(default)]
    pub rotation: Option<[f32; 3]>,
    #[serde(default)]
    pub scale_override: Option<[f32; 3]>,
    #[serde(default = "default_focus_viewport")]
    pub focus_viewport: bool,
}

fn default_sf_m() -> f32 {
    6.0
}
fn default_sf_n() -> f32 {
    1.0
}
fn default_sf_one() -> f32 {
    1.0
}
fn default_sf_resolution() -> u32 {
    32
}
fn default_sf_scale() -> f32 {
    100.0
}
fn default_actor_name_sf() -> String {
    "SuperformulaMesh".to_string()
}

pub async fn superformula_mesh_route(
    State(state): State<AppState>,
    Json(req): Json<SuperformulaMeshRequest>,
) -> Result<Json<Value>, AppError> {
    use crate::procedural::superformula::{superformula_mesh, SuperformulaParams};

    let params = SuperformulaParams {
        m1: req.m1,
        n1_1: req.n1_1,
        n2_1: req.n2_1,
        n3_1: req.n3_1,
        a1: req.a1,
        b1: req.b1,
        m2: req.m2,
        n1_2: req.n1_2,
        n2_2: req.n2_2,
        n3_2: req.n3_2,
        a2: req.a2,
        b2: req.b2,
    };

    let mcp_id = req.mcp_id.clone().unwrap_or_else(|| req.actor_name.clone());
    let request_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64;

    let payload = superformula_mesh(&params, req.resolution, req.scale, &mcp_id, request_id)
        .map_err(|e| AppError::Validation(format!("Superformula mesh generation failed: {}", e)))?;
    payload
        .validate_size()
        .map_err(|e| AppError::Validation(format!("Invalid mesh data: {}", e)))?;

    let location = req.location.unwrap_or([0.0, 0.0, 0.0]);
    let rotation = req.rotation.unwrap_or([0.0, 0.0, 0.0]);
    let scale = req.scale_override.unwrap_or([1.0, 1.0, 1.0]);

    let start = std::time::Instant::now();
    let result = state
        .unreal_client
        .upsert_procedural_mesh(
            &mcp_id,
            &req.actor_name,
            if req.material_path.is_empty() {
                None
            } else {
                Some(&req.material_path)
            },
            [location[0] as f64, location[1] as f64, location[2] as f64],
            [rotation[0] as f64, rotation[1] as f64, rotation[2] as f64],
            [scale[0] as f64, scale[1] as f64, scale[2] as f64],
            req.focus_viewport,
            payload,
        )
        .await;
    let elapsed = start.elapsed();

    match result {
        Ok(resp) => Ok(Json(success_response(json!({
            "unreal_response": resp,
            "elapsed_ms": elapsed.as_millis() as u64,
        })))),
        Err(e) => Err(e),
    }
}

// 笏笏 Phase 1: L-System spline 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

#[derive(Debug, Deserialize)]
pub struct LSystemSplineRequest {
    #[serde(default = "default_ls_axiom")]
    pub axiom: String,
    #[serde(default)]
    pub rules: Vec<[String; 2]>,
    #[serde(default = "default_ls_iterations")]
    pub iterations: u32,
    #[serde(default = "default_ls_step")]
    pub step_length: f32,
    #[serde(default = "default_ls_angle")]
    pub angle_degrees: f32,
    #[serde(default)]
    pub origin: Option<[f32; 3]>,
    #[serde(default)]
    pub heading: Option<[f32; 3]>,
    #[serde(default)]
    pub up: Option<[f32; 3]>,
    #[serde(default)]
    pub preset: Option<String>,
    #[serde(default)]
    pub closed_loop: bool,
    #[serde(default = "default_ls_tangent_mode")]
    pub tangent_mode: String,
    #[serde(default)]
    pub mcp_id: Option<String>,
    #[serde(default = "default_actor_name_ls")]
    pub spline_name: String,
    #[serde(default = "default_create_in_unreal")]
    pub create_in_unreal: bool,
    #[serde(default = "default_focus_viewport")]
    pub focus_viewport: bool,
}

fn default_ls_axiom() -> String {
    "F".to_string()
}
fn default_ls_iterations() -> u32 {
    3
}
fn default_ls_step() -> f32 {
    50.0
}
fn default_ls_angle() -> f32 {
    90.0
}
fn default_ls_tangent_mode() -> String {
    "curve".to_string()
}
fn default_actor_name_ls() -> String {
    "LSystemSpline".to_string()
}
fn default_create_in_unreal() -> bool {
    true
}

pub async fn lsystem_spline_route(
    State(state): State<AppState>,
    Json(req): Json<LSystemSplineRequest>,
) -> Result<Json<Value>, AppError> {
    use crate::procedural::lsystem::{evaluate_lsystem, DimensionMode, LSystemParams};

    let mut params = if let Some(preset_name) = &req.preset {
        crate::procedural::lsystem_presets::resolve_preset(preset_name)
            .ok_or_else(|| AppError::Validation(format!("Unknown preset: {}", preset_name)))?
    } else {
        let rules: Vec<(char, String)> = req
            .rules
            .iter()
            .filter_map(|[sym, repl]| sym.chars().next().map(|c| (c, repl.clone())))
            .collect();

        LSystemParams {
            axiom: req.axiom.clone(),
            rules,
            iterations: req.iterations,
            step_length: req.step_length,
            angle_degrees: req.angle_degrees,
            origin: req.origin.unwrap_or([0.0, 0.0, 0.0]),
            heading: req.heading.unwrap_or([1.0, 0.0, 0.0]),
            up: req.up.unwrap_or([0.0, 0.0, 1.0]),
            dimension_mode: DimensionMode::ThreeD,
        }
    };

    // Allow common tuning fields to override preset values.
    params.iterations = req.iterations.min(10);
    params.step_length = req.step_length;
    if let Some(origin) = req.origin {
        params.origin = origin;
    }
    if let Some(heading) = req.heading {
        params.heading = heading;
    }
    if let Some(up) = req.up {
        params.up = up;
    }

    let result = evaluate_lsystem(&params);
    if result.segments.is_empty() {
        return Err(AppError::Validation(
            "L-System produced no drawable segments".to_string(),
        ));
    }

    let segments_json: Vec<Value> = result
        .segments
        .iter()
        .map(|seg| {
            json!({
                "start": {"x": seg.start[0], "y": seg.start[1], "z": seg.start[2]},
                "end": {"x": seg.end[0], "y": seg.end[1], "z": seg.end[2]},
            })
        })
        .collect();

    let unreal_response = if req.create_in_unreal {
        Some(
            state
                .unreal_client
                .create_spline_from_points(
                    &req.mcp_id
                        .clone()
                        .unwrap_or_else(|| req.spline_name.clone()),
                    &req.spline_name,
                    segments_json.clone(),
                    req.closed_loop,
                    &req.tangent_mode,
                    req.focus_viewport,
                )
                .await?,
        )
    } else {
        None
    };

    Ok(Json(success_response(json!({
        "spline_name": req.spline_name,
        "segment_count": result.segments.len(),
        "segments": segments_json,
        "derived_length": result.derived_string.len(),
        "closed_loop": req.closed_loop,
        "tangent_mode": req.tangent_mode,
        "unreal_response": unreal_response,
    }))))
}

// 笏笏 Phase 1: WFC Grid 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

#[derive(Debug, Deserialize)]
pub struct WfcGridRequest {
    pub width: u32,
    pub height: u32,
    pub tileset: crate::procedural::wfc::WfcTileset,
    #[serde(default)]
    pub seed: Option<u64>,
    #[serde(default)]
    pub periodic: bool,
}

pub async fn wfc_grid_route(
    State(_state): State<AppState>,
    Json(req): Json<WfcGridRequest>,
) -> Result<Json<Value>, AppError> {
    use crate::procedural::generator::{GenerateContext, GenerationLimits};
    use crate::procedural::wfc::{WfcGenerator, WfcParams};
    use crate::procedural::generator::Generator;

    let mut limits = GenerationLimits::default();
    limits.max_iterations = (req.width * req.height * 100).max(1000) as u32;
    let ctx = GenerateContext::new(req.seed, Some(limits));

    let params = WfcParams {
        width: req.width,
        height: req.height,
        tileset: req.tileset,
        seed: req.seed,
        periodic: req.periodic,
    };

    let gen = WfcGenerator;
    let output = gen
        .generate(&params, &ctx)
        .map_err(|e| AppError::Validation(format!("WFC generation failed: {e}")))?;

    Ok(Json(success_response(json!({
        "width": output.data.width,
        "height": output.data.height,
        "tiles": output.data.tiles,
        "stats": output.stats,
    }))))
}

// 笏笏 Procedural Job Registry 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

#[derive(Debug, Deserialize)]
pub struct ProceduralJobSubmitRequest {
    pub generator: String,
    pub params: serde_json::Value,
    #[serde(default)]
    pub seed: Option<u64>,
    #[serde(default)]
    pub limits: Option<ProceduralJobLimitsInput>,
}

#[derive(Debug, Deserialize)]
pub struct ProceduralJobLimitsInput {
    #[serde(default)]
    pub max_iterations: Option<u32>,
    #[serde(default)]
    pub max_execution_ms: Option<u64>,
    #[serde(default)]
    pub max_segment_count: Option<usize>,
    #[serde(default)]
    pub max_actor_count: Option<usize>,
    #[serde(default)]
    pub max_string_length: Option<usize>,
}

pub async fn procedural_job_submit_route(
    State(state): State<AppState>,
    Json(req): Json<ProceduralJobSubmitRequest>,
) -> Result<Json<Value>, AppError> {
    use crate::procedural::generator::GenerationLimits;
    use crate::procedural::jobs::JobGenerator;

    let generator = JobGenerator::from_str(&req.generator).ok_or_else(|| {
        AppError::Validation(format!(
            "Unknown procedural generator '{}': supported = wfc, lsystem",
            req.generator
        ))
    })?;

    let mut limits = GenerationLimits::default();
    if let Some(input) = req.limits {
        if let Some(v) = input.max_iterations { limits.max_iterations = v; }
        if let Some(v) = input.max_execution_ms { limits.max_execution_ms = v; }
        if let Some(v) = input.max_segment_count { limits.max_segment_count = v; }
        if let Some(v) = input.max_actor_count { limits.max_actor_count = v; }
        if let Some(v) = input.max_string_length { limits.max_string_length = v; }
    }

    state.procedural_jobs.evict_old().await;

    let job_id = state
        .procedural_jobs
        .submit(generator, req.params, req.seed, limits)
        .await
        .map_err(AppError::Validation)?;

    Ok(Json(success_response(json!({
        "job_id": job_id,
        "status": "queued"
    }))))
}

pub async fn procedural_job_status_route(
    State(state): State<AppState>,
    axum::extract::Path(job_id): axum::extract::Path<String>,
) -> Result<Json<Value>, AppError> {
    let record = state
        .procedural_jobs
        .status(&job_id)
        .await
        .ok_or_else(|| AppError::NotFound(format!("job '{job_id}' not found")))?;
    Ok(Json(success_response(serde_json::to_value(record).map_err(
        |e| AppError::Internal(format!("serialize job error: {e}")),
    )?)))
}

pub async fn procedural_job_cancel_route(
    State(state): State<AppState>,
    axum::extract::Path(job_id): axum::extract::Path<String>,
) -> Result<Json<Value>, AppError> {
    let record = state
        .procedural_jobs
        .cancel(&job_id)
        .await
        .map_err(AppError::Validation)?;
    Ok(Json(success_response(serde_json::to_value(record).map_err(
        |e| AppError::Internal(format!("serialize job error: {e}")),
    )?)))
}

pub async fn procedural_job_list_route(
    State(state): State<AppState>,
) -> Result<Json<Value>, AppError> {
    state.procedural_jobs.evict_old().await;
    let records = state.procedural_jobs.list().await;
    Ok(Json(success_response(json!({ "jobs": records }))))
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/procedural/create-mesh", post(create_procedural_mesh_route))
        .route("/procedural/sdf-mesh", post(sdf_mesh_route))
        .route("/procedural/superformula-mesh", post(superformula_mesh_route))
        .route("/procedural/lsystem-spline", post(lsystem_spline_route))
        .route("/procedural/wfc-grid", post(wfc_grid_route))
        .route("/procedural/jobs/submit", post(procedural_job_submit_route))
        .route("/procedural/jobs/{job_id}", get(procedural_job_status_route))
        .route("/procedural/jobs/{job_id}/cancel", post(procedural_job_cancel_route))
        .route("/procedural/jobs", get(procedural_job_list_route))
}
