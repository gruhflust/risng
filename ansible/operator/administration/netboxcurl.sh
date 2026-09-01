#!/usr/bin/env bash
# NetBox rack information query via curl
# Usage: BASE_URL=<https://netbox.example.com> ./netboxcurl.sh
# Default BASE_URL matches the playbook target if not provided.

set -euo pipefail

BASE_URL=${BASE_URL:-"https://cmdb01.stable.dc.dev.int.dfs.de"}
NETBOX_USER="risng"
TOKEN_FILE="$HOME/token.md"

if [[ ! -r "${TOKEN_FILE}" ]]; then
  echo "Error: Token file not found or unreadable at ${TOKEN_FILE}" >&2
  exit 1
fi

NETBOX_TOKEN=$(head -n 1 "${TOKEN_FILE}" | tr -d '\r\n')

if [[ -z "${NETBOX_TOKEN}" ]]; then
  echo "Error: Token file at ${TOKEN_FILE} is empty" >&2
  exit 1
fi

curl -k \
  -H "Authorization: Token ${NETBOX_TOKEN}" \
  -H "X-NetBox-User: ${NETBOX_USER}" \
  -H "Accept: application/json" \
  "${BASE_URL}/api/dcim/racks/?limit=0" \
  | jq .
