#!/usr/bin/env bash
# Demo HANA → BigQuery API with curl (no UI). Requires a running API on BASE_URL.
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8080/api/v1}"

echo "== Create programme (use customer_id dev-tenant for default auth) =="
PROG=$(curl -sS -X POST "$BASE_URL/programmes/" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo HANA-BQ","customer_id":"dev-tenant","sap_source_version":"S/4HANA 2020","target_version":"S/4HANA 2023"}')
PID=$(echo "$PROG" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "programme_id=$PID"

echo "== Discovery (stub) → landscape_id =="
DISC=$(curl -sS -X POST "$BASE_URL/discovery/$PID/discover" -H 'Content-Type: application/json' -d '{}')
LID=$(echo "$DISC" | python3 -c "import sys,json; print(json.load(sys.stdin)['landscape_id'])")
echo "landscape_id=$LID"

echo "== Create pipeline =="
PIPE=$(curl -sS -X POST "$BASE_URL/programmes/$PID/hana-bigquery/pipelines" \
  -H 'Content-Type: application/json' \
  -d "{\"landscape_id\":\"$LID\",\"name\":\"Demo pipeline\",\"replication_mode\":\"full\",\"table_mappings\":[{\"source_schema\":\"SYS\",\"source_table\":\"TABLES\",\"target_dataset\":\"demo_ds\",\"target_table\":\"sys_tables\"}]}")
PLID=$(echo "$PIPE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "pipeline_id=$PLID"

echo "== Validate HANA =="
curl -sS -X POST "$BASE_URL/programmes/$PID/hana-bigquery/pipelines/$PLID/validate" \
  -H 'Content-Type: application/json' -d '{}' | python3 -m json.tool

echo "== Run pipeline (5 rows per table) =="
curl -sS -X POST "$BASE_URL/programmes/$PID/hana-bigquery/pipelines/$PLID/runs" \
  -H 'Content-Type: application/json' \
  -d '{"row_limit_per_table":5}' | python3 -m json.tool

echo "Done. Open the UI: Programmes → pick programme → HANA → BigQuery tab."
