use crate::domain::*;
use crate::error::AppError;
use surrealdb::Surreal;
use surrealdb::engine::any::Any;
use surrealdb::sql::Datetime;

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
            "DEFINE FIELD objects ON TABLE scene_snapshot TYPE array;",
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
            self.db.query(*query).await.map_err(|e| AppError::Database(format!("schema migration error: {e}")))?;
        }

        tracing::info!("Schema migrations applied");
        Ok(())
    }

    pub async fn ensure_default_scene(&self) -> Result<(), AppError> {
        let now = Datetime::from(chrono::Utc::now());

        let existing: Option<Scene> = self.db
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

            let _: Option<Scene> = self.db
                .create(("scene", "main"))
                .content(scene)
                .await
                .map_err(|e| AppError::Database(format!("create scene:main error: {e}")))?;

            tracing::info!("Created default scene:main");
        }

        Ok(())
    }

    pub async fn create_scene(&self, name: &str, description: Option<String>) -> Result<Scene, AppError> {
        let now = Datetime::from(chrono::Utc::now());
        let scene = Scene {
            id: format!("scene:{name}"),
            name: name.to_string(),
            description,
            status: "active".to_string(),
            active_revision: 1,
            unreal_project_path: None,
            unreal_level_name: None,
            created_at: now.clone(),
            updated_at: now,
        };

        let created: Option<Scene> = self.db
            .create(("scene", name))
            .content(scene)
            .await
            .map_err(|e| AppError::Database(format!("create scene error: {e}")))?;

        created.ok_or_else(|| AppError::Internal("failed to create scene".to_string()))
    }

    pub async fn upsert_object(&self, obj: &SceneObject) -> Result<SceneObject, AppError> {
        let now = Datetime::from(chrono::Utc::now());
        let record_key = format!("{}:{}", obj.scene.replace("scene:", ""), obj.mcp_id);

        let existing: Option<SceneObject> = self.db
            .select(("scene_object", record_key.as_str()))
            .await
            .map_err(|e| AppError::Database(format!("select object error: {e}")))?;

        if let Some(mut existing_obj) = existing {
            existing_obj.actor_type = obj.actor_type.clone();
            existing_obj.desired_name = obj.desired_name.clone();
            existing_obj.transform = obj.transform.clone();
            existing_obj.asset_ref = obj.asset_ref.clone();
            existing_obj.visual = obj.visual.clone();
            existing_obj.physics = obj.physics.clone();
            existing_obj.tags = obj.tags.clone();
            existing_obj.metadata = obj.metadata.clone();
            existing_obj.desired_hash = obj.desired_hash.clone();
            existing_obj.sync_status = "pending".to_string();
            existing_obj.updated_at = now;
            if obj.group.is_some() {
                existing_obj.group = obj.group.clone();
            }

            let updated: Option<SceneObject> = self.db
                .update(("scene_object", record_key.as_str()))
                .content(existing_obj)
                .await
                .map_err(|e| AppError::Database(format!("update object error: {e}")))?;

            updated.ok_or_else(|| AppError::Internal("failed to update object".to_string()))?;
            self.write_object_tags(&record_key, &obj.tags).await
        } else {
            let mut new_obj = obj.clone();
            new_obj.created_at = now.clone();
            new_obj.updated_at = now;

            let created: Option<SceneObject> = self.db
                .create(("scene_object", record_key.as_str()))
                .content(new_obj)
                .await
                .map_err(|e| AppError::Database(format!("create object error: {e}")))?;

            created.ok_or_else(|| AppError::Internal("failed to create object".to_string()))?;
            self.write_object_tags(&record_key, &obj.tags).await
        }
    }

    async fn write_object_tags(&self, record_key: &str, tags: &[String]) -> Result<SceneObject, AppError> {
        let tags_json = serde_json::to_value(tags)
            .map_err(|e| AppError::Internal(format!("serialize tags error: {e}")))?;

        let updated: Option<SceneObject> = self.db
            .update(("scene_object", record_key))
            .merge(serde_json::json!({ "tags": tags_json }))
            .await
            .map_err(|e| AppError::Database(format!("write object tags error: {e}")))?;

        updated.ok_or_else(|| AppError::Internal("failed to reload object after tag write".to_string()))
    }

    pub async fn list_desired_objects(&self, scene: &str, include_deleted: bool) -> Result<Vec<SceneObject>, AppError> {
        let query = if include_deleted {
            "SELECT * FROM scene_object WHERE scene = $scene"
        } else {
            "SELECT * FROM scene_object WHERE scene = $scene AND deleted = false"
        };

        let objects: Vec<SceneObject> = self.db
            .query(query)
            .bind(("scene", format!("scene:{scene}")))
            .await
            .map_err(|e| AppError::Database(format!("list objects error: {e}")))?
            .take(0)
            .map_err(|e| AppError::Database(format!("list objects parse error: {e}")))?;

        Ok(objects)
    }

    pub async fn mark_object_deleted(&self, scene: &str, mcp_id: &str) -> Result<(), AppError> {
        let record_key = format!("{}:{}", scene, mcp_id);
        let now = Datetime::from(chrono::Utc::now());

        let result: Vec<SceneObject> = self.db
            .query("UPDATE type::thing($id) SET deleted = true, sync_status = \"pending\", updated_at = $now")
            .bind(("id", format!("scene_object:{record_key}")))
            .bind(("now", now))
            .await
            .map_err(|e| AppError::Database(format!("mark deleted error: {e}")))?
            .take(0)
            .map_err(|e| AppError::Database(format!("mark deleted parse error: {e}")))?;

        if result.is_empty() {
            return Err(AppError::NotFound(format!("object {mcp_id} not found in scene {scene}")));
        }

        Ok(())
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

        self.db
            .query("UPDATE type::thing($id) SET status = \"completed\", summary = $summary, ended_at = $now")
            .bind(("id", format!("sync_run:{run_id}")))
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
        let record_key = format!("{}:{}", scene_id, mcp_id);
        let now = Datetime::from(chrono::Utc::now());

        let update_query = if unreal_actor_name.is_some() {
            "UPDATE type::thing($id) SET sync_status = \"synced\", last_applied_hash = $hash, unreal_actor_name = $actor_name, updated_at = $now"
        } else {
            "UPDATE type::thing($id) SET sync_status = \"synced\", last_applied_hash = $hash, updated_at = $now"
        };

        let mut query = self.db.query(update_query)
            .bind(("id", format!("scene_object:{record_key}")))
            .bind(("hash", desired_hash.to_string()))
            .bind(("now", now));

        if let Some(name) = unreal_actor_name {
            query = query.bind(("actor_name", name.to_string()));
        }

        query.await
            .map_err(|e| AppError::Database(format!("mark synced error: {e}")))?;

        Ok(())
    }

    pub async fn mark_object_deleted_applied(
        &self,
        scene_id: &str,
        mcp_id: &str,
    ) -> Result<(), AppError> {
        let record_key = format!("{}:{}", scene_id, mcp_id);
        let now = Datetime::from(chrono::Utc::now());

        self.db
            .query("UPDATE type::thing($id) SET sync_status = \"synced\", updated_at = $now")
            .bind(("id", format!("scene_object:{record_key}")))
            .bind(("now", now))
            .await
            .map_err(|e| AppError::Database(format!("mark deleted applied error: {e}")))?;

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
