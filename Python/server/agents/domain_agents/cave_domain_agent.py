"""Cave Domain Agent - Expert in cave generation, mood, and validation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.cave_domain")


class CaveDomainAgent(BaseAgent):
    """Domain agent specialized in cave generation and atmosphere.
    
    Capabilities:
    - Cave geometry generation (SDF, procedural)
    - Cave mood application (lighting, audio, VFX, post-process)
    - Cave detail scattering (PCG)
    - Cave validation (navigation, collision, metrics)
    - Cave refinement based on metrics
    - Multi-domain coordination (lighting, audio, vfx, post-process)
    """

    name = "cave_domain"
    description = "Expert in cave generation, atmosphere, and validation"
    capabilities = [
        "cave.audit",
        "cave.generate_sdf",
        "cave.apply_pcg",
        "cave.apply_mood",
        "cave.validate",
        "cave.refine_geometry",
        "cave.generate_or_refine",
        "cave.full_pipeline",
    ]
    domains = ["cave", "procedural", "mesh_editing", "validation", "lighting", "audio", "vfx", "post_process"]

    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tool_registry)
        # Register worker agents
        from server.agents.worker_agents.procedural_worker import ProceduralWorkerAgent
        from server.agents.worker_agents.pcg_worker import PCGWorkerAgent
        from server.agents.worker_agents.mesh_worker import MeshWorkerAgent
        from server.agents.worker_agents.nav_worker import NavWorkerAgent
        from server.agents.worker_agents.validation_worker import ValidationWorkerAgent

        self.register_sub_agent(ProceduralWorkerAgent(tool_registry))
        self.register_sub_agent(PCGWorkerAgent(tool_registry))
        self.register_sub_agent(MeshWorkerAgent(tool_registry))
        self.register_sub_agent(NavWorkerAgent(tool_registry))
        self.register_sub_agent(ValidationWorkerAgent(tool_registry))

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute cave domain operations.
        
        Intents:
        - "create cave": Generate new cave
        - "make cave creepy": Apply mood to existing or new cave
        - "audit cave": Check cave metrics
        - "refine cave": Improve cave based on validation
        - "validate cave": Run full validation
        - "full cave pipeline": Complete generation + mood + validation
        """
        self.logger.info(f"CaveDomain executing: {intent[:80]}...")

        text_lower = intent.lower()

        # Determine operation type
        if any(kw in text_lower for kw in ["audit", "check", "inspect", "metrics"]):
            return await self._audit_cave(context)
        
        elif any(kw in text_lower for kw in ["validate", "test", "verify"]):
            return await self._validate_cave(context)
        
        elif any(kw in text_lower for kw in ["refine", "improve", "better", "fix"]):
            return await self._refine_cave(context)
        
        elif any(kw in text_lower for kw in ["full pipeline", "complete", "everything"]):
            return await self._full_pipeline(intent, context)
        
        elif any(kw in text_lower for kw in ["create", "make", "generate", "build", "spawn"]):
            return await self._create_cave(intent, context)
        
        else:
            # Default: apply mood to existing or create new
            return await self._apply_cave_mood(intent, context)

    async def _audit_cave(self, context: AgentContext) -> AgentResult:
        """Audit current cave state."""
        result = await self.call_tool_async(
            "scene_cave_audit",
            scene_id=context.scene_id,
            target=context.target or "cave",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Audit failed"),
                data={"raw_result": result},
            )

        metrics = result.get("cave_metrics", {})
        
        return AgentResult(
            success=True,
            data={
                "audit": result.get("audit"),
                "cave_metrics": metrics,
                "needs_geometry_pass": result.get("needs_geometry_pass", False),
            },
            metrics=metrics,
        )

    async def _validate_cave(self, context: AgentContext) -> AgentResult:
        """Run full cave validation."""
        result = await self.call_tool_async(
            "scene_validate_cave",
            scene_id=context.scene_id,
            target=context.target or "cave",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Validation failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=result.get("passed", False),
            data={
                "validation": result,
                "passed": result.get("passed"),
                "metric_failures": result.get("metric_failures", []),
            },
            metrics=result.get("cave_metrics", {}),
        )

    async def _refine_cave(self, context: AgentContext) -> AgentResult:
        """Refine cave based on current metrics."""
        # First audit
        audit = await self._audit_cave(context)
        if not audit.success:
            return audit

        metrics = audit.metrics
        
        # If needs refinement
        if audit.data.get("needs_geometry_pass") or metrics.get("cave_score", 0) < 0.65:
            self.logger.info("Cave needs geometry refinement")
            
            # Delegate to procedural worker for geometry
            geom_result = await self.delegate(
                "procedural_worker",
                f"refine cave geometry with score {metrics.get('cave_score')}",
                context,
            )
            
            # Apply PCG details
            pcg_result = await self.delegate(
                "pcg_worker",
                "scatter cave details",
                context,
            )
            
            # Validate after refinement
            validation = await self._validate_cave(context)
            
            return self._merge_results([audit, geom_result, pcg_result, validation])
        
        return AgentResult(
            success=True,
            data={"message": "Cave metrics acceptable, no refinement needed"},
            metrics=metrics,
        )

    async def _create_cave(self, intent: str, context: AgentContext) -> AgentResult:
        """Create a new cave with full pipeline."""
        self.logger.info("Creating new cave with full pipeline")
        
        # Extract mood from intent
        mood = self._extract_mood(intent)

        # Run full orchestrator
        result = await self.call_tool_async(
            "scene_cave_generate_or_refine",
            scene_id=context.scene_id,
            mood=mood,
            target=context.target or "cave",
            max_refine_iterations=3,
            cave_score_threshold=0.75,
            include_preview=True,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Cave generation failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={
                "cave_generation": result,
                "initial_metrics": result.get("initial_cave_metrics"),
                "final_metrics": result.get("final_cave_metrics"),
                "validation": result.get("validation"),
                "steps": [s.get("step") for s in result.get("steps", [])],
            },
            metrics=result.get("final_cave_metrics", {}),
        )

    async def _apply_cave_mood(self, intent: str, context: AgentContext) -> AgentResult:
        """Apply mood to existing cave with multi-domain coordination."""
        mood = self._extract_mood(intent)
        
        self.logger.info(f"Applying cave mood: {mood}")
        
        # Apply cave-specific mood
        result = await self.call_tool_async(
            "scene_apply_cave_mood",
            scene_id=context.scene_id,
            mood=mood,
            best_effort=True,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Mood application failed"),
                data={"raw_result": result},
            )

        # Run preview to verify
        preview = await self.call_tool_async(
            "scene_preview",
            scene_id=context.scene_id,
            target="cave",
            batch="surround",
        )

        return AgentResult(
            success=True,
            data={
                "mood": mood,
                "steps": result.get("steps", []),
                "preview": preview,
            },
        )

    async def _full_pipeline(self, intent: str, context: AgentContext) -> AgentResult:
        """Run complete cave pipeline: geometry + mood + validation."""
        self.logger.info("Running full cave pipeline")
        
        # Step 1: Create cave geometry
        cave_result = await self._create_cave(intent, context)
        if not cave_result.success:
            return cave_result
        
        # Step 2: Apply mood
        mood_result = await self._apply_cave_mood(intent, context)
        
        # Step 3: Validate
        validation_result = await self._validate_cave(context)
        
        # Step 4: Preview
        preview_result = await self.call_tool_async(
            "scene_preview",
            scene_id=context.scene_id,
            target="cave",
            batch="surround",
        )
        
        # Merge all results
        merged = self._merge_results([cave_result, mood_result, validation_result])
        merged.data["preview"] = preview_result
        merged.data["pipeline_complete"] = True
        
        return merged

    def _extract_mood(self, intent: str) -> str:
        """Extract mood from intent text."""
        text_lower = intent.lower()
        
        if any(kw in text_lower for kw in ["creepy", "scary", "horror", "不気味", "怖い", "ホラー"]):
            return "creepy"
        elif any(kw in text_lower for kw in ["calm", "peaceful", "serene", "静か", "穏やか"]):
            return "calm"
        elif any(kw in text_lower for kw in ["heroic", "epic", "majestic", "壮大", "英雄的"]):
            return "heroic"
        elif any(kw in text_lower for kw in ["dark", "dim", "darkness", "暗い", "暗闇"]):
            return "dark"
        elif any(kw in text_lower for kw in ["mysterious", "mystery", "神秘", "謎"]):
            return "mysterious"
        
        return "creepy"  # Default mood
