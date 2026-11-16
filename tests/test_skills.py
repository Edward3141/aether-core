"""Tests for the allow-listed skill registry."""
import pytest

from aether_core.extended.knowledge import KnowledgeStore
from aether_core.extended.quality import AgentScorecard
from aether_core.skills import SkillRegistry, SkillSpec, build_builtin_registry


def make_registry(tmp_path):
    return build_builtin_registry(
        KnowledgeStore(tmp_path / "knowledge.sqlite3"),
        AgentScorecard(tmp_path / "metrics.sqlite3"),
    )


def test_builtin_skills_are_registered_and_sorted(tmp_path):
    registry = make_registry(tmp_path)
    names = [item["name"] for item in registry.list()]
    assert names == sorted(names)
    assert {"system.snapshot", "knowledge.search", "knowledge.stats",
            "report.generate"} <= set(names)


def test_system_snapshot_is_read_only_and_usable(tmp_path):
    result = make_registry(tmp_path).execute(
        "system.snapshot", caller="SCOUT"
    )
    assert result["cpu_count"] >= 1
    assert result["disk_total_bytes"] > 0


def test_knowledge_search_never_returns_unverified(tmp_path):
    registry = make_registry(tmp_path)
    knowledge = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    unverified = knowledge.add("network", "Unconfirmed observation", source="SCOUT")
    verified = knowledge.add("network", "Confirmed observation", source="human")
    assert knowledge.verify(verified, evidence={"ticket": "case-123"})
    result = registry.execute(
        "knowledge.search", caller="ANALYST", arguments={"topic": "network"}
    )
    assert [item["id"] for item in result] == [verified]
    assert unverified not in [item["id"] for item in result]


def test_skill_rejects_unknown_names_and_callers(tmp_path):
    registry = make_registry(tmp_path)
    with pytest.raises(ValueError, match="not registered"):
        registry.execute("shell.run", caller="HUMAN")
    with pytest.raises(PermissionError):
        registry.execute("knowledge.search", caller="SCOUT", arguments={"topic": ""})


def test_skill_rejects_extra_and_invalid_arguments(tmp_path):
    registry = make_registry(tmp_path)
    with pytest.raises(ValueError, match="unsupported"):
        registry.execute(
            "knowledge.search", caller="ANALYST",
            arguments={"topic": "x", "sql": "DROP TABLE knowledge"},
        )
    with pytest.raises(ValueError, match="limit"):
        registry.execute(
            "knowledge.search", caller="ANALYST",
            arguments={"topic": "x", "limit": 1000},
        )


def test_registry_rejects_duplicate_skills():
    registry = SkillRegistry()
    skill = SkillSpec("demo", "Demo", ("HUMAN",), lambda args: None)
    registry.register(skill)
    with pytest.raises(ValueError, match="unique"):
        registry.register(skill)

def test_report_skill_and_mcp_caller(tmp_path):
    registry = make_registry(tmp_path)
    report = registry.execute("report.generate", caller="MCP")
    assert report["schema_version"] == 1
    assert report["system_snapshot"]["cpu_count"] >= 1
    assert report["findings"][0]["title"] == "Knowledge ledger"


def test_cli_exposes_skill_commands():
    from aether_core.cli import build_parser

    assert build_parser().parse_args(["skills"]).command == "skills"
    args = build_parser().parse_args([
        "skill", "knowledge.search", "--input", '{"topic":"disk"}'
    ])
    assert args.command == "skill"
    assert args.name == "knowledge.search"


@pytest.mark.parametrize("agent", ["SCOUT", "ANALYST", "FIXER", "AUDITOR"])
def test_each_agent_has_exactly_50_scoped_skills(tmp_path, agent):
    registry = make_registry(tmp_path)
    skills = registry.for_agent(agent)
    assert len(skills) == 50
    assert all(agent in item["allowed_callers"] for item in skills)
    assert all(item["name"].startswith(agent.lower() + ".") for item in skills)


def test_agent_skill_cannot_be_called_by_another_agent(tmp_path):
    registry = make_registry(tmp_path)
    with pytest.raises(PermissionError):
        registry.execute(
            "fixer.rollback.plan.design", caller="SCOUT",
            arguments={"subject": "test", "evidence": []},
        )


def test_role_skill_returns_bounded_structured_advisory(tmp_path):
    registry = make_registry(tmp_path)
    result = registry.execute(
        "analyst.root.cause.analysis", caller="ANALYST",
        arguments={"subject": "service crash", "evidence": ["error at 10:00"]},
    )
    assert result["agent"] == "ANALYST"
    assert result["result_type"] == "structured_advisory"
    assert "does not execute commands" in result["limitations"][1]
