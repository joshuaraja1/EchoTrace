import numpy as np
import pytest

from echotrace_sync.synchronizer import estimate_offset

SAMPLE_RATE = 2_000


def shared_recordings(offset_seconds: float, seed: int = 7):
    """Create recordings where target local time maps to reference time + offset."""
    rng = np.random.default_rng(seed)
    world = rng.normal(0, 0.02, SAMPLE_RATE * 20)
    for event_time in (4.2, 8.75, 13.1, 16.4):
        start = int(event_time * SAMPLE_RATE)
        pulse = np.hanning(120) * rng.uniform(0.8, 1.2)
        world[start : start + pulse.size] += pulse

    reference = world[: SAMPLE_RATE * 15] + rng.normal(0, 0.01, SAMPLE_RATE * 15)
    target_start = int(offset_seconds * SAMPLE_RATE)
    target = world[target_start : target_start + SAMPLE_RATE * 12]
    target = 0.65 * target + rng.normal(0, 0.015, target.size)
    return reference, target


@pytest.mark.parametrize("expected", [1.25, 3.5, 6.0])
def test_estimates_positive_start_offset(expected):
    reference, target = shared_recordings(expected)
    estimate = estimate_offset(reference, target, SAMPLE_RATE, max_offset_seconds=8)
    assert estimate.offset_seconds == pytest.approx(expected, abs=1 / SAMPLE_RATE)
    assert estimate.confidence >= 0.5
    assert estimate.warning is None


def test_reports_ambiguous_unrelated_audio():
    first = np.random.default_rng(1).normal(size=SAMPLE_RATE * 3)
    second = np.random.default_rng(2).normal(size=SAMPLE_RATE * 3)
    estimate = estimate_offset(first, second, SAMPLE_RATE, max_offset_seconds=1)
    assert estimate.confidence < 0.5
    assert estimate.warning is not None


def test_rejects_invalid_max_offset():
    signal = np.ones(100)
    with pytest.raises(ValueError, match="max_offset_seconds"):
        estimate_offset(signal, signal, SAMPLE_RATE, max_offset_seconds=0)
