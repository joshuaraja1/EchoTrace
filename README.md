# EchoTrace

**One timeline. Every perspective.**

EchoTrace is an evidence reconstruction engine for commercial fleet incidents. It accepts fragmented
video, image, and document evidence; estimates a shared clock; builds an evidence-backed sequence;
and answers investigator questions with citations. It reconstructs what the evidence appears to
show and never assigns fault or liability.

## Implemented MVP

- Secure registration/login and owner-scoped investigations.
- Immutable, SHA-256-fingerprinted MP4, MOV, JPG, PNG, TXT, and PDF evidence.
- FFmpeg/OpenCV processing, optional YOLO detection, baseline tracking, and eight PRD event types.
- Metadata, audio, visual-motion, and trajectory-event synchronization with visible confidence.
- One chronological timeline with protected evidence/frame citations and audited corrections.
- Cross-camera match candidates with investigator confirmation or rejection.
- Grounded summary/Q&A through local rules or optional Microsoft Foundry and Azure AI Search.
- Optional private Azure AI Video Indexer transcript, OCR, label, scene, and shot enrichment.
- Interactive Next.js competition UI with three-camera playback, event jumps, Ask, and graph views.
- Phase 6 evaluator for every technical metric specified by the PRD.

## Run locally

Requirements: Python 3.9+, Node.js 22+, FFmpeg, and npm.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
echotrace-api --reload
```

In a second terminal:

```bash
cd web
npm install
npm run dev
```

Open the product at [http://127.0.0.1:3000](http://127.0.0.1:3000) and API documentation at
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

The containerized equivalent is:

```bash
docker compose up --build
```

## Verify

```bash
source .venv/bin/activate
pytest
ruff check src tests
cd web && npm run lint && npm run build
```

Evaluate a labeled incident trial:

```bash
echotrace-evaluate-trial examples/validation/controlled-trial.json \
  --output artifacts/validation/controlled-trial-report.json
```

The included JSON is a schema example with illustrative numbers—not a published performance result.

## Specialist CLIs

Probe one video and emit evidence-linked analysis:

```bash
echotrace-process-video camera-a.mp4 --output artifacts/camera-a --sample-fps 2
```

Estimate direct source offsets:

```bash
echotrace-sync camera-a.mp4 camera-b.mp4 camera-c.mp4 \
  --reference camera-a.mp4 --output artifacts/synchronization.json
```

Install optional YOLO support with `pip install -e '.[vision]'`. Install Azure adapters with
`pip install -e '.[azure]'`.

## Project truth

The software path for PRD phases 0–6 is implemented. The product is not yet entitled to accuracy,
availability, time-saved, or Imagine Cup readiness claims until the staged three-camera demo,
controlled/public/negative datasets, Azure deployment, and customer validation are actually run.

- [PRD traceability](docs/PRD_TRACEABILITY.md)
- [Backend and Azure adapter configuration](docs/BACKEND.md)
- [Deployment guide](docs/DEPLOYMENT.md)
- [Canonical phase roadmap](docs/ROADMAP.md)
- [Phase 0 measurement gate](docs/PHASE_0.md)
- [Phase 1 pipeline notes](docs/PHASE_1.md)
