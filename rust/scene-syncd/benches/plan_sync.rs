use criterion::{black_box, criterion_group, criterion_main, Criterion};
use scene_syncd::compiler::context::CompilerContext;
use scene_syncd::compiler::passes::diff::DiffPlanningPass;
use scene_syncd::compiler::passes::Pass;
use scene_syncd::domain::{Rotator, SceneObject, Transform, Vec3};
use serde_json::json;

fn make_object(mcp_id: &str, x: f64) -> SceneObject {
    SceneObject {
        id: String::new(),
        scene: "scene:bench".to_string(),
        group: None,
        mcp_id: mcp_id.to_string(),
        desired_name: mcp_id.to_string(),
        unreal_actor_name: None,
        actor_type: "StaticMeshActor".to_string(),
        asset_ref: json!({}),
        transform: Transform {
            location: Vec3 { x, y: 0.0, z: 0.0 },
            rotation: Rotator {
                pitch: 0.0,
                yaw: 0.0,
                roll: 0.0,
            },
            scale: Vec3 {
                x: 1.0,
                y: 1.0,
                z: 1.0,
            },
        },
        visual: json!({}),
        physics: json!({}),
        tags: vec!["layout_kind:keep".to_string()],
        metadata: json!({}),
        desired_hash: String::new(),
        last_applied_hash: None,
        sync_status: "pending".to_string(),
        deleted: false,
        revision: 1,
        created_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
        updated_at: surrealdb::sql::Datetime::from(chrono::Utc::now()),
    }
}

fn bench_plan_sync(c: &mut Criterion) {
    for size in [10, 50, 100, 500] {
        let desired: Vec<SceneObject> = (0..size)
            .map(|i| make_object(&format!("obj_{}", i), i as f64 * 100.0))
            .collect();
        // Actual is identical to desired → all NoOps
        let actual = desired.clone();

        c.bench_function(&format!("plan_sync_{}", size), |b| {
            b.iter(|| {
                let mut ctx = CompilerContext::new("bench".to_string());
                ctx.objects = desired.clone();
                let pass = DiffPlanningPass::with_actual(actual.clone());
                black_box(pass.run(&mut ctx).unwrap());
            })
        });
    }
}

criterion_group!(benches, bench_plan_sync);
criterion_main!(benches);
