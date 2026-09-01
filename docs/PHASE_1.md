# Phase 1 — Core Video Pipeline

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

## Next implementation steps

1. Run YOLO on controlled RC-car footage and record detection failure cases.
2. Replace or augment IoU matching with ByteTrack once detections are validated.
3. Add trajectory-derived stop, direction-change, and path-convergence candidates.
4. Connect Phase 0 offsets so local observation timestamps map to unified incident time.
5. Add batch processing for all camera sources in one investigation.

Every derived event must retain its supporting frame and confidence. None of these events should
be described as legal fault or liability.
