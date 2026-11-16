from aether_core.platform_inspection import collect_platform_findings


def test_platform_inspection_returns_real_bounded_categories():
    findings = collect_platform_findings()
    titles = {finding.title for finding in findings}
    assert {
        "System identity",
        "Process inventory",
        "Memory usage",
        "Storage inventory",
        "Network interfaces",
        "System uptime",
        "Service inventory unavailable",
    }.issubset(titles) or {
        "System identity",
        "Process inventory",
        "Memory usage",
        "Storage inventory",
        "Network interfaces",
        "System uptime",
        "Windows service inventory",
    }.issubset(titles)
    assert all(len(item.detail) <= 4000 for item in findings)
    assert all(item.confidence == 1.0 for item in findings)


def test_platform_inspection_does_not_expose_network_addresses_or_process_names():
    findings = collect_platform_findings()
    network = next(item for item in findings if item.title == "Network interfaces")
    process = next(item for item in findings if item.title == "Process inventory")
    assert "IP addresses" in network.detail
    assert "processes were visible" in process.detail
