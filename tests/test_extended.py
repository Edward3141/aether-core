from aether_core.extended.knowledge import KnowledgeStore
from aether_core.extended.monitor import collect_snapshot
from aether_core.extended.quality import AgentScorecard
from aether_core.extended.reports import build_report, report_json, report_markdown

def test_memory_requires_explicit_evidence(tmp_path):
    store = KnowledgeStore(tmp_path / "memory.db")
    item = store.add("network", "Possible DNS issue", source="ANALYST")
    assert store.search("network") == []
    assert store.search("network", verified_only=False)[0]["status"] == "unverified"
    try: store.verify(item, evidence={})
    except ValueError: pass
    else: raise AssertionError("empty verification evidence must be rejected")
    assert store.verify(item, evidence={"checked_by": "human", "result": "confirmed"})
    assert len(store.search("network")) == 1
    assert not store.verify(item, evidence={"result": "again"})

def test_scorecard_is_transparent():
    scores = AgentScorecard()
    scores.record("scout", success=True); scores.record("SCOUT", success=False)
    metric = scores.snapshot()[0]
    assert metric.agent == "SCOUT" and metric.runs == 2 and metric.success_rate == 0.5

def test_monitor_and_reports_are_serializable(tmp_path):
    snap = collect_snapshot(tmp_path)
    assert snap.disk_total_bytes >= snap.disk_free_bytes
    report = build_report(snapshot=snap.to_dict())
    assert '"schema_version": 1' in report_json(report)
    assert "does not authorize repairs" in report_markdown(report)
