"""Tests for A2A Protocol Agent Cards."""

from __future__ import annotations

import pytest

from server.agents.agent_card import AgentCard, AgentCardDirectory, build_directory_from_orchestrator
from server.agents.base_agent import AgentContext, AgentResult, BaseAgent


class DummyAgent(BaseAgent):
    name = "dummy_agent"
    description = "A dummy agent for testing"
    capabilities = ["cap_a", "cap_b"]
    domains = ["test_domain"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        return AgentResult()


class AnotherAgent(BaseAgent):
    name = "another_agent"
    description = "Another dummy agent"
    capabilities = ["cap_b", "cap_c"]
    domains = ["other_domain"]

    async def execute(self, intent: str, context: AgentContext) -> AgentResult:
        return AgentResult()


class TestAgentCard:
    """Test AgentCard dataclass."""

    def test_basic_creation(self):
        card = AgentCard(
            name="test_agent",
            description="Test agent",
            capabilities=["cap1", "cap2"],
            domains=["domain1"],
        )
        assert card.name == "test_agent"
        assert card.description == "Test agent"
        assert card.capabilities == ["cap1", "cap2"]
        assert card.domains == ["domain1"]
        assert card.input_modes == ["text"]
        assert card.output_modes == ["scene_delta", "validation_report"]
        assert card.version == "1.0"
        assert card.url is None

    def test_to_dict(self):
        card = AgentCard(
            name="test_agent",
            description="Test agent",
            capabilities=["cap1"],
            domains=["domain1"],
            input_modes=["text", "image"],
            output_modes=["scene_delta"],
            version="2.0",
            url="http://example.com",
        )
        d = card.to_dict()
        assert d["name"] == "test_agent"
        assert d["description"] == "Test agent"
        assert d["capabilities"] == ["cap1"]
        assert d["domains"] == ["domain1"]
        assert d["input_modes"] == ["text", "image"]
        assert d["output_modes"] == ["scene_delta"]
        assert d["version"] == "2.0"
        assert d["url"] == "http://example.com"

    def test_from_agent(self):
        agent = DummyAgent()
        card = AgentCard.from_agent(agent)
        assert card.name == "dummy_agent"
        assert card.description == "A dummy agent for testing"
        assert card.capabilities == ["cap_a", "cap_b"]
        assert card.domains == ["test_domain"]

    def test_from_agent_missing_attrs(self):
        class MinimalAgent:
            pass

        card = AgentCard.from_agent(MinimalAgent())
        assert card.name == "unknown"
        assert card.description == ""
        assert card.capabilities == []
        assert card.domains == []

    def test_from_agent_copies_lists(self):
        agent = DummyAgent()
        card = AgentCard.from_agent(agent)
        card.capabilities.append("extra")
        assert "extra" not in agent.capabilities


class TestAgentCardDirectory:
    """Test AgentCardDirectory."""

    def test_register_and_get(self):
        directory = AgentCardDirectory()
        card = AgentCard(name="agent1", description="desc")
        directory.register(card)
        assert directory.get("agent1") is card
        assert directory.get("missing") is None

    def test_list_all(self):
        directory = AgentCardDirectory()
        directory.register(AgentCard(name="a", description="A"))
        directory.register(AgentCard(name="b", description="B"))
        all_cards = directory.list_all()
        assert len(all_cards) == 2
        assert {c.name for c in all_cards} == {"a", "b"}

    def test_find_by_capability(self):
        directory = AgentCardDirectory()
        directory.register(AgentCard(name="a", description="A", capabilities=["cap1", "cap2"]))
        directory.register(AgentCard(name="b", description="B", capabilities=["cap2", "cap3"]))
        directory.register(AgentCard(name="c", description="C", capabilities=["cap3"]))

        found = directory.find_by_capability("cap2")
        assert len(found) == 2
        assert {c.name for c in found} == {"a", "b"}

        found = directory.find_by_capability("cap1")
        assert len(found) == 1
        assert found[0].name == "a"

        found = directory.find_by_capability("missing")
        assert found == []

    def test_find_by_domain(self):
        directory = AgentCardDirectory()
        directory.register(AgentCard(name="a", description="A", domains=["dom1", "dom2"]))
        directory.register(AgentCard(name="b", description="B", domains=["dom2"]))

        found = directory.find_by_domain("dom2")
        assert len(found) == 2

        found = directory.find_by_domain("dom1")
        assert len(found) == 1
        assert found[0].name == "a"

    def test_to_json(self):
        directory = AgentCardDirectory()
        directory.register(AgentCard(name="a", description="A"))
        directory.register(AgentCard(name="b", description="B"))
        json_data = directory.to_json()
        assert json_data["count"] == 2
        assert len(json_data["agents"]) == 2


class TestBuildDirectoryFromOrchestrator:
    """Test building directory from orchestrator."""

    def test_build_from_orchestrator(self):
        class FakeOrchestrator:
            sub_agents = {
                "dummy_agent": DummyAgent(),
                "another_agent": AnotherAgent(),
            }

        orchestrator = FakeOrchestrator()
        directory = build_directory_from_orchestrator(orchestrator)

        assert directory.get("dummy_agent") is not None
        assert directory.get("another_agent") is not None
        assert directory.get("missing") is None

        all_cards = directory.list_all()
        assert len(all_cards) == 2

    def test_build_from_empty_orchestrator(self):
        class EmptyOrchestrator:
            sub_agents = {}

        directory = build_directory_from_orchestrator(EmptyOrchestrator())
        assert directory.list_all() == []
        assert directory.to_json()["count"] == 0

    def test_build_from_orchestrator_capabilities(self):
        class FakeOrchestrator:
            sub_agents = {
                "dummy_agent": DummyAgent(),
                "another_agent": AnotherAgent(),
            }

        directory = build_directory_from_orchestrator(FakeOrchestrator())
        cap_b_agents = directory.find_by_capability("cap_b")
        assert len(cap_b_agents) == 2

        cap_c_agents = directory.find_by_capability("cap_c")
        assert len(cap_c_agents) == 1
        assert cap_c_agents[0].name == "another_agent"

    def test_build_from_orchestrator_domains(self):
        class FakeOrchestrator:
            sub_agents = {
                "dummy_agent": DummyAgent(),
                "another_agent": AnotherAgent(),
            }

        directory = build_directory_from_orchestrator(FakeOrchestrator())
        test_domain_agents = directory.find_by_domain("test_domain")
        assert len(test_domain_agents) == 1
        assert test_domain_agents[0].name == "dummy_agent"
