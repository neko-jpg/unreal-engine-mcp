use criterion::{black_box, criterion_group, criterion_main, Criterion};
use scene_syncd::compiler::context::CompilerContext;
use scene_syncd::compiler::passes::lower_geometry::GeometryLoweringPass;
use scene_syncd::compiler::passes::normalize::NormalizePass;
use scene_syncd::compiler::passes::validate::ValidatePass;
use scene_syncd::compiler::pipeline::CompilerPipeline;
use scene_syncd::domain::{Rotator, SceneObject, Transform, Vec3};
use serde_json::json;

fn make_object(mcp_id: &str, x: f64, y: f64, kind: &str) -> SceneObject {
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
            location: Vec3 { x, y, z: 0.0 },
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
        tags: vec![format!("layout_kind:{}", kind)],
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

fn build_context(count: usize) -> CompilerContext {
    let mut ctx = CompilerContext::new("bench".to_string());
    let kinds = ["keep", "tower", "curtain_wall", "gatehouse", "ground"];
    ctx.objects = (0..count)
        .map(|i| {
            let kind = kinds[i % kinds.len()];
            let x = (i % 100) as f64 * 500.0;
            let y = (i / 100) as f64 * 500.0;
            make_object(&format!("obj_{}", i), x, y, kind)
        })
        .collect();
    ctx
}

fn bench_pipeline(c: &mut Criterion) {
    for size in [10, 50, 100, 500] {
        c.bench_function(&format!("pipeline_{}", size), |b| {
            b.iter(|| {
                // Re-clone context each iteration so passes don't accumulate state
                let mut fresh = CompilerPipeline::new(
                    build_context(size),
                    vec![
                        Box::new(GeometryLoweringPass),
                        Box::new(NormalizePass),
                        Box::new(ValidatePass::default()),
                    ],
                );
                black_box(fresh.run("preview").unwrap());
            })
        });
    }
}

criterion_group!(benches, bench_pipeline);
criterion_main!(benches);
