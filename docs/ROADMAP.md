# EchoTrace PRD Implementation Roadmap

This roadmap translates the EchoTrace Product Requirements Document into implementation gates.
It is the sequencing source of truth. A phase is not complete because some of its components
exist; its exit criterion must be demonstrated.

## Product guardrails

Every phase must preserve these PRD rules:

- Evidence first: derived events retain source, timestamp, supporting frame or interval, and confidence.
- Human in the loop: investigators can review and eventually correct AI output.
- Visible uncertainty: low-confidence results are labeled, never silently promoted to facts.
- Reconstruction, not liability: EchoTrace never assigns fault, guilt, or legal responsibility.
- Original evidence is immutable; derived analysis is stored separately.
- No facial recognition, license-plate recognition, 3D reconstruction, surveillance, or liability automation in the MVP.

## Phase 0 — Technical feasibility

PRD goal: align two controlled recordings reliably by detecting shared evidence and estimating the
time offset.

Implemented:

- FFmpeg audio extraction;
- GCC-PHAT shared-audio offset estimation;
- confidence diagnostics and weak-match warning;
- JSON synchronization manifest;
- ground-truth evaluation command;
- synthetic known-offset tests.

Pending exit evidence:

- independently recorded controlled camera footage;
- measured median absolute synchronization error;
- demonstrated median error at or below 0.5 seconds across repeated trials.

Status: **software baseline verified; real-camera exit criterion pending**.

## Phase 1 — Basic reconstruction engine

PRD scope:

- video upload;
- OpenCV processing;
- supported-object detection;
- per-video object tracking;
- simple event detection;
- manual synchronization adjustment;
- one investigation working end to end.

Implemented:

- FFprobe metadata extraction;
- FFmpeg evidence-frame sampling;
- optional Ultralytics YOLO adapter;
- supported class filtering;
- baseline IoU tracking;
- evidence-linked first/last appearance events;
- JSON analysis artifacts.
- SQLite investigation/evidence persistence;
- immutable MP4/MOV upload with SHA-256 evidence digest;
- OpenCV frame quality and motion processing;
- stop and direction-change event candidates;
- manual synchronization adjustment with audit history;
- end-to-end FastAPI investigation processing and review endpoints.

Exit criterion: one investigation can be created, populated with video evidence, processed,
reviewed, and manually adjusted end to end.

Status: **Phase 1 software gate implemented and tested**. Controlled-footage YOLO/tracking quality
remains an empirical validation task; no accuracy claim has been made.

## Phase 2 — Automatic synchronization

Implement only after the Phase 1 end-to-end flow exists:

- embedded timestamp/metadata alignment;
- improved audio fingerprint comparison;
- visual shared-event matching;
- trajectory-based matching;
- fused offset and synchronization confidence for two to three recordings;
- graceful handling of missing audio and poor-quality evidence.

The current Phase 0 audio engine becomes one signal in this fusion layer; it does not by itself
satisfy Phase 2.

Exit criterion: two to three controlled recordings synchronize automatically and expose confidence
plus supporting alignment signals.

## Phase 3 — Unified timeline

- global incident clock;
- local-to-global timestamp mapping;
- event merging and deduplication;
- confidence scoring;
- evidence references and clickable supporting intervals.

Exit criterion: all analyzed sources produce one chronological, evidence-backed incident timeline.

## Phase 4 — Azure AI layer

- meaningful Azure video intelligence where it improves evidence extraction;
- Azure AI Foundry/Azure OpenAI for constrained summaries and questions;
- Azure AI Search for evidence retrieval and grounding;
- citations for every material generated claim;
- uncertainty-aware language such as “appears,” “estimated,” and “possible.”

Exit criterion: incident summaries and answers are grounded only in investigation evidence and
return inspectable citations.

## Phase 5 — Competition UI

- authentication and investigation dashboard;
- investigation creation and evidence uploader;
- processing statuses and failure states;
- synchronized multi-camera player;
- clickable unified timeline and evidence panel;
- Ask EchoTrace;
- evidence graph;
- human confirmation/correction controls.

Exit criterion: the three-camera staged collision demo works repeatedly, including the impact
jump and the cited “five seconds before impact” answer.

## Phase 6 — Validation

- 20–50 controlled staged incidents over time;
- appropriately licensed public real-world crash data;
- negative/no-collision footage;
- varying frame rates, resolutions, lighting, audio availability, and video quality;
- synchronization error, event timestamp error, detection precision/recall, collision F1,
  cross-camera matching accuracy, and evidence citation accuracy.

No performance or business metric may be claimed until it is measured and the sample size is
reported.

## Functional requirement traceability

- FR-001 Authentication — Phase 5, pending.
- FR-002 Investigation creation — Phase 1 backend implemented; UI in Phase 5.
- FR-003 Evidence upload — Phase 1 video upload implemented; other evidence types remain MVP work.
- FR-004 Video processing — Phase 1 implemented.
- FR-005 Object detection — adapter implemented; real-footage validation pending.
- FR-006 Tracking — baseline implemented; upgrade and validation pending.
- FR-007 Synchronization — Phase 0 audio baseline implemented; Phase 2 fusion pending.
- FR-008 Event detection — entry, exit, stop, and direction-change candidates implemented.
- FR-009 Timeline generation — Phase 3, pending.
- FR-010 Multi-camera playback — Phase 5, pending.
- FR-011 Evidence links — frame citations exist in the baseline; complete timeline links pending.
- FR-012 Confidence — baseline detection/synchronization confidence exists; fusion pending.
- FR-013 Incident summary — Phase 4, pending.
- FR-014 Question answering — Phase 4, pending.
- FR-015 Human corrections — audited manual sync implemented; full review controls in Phase 5.
