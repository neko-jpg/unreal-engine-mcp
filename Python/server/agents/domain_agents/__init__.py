"""Domain agents package."""

from __future__ import annotations

from server.agents.domain_agents.animation_domain_agent import AnimationDomainAgent
from server.agents.domain_agents.architecture_domain_agent import ArchitectureDomainAgent
from server.agents.domain_agents.audio_domain_agent import AudioDomainAgent
from server.agents.domain_agents.cave_domain_agent import CaveDomainAgent
from server.agents.domain_agents.cinematic_domain_agent import CinematicDomainAgent
from server.agents.domain_agents.foliage_domain_agent import FoliageDomainAgent
from server.agents.domain_agents.gameplay_domain_agent import GameplayDomainAgent
from server.agents.domain_agents.import_export_domain_agent import ImportExportDomainAgent
from server.agents.domain_agents.landscape_domain_agent import LandscapeDomainAgent
from server.agents.domain_agents.level_management_domain_agent import LevelManagementDomainAgent
from server.agents.domain_agents.lighting_domain_agent import LightingDomainAgent
from server.agents.domain_agents.material_domain_agent import MaterialDomainAgent
from server.agents.domain_agents.networking_domain_agent import NetworkingDomainAgent
from server.agents.domain_agents.npc_domain_agent import NpcDomainAgent
from server.agents.domain_agents.physics_domain_agent import PhysicsDomainAgent
from server.agents.domain_agents.postprocess_domain_agent import PostProcessDomainAgent
from server.agents.domain_agents.project_editor_domain_agent import ProjectEditorDomainAgent
from server.agents.domain_agents.ui_domain_agent import UiDomainAgent
from server.agents.domain_agents.validation_domain_agent import ValidationDomainAgent
from server.agents.domain_agents.vfx_domain_agent import VfxDomainAgent
from server.agents.domain_agents.asset_management_domain_agent import AssetManagementDomainAgent

__all__ = [
    "AnimationDomainAgent",
    "ArchitectureDomainAgent",
    "AssetManagementDomainAgent",
    "AudioDomainAgent",
    "CaveDomainAgent",
    "CinematicDomainAgent",
    "FoliageDomainAgent",
    "GameplayDomainAgent",
    "ImportExportDomainAgent",
    "LandscapeDomainAgent",
    "LevelManagementDomainAgent",
    "LightingDomainAgent",
    "MaterialDomainAgent",
    "NetworkingDomainAgent",
    "NpcDomainAgent",
    "PhysicsDomainAgent",
    "PostProcessDomainAgent",
    "ProjectEditorDomainAgent",
    "UiDomainAgent",
    "ValidationDomainAgent",
    "VfxDomainAgent",
]
