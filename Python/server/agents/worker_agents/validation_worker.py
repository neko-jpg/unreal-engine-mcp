"""Validation Worker Agent - Handles testing and validation tasks."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.validation_worker")


class ValidationWorkerAgent(BaseAgent):
    """Worker agent for testing and validation operations.
    
    Capabilities:
    - Collision validation
    - Navigation validation
    - Performance budget validation
    - Gameplay screenshot tests
    """

    name = "validation_worker"
    description = "Handles testing, validation, and quality assurance"
    capabilities = [
        "validation.collision",
        "validation.screenshot",
        "nav.validate",
    ]
    domains = ["validation", "testing"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute validation tasks."""
        self.logger.info(f"ValidationWorker executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "collision" in text_lower:
            return await self._validate_collision(context)
        elif "navigation" in text_lower or "navmesh" in text_lower:
            return await self._validate_navigation(context)
        elif "performance" in text_lower:
            return await self._validate_performance(context)
        elif "screenshot" in text_lower:
            return await self._run_screenshot_test(context)
        elif "full" in text_lower or "all" in text_lower:
            return await self._run_full_validation(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown validation task: {intent}",
            )

    async def _validate_collision(self, context: AgentContext) -> AgentResult:
        """Validate collision geometry."""
        result = await self.call_tool_async(
            "run_collision_validation",
            scope="Level",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Collision validation failed"),
                data={"raw_result": result},
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
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"navigation": result},
        )

    async def _validate_performance(self, context: AgentContext) -> AgentResult:
        """Validate performance budget."""
        result = await self.call_tool_async(
            "run_performance_budget_validation",
            max_frame_ms=context.metadata.get("max_frame_ms", 16.6),
            max_gpu_ms=context.metadata.get("max_gpu_ms", 16.6),
            max_memory_mb=context.metadata.get("max_memory_mb", 4096),
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Performance validation failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"performance": result},
        )

    async def _run_screenshot_test(self, context: AgentContext) -> AgentResult:
        """Run gameplay screenshot test."""
        result = await self.call_tool_async(
            "run_gameplay_screenshot_test",
            screenshot_id=context.metadata.get("screenshot_id", "test_001"),
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Screenshot test failed"),
                data={"raw_result": result},
            )

        return AgentResult(
            success=True,
            data={"screenshot": result},
        )

    async def _run_full_validation(self, context: AgentContext) -> AgentResult:
        """Run full validation suite."""
        results = []
        
        collision = await self._validate_collision(context)
        results.append(collision)
        
        navigation = await self._validate_navigation(context)
        results.append(navigation)
        
        performance = await self._validate_performance(context)
        results.append(performance)
        
        merged = self._merge_results(results)
        merged.data["validation_type"] = "full"
        
        return merged
