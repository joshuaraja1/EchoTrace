# EchoTrace Backend

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
echotrace-api --reload
```

Interactive API documentation: `http://127.0.0.1:8000/docs`.

The API requires authentication by default. Register through `/auth/register`, then use the
returned bearer token. Passwords are salted and hashed with PBKDF2-HMAC-SHA256. Tokens are signed,
expire after eight hours, and use a secret stored with owner-only permissions under the data
directory unless `ECHOTRACE_JWT_SECRET` is configured.

## End-to-end flow

1. Register or log in.
2. Create an investigation.
3. Upload MP4, MOV, JPG, JPEG, PNG, TXT, or PDF evidence.
4. Process the investigation.
5. Automatically synchronize at least two analyzed videos.
6. Review offsets and manually correct them when necessary.
7. Review the unified timeline and object match candidates.
8. Confirm or reject cross-camera matches.
9. Request a cited summary or ask an evidence-grounded question.
10. Inspect the evidence graph.

## Backend API groups

- `/auth`: registration, login, and current user.
- `/investigations`: investigation lifecycle and owner scoping.
- `/evidence`: immutable upload records and processing state.
- `/process`: multimodal processing and derived artifacts.
- `/synchronize`: metadata, audio, visual-motion, and trajectory-event alignment fusion.
- `/timeline`: local-to-global time mapping and evidence citations.
- `/objects`: observations and cross-camera match review.
- `/summary` and `/ask`: grounded incident intelligence.
- `/graph`: inspectable investigation → evidence → event relationships.

## Data safety

- Original evidence files are never modified after upload.
- SHA-256 digests identify stored evidence.
- Derived frames, text, observations, events, and AI responses are stored separately.
- Low-confidence synchronization and object matches require review.
- AI output is limited to supplied investigation evidence and cannot determine fault or liability.
- Uploaded evidence is owner-scoped through authenticated investigations.

## Microsoft Foundry

The default reasoner and search implementation are deterministic local providers so development
does not require cloud credentials.

Install Azure adapters:

```bash
pip install -e '.[azure]'
az login
```

Configure Microsoft Foundry reasoning:

```bash
export ECHOTRACE_REASONER=azure
export AZURE_AI_PROJECT_ENDPOINT='https://RESOURCE.services.ai.azure.com/api/projects/PROJECT'
export AZURE_AI_MODEL='YOUR_MODEL_DEPLOYMENT'
```

Configure Azure AI Search:

```bash
export ECHOTRACE_SEARCH=azure
export AZURE_SEARCH_ENDPOINT='https://RESOURCE.search.windows.net'
export AZURE_SEARCH_INDEX='echotrace-evidence'
```

The Search index must expose these fields: `id` (key), `investigation_id` (filterable), `event_id`,
`content` (searchable), `event_type`, and `timestamp_seconds`. Azure calls use
`DefaultAzureCredential`; credentials are not stored in source code.

Private Azure AI Video Indexer is also supported for transcript, OCR, scene, label, and keyword
enrichment. See [DEPLOYMENT.md](DEPLOYMENT.md) for its environment variables and safeguards.

## Runtime configuration

- `ECHOTRACE_DATA_DIR`: local evidence/database root; default `./data`.
- `ECHOTRACE_JWT_SECRET`: production token signing secret.
- `ECHOTRACE_CORS_ORIGINS`: comma-separated frontend origins; defaults to local port 3000.
- `ECHOTRACE_REASONER`: `local` or `azure`.
- `ECHOTRACE_SEARCH`: `local` or `azure`.
- `ECHOTRACE_VIDEO_INTELLIGENCE`: `local` or `azure`.

## Known deployment work

The local MVP uses SQLite, local immutable file storage, and synchronous processing. Production
deployment still requires Azure Blob Storage, PostgreSQL, a background job queue, tenant-level
authorization, retention policies, monitoring, and provisioned Microsoft Foundry/Search resources.
Those are deployment-hardening tasks, not completed production claims.
