# Phase 0 — Synchronization Feasibility

## Decision gate

Continue with EchoTrace if controlled multi-camera recordings achieve median absolute offset
error of **0.5 seconds or less**. The stretch target is 0.25 seconds. Record the result; do not
claim either target until measured on real footage.

## Experiment protocol

1. Record one staged RC-car event from three phones.
2. Start each camera at a deliberately different time.
3. Include shared sounds (tone, horn, impact) while keeping normal ambient noise.
4. Establish ground truth with a visible flash plus an audio click captured by every camera.
5. Run `echotrace-sync` with Camera A as reference.
6. Compare every estimated offset with ground truth.
7. Repeat across at least 10 trials before deciding whether the audio baseline is viable.

Save one JSON result per trial under `artifacts/phase-0/` and calculate:

- absolute error per camera;
- median and 95th-percentile error;
- failure rate (`confidence < 0.5` or error above 0.5 seconds);
- conditions associated with failures (missing audio, clipping, distance, wind, echo).

## Scope of this spike

Included now: FFmpeg audio extraction, pairwise offset estimation, confidence diagnostics,
multi-source manifest, and ground-truth unit tests.

Deferred until the audio baseline is measured: metadata fusion, visual-event matching,
trajectory matching, object detection, tracking, backend APIs, database, and frontend.

## Interpretation

Low confidence is a usable result, not an error to conceal. It should trigger manual alignment
or a later visual synchronization method. EchoTrace reconstructs evidence; it does not assign
fault or liability.

