# Phase 1A — Core Video Pipeline Baseline

This is the first implementation slice of PRD Phase 1, **not the Phase 1 exit point**.

## Implemented baseline

- FFprobe metadata extraction: duration, dimensions, FPS, and audio presence.
- Deterministic JPEG evidence-frame extraction with FFmpeg.
- Detector interface with no-model and Ultralytics YOLO implementations.
- MVP classes: car, truck, motorcycle, bicycle, and person.
- Lightweight IoU identity tracking within one camera.
- First/last appearance events with timestamp, confidence, track ID, and frame citation.
- JSON analysis artifact suitable for a future backend or synchronized timeline.

## Current limitations

The tracker is intentionally a baseline, not ByteTrack or DeepSORT. It can lose identity during
occlusion, abrupt motion, or sparse sampling. Object detection requires the optional `vision`
dependency and a downloaded model. The default no-model mode produces metadata and frames but no
observations. Collision and stop detection are not yet implemented because they need reliable
trajectories and real test footage.

The following PRD Phase 1 requirements are still pending:

- investigation-scoped video upload;
- OpenCV processing integration;
- manual synchronization adjustment;
- persistent investigation/evidence records;
- an end-to-end investigation flow.

## Phase 1 exit criterion

Phase 1 is complete only when one investigation works end to end: create an investigation, upload
its video evidence, process it, detect and track supported objects, generate simple events, review
the results, and manually correct synchronization when required.

## Next implementation steps, in PRD order

1. Add investigation and evidence models plus a local FastAPI upload flow.
2. Add OpenCV processing and run YOLO on controlled RC-car footage.
3. Replace or augment IoU matching with ByteTrack once detections are validated.
4. Add simple trajectory-derived stop and direction-change candidates.
5. Add manual synchronization adjustment and persist the corrected offset separately.
6. Process all camera sources within one investigation end to end.

Every derived event must retain its supporting frame and confidence. None of these events should
be described as legal fault or liability.
