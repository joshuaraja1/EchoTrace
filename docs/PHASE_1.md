# Phase 1 — Basic Reconstruction Engine

The Phase 1 software exit criterion is implemented and covered by an end-to-end API test.

## Implemented baseline

- FFprobe metadata extraction: duration, dimensions, FPS, and audio presence.
- Deterministic JPEG evidence-frame extraction with FFmpeg.
- Detector interface with no-model and Ultralytics YOLO implementations.
- MVP classes: car, truck, motorcycle, bicycle, and person.
- Lightweight IoU identity tracking within one camera.
- First/last appearance events with timestamp, confidence, track ID, and frame citation.
- JSON analysis artifact suitable for a future backend or synchronized timeline.
- SQLite-backed investigations and evidence records.
- Investigation-scoped MP4/MOV upload with immutable storage and SHA-256 digest.
- OpenCV brightness, sharpness, and motion analysis for extracted evidence frames.
- Synchronous investigation processing with analyzed/failed/review status.
- Manual synchronization adjustment with reviewer note and complete offset history.
- Investigation status, evidence, objects, timeline, and synchronization endpoints.
- Simple stop and direction-change candidates with qualified wording and frame evidence.

## Current limitations

The tracker is intentionally a baseline, not ByteTrack or DeepSORT. It can lose identity during
occlusion, abrupt motion, or sparse sampling. Object detection requires the optional `vision`
dependency and a downloaded model. The default no-model mode produces metadata and frames but no
observations. Collision and stop detection are not yet implemented because they need reliable
trajectories and real test footage.

## Phase 1 exit criterion

Phase 1 is complete only when one investigation works end to end: create an investigation, upload
its video evidence, process it, detect and track supported objects, generate simple events, review
the results, and manually correct synchronization when required.

Verified path: create investigation → upload a real generated MP4 → extract/probe/process frames →
run OpenCV → detect and track a test vehicle → create evidence-linked events → adjust the offset →
retrieve the corrected timeline and audit history.

## Remaining validation, not missing Phase 1 software

1. Run YOLO on controlled RC-car footage and record detection failure cases.
2. Decide whether IoU tracking is sufficient or must be replaced with ByteTrack.
3. Measure event quality on controlled footage before expanding event types.
4. Complete the real-camera Phase 0 synchronization gate.

These are empirical validation activities. Performance must not be claimed until measured.

Every derived event must retain its supporting frame and confidence. None of these events should
be described as legal fault or liability.
