from types import SimpleNamespace

from aether_core import platform_adapters as adapters


def test_fixed_probe_uses_no_shell_bounded_timeout_and_no_stdin(monkeypatch):
    seen = {}
    monkeypatch.setattr(adapters.shutil, "which", lambda name: "/usr/bin/" + name)

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        seen.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="safe output", stderr="")

    monkeypatch.setattr(adapters.subprocess, "run", fake_run)
    assert adapters._run_fixed(("systemctl", "list-units")) == (0, "safe output\n")
    assert seen["shell"] is False
    assert seen["timeout"] == adapters._TIMEOUT_SECONDS
    assert seen["stdin"] is adapters.subprocess.DEVNULL
    assert seen["argv"] == ["/usr/bin/systemctl", "list-units"]


def test_fixed_probe_redacts_secrets_and_bounds_output(monkeypatch):
    monkeypatch.setattr(adapters.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(
        adapters.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="password=hunter2\nAuthorization: Bearer abc123\nurl=https://alice:secretpass@example.test/path\n",
            stderr="",
        ),
    )
    result = adapters._run_fixed(("journalctl", "-n", "5"))
    assert result is not None
    assert "hunter2" not in result[1]
    assert "abc123" not in result[1]
    assert "alice:secretpass" not in result[1]
    assert "[REDACTED]" in result[1]


def test_linux_native_adapters_report_services_packages_logs_firewall_and_home(monkeypatch):
    monkeypatch.setattr(adapters.platform, "system", lambda: "Linux")
    monkeypatch.setattr(adapters.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(adapters, "_run_fixed", lambda argv: (
        0, "active\n" if argv[0] in {"ufw", "firewall-cmd"} else "one\ntwo\n"
    ))
    findings = adapters.collect_native_findings()
    titles = {item.title for item in findings}
    assert {
        "Linux service health",
        "Package inventory",
        "System error log summary",
        "Firewall posture",
        "Home directory permissions",
    }.issubset(titles)
    assert all(len(item.detail) <= 4000 for item in findings)
    firewall = next(item for item in findings if item.title == "Firewall posture")
    assert "active" in firewall.detail


def test_macos_native_adapters_are_fixed_and_bounded(monkeypatch):
    monkeypatch.setattr(adapters.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(adapters.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(adapters, "_run_fixed", lambda argv: (0, "one\ntwo\n"))
    findings = adapters.collect_native_findings()
    titles = {item.title for item in findings}
    assert {
        "macOS service inventory",
        "Package inventory",
        "System error log summary",
        "Firewall posture",
    }.issubset(titles)


def test_windows_adapter_does_not_claim_unimplemented_package_or_log_support(monkeypatch):
    monkeypatch.setattr(adapters.platform, "system", lambda: "Windows")
    monkeypatch.setattr(adapters.shutil, "which", lambda name: None)
    findings = adapters.collect_native_findings()
    by_title = {item.title: item for item in findings}
    assert "Probe unavailable" in by_title["Package inventory"].detail
    assert "Probe unavailable" in by_title["System error log summary"].detail
    assert "Windows native services" in by_title
