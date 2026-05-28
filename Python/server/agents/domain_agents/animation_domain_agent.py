"""Animation Domain Agent - Expert in skeletal meshes, animation, and rigging."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.animation_domain")


class AnimationDomainAgent(BaseAgent):
    """Domain agent for animation and rigging operations.
    
    Capabilities:
    - Animation blueprint creation
    - Blend space creation
    - Animation montage creation
    - IK rig setup
    """

    name = "animation_domain"
    description = "Expert in animation and rigging"
    capabilities = [
        "anim.create_blueprint",
        "anim.create_blendspace",
        "anim.create_montage",
        "anim.setup_ik",
    ]
    domains = ["animation", "rigging", "skeletal"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute animation operations."""
        self.logger.info(f"AnimationDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if "blueprint" in text_lower or "anim bp" in text_lower:
            return await self._create_anim_blueprint(context)
        elif "blendspace" in text_lower or "blend space" in text_lower:
            return await self._create_blendspace(context)
        elif "montage" in text_lower:
            return await self._create_montage(context)
        elif "ik" in text_lower or "rig" in text_lower:
            return await self._setup_ik(context)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown animation task: {intent}",
            )

    async def _create_anim_blueprint(self, context: AgentContext) -> AgentResult:
        """Create animation blueprint."""
        result = await self.call_tool_async(
            "create_animation_blueprint",
            asset_path="/Game/Animation/ABP_Character",
            skeleton_path="/Game/Mannequin/SK_Mannequin_Skeleton",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Animation blueprint creation failed"),
            )

        return AgentResult(
            success=True,
            data={"anim_blueprint": result},
        )

    async def _create_blendspace(self, context: AgentContext) -> AgentResult:
        """Create blend space."""
        result = await self.call_tool_async(
            "create_blend_space",
            asset_path="/Game/Animation/BS_Locomotion",
            skeleton_path="/Game/Mannequin/SK_Mannequin_Skeleton",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Blend space creation failed"),
            )

        return AgentResult(
            success=True,
            data={"blendspace": result},
        )

    async def _create_montage(self, context: AgentContext) -> AgentResult:
        """Create animation montage."""
        result = await self.call_tool_async(
            "create_anim_montage",
            asset_path="/Game/Animation/AM_Attack",
            skeleton_path="/Game/Mannequin/SK_Mannequin_Skeleton",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Montage creation failed"),
            )

        return AgentResult(
            success=True,
            data={"montage": result},
        )

    async def _setup_ik(self, context: AgentContext) -> AgentResult:
        """Setup IK rig."""
        result = await self.call_tool_async(
            "create_ik_rig",
            asset_name="IKRig_Character",
            asset_path="/Game/Animation",
            skeletal_mesh_path="/Game/Mannequin/SK_Mannequin",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "IK rig setup failed"),
            )

        return AgentResult(
            success=True,
            data={"ik_rig": result},
        )
