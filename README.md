# EchoTrace

EchoTrace turns fragmented incident evidence into one synchronized, explainable timeline.

This repository currently contains the **Phase 0 technical feasibility spike**. It tests the
project's highest-risk assumption before any application UI is built:

> Can independently started recordings of the same physical event be synchronized to within
> 0.5 seconds in controlled conditions?

## Current capability

The `echotrace-sync` CLI:

- extracts mono PCM audio from video/audio files with FFmpeg;
- estimates each recording's offset against a chosen reference using GCC-PHAT correlation;
- emits a machine-readable synchronization manifest;
- reports confidence, peak quality, and warnings instead of hiding uncertainty.

Offset convention: `global_time = local_media_time + offset_seconds`. A recording that began
7 seconds after the reference should therefore receive an offset near `+7.0`.

## Setup

Requirements: Python 3.9+ and FFmpeg.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Run

```bash
echotrace-sync camera-a.mp4 camera-b.mp4 camera-c.mp4 \
  --reference camera-a.mp4 \
  --output artifacts/synchronization.json
```

For recordings with a known maximum separation, constrain the search to reduce false matches:

```bash
echotrace-sync camera-a.mp4 camera-b.mp4 --max-offset 30
```

## Verify

```bash
pytest
ruff check .
```

The next real-world gate is documented in [docs/PHASE_0.md](docs/PHASE_0.md).

