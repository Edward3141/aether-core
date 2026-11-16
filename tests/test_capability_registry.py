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
    assert "repair.execute" in [x["capability_id"] for x in registry.list_for_role("EXECUTOR", "Darwin")]
    assert "repair.execute" not in [x["capability_id"] for x in registry.list_for_role("EXECUTOR", "Windows")]
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



def test_summary_filters_repair_execution_for_unsupported_platforms():
    registry = CapabilityRegistry()
    linux = registry.summary("Linux")
    windows = registry.summary("Windows")
    assert "repair.execute" in linux["roles"]["EXECUTOR"]
    assert "repair.execute" not in windows["roles"]["EXECUTOR"]
    assert windows["platform"] == "windows"


def test_catalog_discloses_implementation_status_instead_of_implying_all_are_live():
    registry = CapabilityRegistry()
    scout = {item["capability_id"]: item for item in registry.list_for_role("SCOUT", "Linux")}
    assert scout["system.identity"]["implementation_status"] == "implemented_read_only"
    assert scout["process.inspect"]["implementation_status"] == "partial_read_only"
    assert scout["logs.inspect"]["implementation_status"] == "metadata_only"
    assert scout["packages.inspect"]["implementation_status"] == "metadata_only"
    summary = registry.summary("Linux")
    assert summary["implementation_status"]["repair.execute"] == "partial_one_action"
    assert summary["implementation_status"]["backup.plan"] == "not_implemented"


def test_orchestrator_binds_fifth_component_executor_capability(tmp_path):
    from aether_core.database import Database
    from aether_core.orchestrator import Orchestrator

    workflow = Orchestrator(Database(tmp_path / "state.sqlite3"))
    executor_capabilities = workflow.executor.available_capabilities()
    repair = next(item for item in executor_capabilities if item["capability_id"] == "repair.execute")
    assert repair["implementation_status"] == "partial_one_action"
    assert repair["executable"] is False
