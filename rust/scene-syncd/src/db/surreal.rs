use crate::domain::*;
use crate::error::AppError;
use surrealdb::engine::any::Any;
use surrealdb::sql::Datetime;
use surrealdb::Surreal;

/// Build a scene_object record key, stripping any `scene:` prefix from the scene id.
pub fn scene_object_record_key(scene_id: &str, mcp_id: &str) -> String {
    format!("{}:{}", scene_id.replace("scene:", ""), mcp_id)
}

#[derive(Debug, Clone)]
pub struct SurrealSceneRepository {
    db: Surreal<Any>,
}

impl SurrealSceneRepository {
    pub fn new(db: Surreal<Any>) -> Self {
        Self { db }
    }

    pub async fn ensure_schema(&self) -> Result<(), AppError> {
        let queries = [
            "DEFINE TABLE scene SCHEMAFULL;",
            "DEFINE FIELD name ON TABLE scene TYPE string;",
            "DEFINE FIELD description ON TABLE scene TYPE option<string>;",
            "DEFINE FIELD status ON TABLE scene TYPE string DEFAULT \"active\";",
            "DEFINE FIELD active_revision ON TABLE scene TYPE int DEFAULT 1;",
            "DEFINE FIELD unreal_project_path ON TABLE scene TYPE option<string>;",
            "DEFINE FIELD unreal_level_name ON TABLE scene TYPE option<string>;",
            "DEFINE FIELD created_at ON TABLE scene TYPE datetime DEFAULT time::now();",
            "DEFINE FIELD updated_at ON TABLE scene TYPE datetime DEFAULT time::now();",

            "DEFINE TABLE scene_group SCHEMAFULL;",
            "DEFINE FIELD OVERWRITE scene ON TABLE scene_group TYPE string;",
            "DEFINE FIELD kind ON TABLE scene_group TYPE string;",
            "DEFINE FIELD tool_name ON TABLE scene_group TYPE option<string>;",
            "DEFINE FIELD name ON TABLE scene_group TYPE string;",
            "DEFINE FIELD params ON TABLE scene_group TYPE object DEFAULT {};",
            "DEFINE FIELD seed ON TABLE scene_group TYPE option<string>;",
            "DEFINE FIELD revision ON TABLE scene_group TYPE int DEFAULT 1;",
            "DEFINE FIELD deleted ON TABLE scene_group TYPE bool DEFAULT false;",
            "DEFINE FIELD created_at ON TABLE scene_group TYPE datetime DEFAULT time::now();",
            "DEFINE FIELD updated_at ON TABLE scene_group TYPE datetime DEFAULT time::now();",

            "DEFINE TABLE scene_object SCHEMAFULL;",
            "DEFINE FIELD OVERWRITE scene ON TABLE scene_object TYPE string;",
            "DEFINE FIELD OVERWRITE group ON TABLE scene_object TYPE option<string>;",
            "DEFINE FIELD mcp_id ON TABLE scene_object TYPE string;",
            "DEFINE FIELD desired_name ON TABLE scene_object TYPE string;",
            "DEFINE FIELD unreal_actor_name ON TABLE scene_object TYPE option<string>;",
            "DEFINE FIELD actor_type ON TABLE scene_object TYPE string;",
            "DEFINE FIELD asset_ref ON TABLE scene_object TYPE object DEFAULT {};",
            "DEFINE FIELD asset_ref.path ON TABLE scene_object TYPE option<string>;",
            "DEFINE FIELD transform ON TABLE scene_object TYPE object;",
            "DEFINE FIELD transform.location ON TABLE scene_object TYPE object;",
            "DEFINE FIELD transform.location.x ON TABLE scene_object TYPE number;",
            "DEFINE FIELD transform.location.y ON TABLE scene_object TYPE number;",
            "DEFINE FIELD transform.location.z ON TABLE scene_object TYPE number;",
            "DEFINE FIELD transform.rotation ON TABLE scene_object TYPE object;",
            "DEFINE FIELD transform.rotation.pitch ON TABLE scene_object TYPE number;",
            "DEFINE FIELD transform.rotation.yaw ON TABLE scene_object TYPE number;",
            "DEFINE FIELD transform.rotation.roll ON TABLE scene_object TYPE number;",
            "DEFINE FIELD transform.scale ON TABLE scene_object TYPE object;",
            "DEFINE FIELD transform.scale.x ON TABLE scene_object TYPE number;",
            "DEFINE FIELD transform.scale.y ON TABLE scene_object TYPE number;",
            "DEFINE FIELD transform.scale.z ON TABLE scene_object TYPE number;",
            "DEFINE FIELD visual ON TABLE scene_object TYPE object DEFAULT {};",
            "DEFINE FIELD physics ON TABLE scene_object TYPE object DEFAULT {};",
            "DEFINE FIELD tags ON TABLE scene_object TYPE array DEFAULT [];",
            "DEFINE FIELD tags.* ON TABLE scene_object TYPE string;",
            "DEFINE FIELD metadata ON TABLE scene_object TYPE object DEFAULT {};",
            "DEFINE FIELD desired_hash ON TABLE scene_object TYPE string;",
            "DEFINE FIELD last_applied_hash ON TABLE scene_object TYPE option<string>;",
            "DEFINE FIELD sync_status ON TABLE scene_object TYPE string DEFAULT \"pending\";",
            "DEFINE FIELD deleted ON TABLE scene_object TYPE bool DEFAULT false;",
            "DEFINE FIELD revision ON TABLE scene_object TYPE int DEFAULT 1;",
            "DEFINE FIELD created_at ON TABLE scene_object TYPE datetime DEFAULT time::now();",
            "DEFINE FIELD updated_at ON TABLE scene_object TYPE datetime DEFAULT time::now();",

            "DEFINE INDEX scene_object_scene_mcp_id ON TABLE scene_object COLUMNS scene, mcp_id UNIQUE;",
            "DEFINE INDEX scene_object_scene_group ON TABLE scene_object COLUMNS scene, group;",
            "DEFINE INDEX scene_object_sync_status ON TABLE scene_object COLUMNS scene, sync_status;",

            "DEFINE TABLE scene_snapshot SCHEMAFULL;",
            "DEFINE FIELD OVERWRITE scene ON TABLE scene_snapshot TYPE string;",
            "DEFINE FIELD name ON TABLE scene_snapshot TYPE string;",
            "DEFINE FIELD description ON TABLE scene_snapshot TYPE option<string>;",
            "DEFINE FIELD revision ON TABLE scene_snapshot TYPE int;",
            "DEFINE FIELD groups ON TABLE scene_snapshot TYPE array;",
            "DEFINE FIELD groups.* ON TABLE scene_snapshot FLEXIBLE TYPE object;",
            "DEFINE FIELD objects ON TABLE scene_snapshot TYPE array;",
            "DEFINE FIELD objects.* ON TABLE scene_snapshot FLEXIBLE TYPE object;",
            "DEFINE FIELD created_at ON TABLE scene_snapshot TYPE datetime DEFAULT time::now();",

            "DEFINE TABLE sync_run SCHEMAFULL;",
            "DEFINE FIELD OVERWRITE scene ON TABLE sync_run TYPE string;",
            "DEFINE FIELD mode ON TABLE sync_run TYPE string;",
            "DEFINE FIELD status ON TABLE sync_run TYPE string;",
            "DEFINE FIELD summary ON TABLE sync_run TYPE object DEFAULT {};",
            "DEFINE FIELD started_at ON TABLE sync_run TYPE datetime DEFAULT time::now();",
            "DEFINE FIELD ended_at ON TABLE sync_run TYPE option<datetime>;",
            "DEFINE FIELD error ON TABLE sync_run TYPE option<string>;",

            "DEFINE TABLE scene_operation SCHEMAFULL;",
            "DEFINE FIELD OVERWRITE scene ON TABLE scene_operation TYPE string;",
            "DEFINE FIELD OVERWRITE sync_run ON TABLE scene_operation TYPE string;",
            "DEFINE FIELD OVERWRITE object ON TABLE scene_operation TYPE option<string>;",
            "DEFINE FIELD mcp_id ON TABLE scene_operation TYPE option<string>;",
            "DEFINE FIELD action ON TABLE scene_operation TYPE string;",
            "DEFINE FIELD reason ON TABLE scene_operation TYPE string;",
            "DEFINE FIELD desired ON TABLE scene_operation TYPE option<object>;",
            "DEFINE FIELD actual ON TABLE scene_operation TYPE option<object>;",
            "DEFINE FIELD status ON TABLE scene_operation TYPE string;",
            "DEFINE FIELD attempts ON TABLE scene_operation TYPE int DEFAULT 1;",
            "DEFINE FIELD error ON TABLE scene_operation TYPE option<string>;",
            "DEFINE FIELD created_at ON TABLE scene_operation TYPE datetime DEFAULT time::now();",

            "DEFINE TABLE actor_observation SCHEMAFULL;",
            "DEFINE FIELD OVERWRITE scene ON TABLE actor_observation TYPE string;",
            "DEFINE FIELD OVERWRITE sync_run ON TABLE actor_observation TYPE option<string>;",
            "DEFINE FIELD mcp_id ON TABLE actor_observation TYPE option<string>;",
            "DEFINE FIELD unreal_actor_name ON TABLE actor_observation TYPE string;",
            "DEFINE FIELD class_name ON TABLE actor_observation TYPE string;",
            "DEFINE FIELD transform ON TABLE actor_observation TYPE object;",
            "DEFINE FIELD tags ON TABLE actor_observation TYPE array;",
            "DEFINE FIELD raw ON TABLE actor_observation TYPE option<object>;",
            "DEFINE FIELD observed_at ON TABLE actor_observation TYPE datetime DEFAULT time::now();",
        ];

        for query in &queries {
            self.db
                .query(*query)
                .await
                .map_err(|e| AppError::Database(format!("schema migration error: {e}")))?;
        }

        tracing::info!("Schema migrations applied");
        Ok(())
    }

    pub async fn ensure_default_scene(&self) -> Result<(), AppError> {
        let now = Datetime::from(chrono::Utc::now());

        let existing: Option<Scene> = self
            .db
            .select(("scene", "main"))
            .await
            .map_err(|e| AppError::Database(format!("select scene:main error: {e}")))?;

        if existing.is_none() {
            let scene = Scene {
                id: "scene:main".to_string(),
                name: "Main Scene".to_string(),
                description: Some("Default managed scene".to_string()),
                status: "active".to_string(),
                active_revision: 1,
                unreal_project_path: None,
                unreal_level_name: None,
                created_at: now.clone(),
                updated_at: now,
            };

            let _: Option<Scene> = self
                .db
                .create(("scene", "main"))
                .content(scene)
                .await
                .map_err(|e| AppError::Database(format!("create scene:main error: {e}")))?;

            tracing::info!("Created default scene:main");
        }

        Ok(())
    }

    pub async fn create_scene(
        &self,
        scene_id: &str,
        name: &str,
        description: Option<String>,
    ) -> Result<Scene, AppError> {
        let now = Datetime::from(chrono::Utc::now());
        let scene = Scene {
            id: format!("scene:{scene_id}"),
            name: name.to_string(),
            description,
            status: "active".to_string(),
            active_revision: 1,
            unreal_project_path: None,
            unreal_level_name: None,
            created_at: now.clone(),
            updated_at: now,
        };

        let created: Option<Scene> = self
            .db
            .create(("scene", scene_id))
            .content(scene)
            .await
            .map_err(|e| AppError::Database(format!("create scene error: {e}")))?;

        created.ok_or_else(|| AppError::Internal("failed to create scene".to_string()))
    }

    pub async fn upsert_scene(
        &self,
        scene_id: &str,
        name: &str,
        description: Option<String>,
    ) -> Result<Scene, AppError> {
        let now = Datetime::from(chrono::Utc::now());

        let existing: Option<Scene> = self
            .db
            .select(("scene", scene_id))
            .await
            .map_err(|e| AppError::Database(format!("select scene error: {e}")))?;

        if let Some(mut scene) = existing {
            scene.name = name.to_string();
            if description.is_some() {
                scene.description = description;
            }
            scene.updated_at = now;
            let updated: Option<Scene> =
                self.db
                    .update(("scene", scene_id))
                    .content(scene)
                    .await
                    .map_err(|e| AppError::Database(format!("update scene error: {e}")))?;
            updated.ok_or_else(|| AppError::Internal("failed to update scene".to_string()))
        } else {
            self.create_scene(scene_id, name, description).await
        }
    }

    pub async fn upsert_object(&self, obj: &SceneObject) -> Result<SceneObject, AppError> {
        let record_key = scene_object_record_key(&obj.scene, &obj.mcp_id);
        let key_owned = record_key.clone();
        let scene_id = obj.scene.trim_start_matches("scene:");

        let updated: Option<SceneObject> = self
            .db
            .query(
                "IF type::thing($table, $key).id THEN \
                 UPDATE type::thing($table, $key) SET \
                    scene = $scene, \
                    group = $group, \
                    mcp_id = $mcp_id, \
                    desired_name = $desired_name, \
                    actor_type = $actor_type, \
                    asset_ref = $asset_ref, \
                    transform = $transform, \
                    visual = $visual, \
                    physics = $physics, \
                    tags = $tags, \
                    metadata = $metadata, \
                    desired_hash = $desired_hash, \
                    deleted = $deleted, \
                    sync_status = 'pending', \
                    updated_at = time::now() \
                 ELSE \
                 CREATE type::thing($table, $key) CONTENT { \
                    scene: $scene, \
                    group: $group, \
                    mcp_id: $mcp_id, \
                    desired_name: $desired_name, \
                    actor_type: $actor_type, \
                    asset_ref: $asset_ref, \
                    transform: $transform, \
                    visual: $visual, \
                    physics: $physics, \
                    tags: $tags, \
                    metadata: $metadata, \
                    desired_hash: $desired_hash, \
                    deleted: $deleted, \
                    sync_status: 'pending', \
                    created_at: time::now(), \
                    updated_at: time::now() \
                 } \
                 END"
            )
            .bind(("table", "scene_object"))
            .bind(("key", key_owned))
            .bind(("scene", format!("scene:{scene_id}")))
            .bind(("group", obj.group.clone()))
            .bind(("mcp_id", obj.mcp_id.clone()))
            .bind(("desired_name", obj.desired_name.clone()))
            .bind(("actor_type", obj.actor_type.clone()))
            .bind(("asset_ref", obj.asset_ref.clone()))
            .bind(("transform", obj.transform.clone()))
            .bind(("visual", obj.visual.clone()))
            .bind(("physics", obj.physics.clone()))
            .bind(("tags", obj.tags.clone()))
            .bind(("metadata", obj.metadata.clone()))
            .bind(("desired_hash", obj.desired_hash.clone()))
            .bind(("deleted", obj.deleted))
            .await
            .map_err(|e| AppError::Database(format!("upsert object error: {e}")))?
            .take(0)
            .map_err(|e| AppError::Database(format!("upsert object parse error: {e}")))?;

        updated.ok_or_else(|| AppError::Internal("failed to upsert object".to_string()))
    }

    pub async fn list_desired_objects(
        &self,
        scene: &str,
        include_deleted: bool,
        group_id: Option<&str>,
        limit: Option<usize>,
    ) -> Result<Vec<SceneObject>, AppError> {
        let mut conditions = vec![format!("scene = $scene")];
        if !include_deleted {
            conditions.push("deleted = false".to_string());
        }
        if group_id.is_some() {
            conditions.push("group = $group".to_string());
        }
        let where_clause = conditions.join(" AND ");
        let mut query = format!("SELECT * FROM scene_object WHERE {where_clause}");
        if let Some(n) = limit {
            query.push_str(&format!(" LIMIT {n}"));
        }

        let mut q = self.db.query(query).bind(("scene", format!("scene:{scene}")));
        if let Some(gid) = group_id {
            q = q.bind(("group", format!("scene_group:{gid}")));
        }

        let objects: Vec<SceneObject> = q
            .await
            .map_err(|e| AppError::Database(format!("list objects error: {e}")))?
            .take(0)
            .map_err(|e| AppError::Database(format!("list objects parse error: {e}")))?;

        Ok(objects)
    }

    pub async fn mark_object_deleted(&self, scene: &str, mcp_id: &str) -> Result<(), AppError> {
        let record_key = scene_object_record_key(scene, mcp_id);

        let updated: Option<SceneObject> = self
            .db
            .update(("scene_object", record_key.as_str()))
            .merge(serde_json::json!({
                "deleted": true,
                "sync_status": "pending",
            }))
            .await
            .map_err(|e| AppError::Database(format!("mark deleted error: {e}")))?;

        if updated.is_none() {
            return Err(AppError::NotFound(format!(
                "object {mcp_id} not found in scene {scene}"
            )));
        }

        Ok(())
    }

    pub async fn create_group(
        &self,
        scene_id: &str,
        kind: &str,
        name: &str,
        tool_name: Option<String>,
        params: serde_json::Value,
        seed: Option<String>,
    ) -> Result<SceneGroup, AppError> {
        let now = Datetime::from(chrono::Utc::now());
        let record_key = format!("{}:{}", scene_id, name);
        let group = SceneGroup {
            id: format!("scene_group:{record_key}"),
            scene: format!("scene:{scene_id}"),
            kind: kind.to_string(),
            tool_name,
            name: name.to_string(),
            params,
            seed,
            revision: 1,
            deleted: false,
            created_at: now.clone(),
            updated_at: now,
        };

        let created: Option<SceneGroup> = self
            .db
            .create(("scene_group", record_key.as_str()))
            .content(group)
            .await
            .map_err(|e| AppError::Database(format!("create group error: {e}")))?;

        created.ok_or_else(|| AppError::Internal("failed to create group".to_string()))
    }

    pub async fn list_groups(
        &self,
        scene_id: &str,
        include_deleted: bool,
    ) -> Result<Vec<SceneGroup>, AppError> {
        let query = if include_deleted {
            "SELECT * FROM scene_group WHERE scene = $scene"
        } else {
            "SELECT * FROM scene_group WHERE scene = $scene AND deleted = false"
        };

        let groups: Vec<SceneGroup> = self
            .db
            .query(query)
            .bind(("scene", format!("scene:{scene_id}")))
            .await
            .map_err(|e| AppError::Database(format!("list groups error: {e}")))?
            .take(0)
            .map_err(|e| AppError::Database(format!("list groups parse error: {e}")))?;

        Ok(groups)
    }

    pub async fn create_snapshot(
        &self,
        scene_id: &str,
        name: &str,
        description: Option<String>,
    ) -> Result<SceneSnapshot, AppError> {
        let now = Datetime::from(chrono::Utc::now());
        let snapshot_key = format!("{}_{}", scene_id, chrono::Utc::now().format("%Y%m%d%H%M%S"));
        let objects = self.list_desired_objects(scene_id, false, None, None).await?;
        let snapshot = SceneSnapshot {
            id: format!("scene_snapshot:{snapshot_key}"),
            scene: format!("scene:{scene_id}"),
            name: name.to_string(),
            description,
            revision: 1,
            groups: Vec::new(),
            objects,
            created_at: now,
        };

        let created: Option<SceneSnapshot> = self
            .db
            .create(("scene_snapshot", snapshot_key.as_str()))
            .content(snapshot.clone())
            .await
            .map_err(|e| AppError::Database(format!("create snapshot error: {e}")))?;

        created
            .map(|_| snapshot)
            .ok_or_else(|| AppError::Internal("failed to create snapshot".to_string()))
    }

    pub async fn list_snapshots(
        &self,
        scene_id: &str,
    ) -> Result<Vec<SceneSnapshot>, AppError> {
        let snapshots: Vec<SceneSnapshot> = self
            .db
            .query("SELECT * FROM scene_snapshot WHERE scene = $scene")
            .bind(("scene", format!("scene:{scene_id}")))
            .await
            .map_err(|e| AppError::Database(format!("list snapshots error: {e}")))?
            .take(0)
            .map_err(|e| AppError::Database(format!("list snapshots parse error: {e}")))?;

        Ok(snapshots)
    }

    pub async fn restore_snapshot(
        &self,
        snapshot_id: &str,
        restore_mode: &str,
    ) -> Result<serde_json::Value, AppError> {
        if restore_mode != "replace_desired" {
            return Err(AppError::Validation(format!(
                "unsupported restore_mode {restore_mode}; expected replace_desired"
            )));
        }

        let snapshot_key = snapshot_id
            .strip_prefix("scene_snapshot:")
            .unwrap_or(snapshot_id);
        let snapshot: Option<SceneSnapshot> = self
            .db
            .select(("scene_snapshot", snapshot_key))
            .await
            .map_err(|e| AppError::Database(format!("select snapshot error: {e}")))?;
        let snapshot = snapshot
            .ok_or_else(|| AppError::NotFound(format!("snapshot {snapshot_id} not found")))?;

        let scene_id = snapshot
            .scene
            .strip_prefix("scene:")
            .unwrap_or(&snapshot.scene);
        let snapshot_ids: std::collections::HashSet<String> = snapshot
            .objects
            .iter()
            .map(|obj| obj.mcp_id.clone())
            .collect();

        let existing = self.list_desired_objects(scene_id, false, None, None).await?;
        let mut tombstoned = 0usize;
        for obj in existing {
            if !snapshot_ids.contains(&obj.mcp_id) {
                self.mark_object_deleted(scene_id, &obj.mcp_id).await?;
                tombstoned += 1;
            }
        }

        let mut restored = 0usize;
        for mut obj in snapshot.objects {
            obj.scene = snapshot.scene.clone();
            obj.deleted = false;
            obj.sync_status = "pending".to_string();
            obj.last_applied_hash = None;
            self.upsert_object(&obj).await?;
            restored += 1;
        }

        Ok(serde_json::json!({
            "snapshot_id": format!("scene_snapshot:{snapshot_key}"),
            "scene_id": scene_id,
            "restore_mode": restore_mode,
            "restored_objects": restored,
            "tombstoned_objects": tombstoned,
        }))
    }

    pub async fn create_sync_run(
        &self,
        run_id: &str,
        scene_id: &str,
        mode: &str,
        status: &str,
    ) -> Result<(), AppError> {
        self.db
            .query(
                "CREATE type::thing($id) SET scene = $scene, mode = $mode, status = $status, summary = {}, started_at = time::now(), ended_at = NULL, error = NULL"
            )
            .bind(("id", format!("sync_run:{run_id}")))
            .bind(("scene", format!("scene:{scene_id}")))
            .bind(("mode", mode.to_string()))
            .bind(("status", status.to_string()))
            .await
            .map_err(|e| AppError::Database(format!("create sync_run error: {e}")))?;

        Ok(())
    }

    pub async fn finish_sync_run(
        &self,
        run_id: &str,
        summary: &crate::sync::applier::SyncApplySummary,
    ) -> Result<(), AppError> {
        let now = Datetime::from(chrono::Utc::now());

        let summary_json = serde_json::to_value(summary)
            .map_err(|e| AppError::Internal(format!("serialize summary error: {e}")))?;

        let status = if summary.failed > 0 {
            "completed_with_errors"
        } else {
            "completed"
        };

        self.db
            .query(
                "UPDATE type::thing($id) SET status = $status, summary = $summary, ended_at = $now",
            )
            .bind(("id", format!("sync_run:{run_id}")))
            .bind(("status", status.to_string()))
            .bind(("summary", summary_json))
            .bind(("now", now))
            .await
            .map_err(|e| AppError::Database(format!("finish sync_run error: {e}")))?;

        Ok(())
    }

    pub async fn mark_object_synced(
        &self,
        scene_id: &str,
        mcp_id: &str,
        desired_hash: &str,
        unreal_actor_name: Option<&str>,
    ) -> Result<(), AppError> {
        let record_key = scene_object_record_key(scene_id, mcp_id);

        let updated: Option<SceneObject> = if let Some(name) = unreal_actor_name {
            self.db
                .update(("scene_object", record_key.as_str()))
                .merge(serde_json::json!({
                    "sync_status": "synced",
                    "last_applied_hash": desired_hash,
                    "unreal_actor_name": name,
                }))
                .await
                .map_err(|e| AppError::Database(format!("mark synced error: {e}")))?
        } else {
            self.db
                .update(("scene_object", record_key.as_str()))
                .merge(serde_json::json!({
                    "sync_status": "synced",
                    "last_applied_hash": desired_hash,
                }))
                .await
                .map_err(|e| AppError::Database(format!("mark synced error: {e}")))?
        };

        if updated.is_none() {
            return Err(AppError::NotFound(format!(
                "object {mcp_id} not found in scene {scene_id}"
            )));
        }

        Ok(())
    }

    pub async fn mark_object_deleted_applied(
        &self,
        scene_id: &str,
        mcp_id: &str,
    ) -> Result<(), AppError> {
        let record_key = scene_object_record_key(scene_id, mcp_id);

        let updated: Option<SceneObject> = self
            .db
            .update(("scene_object", record_key.as_str()))
            .merge(serde_json::json!({
                "sync_status": "synced",
            }))
            .await
            .map_err(|e| AppError::Database(format!("mark deleted applied error: {e}")))?;

        if updated.is_none() {
            return Err(AppError::NotFound(format!(
                "object {mcp_id} not found in scene {scene_id}"
            )));
        }

        Ok(())
    }

    pub async fn record_operation(
        &self,
        run_id: &str,
        scene_id: &str,
        mcp_id: &str,
        action: &str,
        status: &str,
        reason: &str,
    ) -> Result<(), AppError> {
        self.db
            .query(
                "CREATE scene_operation SET scene = $scene, sync_run = $sync_run, mcp_id = $mcp_id, action = $action, reason = $reason, status = $status, attempts = 1, created_at = time::now()"
            )
            .bind(("scene", format!("scene:{scene_id}")))
            .bind(("sync_run", format!("sync_run:{run_id}")))
            .bind(("mcp_id", mcp_id.to_string()))
            .bind(("action", action.to_string()))
            .bind(("reason", reason.to_string()))
            .bind(("status", status.to_string()))
            .await
            .map_err(|e| AppError::Database(format!("record operation error: {e}")))?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn record_key_strips_scene_prefix() {
        assert_eq!(
            scene_object_record_key("scene:main", "obj_1"),
            "main:obj_1"
        );
    }

    #[test]
    fn record_key_bare_scene_id_unchanged() {
        assert_eq!(
            scene_object_record_key("main", "obj_1"),
            "main:obj_1"
        );
    }

    #[test]
    fn record_key_consistent_across_prefix_variants() {
        let with_prefix = scene_object_record_key("scene:my_scene", "actor_42");
        let without_prefix = scene_object_record_key("my_scene", "actor_42");
        assert_eq!(with_prefix, without_prefix);
    }

    #[test]
    fn record_key_double_prefix_stripped() {
        // .replace replaces all occurrences
        assert_eq!(
            scene_object_record_key("scene:scene:x", "obj"),
            "x:obj"
        );
    }
}
