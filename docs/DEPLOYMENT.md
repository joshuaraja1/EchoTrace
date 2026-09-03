# EchoTrace deployment guide

## Local competition stack

Run both applications with containers:

```bash
docker compose up --build
```

The workspace is served at `http://127.0.0.1:3000`; authenticated API documentation is at
`http://127.0.0.1:8000/docs`. The Compose volume persists original evidence, analysis artifacts,
the SQLite database, and the signing secret.

For faster development, run the services directly:

```bash
source .venv/bin/activate
echotrace-api --reload
```

```bash
cd web
npm install
npm run dev
```

## Azure application adapters

EchoTrace defaults to deterministic local analysis. Install and authenticate Azure adapters only
when provisioned resources are available:

```bash
pip install -e '.[azure]'
az login
```

Microsoft Foundry reasoning:

```bash
export ECHOTRACE_REASONER=azure
export AZURE_AI_PROJECT_ENDPOINT='https://RESOURCE.services.ai.azure.com/api/projects/PROJECT'
export AZURE_AI_MODEL='MODEL_DEPLOYMENT'
```

Azure AI Search grounding:

```bash
export ECHOTRACE_SEARCH=azure
export AZURE_SEARCH_ENDPOINT='https://RESOURCE.search.windows.net'
export AZURE_SEARCH_INDEX='echotrace-evidence'
```

Private Azure AI Video Indexer enrichment:

```bash
export ECHOTRACE_VIDEO_INTELLIGENCE=azure
export AZURE_VIDEO_INDEXER_SUBSCRIPTION_ID='SUBSCRIPTION_ID'
export AZURE_VIDEO_INDEXER_RESOURCE_GROUP='RESOURCE_GROUP'
export AZURE_VIDEO_INDEXER_ACCOUNT_NAME='ACCOUNT_RESOURCE_NAME'
export AZURE_VIDEO_INDEXER_ACCOUNT_ID='ACCOUNT_GUID'
export AZURE_VIDEO_INDEXER_LOCATION='REGION'
```

The adapter requests a short-lived account token through `DefaultAzureCredential`, uploads with
`privacy=Private`, excludes face/observed-person/emotion models, and retains only transcript, OCR,
labels, keywords, scenes, and shots. A Video Indexer outage is recorded as an enrichment warning;
the local evidence pipeline remains usable.

## Azure Container Apps scaffold

`azure.yaml` describes the API and web containers for Azure Developer CLI. Before `azd up`, set the
web build argument `NEXT_PUBLIC_API_URL` to the final HTTPS API ingress and configure the API CORS
origin to the final HTTPS web ingress. Use a production `ECHOTRACE_JWT_SECRET` from Key Vault.

The repository is container-ready, but the local SQLite/file volume is deliberately not presented
as production cloud storage. A production pilot still requires Azure Blob Storage, PostgreSQL,
managed identities, private networking or equivalent access controls, retention rules, backups,
and monitoring. Those resource choices affect cost and customer data governance and therefore
must be provisioned with the owner's Azure subscription rather than guessed in source code.
