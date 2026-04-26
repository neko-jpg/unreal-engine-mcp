use scene_syncd::db::SurrealSceneRepository;
use scene_syncd::domain::*;
use surrealdb::engine::any::Any;
use surrealdb::sql::Datetime;
use surrealdb::Surreal;

async fn setup_db() -> Surreal<Any> {
    let db: Surreal<Any> = Surreal::init();
    db.connect("memory").await.unwrap();
    db.use_ns("test").use_db("test").await.unwrap();
    db
}

fn make_object(scene: &str, mcp_id: &str) -> SceneObject {
    let now = Datetime::from(chrono::Utc::now());
    SceneObject {
        id: String::new(),
        scene: format!("scene:{scene}"),
        group: None,
        mcp_id: mcp_id.to_string(),
        desired_name: mcp_id.to_string(),
        unreal_actor_name: None,
        actor_type: "StaticMeshActor".to_string(),
        asset_ref: serde_json::json!({"path": "/Engine/BasicShapes/Cube.Cube"}),
        transform: Transform::default(),
        visual: serde_json::json!({}),
        physics: serde_json::json!({}),
        tags: vec!["test".to_string()],
        metadata: serde_json::json!({}),
        desired_hash: "fake_hash".to_string(),
        last_applied_hash: None,
        sync_status: "pending".to_string(),
        deleted: false,
        revision: 1,
        created_at: now.clone(),
        updated_at: now,
    }
}

#[tokio::test]
async fn ensure_schema_and_default_scene() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    let scene = repo.upsert_scene("test_scene", "Test", None).await.unwrap();
    assert_eq!(scene.name, "Test");
}

#[tokio::test]
async fn upsert_and_list_objects() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    let obj = make_object("main", "cube_01");
    repo.upsert_object(&obj).await.unwrap();

    let objects = repo.list_desired_objects("main", false, None, None).await.unwrap();
    assert_eq!(objects.len(), 1);
    assert_eq!(objects[0].mcp_id, "cube_01");
}

#[tokio::test]
async fn upsert_updates_existing_object() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    let mut obj = make_object("main", "cube_01");
    obj.transform.location.x = 100.0;
    obj.desired_hash = "hash_v1".to_string();
    repo.upsert_object(&obj).await.unwrap();

    let mut updated = make_object("main", "cube_01");
    updated.transform.location.x = 200.0;
    updated.desired_hash = "hash_v2".to_string();
    repo.upsert_object(&updated).await.unwrap();

    let objects = repo.list_desired_objects("main", false, None, None).await.unwrap();
    assert_eq!(objects.len(), 1);
    assert_eq!(objects[0].transform.location.x, 200.0);
    assert_eq!(objects[0].desired_hash, "hash_v2");
}

#[tokio::test]
async fn list_objects_excludes_deleted() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    repo.upsert_object(&make_object("main", "cube_01")).await.unwrap();
    repo.upsert_object(&make_object("main", "cube_02")).await.unwrap();

    repo.mark_object_deleted("main", "cube_01").await.unwrap();

    let active = repo.list_desired_objects("main", false, None, None).await.unwrap();
    assert_eq!(active.len(), 1);
    assert_eq!(active[0].mcp_id, "cube_02");

    let all = repo.list_desired_objects("main", true, None, None).await.unwrap();
    assert_eq!(all.len(), 2);
}

#[tokio::test]
async fn list_objects_group_id_filter() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    let mut obj_a = make_object("main", "cube_a");
    obj_a.group = Some("scene_group:wall_01".to_string());
    repo.upsert_object(&obj_a).await.unwrap();

    let mut obj_b = make_object("main", "cube_b");
    obj_b.group = Some("scene_group:pyramid_01".to_string());
    repo.upsert_object(&obj_b).await.unwrap();

    repo.upsert_object(&make_object("main", "cube_c")).await.unwrap();

    let wall_objs = repo
        .list_desired_objects("main", false, Some("wall_01"), None)
        .await
        .unwrap();
    assert_eq!(wall_objs.len(), 1);
    assert_eq!(wall_objs[0].mcp_id, "cube_a");
}

#[tokio::test]
async fn list_objects_limit() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    for i in 0..10 {
        repo.upsert_object(&make_object("main", &format!("cube_{i:02}")))
            .await
            .unwrap();
    }

    let limited = repo
        .list_desired_objects("main", false, None, Some(3))
        .await
        .unwrap();
    assert_eq!(limited.len(), 3);
}

#[tokio::test]
async fn mark_object_synced() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    repo.upsert_object(&make_object("main", "cube_01")).await.unwrap();

    repo.mark_object_synced("main", "cube_01", "hash_v1", Some("SM_Cube_01"))
        .await
        .unwrap();

    let objects = repo.list_desired_objects("main", false, None, None).await.unwrap();
    assert_eq!(objects[0].sync_status, "synced");
    assert_eq!(objects[0].last_applied_hash.as_deref(), Some("hash_v1"));
    assert_eq!(objects[0].unreal_actor_name.as_deref(), Some("SM_Cube_01"));
}

#[tokio::test]
async fn create_and_list_groups() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    repo.create_group("main", "wall", "my_wall", Some("create_wall".to_string()), serde_json::json!({"length": 5}), None)
        .await
        .unwrap();

    let groups = repo.list_groups("main", false).await.unwrap();
    assert_eq!(groups.len(), 1);
    assert_eq!(groups[0].name, "my_wall");
    assert_eq!(groups[0].kind, "wall");
}

#[tokio::test]
async fn create_and_list_snapshots() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    repo.upsert_object(&make_object("main", "cube_01")).await.unwrap();
    repo.upsert_object(&make_object("main", "cube_02")).await.unwrap();

    let snap = repo
        .create_snapshot("main", "initial", Some("first snapshot".to_string()))
        .await
        .unwrap();
    assert_eq!(snap.objects.len(), 2);

    let snapshots = repo.list_snapshots("main").await.unwrap();
    assert_eq!(snapshots.len(), 1);
}

#[tokio::test]
async fn restore_snapshot() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    repo.upsert_object(&make_object("main", "cube_01")).await.unwrap();
    repo.upsert_object(&make_object("main", "cube_02")).await.unwrap();

    let snap = repo
        .create_snapshot("main", "pre_change", None)
        .await
        .unwrap();

    // Add a third object after snapshot
    repo.upsert_object(&make_object("main", "cube_03")).await.unwrap();

    let summary = repo
        .restore_snapshot(&snap.id, "replace_desired")
        .await
        .unwrap();

    assert_eq!(summary["restored_objects"], 2);
    assert_eq!(summary["tombstoned_objects"], 1);

    // cube_03 should be deleted, cube_01 and cube_02 restored
    let active = repo.list_desired_objects("main", false, None, None).await.unwrap();
    let active_ids: Vec<&str> = active.iter().map(|o| o.mcp_id.as_str()).collect();
    assert!(active_ids.contains(&"cube_01"));
    assert!(active_ids.contains(&"cube_02"));
    assert!(!active_ids.contains(&"cube_03"));
}

#[tokio::test]
async fn record_operation_and_sync_run() {
    let db = setup_db().await;
    let repo = SurrealSceneRepository::new(db);
    repo.ensure_schema().await.unwrap();
    repo.ensure_default_scene().await.unwrap();

    repo.create_sync_run("run_001", "main", "apply_safe", "running")
        .await
        .unwrap();

    repo.record_operation("run_001", "main", "cube_01", "create", "ok", "new object")
        .await
        .unwrap();

    let summary = scene_syncd::sync::applier::SyncApplySummary {
        total: 1,
        succeeded: 1,
        failed: 0,
        skipped: 0,
        creates: 1,
        update_transforms: 0,
        update_visuals: 0,
        deletes: 0,
        noops: 0,
    };
    repo.finish_sync_run("run_001", &summary).await.unwrap();
}