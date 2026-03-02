#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-19765}"
LOG_FILE="${2:-$HOME/cheaplanwatch/cheaplanwatch-qperf.log}"
RUN_META_FILE="${CHEAPLANWATCH_RUN_META_FILE:-$HOME/cheaplanwatch/current-run.env}"
MODE_NOTE="cheaplanwatch live mode (live|imix) | cheaplantest uses IMIX profile matrix"
TARGETS_FILE="${CHEAPLANWATCH_TARGETS_FILE:-${RISNG_ANSIBLE_DIR:-}/runtime/qperf/qperf_targets.yml}"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=2 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)

read_meta() {
  if [ -f "$RUN_META_FILE" ]; then
    # shellcheck disable=SC1090
    source "$RUN_META_FILE"
  fi
}

list_targets() {
  [ -f "$TARGETS_FILE" ] || return 0
  awk '
    /^  - name:/ {name=$3; gsub(/"/, "", name)}
    /^    ip:/ {ip=$2; gsub(/"/, "", ip); if(name!="" && ip!="") print name " " ip}
  ' "$TARGETS_FILE"
}

latest_sample_line() {
  local ip="${1:?ip missing}" run_id="${2:?run id missing}"
  ssh "${SSH_OPTS[@]}" "root@${ip}" "f=/tmp/cheaplanwatch/${run_id}-*.samples.ndjson; test -e \$f || exit 3; tail -n 1 \$f 2>/dev/null | tail -n 1" 2>/dev/null || true
}

parse_sample() {
  python3 - <<'PY' "$1"
import json, sys
line = sys.argv[1].strip()
if not line:
    print('n/a|n/a|n/a|n/a|n/a')
    raise SystemExit
try:
    obj = json.loads(line)
except Exception:
    print('parse-error|parse-error|parse-error|parse-error|parse-error')
    raise SystemExit
print('|'.join([
    str(obj.get('ts_iso', obj.get('ts_epoch', ''))),
    str(obj.get('tcp_bw', 'n/a')),
    str(obj.get('tcp_lat', 'n/a')),
    str(obj.get('imix_msg_size', '')),
    str(obj.get('mode', '')),
]))
PY
}

render_client_table() {
  local tsv_file="${1:?tsv file missing}"
  python3 - <<'PY' "$tsv_file"
import re, sys
from pathlib import Path

path = Path(sys.argv[1])
rows = []
if path.exists():
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 6:
            continue
        rows.append(parts[:6])

def bw_to_gbit_and_gbyte_per_s(text: str):
    """Convert bandwidth string to normalized Gbit/s and GByte/s.
    Handles qperf/iperf-like forms such as:
      - 26.4 Gbit/s
      - 26.4 Gbits/sec
      - 3.1 GB/sec
      - 980 Mb/s
    Returns (gbit_s, gbyte_s) or (None, None).
    """
    if not text:
        return None, None

    s = text.strip()
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*([kKmMgGtT]?)([bB])(?:it|yte)?(?:/s|/sec|ps)?', s)
    if not m:
        return None, None

    val = float(m.group(1))
    prefix = m.group(2).upper()
    b_or_B = m.group(3)  # lowercase b=bit, uppercase B=byte

    prefix_factor = {
        '': 1.0,
        'K': 1e3,
        'M': 1e6,
        'G': 1e9,
        'T': 1e12,
    }.get(prefix, 1.0)

    if b_or_B == 'B':
        byte_per_s = val * prefix_factor
        bit_per_s = byte_per_s * 8.0
    else:
        bit_per_s = val * prefix_factor
        byte_per_s = bit_per_s / 8.0

    gbit_s = bit_per_s / 1e9
    gbyte_s = byte_per_s / 1e9
    return gbit_s, gbyte_s

print(f"{'client':18} {'ip':16} {'tcp_bw(raw)':18} {'tcp_bw[Gbit/s]':13} {'tcp_bw[GB/s]':12} {'tcp_lat':12} {'imix_msg_size':14} {'mode':8}")

total_gbit = 0.0
total_gbyte = 0.0
count_bw = 0
for name, ip, bw, lat, imix, mode in rows:
    gbit, gbyte = bw_to_gbit_and_gbyte_per_s(bw)
    if gbit is not None and gbyte is not None:
        total_gbit += gbit
        total_gbyte += gbyte
        count_bw += 1
        gbit_s = f"{gbit:10.3f}"
        gbyte_s = f"{gbyte:9.3f}"
    else:
        gbit_s = f"{'n/a':>10}"
        gbyte_s = f"{'n/a':>9}"

    print(f"{name[:18]:18} {ip[:16]:16} {bw[:18]:18} {gbit_s:13} {gbyte_s:12} {lat[:12]:12} {imix[:14] or 'live':14} {(mode or 'n/a')[:8]:8}")

print('')
print(f"SUM from clients: tcp_bw_total ≈ {total_gbit:.3f} Gbit/s | {total_gbyte:.3f} GB/s (across {count_bw}/{len(rows)} parsed clients)")
print('Hint: this is a sum of client-side measured rates normalized by unit, not kernel NIC counters.')
PY
}

while true; do
  clear
  read_meta

  port_now="${SERVER_PORT:-$PORT}"
  run_id_now="${CHEAPLANWATCH_RUN_ID:-${RUN_ID:-}}"
  mode_now="${WATCH_MODE:-n/a}"

  echo "risng - Cloud Host Endpoint Analysis Probe"
  echo "cheapwatch | $(date '+%F %T')"
  echo "Port: ${port_now}"
  echo "Run : ${run_id_now:-unknown}"
  echo "Mode: ${mode_now} | ${MODE_NOTE}"
  echo "Log : ${LOG_FILE}"
  echo

  echo "[qperf listener + client connections]"
  ss -tanp 2>/dev/null | grep -E ":${port_now}\\b" || echo "no connections"
  echo

  echo "[per-client latest sample + summed throughput]"
  if [ -z "${run_id_now:-}" ]; then
    echo "no run id yet (start cheaplanwatchserver first)"
  else
    tmp_tsv="$(mktemp)"
    while read -r name ip; do
      [ -n "$name" ] || continue
      sample="$(latest_sample_line "$ip" "$run_id_now")"
      parsed="$(parse_sample "$sample")"
      ts="${parsed%%|*}"; rest="${parsed#*|}"
      bw="${rest%%|*}"; rest="${rest#*|}"
      lat="${rest%%|*}"; rest="${rest#*|}"
      imix="${rest%%|*}"; mode="${rest#*|}"
      printf "%s\t%s\t%s\t%s\t%s\t%s\n" "$name" "$ip" "$bw" "$lat" "${imix:-live}" "${mode:-$mode_now}" >> "$tmp_tsv"
    done < <(list_targets)

    render_client_table "$tmp_tsv"
    rm -f "$tmp_tsv"
  fi
  echo

  echo "[last qperf log lines (non-noisy)]"
  if [ -f "${LOG_FILE}" ]; then
    grep -v "failed to receive request version: client not responding" "${LOG_FILE}" | tail -n 20 || true
  else
    echo "no log yet"
  fi
  echo

  echo "[noise counter: client not responding]"
  if [ -f "${LOG_FILE}" ]; then
    grep -c "failed to receive request version: client not responding" "${LOG_FILE}" || true
  else
    echo "0"
  fi
  echo

  echo "Ctrl+C beendet cheapwatch"
  sleep 2
done
