from echotrace_sync.evaluation import evaluate_manifest


def test_evaluation_computes_phase_zero_gate():
    manifest = {
        "sources": {
            "/tmp/a.mp4": {"offset_seconds": 0.0},
            "/tmp/b.mp4": {"offset_seconds": 3.25},
            "/tmp/c.mp4": {"offset_seconds": 6.2},
        }
    }
    report = evaluate_manifest(manifest, {"a.mp4": 0, "b.mp4": 3.4, "c.mp4": 6.0})
    assert report["median_absolute_error_seconds"] == 0.15
    assert report["failure_rate"] == 0
    assert report["phase_0_gate_passed"] is True

