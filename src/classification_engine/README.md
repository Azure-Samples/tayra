# Classification Engine

FastAPI microservice plus background workers that classify call-center transcripts stored in Azure Cosmos DB. It exposes a lightweight API for fetching transcription data and a CLI/worker pipeline that replays Cosmos records through an Azure AI Foundry agent to assign intent labels (order creation/modification/follow-up/other).

## Prerequisites
- Python 3.11+
- Azure resources: Cosmos DB (Core/SQL), Azure AI Foundry project + model deployment, Storage account for transcripts (optional)
- Environment variables in `.env` (see `.env.example` if available):
	- `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DB_TRANSCRIPTION`, `CONTAINER_NAME`
	- `AZURE_AI_PROJECT_ENDPOINT`, `AZURE_AI_MODEL_DEPLOYMENT_NAME`, `CALL_CLASSIFIER_AGENT_NAME`
	- Optional: `COSMOS_USE_AAD=true` to rely on Azure AD auth

## Install
```bash
cd src/classification_engine
pip install -r requirements.txt  # or `pip install -e .` from repo root
```

## Run the FastAPI surface
```bash
uvicorn app.main:app --reload --port 8080
# or use the helper script
bash run.sh
```
Endpoints:
- `POST /classification` – enqueue the background job via `background.run_classification_job`.
- `GET /transcriptions`, `/transcription-by-file`, `/classification-records` – read Cosmos data.

## Batch classification pipeline
Classify all transcripts via Azure AI agent:
```bash
python src/classification_engine/app/classify.py \
	--manager-name "REGION_A" \
	--specialist-name "AGENT_01" \
	--limit 50 \
	--skip-already-classified False  # reprocess existing results
```
Key flags (also configurable through env vars):
- `--skip-already-classified`: set to `False` to reclassify everything.
- `--only-valid-calls`: default `True`; flip to include short/invalid calls.

Reclassification tips:
1. Set `skip_already_classified=False` when running the pipeline.
2. (Optional) Clear historical records in the `classifications` container if you want a fresh output set.

## Build the container image
Use the provided Dockerfile to package the FastAPI surface and background workers. From the repo root:

```bash
# Build remotely with Azure Container Registry (no local Docker needed)

# assumes ACR_NAME already exported (e.g., export ACR_NAME=tayraacr123)
RES_GROUP="$ACR_NAME"

az group create --resource-group "$RES_GROUP" --location eastus

az acr create \
  --resource-group "$RES_GROUP" \
  --name "$ACR_NAME" \
  --sku Standard \
  --location eastus

az acr build \
  --registry $ACR_NAME \
  --image tayra-classification:latest \
  --file src/classification_engine/DOCKERFILE \
  .
	

# Or run locally if Docker Desktop is available
docker build -f src/classification_engine/DOCKERFILE -t tayra-classification:local .
docker run --rm -p 8080:8080 --env-file .env tayra-classification:local
```
After the ACR build finishes, reference `<acrName>.azurecr.io/tayra-classification:latest` in your deployment (Container Apps, App Service, etc.).

## Deploy the web app stack (infra.webapp.bicep)
`src/classification_engine/infra.webapp.bicep` provisions the entire web tier (Storage, App Service plan, Function, Web Apps, Cosmos DB, Search, Speech, API Management, Service Bus). The template now targets a resource group scope, so create/select a resource group first.

1. Sign in, select your subscription, and create (or reuse) a resource group. Optionally set it as the global default so subsequent `az` commands don’t need `--resource-group` each time:

```bash
az login
az account set --subscription <subscription-id>

# Optional but handy so az CLI always uses this group/location by default
az configure --defaults group=rg-tayra-app location=eastus
```

2. Deploy the Bicep at the **resource group** scope. Override globally unique names as needed (storage, web apps, speech, etc.). The `location` parameter inherits from the group, so you typically don’t need to set it explicitly.

```bash
az deployment group create \
  --template-file src/classification_engine/infra.webapp.bicep \
  --resource-group rg-tayra-app \
  --parameters \
    storageAccountName=<uniqueStorage> \
    webApiName=<uniqueApiApp> \
    webAdapterName=<uniqueAdapterApp> \
    speechAccountName=<uniqueSpeechName>
```

3. Capture the outputs (`webApiEndpoint`, `webAdapterEndpoint`, `storageEndpoint`, `cosmosDbEndpoint`, etc.) and feed them into your app settings or deployment secrets. Re-run the deployment with `--parameters containerImage=<registry/image:tag>` if you want App Service to pull a container instead of code.

## Troubleshooting
- Missing env vars → Runtime errors from `ClassificationDatabase` or `CosmosTranscriptionRepository`.
- `ServiceResponseException` or `429` from Azure AI → pipeline auto-retries with backoff; adjust `CALL_CLASSIFIER_MAX_RETRIES` and `CALL_CLASSIFIER_RETRY_BACKOFF` for heavier loads.
- Cosmos AAD auth: set `COSMOS_USE_AAD=true` and ensure `az login`/managed identity has `Cosmos DB Account Reader` + `Data Contributor` roles.
