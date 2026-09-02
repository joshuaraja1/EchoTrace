from echotrace_sync.fusion import SyncSignal, fuse_signals, metadata_signal


def test_metadata_signal_uses_recording_start_difference():
    signal = metadata_signal(
        {"creation_time": "2026-09-02T12:00:00Z"},
        {"creation_time": "2026-09-02T12:00:07.140000Z"},
    )
    assert signal is not None
    assert signal.offset_seconds == 7.14
    assert signal.confidence == 0.95


def test_fusion_prefers_consistent_high_confidence_signals():
    result = fuse_signals(
        [
            SyncSignal("metadata", 7.14, 0.95, {}),
            SyncSignal("audio", 7.12, 0.9, {}),
            SyncSignal("visual", 12.0, 0.2, {}),
        ]
    )
    assert result.offset_seconds == 7.14
    assert result.confidence >= 0.5


def test_fusion_exposes_missing_signal_uncertainty():
    result = fuse_signals([])
    assert result.confidence == 0
    assert result.warning
