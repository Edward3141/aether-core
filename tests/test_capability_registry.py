from aether_core.capability_registry import Capability, CapabilityRegistry, detect_platform


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
    windows_services = next(item for item in windows if item["capability_id"] == "service.inspect")
    assert "available_command_binaries" in windows_services
    assert "available_commands" not in windows_services


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



def test_registry_rejects_invalid_or_executable_custom_metadata():
    import pytest

    executable = Capability(
        "unsafe", "test", "must not execute", ("SCOUT",), ("linux",),
        {"linux": ("rm -rf /",)}, "read_only", executable=True,
    )
    with pytest.raises(ValueError, match="must never enable command execution"):
        CapabilityRegistry((executable,))

    invalid_role = Capability(
        "bad-role", "test", "invalid role", ("ROOT",), ("linux",),
        {"linux": ()}, "read_only",
    )
    with pytest.raises(ValueError, match="invalid role scope"):
        CapabilityRegistry((invalid_role,))

    invalid_platform = Capability(
        "bad-platform", "test", "invalid platform", ("SCOUT",), ("plan9",),
        {"plan9": ()}, "read_only",
    )
    with pytest.raises(ValueError, match="invalid platform scope"):
        CapabilityRegistry((invalid_platform,))
