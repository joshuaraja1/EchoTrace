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

Evaluate estimated offsets against measured ground truth:

```bash
echotrace-evaluate-sync artifacts/synchronization.json ground-truth.json \
  --output artifacts/evaluation.json
```

Ground truth is a JSON object mapping source paths or unique filenames to offsets:

```json
{"camera-a.mp4": 0.0, "camera-b.mp4": 7.14, "camera-c.mp4": 13.02}
```

The real-world decision gate is documented in [docs/PHASE_0.md](docs/PHASE_0.md).

## Phase 1A video pipeline

The first Phase 1 slice can probe a video, sample evidence frames, run an optional YOLO model,
track detections within that video, and emit a basic evidence-linked timeline:

```bash
echotrace-process-video camera-a.mp4 \
  --output artifacts/camera-a \
  --sample-fps 2
```

The default detector is `none`, which verifies metadata and frame extraction without downloading
a model. To enable vehicle/person detection:

```bash
pip install -e '.[vision]'
echotrace-process-video camera-a.mp4 \
  --output artifacts/camera-a \
  --detector yolo \
  --model yolo11n.pt
```

See [docs/PHASE_1.md](docs/PHASE_1.md) for the implemented slice, remaining Phase 1 gate, and next
steps. [docs/ROADMAP.md](docs/ROADMAP.md) is the canonical PRD implementation sequence.

## Start the reconstruction API

```bash
source .venv/bin/activate
echotrace-api --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive API documentation.
Register with `POST /auth/register`, copy the returned bearer token, and select **Authorize** in
the interactive documentation. The API supports the reconstruction workflow:

1. `POST /investigations`
2. `POST /investigations/{id}/evidence` with an MP4 or MOV file
3. `POST /investigations/{id}/process`
4. Review `/status`, `/objects`, and `/timeline`
5. `PATCH /investigations/{id}/evidence/{evidence_id}/synchronization`

Original evidence is stored immutably under `data/evidence/`; its SHA-256 digest is recorded.
Derived frames and analysis are stored separately under `data/analysis/`.

Backend phases 2–4 add automatic multi-signal synchronization, unified incident time, cross-camera
match candidates, evidence-grounded summaries/Q&A, and an inspectable evidence graph. See
[docs/BACKEND.md](docs/BACKEND.md) for configuration and [docs/ROADMAP.md](docs/ROADMAP.md) for
honest completion gates.
