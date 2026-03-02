#!/usr/bin/env bash
set -euo pipefail

# cheaplanwatch_eantc runtime loader
# Parallel variant of cheaplanwatch-runner.sh to keep legacy unchanged.

SERVER_IP="${CHEAPLANWATCH_SERVER_IP:-10.228.229.7}"
SERVER_PORT="${CHEAPLANWATCH_SERVER_PORT:-}"
PORT_CANDIDATES="${CHEAPLANWATCH_PORT_CANDIDATES:-8088 18088 28088}"
REMOTE_URL="${CHEAPLANWATCH_URL:-}"
CACHE_DIR="/var/cache/cheaplanwatch"
CACHE_FILE="${CACHE_DIR}/cheaplanwatch-client_eantc.sh"
EMBEDDED="/usr/local/lib/cheaplanwatch/embedded_eantc.sh"

mkdir -p "${CACHE_DIR}"

# 1) Try dynamic fetch from server (runtime replaceable)
if command -v curl >/dev/null 2>&1; then
  fetched=0
  if [ -n "${REMOTE_URL}" ]; then
    if curl -fsSL --connect-timeout 3 --max-time 8 "${REMOTE_URL}" -o "${CACHE_FILE}.new"; then
      chmod +x "${CACHE_FILE}.new"
      mv "${CACHE_FILE}.new" "${CACHE_FILE}"
      fetched=1
    fi
  else
    ports="${PORT_CANDIDATES}"
    [ -n "${SERVER_PORT}" ] && ports="${SERVER_PORT} ${PORT_CANDIDATES}"
    for p in ${ports}; do
      url="http://${SERVER_IP}:${p}/cheaplanwatch-client_eantc.sh"
      if curl -fsSL --connect-timeout 3 --max-time 8 "$url" -o "${CACHE_FILE}.new"; then
        chmod +x "${CACHE_FILE}.new"
        mv "${CACHE_FILE}.new" "${CACHE_FILE}"
        fetched=1
        break
      fi
    done
  fi
  [ "$fetched" -eq 0 ] && rm -f "${CACHE_FILE}.new" || true
fi

# 2) Prefer freshest cached copy
if [ -x "${CACHE_FILE}" ]; then
  exec "${CACHE_FILE}" "$@"
fi

# 3) Fallback embedded copy from image build
exec "${EMBEDDED}" "$@"
