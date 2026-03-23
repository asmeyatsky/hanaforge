# HanaForge

**HanaForge** is an API-first platform for planning and operating **SAP S/4HANA** migration programmes on **Google Cloud**. It focuses on discovery, custom-code analysis, data-readiness checks against uploaded exports, infrastructure sizing and Terraform-style landing-zone generation, migration task orchestration (planning and simulated execution), cutover gates, benchmarks, and AI-assisted workflows (Anthropic).

## What this project does

| Area | Capability |
|------|------------|
| **Programmes** | Create and manage migration programmes (target S/4HANA version, scope). |
| **Discovery** | Connect to SAP (via adapter ports), extract metadata, custom objects, integration points; complexity scoring. |
| **ABAP** | Upload ABAP source archives (ZIP), parse objects, analysis workflows. |
| **Data readiness** | Upload **CSV / XLSX / LTMC XML** table exports, run profiling, BP consolidation and universal journal assessments, transformation-rule generation. |
| **Infrastructure** | GCP cost estimates, SAP-on-GCP validation, Terraform HCL generation (VPC, subnets, **SAP HANA on Compute Engine**, app servers, monitoring). |
| **Migration orchestrator** | Task graphs (e.g. DMO-style steps), batch execution hooks (stubs/simulation in places), audit trail. |
| **Cutover / hypercare** | Go/no-go gates, runbooks (domain services). |
| **Persistence** | In-memory repositories by default; optional **Firestore** and **GCS** when configured. |
| **Frontend** | React (Vite) UI; production Docker image builds static assets and serves via the API host. |
| **HANA → BigQuery** | Programme-scoped **data pipelines**: map HANA tables to BigQuery datasets/tables, validate connectivity, run **extract → stage → load** (stub or real). |

OpenAPI docs are available at `/docs` when the API is running.

## SAP HANA → BigQuery pipelines

HanaForge includes a **first-party path** to copy table data from **SAP HANA** into **BigQuery**:

1. **Define a pipeline** under a programme (requires an existing **landscape** from discovery): source schema/table → target dataset/table.
2. **Validate** HANA connectivity (optional body overrides connection settings).
3. **Run** the pipeline: CSV extract (stub or **`hdbcli`** when `HANAFORGE_HANA_ADDRESS` is set), stage to **local storage** or **GCS** (`HANAFORGE_GCS_BUCKET` + `HANAFORGE_GCP_PROJECT_ID`), then **BigQuery load** (stub or real when `HANAFORGE_BQ_USE_REAL_CLIENT=true`).

**API** (all under `/api/v1/programmes/{programme_id}/…`):

- `POST …/hana-bigquery/pipelines` — create pipeline  
- `GET …/hana-bigquery/pipelines` — list  
- `GET …/hana-bigquery/pipelines/{pipeline_id}` — get  
- `POST …/hana-bigquery/pipelines/{pipeline_id}/validate` — HANA connectivity check  
- `POST …/hana-bigquery/pipelines/{pipeline_id}/runs` — execute (JSON: optional `row_limit_per_table`, nested `hana_connection`)  
- `GET …/hana-bigquery/pipelines/{pipeline_id}/runs` — list runs  
- `GET …/hana-bigquery/pipelines/{pipeline_id}/runs/{run_id}` — run detail  

**Defaults without HANA env vars:** a **stub** extractor returns synthetic CSV so flows can be tested locally. **Real BigQuery** loads require **`gs://`** staging — set **GCS bucket + project** and enable **`HANAFORGE_BQ_USE_REAL_CLIENT`**. **CDC** mode is accepted on pipelines but **not implemented** yet (runs return 400).

**Still separate from “data readiness”:** uploading CSV/XLSX/LTMC for **profiling** (`/api/v1/data-readiness/…`) remains a distinct feature for S/4 migration quality, not the HANA→BQ loader.

**Optional:** `pip install 'hanaforge[hana]'` for the **`hdbcli`** driver.

## Requirements

- **Python** 3.12+
- **Node.js** 20+ (for local frontend development)
- Optional: **Docker** for containerized run
- Optional: GCP project, Firestore, GCS bucket, Anthropic API key for full cloud/AI features

## Configuration

Settings use the `HANAFORGE_` prefix (see `infrastructure/config/settings.py`). Examples:

| Variable | Purpose |
|----------|---------|
| `HANAFORGE_GCP_PROJECT_ID` | GCP project |
| `HANAFORGE_FIRESTORE_DATABASE` | Firestore database id |
| `HANAFORGE_GCS_BUCKET` | Artefact / export storage |
| `HANAFORGE_ANTHROPIC_API_KEY` | Claude / agent features |
| `HANAFORGE_USE_FIRESTORE` | `true` to use Firestore instead of in-memory repos |
| `HANAFORGE_AUTH_ENABLED` | `true` to enforce JWT auth |
| `HANAFORGE_CORS_ALLOWED_ORIGINS` | Comma-separated origins or `*` (dev only) |
| `HANAFORGE_HANA_ADDRESS` | HANA host (enables `hdbcli` extractor when set) |
| `HANAFORGE_HANA_PORT` | HANA SQL port (default `443`) |
| `HANAFORGE_HANA_USER` / `HANAFORGE_HANA_PASSWORD` | HANA credentials (prefer secrets in production) |
| `HANAFORGE_BQ_USE_REAL_CLIENT` | `true` for real BigQuery load jobs (needs GCS staging URI) |
| `HANAFORGE_BQ_DEFAULT_LOCATION` | BigQuery dataset location (e.g. `US`) |

Copy `.env.example` to `.env` and adjust names to match the `HANAFORGE_` prefix as needed.

## Run the API locally

```bash
cd /path/to/hanaforge
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

uvicorn presentation.api.main:app --reload --host 0.0.0.0 --port 8080
```

- Health: `GET http://localhost:8080/health`
- API base: `/api/v1/...` (e.g. `/api/v1/programmes`)

## Run the frontend locally

```bash
cd frontend
npm ci
npm run dev
```

The dev server proxies `/api` to **`http://localhost:8080`** (same port as the `uvicorn` example above).

## Demo: HANA → BigQuery — **stub only** (~5 min)

No SAP HANA instance, no GCP project, and no `hdbcli` are required. Defaults use a **synthetic CSV** extractor and a **fake BigQuery job id**; staging goes to **local disk** under `/tmp/hanaforge-storage/` as `hanaforge-local://…` URIs.

**Do not set** (for this demo): `HANAFORGE_HANA_ADDRESS`, `HANAFORGE_BQ_USE_REAL_CLIENT`, or a GCS bucket for staging. Leave **`HANAFORGE_AUTH_ENABLED`** unset or `false`.

1. **Terminal A — API**

   ```bash
   cd /path/to/hanaforge
   source .venv/bin/activate   # or create venv per “Run the API locally”
   uvicorn presentation.api.main:app --reload --host 0.0.0.0 --port 8080
   ```

2. **Terminal B — UI**

   ```bash
   cd frontend && npm ci && npm run dev
   ```

   Open `http://localhost:3000`, create a programme with **customer_id** `dev-tenant`, open it → **HANA → BigQuery**.

3. **Run discovery (stub SAP)** → **Create pipeline** → **Validate HANA** → **Run pipeline**. Expect **completed** status, **row_limit** respected, **`hanaforge-local://…`**, and **`stub-load-job-…`**.

**Curl-only:** `./scripts/demo_hana_bigquery.sh` (same stub path; requires API on port 8080).

## Docker

```bash
docker build -t hanaforge .
docker run --rm -p 8080:8080 --env-file .env hanaforge
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

For CI-style checks: `pip install -e ".[ci]"` then run **ruff**, **mypy**, and **pytest** as in your pipeline.

## Architecture (brief)

- **`domain/`** — entities, value objects, domain services (pure business logic).
- **`application/`** — use cases, commands, queries, orchestration.
- **`infrastructure/`** — adapters (SAP RFC stub, Firestore/GCS, parsers, MCP servers, Terraform text generation).
- **`presentation/`** — FastAPI routes and middleware.

This follows a hexagonal / ports-and-adapters style: many external systems are behind interfaces and may be stubbed in development.

## Licence / status

Internal or project-specific licence is not set in this README; refer to repository policies. This is an active codebase—verify behaviour against tests and your environment before production use.
