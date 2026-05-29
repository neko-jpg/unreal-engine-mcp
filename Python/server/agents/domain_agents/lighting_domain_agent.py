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

    def _get_spawned_name(self, result: Dict[str, Any], fallback: str) -> str:
        """Extract the actual UE actor name from a spawn response."""
        if not isinstance(result, dict):
            return fallback
        return result.get("name") or result.get("actor_name") or result.get("final_name") or fallback

    async def _create_dark_lighting(self, context: AgentContext) -> AgentResult:
        """Create dark/creepy lighting setup."""
        steps = []

        # Check if cave was just created and auto-adjust
        cave_result = context.metadata.get("cave_result")
        if cave_result and cave_result.get("success"):
            return await self._auto_adjust_for_cave(context, cave_result)

        # Ensure DirectionalLight exists, then dim it
        result = await self.call_tool_async(
            "spawn_actor",
            name="DirectionalLight",
            type="DirectionalLight",
            location=[0, 0, 1000],
        )
        steps.append({"step": "ensure_directional", "result": result})
        dir_light_name = self._get_spawned_name(result, "DirectionalLight")

        result = await self.call_tool_async(
            "set_light_intensity",
            actor_name=dir_light_name,
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
            light_name = self._get_spawned_name(result, f"CaveLight_{i}")

            result = await self.call_tool_async(
                "set_light_intensity",
                actor_name=light_name,
                intensity=2.5,
            )
            steps.append({"step": f"set_intensity_{i}", "result": result})

            result = await self.call_tool_async(
                "set_light_color",
                actor_name=light_name,
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

        # Ensure and dim directional light for cave interior
        result = await self.call_tool_async(
            "spawn_actor",
            name="DirectionalLight",
            type="DirectionalLight",
            location=[0, 0, 1000],
        )
        steps.append({"step": "ensure_directional_for_cave", "result": result})
        dir_light_name = self._get_spawned_name(result, "DirectionalLight")

        result = await self.call_tool_async(
            "set_light_intensity",
            actor_name=dir_light_name,
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
            light_name = self._get_spawned_name(result, f"CaveAmbientLight_{i}")

            result = await self.call_tool_async(
                "set_light_intensity",
                actor_name=light_name,
                intensity=1.8,
            )
            steps.append({"step": f"set_ambient_intensity_{i}", "result": result})

            result = await self.call_tool_async(
                "set_light_color",
                actor_name=light_name,
                color=[0.8, 0.6, 0.4],
            )
            steps.append({"step": f"set_ambient_color_{i}", "result": result})

            result = await self.call_tool_async(
                "set_light_attenuation_radius",
                actor_name=light_name,
                radius=800.0,
            )
            steps.append({"step": f"set_ambient_radius_{i}", "result": result})

        dramatic_lights = [
            {
                "name": "Cave_MainTorch_Warm",
                "location": [-depth * 0.45, -160.0, 170.0],
                "intensity": 2600.0,
                "color": [1.0, 0.55, 0.22],
                "temperature": 2200.0,
                "radius": 650.0,
            },
            {
                "name": "Cave_DistantGlow_Cool",
                "location": [depth * 0.42, 120.0, 260.0],
                "intensity": 1200.0,
                "color": [0.36, 0.55, 1.0],
                "temperature": 7800.0,
                "radius": 950.0,
            },
            {
                "name": "Cave_EmissiveCrystal_Glow",
                "location": [depth * 0.18, 260.0, 240.0],
                "intensity": 820.0,
                "color": [0.2, 0.85, 1.0],
                "temperature": 7600.0,
                "radius": 520.0,
            },
        ]
        for spec in dramatic_lights:
            result = await self.call_tool_async(
                "spawn_actor",
                name=spec["name"],
                type="PointLight",
                location=spec["location"],
            )
            steps.append({"step": f"spawn_{spec['name']}", "result": result})
            light_name = self._get_spawned_name(result, spec["name"])
            for step_name, tool_name, kwargs in (
                ("intensity", "set_light_intensity", {"actor_name": light_name, "intensity": spec["intensity"]}),
                ("color", "set_light_color", {"actor_name": light_name, "color": spec["color"]}),
                ("temperature", "set_light_temperature", {"actor_name": light_name, "temperature": spec["temperature"]}),
                ("radius", "set_light_attenuation_radius", {"actor_name": light_name, "radius": spec["radius"]}),
            ):
                result = await self.call_tool_async(tool_name, **kwargs)
                steps.append({"step": f"{spec['name']}_{step_name}", "result": result})

        # Ensure fog actor exists, then configure it
        fog_result = await self.call_tool_async(
            "spawn_actor",
            name="Cave_Fog",
            type="ExponentialHeightFog",
            location=[0, 0, 0],
        )
        steps.append({"step": "ensure_fog", "result": fog_result})
        fog_name = self._get_spawned_name(fog_result, "Cave_Fog")

        result = await self.call_tool_async(
            "set_height_fog_properties",
            actor_name=fog_name,
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
            data={
                "lighting_setup": "auto_cave",
                "steps": steps,
                "dramatic_lighting_pattern": {
                    "main_torch_temperature": 2200.0,
                    "distant_glow_temperature": 7800.0,
                    "volumetric_fog_density": 0.06,
                    "emissive_crystal_glow": True,
                    "flicker_ready": True,
                },
            },
            warnings=[f"{s['step']}: {s['result'].get('error')}" for s in failures],
        )

    async def _create_bright_lighting(self, context: AgentContext) -> AgentResult:
        """Create bright lighting setup."""
        # Ensure DirectionalLight exists
        spawn_res = await self.call_tool_async(
            "spawn_actor",
            name="DirectionalLight",
            type="DirectionalLight",
            location=[0, 0, 1000],
        )
        dir_light_name = self._get_spawned_name(spawn_res, "DirectionalLight")

        result = await self.call_tool_async(
            "set_light_intensity",
            actor_name=dir_light_name,
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
        spawn_res = await self.call_tool_async(
            "spawn_actor",
            name="Cave_Fog",
            type="ExponentialHeightFog",
            location=[0, 0, 0],
        )
        fog_name = self._get_spawned_name(spawn_res, "Cave_Fog")

        result = await self.call_tool_async(
            "set_height_fog_properties",
            actor_name=fog_name,
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
