# PRD implementation traceability

This audit follows the supplied EchoTrace Product Requirements Document. “Implemented” means a
working software path exists and has automated verification. It does not substitute for footage,
customer interviews, cloud credentials, or measured accuracy trials.

## Phase 0 — technical feasibility

Implemented: FFmpeg extraction, GCC-PHAT alignment, confidence diagnostics, known-offset evaluator,
and synthetic tests.

External exit evidence still required: repeated independently recorded camera trials with reported
sample size and median error below 0.5 seconds.

## Phase 1 — basic reconstruction engine

Implemented: owner-scoped investigations; immutable and hashed MP4, MOV, JPG, PNG, TXT, and PDF
uploads; metadata and frame extraction; OpenCV quality/motion analysis; optional YOLO detection;
per-video tracking; all eight specified candidate event types; processing/error status; audited
manual synchronization; event, object, match, and confidence correction layers.

Empirical work still required: tune and measure YOLO/tracking/event quality on the target footage.

## Phase 2 — automatic synchronization

Implemented: recording metadata, GCC-PHAT audio, visual-motion correlation, trajectory-derived event
alignment, robust signal fusion, confidence, diagnostics, missing-signal behavior, two-to-three
video API flow, and manual override history.

External exit evidence still required: the controlled three-camera dataset and measured offsets.

## Phase 3 — unified timeline

Implemented: local-to-global clock conversion, stable event IDs, conservative cross-source merging,
confidence, source/local/global timestamps, protected frame URLs, chronological navigation, and
audited human corrections that do not mutate original analysis.

## Phase 4 — Azure AI layer

Implemented locally: evidence-only retrieval, cited deterministic summaries and Q&A, unsupported
evidence refusal, uncertainty wording, response audit storage, and an inspectable evidence graph.

Implemented as optional Azure adapters: Microsoft Foundry/OpenAI Responses, tenant-filtered Azure AI
Search, and private Azure AI Video Indexer transcript/OCR/scene enrichment. Face-related insight
models and output are excluded. Azure credentials are never stored in the repository.

External exit evidence still required: provision resources, create the Search schema, deploy, and
run grounded-response evaluation against a labeled set.

## Phase 5 — competition UI

Implemented: landing page; registration/login; investigation dashboard and creation; drag-and-drop
uploader; evidence processing/synchronization controls and failure states; protected media fetches;
three-view synchronized playback; global play/pause/scrub; event jumps; feed isolation; playback
speed; manual alignment; clickable evidence-backed timeline; event confidence/time/text corrections;
object labels; cross-camera confirmation/rejection; cited summary/Q&A; object-aware interactive graph;
responsive layouts; and visible no-fault/immutable-evidence safeguards.

External exit evidence still required: load the final staged three-camera collision and rehearse the
exact impact-jump and “five seconds before impact” flow repeatedly.

## Phase 6 — validation

Implemented: `echotrace-evaluate-trial` calculates median synchronization error, median event-time
error, object precision/recall/F1, collision precision/recall/F1, matching accuracy, citation
accuracy, and the PRD target gates from a labeled JSON trial. A schema example lives under
`examples/validation/`.

External exit evidence still required: collect 20–50 controlled incidents, select appropriately
licensed public footage, include no-collision negatives and quality variants, run the evaluator,
and report the sample size. No accuracy or time-saved metric is claimed before that work.

## Functional requirements

FR-001 through FR-015 have implemented MVP software paths. Automated backend tests cover auth,
owner scope, upload integrity, processing, synchronization fusion, timeline citations, AI grounding,
human correction persistence, object matching, the graph, and evaluation math. Frontend lint and a
production Next.js build cover the competition interface contract.

## Intentionally excluded or deferred

The PRD marks full report generation, telemetry/GPS, statement contradiction analysis, 2D/3D
trajectory visualization, mobile apps, facial/license-plate recognition, fault/liability decisions,
police integration, surveillance, and automated claims decisions as future or out of scope. None is
silently represented as an MVP feature.

Customer interviews, an organizational pilot, business success metrics, production storage and
database migration, retention policy, and 95% demonstration availability are operational validation
work—not facts that can be established by repository code alone.
