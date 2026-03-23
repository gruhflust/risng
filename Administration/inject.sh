#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# inject.sh - Überträgt lokales Git-Repo per tar + ssh auf Zielhost
# -----------------------------------------------------------------------------
# Voraussetzung: passwortloser SSH-Zugriff
# Ziel: ~/risng auf Remote-Host exakt wie lokal
# -----------------------------------------------------------------------------

set -euo pipefail

TARGET_USER="risng"
TARGET_HOST="192.168.100.100"
REMOTE_SSH="${TARGET_USER}@${TARGET_HOST}"

REPO_NAME="risng"
REMOTE_HOME="/home/${TARGET_USER}"
REMOTE_PATH="${REMOTE_HOME}/${REPO_NAME}"

LOCAL_REPO="$(git rev-parse --show-toplevel)"

if ! git -C "${LOCAL_REPO}" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo "ERROR: ${LOCAL_REPO} ist kein gültiges Git-Repository"
  exit 1
fi

# 1. Verzeichnis auf Remote erzeugen
ssh "${REMOTE_SSH}" "mkdir -p '${REMOTE_PATH}'"

# 2. Lokales Repo als tar streamen und remote entpacken
echo "Übertrage Repository nach ${REMOTE_SSH}:${REMOTE_PATH} ..."
tar -C "${LOCAL_REPO}" -cf - . | ssh "${REMOTE_SSH}" "tar -xf - -C '${REMOTE_PATH}'"

# 3. Git-Status anzeigen (optional)
ssh "${REMOTE_SSH}" "cd '${REMOTE_PATH}' && git rev-parse --abbrev-ref HEAD && git log --oneline -1"

echo "Repository wurde erfolgreich übertragen."
