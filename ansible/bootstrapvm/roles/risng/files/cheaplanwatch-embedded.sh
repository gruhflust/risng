#!/usr/bin/env bash
set -euo pipefail

echo "cheaplanwatch (embedded fallback)"
echo "Noch keine Watch-Logik implementiert."
echo "Host: $(hostname) | IP: $(hostname -I 2>/dev/null | awk '{print $1}')"
