"""Exhaustive contract smoke tests for all 200 registered role skills.

These tests verify registration, caller isolation, bounded input validation and
structured advisory output. They deliberately do not claim that advisory
contracts perform real host inspection or remediation.
"""
import pytest

from aether_core.extended.knowledge import KnowledgeStore
from aether_core.extended.quality import AgentScorecard
from aether_core.skills import build_builtin_registry


AGENTS = ("SCOUT", "ANALYST", "FIXER", "AUDITOR")


@pytest.fixture
def registry(tmp_path):
    return build_builtin_registry(
        KnowledgeStore(tmp_path / "knowledge.sqlite3"),
        AgentScorecard(tmp_path / "metrics.sqlite3"),
    )


def role_skills(registry):
    return [
        item
        for item in registry.list()
        if item["name"].split(".", 1)[0].upper() in AGENTS
    ]


def test_all_200_role_skills_are_registered_exactly_once(registry):
    skills = role_skills(registry)
    assert len(skills) == 200
    names = [item["name"] for item in skills]
    assert len(names) == len(set(names))
    for agent in AGENTS:
        owned = [item for item in skills if item["name"].startswith(agent.lower() + ".")]
        assert len(owned) == 50
        assert all(agent in item["allowed_callers"] for item in owned)


@pytest.mark.parametrize("agent", AGENTS)
def test_every_role_skill_executes_its_bounded_advisory_contract(registry, agent):
    for spec in registry.for_agent(agent):
        result = registry.execute(
            spec["name"],
            caller=agent,
            arguments={
                "subject": "isolated contract smoke test",
                "evidence": ["synthetic evidence only"],
                "context": {"test": True},
            },
        )
        assert result["agent"] == agent
        assert result["skill"] == spec["name"]
        assert result["result_type"] == "structured_advisory"
        assert result["evidence_received"] == ["synthetic evidence only"]
        assert any("does not execute commands" in item for item in result["limitations"])


@pytest.mark.parametrize("agent", AGENTS)
def test_each_agent_is_denied_every_other_agents_skills(registry, agent):
    other_agents = [candidate for candidate in AGENTS if candidate != agent]
    for other in other_agents:
        for spec in registry.for_agent(other):
            with pytest.raises(PermissionError):
                registry.execute(
                    spec["name"],
                    caller=agent,
                    arguments={"subject": "unauthorized cross-agent call"},
                )


@pytest.mark.parametrize("agent", AGENTS)
def test_all_role_skills_reject_unknown_fields_and_oversized_inputs(registry, agent):
    for spec in registry.for_agent(agent):
        with pytest.raises(ValueError, match="unsupported"):
            registry.execute(
                spec["name"],
                caller=agent,
                arguments={"unexpected": "must be rejected"},
            )
        with pytest.raises(ValueError):
            registry.execute(
                spec["name"],
                caller=agent,
                arguments={"subject": "x" * 501},
            )
        with pytest.raises(ValueError):
            registry.execute(
                spec["name"],
                caller=agent,
                arguments={"evidence": ["x" * 2001]},
            )
