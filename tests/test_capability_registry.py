from aether_core.capability_registry import CapabilityRegistry, detect_platform


def test_platform_detection():
    assert detect_platform("Linux") == "linux"
    assert detect_platform("Darwin") == "macos"
    assert detect_platform("Windows") == "windows"
    assert detect_platform("FreeBSD") == "other"


def test_role_scoping_and_platform_adaptation():
    registry = CapabilityRegistry()
    linux = registry.list_for_role("SCOUT", "Linux")
    windows = registry.list_for_role("SCOUT", "Windows")
    assert any(item["capability_id"] == "service.inspect" for item in linux)
    assert any("Get-Service" in item["command_references"] for item in windows
               if item["capability_id"] == "service.inspect")
    assert all(item["executable"] is False for item in linux + windows)


def test_executor_is_only_role_with_repair_execution_capability():
    registry = CapabilityRegistry()
    assert "repair.execute" in [x["capability_id"] for x in registry.list_for_role("EXECUTOR", "Linux")]
    for role in ("SCOUT", "ANALYST", "FIXER", "AUDITOR"):
        assert "repair.execute" not in [x["capability_id"] for x in registry.list_for_role(role, "Linux")]


def test_fixer_can_propose_but_not_execute():
    registry = CapabilityRegistry()
    fixer = {x["capability_id"]: x for x in registry.list_for_role("FIXER", "Windows")}
    assert fixer["configuration.plan"]["access"] == "proposal_only"
    assert fixer["backup.plan"]["access"] == "proposal_only"
    assert "repair.execute" not in fixer


def test_unknown_role_and_capability_fail_closed():
    registry = CapabilityRegistry()
    import pytest
    with pytest.raises(ValueError, match="Unknown AETHER CORE role"):
        registry.list_for_role("ROOT", "Linux")
    with pytest.raises(ValueError, match="Unknown capability"):
        registry.get("arbitrary.command")
