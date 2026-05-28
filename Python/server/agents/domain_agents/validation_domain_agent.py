"""Validation Domain Agent - Expert in testing and quality assurance."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.validation_domain")


class ValidationDomainAgent(BaseAgent):
    """Domain agent for validation and testing operations.
    
    Capabilities:
    - Collision validation
    - Navigation validation
    - Performance budget validation
    - Screenshot testing
    - Full validation suite
    """

    name = "validation_domain"
    description = "Expert in testing and quality assurance"
    capabilities = [
        "validation.collision",
        "validation.navigation",
        "validation.performance",
        "validation.screenshot",
    ]
    domains = ["validation", "testing", "quality"]

    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tool_registry)
        # Register worker agents for advanced validation pipelines
        from server.agents.worker_agents.nav_worker import NavWorkerAgent
        from server.agents.worker_agents.validation_worker import ValidationWorkerAgent

        self.register_sub_agent(NavWorkerAgent(tool_registry))
        self.register_sub_agent(ValidationWorkerAgent(tool_registry))

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute validation operations."""
        self.logger.info(f"ValidationDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "full" in text_lower or "all" in text_lower:
            return await self._run_full_validation(context)
        elif "collision" in text_lower:
            return await self._validate_collision(context)
        elif "navigation" in text_lower or "nav" in text_lower:
            return await self._validate_navigation(context)
        elif "performance" in text_lower:
            return await self._validate_performance(context)
        elif "screenshot" in text_lower:
            return await self._run_screenshot_test(context)
        else:
            return await self._run_full_validation(context)

    async def _run_full_validation(self, context: AgentContext) -> AgentResult:
        """Run full validation suite with worker coordination."""
        results = []
        steps = []

        # Step 1: Collision validation
        collision = await self._validate_collision(context)
        results.append(collision)
        steps.append({"step": "collision", "success": collision.success})

        # Step 2: Navigation validation (delegate to nav worker for detailed analysis)
        nav_worker_result = await self.delegate(
            "nav_worker",
            f"detailed navmesh validation for {context.scene_id}",
            context,
        )
        results.append(nav_worker_result)
        steps.append({"step": "nav_worker", "success": nav_worker_result.success})

        # Fallback to basic nav validation if worker fails
        if not nav_worker_result.success:
            navigation = await self._validate_navigation(context)
            results.append(navigation)
            steps.append({"step": "navigation_fallback", "success": navigation.success})

        # Step 3: Performance validation
        performance = await self._validate_performance(context)
        results.append(performance)
        steps.append({"step": "performance", "success": performance.success})

        # Step 4: Screenshot validation
        screenshot = await self._run_screenshot_test(context)
        results.append(screenshot)
        steps.append({"step": "screenshot", "success": screenshot.success})

        # Step 5: Delegate to validation worker for cross-domain checks
        cross_domain = await self.delegate(
            "validation_worker",
            f"cross-domain consistency check for {context.scene_id}",
            context,
        )
        results.append(cross_domain)
        steps.append({"step": "cross_domain", "success": cross_domain.success})

        merged = self._merge_results(results)
        merged.data["validation_type"] = "full"
        merged.data["validation_steps"] = steps

        # Generate fix plan if any validation failed
        if not merged.success:
            try:
                from server.scene_generate_fix_plan import scene_generate_fix_plan

                diagnostics = []
                for r in results:
                    if not r.success and r.error:
                        diagnostics.append({
                            "type": "validation_failure",
                            "message": r.error,
                            "domain": r.data.get("domain", "unknown"),
                        })
                if diagnostics:
                    fix_plan = scene_generate_fix_plan(
                        scene_id=context.scene_id,
                        diagnostics=diagnostics,
                    )
                    merged.data["fix_plan"] = fix_plan
            except ImportError:
                # Fallback: generate simple fix plan inline
                diagnostics = []
                for r in results:
                    if not r.success and r.error:
                        diagnostics.append({
                            "type": "validation_failure",
                            "message": r.error,
                            "domain": r.data.get("domain", "unknown"),
                        })
                if diagnostics:
                    merged.data["fix_plan"] = {
                        "scene_id": context.scene_id,
                        "diagnostics": diagnostics,
                        "suggested_actions": [
                            "Review failed validation steps",
                            "Check scene-syncd logs for details",
                            "Re-run specific validation domain tests",
                        ],
                    }
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(f"Could not generate fix plan: {exc}")

        return merged

    async def _validate_collision(self, context: AgentContext) -> AgentResult:
        """Validate collision."""
        result = await self.call_tool_async(
            "run_collision_validation",
            scope="Level",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Collision validation failed"),
            )

        return AgentResult(
            success=True,
            data={"collision": result},
        )

    async def _validate_navigation(self, context: AgentContext) -> AgentResult:
        """Validate navigation."""
        result = await self.call_tool_async(
            "run_navigation_validation",
            scope="Level",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Navigation validation failed"),
            )

        return AgentResult(
            success=True,
            data={"navigation": result},
        )

    async def _validate_performance(self, context: AgentContext) -> AgentResult:
        """Validate performance."""
        result = await self.call_tool_async(
            "run_performance_budget_validation",
            max_frame_ms=16.6,
            max_gpu_ms=16.6,
            max_memory_mb=4096,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Performance validation failed"),
            )

        return AgentResult(
            success=True,
            data={"performance": result},
        )

    async def _run_screenshot_test(self, context: AgentContext) -> AgentResult:
        """Run screenshot test."""
        result = await self.call_tool_async(
            "run_gameplay_screenshot_test",
            screenshot_id="validation_test",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Screenshot test failed"),
            )

        return AgentResult(
            success=True,
            data={"screenshot": result},
        )
