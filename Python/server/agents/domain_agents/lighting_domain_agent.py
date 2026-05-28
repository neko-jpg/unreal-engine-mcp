"""Lighting Domain Agent - Expert in lighting setup and mood creation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger("agents.lighting_domain")


class LightingDomainAgent(BaseAgent):
    """Domain agent for lighting operations.
    
    Capabilities:
    - Light intensity/color/temperature control
    - Shadow settings
    - Volumetric scattering
    - Atmospheric lighting
    """

    name = "lighting_domain"
    description = "Expert in lighting setup and atmosphere"
    capabilities = [
        "light.set_intensity",
        "light.set_color",
        "light.set_temperature",
        "light.set_attenuation_radius",
        "light.set_shadow_enabled",
        "light.set_volumetric_scattering",
        "atmosphere.set_height_fog",
        "atmosphere.set_sky_atmosphere",
        "atmosphere.set_volumetric_fog",
    ]
    domains = ["lighting", "atmosphere"]

    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tool_registry)
        # Register worker agents for advanced lighting coordination
        from server.agents.worker_agents.procedural_worker import ProceduralWorkerAgent
        from server.agents.worker_agents.pcg_worker import PCGWorkerAgent

        self.register_sub_agent(ProceduralWorkerAgent(tool_registry))
        self.register_sub_agent(PCGWorkerAgent(tool_registry))

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        """Execute lighting operations."""
        self.logger.info(f"LightingDomain executing: {intent[:80]}...")
        text_lower = intent.lower()

        if any(kw in text_lower for kw in ["dark", "dim", "low", "creepy", "shadow"]):
            return await self._create_dark_lighting(context)
        elif any(kw in text_lower for kw in ["bright", "light", "torch", "lamp", "warm"]):
            return await self._create_bright_lighting(context)
        elif "fog" in text_lower or "mist" in text_lower:
            return await self._setup_fog(context)
        elif "sky" in text_lower:
            return await self._setup_sky(context)
        else:
            return await self._create_dark_lighting(context)

    async def _create_dark_lighting(self, context: AgentContext) -> AgentResult:
        """Create dark/creepy lighting setup."""
        steps = []

        # Check if cave was just created and auto-adjust
        cave_result = context.metadata.get("cave_result")
        if cave_result and cave_result.get("success"):
            return await self._auto_adjust_for_cave(context, cave_result)

        # Dim main lights
        result = await self.call_tool_async(
            "set_light_intensity",
            actor_name="DirectionalLight",
            intensity=0.3,
        )
        steps.append({"step": "dim_directional", "result": result})

        # Add point lights in cave
        for i, loc in enumerate([[0, -500, 200], [0, 500, 200], [0, 0, 400]]):
            result = await self.call_tool_async(
                "spawn_actor",
                name=f"CaveLight_{i}",
                type="PointLight",
                location=loc,
            )
            steps.append({"step": f"spawn_light_{i}", "result": result})

            result = await self.call_tool_async(
                "set_light_intensity",
                actor_name=f"CaveLight_{i}",
                intensity=2.5,
            )
            steps.append({"step": f"set_intensity_{i}", "result": result})

            result = await self.call_tool_async(
                "set_light_color",
                actor_name=f"CaveLight_{i}",
                color=[0.9, 0.7, 0.5],
            )
            steps.append({"step": f"set_color_{i}", "result": result})

        failures = [s for s in steps if s["result"].get("success") is False]

        return AgentResult(
            success=len(failures) < len(steps),
            data={"lighting_setup": "dark_creepy", "steps": steps},
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    async def _auto_adjust_for_cave(self, context: AgentContext, cave_result: Dict[str, Any]) -> AgentResult:
        """Auto-adjust lighting based on cave generation results."""
        self.logger.info("Auto-adjusting lighting for newly created cave")
        steps = []

        # Dim directional light significantly for cave interior
        result = await self.call_tool_async(
            "set_light_intensity",
            actor_name="DirectionalLight",
            intensity=0.1,
        )
        steps.append({"step": "dim_directional_for_cave", "result": result})

        # Spawn ambient point lights along cave path
        metrics = cave_result.get("data", {}).get("final_metrics", {})
        depth = metrics.get("depth", 1200)
        num_lights = max(3, min(8, int(depth / 300)))

        for i in range(num_lights):
            loc = [i * (depth / num_lights) - depth / 2, 0.0, 200.0]
            result = await self.call_tool_async(
                "spawn_actor",
                name=f"CaveAmbientLight_{i}",
                type="PointLight",
                location=loc,
            )
            steps.append({"step": f"spawn_ambient_light_{i}", "result": result})

            result = await self.call_tool_async(
                "set_light_intensity",
                actor_name=f"CaveAmbientLight_{i}",
                intensity=1.8,
            )
            steps.append({"step": f"set_ambient_intensity_{i}", "result": result})

            result = await self.call_tool_async(
                "set_light_color",
                actor_name=f"CaveAmbientLight_{i}",
                color=[0.8, 0.6, 0.4],
            )
            steps.append({"step": f"set_ambient_color_{i}", "result": result})

            result = await self.call_tool_async(
                "set_light_attenuation_radius",
                actor_name=f"CaveAmbientLight_{i}",
                radius=800.0,
            )
            steps.append({"step": f"set_ambient_radius_{i}", "result": result})

        # Add volumetric fog for atmosphere
        result = await self.call_tool_async(
            "set_height_fog_properties",
            actor_name="Cave_Fog",
            fog_density=0.06,
            fog_height_falloff=0.15,
            fog_max_opacity=0.75,
            start_distance=100.0,
            light_inscattering_color=[0.1, 0.12, 0.15],
        )
        steps.append({"step": "cave_fog", "result": result})

        failures = [s for s in steps if s["result"].get("success") is False]

        return AgentResult(
            success=len(failures) < len(steps),
            data={"lighting_setup": "auto_cave", "steps": steps},
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    async def _create_bright_lighting(self, context: AgentContext) -> AgentResult:
        """Create bright lighting setup."""
        result = await self.call_tool_async(
            "set_light_intensity",
            actor_name="DirectionalLight",
            intensity=5.0,
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Bright lighting setup failed"),
            )

        return AgentResult(
            success=True,
            data={"lighting_setup": "bright"},
        )

    async def _setup_fog(self, context: AgentContext) -> AgentResult:
        """Setup atmospheric fog."""
        result = await self.call_tool_async(
            "set_height_fog_properties",
            actor_name="Cave_Fog",
            fog_density=0.08,
            fog_height_falloff=0.18,
            fog_max_opacity=0.82,
            start_distance=80.0,
            light_inscattering_color=[0.12, 0.14, 0.18],
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Fog setup failed"),
            )

        return AgentResult(
            success=True,
            data={"fog": result},
        )

    async def _setup_sky(self, context: AgentContext) -> AgentResult:
        """Setup sky atmosphere."""
        result = await self.call_tool_async(
            "set_sky_atmosphere_properties",
            actor_name="SkyAtmosphere",
        )
        
        if result.get("success") is False:
            return AgentResult(
                success=False,
                error=result.get("error", "Sky setup failed"),
            )

        return AgentResult(
            success=True,
            data={"sky": result},
        )
