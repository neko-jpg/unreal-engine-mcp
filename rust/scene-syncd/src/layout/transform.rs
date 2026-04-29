use crate::domain::{Rotator, Vec3};
use crate::layout::entity_resolver::compute_location;
use crate::layout::kind_registry::{KindRegistry, LAYER_GAP};
use crate::layout::span::Span;

pub fn compute_rotation(properties: &serde_json::Value, span: Option<&Span>) -> Rotator {
    if let Some(rot) = properties.get("rotation") {
        return Rotator {
            pitch: rot.get("pitch").and_then(|v| v.as_f64()).unwrap_or(0.0),
            yaw: rot.get("yaw").and_then(|v| v.as_f64()).unwrap_or(0.0),
            roll: rot.get("roll").and_then(|v| v.as_f64()).unwrap_or(0.0),
        };
    }
    if let Some(span) = span {
        return Rotator {
            pitch: 0.0,
            yaw: span.yaw_degrees(),
            roll: 0.0,
        };
    }
    Rotator {
        pitch: 0.0,
        yaw: 0.0,
        roll: 0.0,
    }
}

pub fn compute_scale(kind: &str, properties: &serde_json::Value, span: Option<&Span>) -> Vec3 {
    match kind {
        "ground" | "moat" => Vec3 {
            x: properties
                .get("width")
                .and_then(|v| v.as_f64())
                .unwrap_or(10000.0)
                / 100.0,
            y: properties
                .get("depth")
                .and_then(|v| v.as_f64())
                .unwrap_or(10000.0)
                / 100.0,
            z: 1.0,
        },
        "curtain_wall" => {
            let height = properties
                .get("height")
                .and_then(|v| v.as_f64())
                .unwrap_or(400.0);
            let thickness = properties
                .get("thickness")
                .and_then(|v| v.as_f64())
                .unwrap_or(50.0);
            if let Some(span) = span {
                Vec3 {
                    x: span.length() / 100.0,
                    y: thickness / 100.0,
                    z: height / 100.0,
                }
            } else {
                Vec3 {
                    x: 10.0,
                    y: thickness / 100.0,
                    z: height / 100.0,
                }
            }
        }
        "bridge" => {
            let width = properties
                .get("width")
                .and_then(|v| v.as_f64())
                .unwrap_or(400.0);
            let height = properties
                .get("height")
                .and_then(|v| v.as_f64())
                .unwrap_or(20.0);
            if let Some(span) = span {
                Vec3 {
                    x: span.length() / 100.0,
                    y: width / 100.0,
                    z: height / 100.0,
                }
            } else {
                Vec3 {
                    x: 10.0,
                    y: width / 100.0,
                    z: height / 100.0,
                }
            }
        }
        _ => {
            if let Some(size) = extract_vec3(properties, "size") {
                size
            } else if let (Some(w), Some(h), Some(d)) = (
                properties.get("width").and_then(|v| v.as_f64()),
                properties.get("height").and_then(|v| v.as_f64()),
                properties.get("depth").and_then(|v| v.as_f64()),
            ) {
                Vec3 {
                    x: w / 100.0,
                    y: d / 100.0,
                    z: h / 100.0,
                }
            } else {
                Vec3 {
                    x: 1.0,
                    y: 1.0,
                    z: 1.0,
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::layout::kind_registry::KindRegistry;

    #[test]
    fn ground_layer_is_below_zero() {
        let registry = KindRegistry::default();
        let t = make_transform("ground", &serde_json::json!({}), None, &registry);
        assert_eq!(t.location.z, -100.0);
    }

    #[test]
    fn moat_layer_is_below_ground() {
        let registry = KindRegistry::default();
        let t = make_transform("moat", &serde_json::json!({}), None, &registry);
        assert_eq!(t.location.z, -200.0);
    }

    #[test]
    fn bridge_layer_is_above_ground() {
        let registry = KindRegistry::default();
        let t = make_transform("bridge", &serde_json::json!({}), None, &registry);
        assert_eq!(t.location.z, 100.0);
    }

    #[test]
    fn wall_layer_zero_with_bottom_grounding() {
        let registry = KindRegistry::default();
        let props = serde_json::json!({"height": 400.0, "thickness": 50.0});
        let t = make_transform("curtain_wall", &props, None, &registry);
        // layer 0 → Z=0, bottom grounding adds scale.z * 100 / 2 = 4.0 * 50 = 200
        assert_eq!(t.location.z, 200.0);
    }

    #[test]
    fn explicit_z_overrides_layer() {
        let registry = KindRegistry::default();
        let props = serde_json::json!({"location": {"x": 0.0, "y": 0.0, "z": 500.0}});
        let t = make_transform("ground", &props, None, &registry);
        // explicit Z=500 should NOT get layer offset, and ground is not bottom-grounded
        assert_eq!(t.location.z, 500.0);
    }

    #[test]
    fn keep_bottom_grounding_raises_z() {
        let registry = KindRegistry::default();
        let props = serde_json::json!({"size": {"x": 8.0, "y": 8.0, "z": 20.0}});
        let t = make_transform("keep", &props, None, &registry);
        // layer 0 → Z=0, bottom grounding: scale.z=20, offset = 20*100/2 = 1000
        assert_eq!(t.location.z, 1000.0);
    }

    #[test]
    fn moat_and_ground_different_z_no_z_fighting() {
        let registry = KindRegistry::default();
        let moat = make_transform("moat", &serde_json::json!({}), None, &registry);
        let ground = make_transform("ground", &serde_json::json!({}), None, &registry);
        assert_ne!(moat.location.z, ground.location.z);
        assert!(moat.location.z < ground.location.z);
    }
}

fn extract_vec3(value: &serde_json::Value, field: &str) -> Option<Vec3> {
    let obj = value.get(field)?;
    Some(Vec3 {
        x: obj.get("x")?.as_f64()?,
        y: obj.get("y")?.as_f64()?,
        z: obj.get("z")?.as_f64()?,
    })
}

/// Kinds whose Unreal actor origin is at the center; offset Z up by half the
/// height so the bottom face sits on the ground plane.
const BOTTOM_GROUNDED_KINDS: &[&str] = &["curtain_wall", "tower", "keep", "gatehouse"];

pub fn make_transform(
    kind: &str,
    properties: &serde_json::Value,
    span: Option<&Span>,
    registry: &KindRegistry,
) -> crate::domain::Transform {
    let mut location = compute_location(kind, properties, span);
    let scale = compute_scale(kind, properties, span);

    // If location.z was not explicitly set, apply layer-based Z offset.
    let has_explicit_z = properties
        .get("location")
        .and_then(|l| l.get("z"))
        .and_then(|z| z.as_f64())
        .is_some();

    if !has_explicit_z {
        let layer = registry.get(kind).map(|s| s.layer).unwrap_or(0);
        location.z = layer as f64 * LAYER_GAP;
    }

    // Center-origin kinds: raise by half the height so the bottom face sits
    // on the ground plane.
    if BOTTOM_GROUNDED_KINDS.contains(&kind) {
        location.z += scale.z * 100.0 / 2.0;
    }

    crate::domain::Transform {
        location,
        rotation: compute_rotation(properties, span),
        scale,
    }
}
