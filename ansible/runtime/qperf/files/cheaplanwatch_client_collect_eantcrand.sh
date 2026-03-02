#!/usr/bin/env bash
set -euo pipefail

# cheaplanwatch_client_collect_eantcrand.sh
# Randomized EANTC IMIX per-sample selection (weighted), to avoid sequential blocks.
#
# Usage:
#   cheaplanwatch_client_collect_eantcrand.sh <server_ip> <server_port> <duration_sec> <interval_sec> <out_json> <out_log>

SERVER_IP="${1:?server_ip}"
SERVER_PORT="${2:?server_port}"
DURATION_SEC="${3:?duration_sec}"
INTERVAL_SEC="${4:?interval_sec}"
JSON_OUT="${5:?out_json}"
LOG_OUT="${6:?out_log}"

REPORT_BANNER="risng - Cloud Host Endpoint Analysis Probe"
MODE="eantc-imix-rand"

# deterministic seed optional (env); if absent, seed from epoch
SEED="${CHEAPLANWATCH_SEED:-$(date +%s)}"
RANDOM="$SEED"

# EANTC weights
# format: msg_size|weight
IMIX_TABLE=(
  "60:60:*5243|5243"
  "132:132:*861|861"
  "296:296:*273|273"
  "468:468:*233|233"
  "557:557:*230|230"
  "952:952:*127|127"
  "1010:1010:*151|151"
  "1500:1500:*2882|2882"
  "8800:8800:*2|2"
)

TOTAL_WEIGHT=0
for row in "${IMIX_TABLE[@]}"; do
  w="${row##*|}"
  TOTAL_WEIGHT=$((TOTAL_WEIGHT + w))
done

pick_msg_size() {
  # weighted random draw using $RANDOM (0..32767)
  # We expand to a bigger range with two draws.
  local r1=$RANDOM
  local r2=$RANDOM
  local r=$(( (r1 << 15) ^ r2 ))
  local x=$(( r % TOTAL_WEIGHT ))
  local acc=0
  local entry msg w
  for entry in "${IMIX_TABLE[@]}"; do
    msg="${entry%%|*}"
    w="${entry##*|}"
    acc=$((acc + w))
    if [ "$x" -lt "$acc" ]; then
      printf '%s' "$msg"
      return 0
    fi
  done
  printf '%s' "1500:1500:*2882"
}

qperf_metric() {
  # parse the numeric+unit token from qperf output line(s)
  awk '{for(i=1;i<=NF;i++){if($i ~ /^[0-9]+(\.[0-9]+)?$/){print $i " " $(i+1); exit}}}'
}

run_qperf_test() {
  local test="$1"
  local msg_size="$2"
  qperf -lp "$SERVER_PORT" "$SERVER_IP" "$test" -oo "msg_size:${msg_size}" 2>/dev/null || true
}

has_iperf3=0
command -v iperf3 >/dev/null 2>&1 && has_iperf3=1

baseline_tcp_bw_raw="$(qperf -lp "$SERVER_PORT" "$SERVER_IP" tcp_bw 2>/dev/null | qperf_metric || true)"
baseline_tcp_lat_raw="$(qperf -lp "$SERVER_PORT" "$SERVER_IP" tcp_lat 2>/dev/null | qperf_metric || true)"
baseline_tcp_bw="${baseline_tcp_bw_raw:-n/a}"
baseline_tcp_lat="${baseline_tcp_lat_raw:-n/a}"

baseline_iperf=""
if [ "$has_iperf3" -eq 1 ]; then
  baseline_iperf="$(iperf3 -c "$SERVER_IP" -t 5 2>/dev/null | awk '/receiver$/ {print $(NF-2) " " $(NF-1); exit}' || true)"
fi
[ -z "${baseline_iperf}" ] && baseline_iperf="n/a (iperf3 server not reachable?)"

ping_line="$(ping -c 8 "$SERVER_IP" 2>/dev/null | awk -F'=' '/rtt|round-trip/ {print $2}' | tr -d ' ' || true)"
base_ping_avg="$(printf '%s' "$ping_line" | cut -d/ -f2)"
base_ping_jitter="$(printf '%s' "$ping_line" | cut -d/ -f4)"
if ping -M do -s 1472 -c 1 "$SERVER_IP" >/dev/null 2>&1; then mtu_status="ok"; else mtu_status="failed"; fi

RUN_TS="$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)"
HOST_SHORT="$(hostname -s 2>/dev/null || hostname)"
SAMPLES_NDJSON="${JSON_OUT}.samples.ndjson"

# observed counts (assoc array)
declare -A OBS_COUNTS
for row in "${IMIX_TABLE[@]}"; do
  msg="${row%%|*}"
  OBS_COUNTS["$msg"]=0
done

: >"$SAMPLES_NDJSON"
: >"$LOG_OUT"

write_json() {
python3 - <<'PY' "$SAMPLES_NDJSON" "$JSON_OUT" "$RUN_TS" "$HOST_SHORT" "$SERVER_IP" "$SERVER_PORT" "$baseline_tcp_bw" "$baseline_tcp_lat" "$baseline_iperf" "$base_ping_avg" "$base_ping_jitter" "$mtu_status" "$REPORT_BANNER" "$MODE" "$SEED" "$TOTAL_WEIGHT" "${IMIX_TABLE[@]}"
import json, pathlib, sys
samples_path, json_out, run_ts, host_short, server_ip, server_port, b_bw, b_lat, b_iperf, b_avg, b_jit, mtu, banner, mode, seed, total_weight, *imix_table = sys.argv[1:]
# read samples
samples=[]
sp=pathlib.Path(samples_path)
if sp.exists():
    for line in sp.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if line:
            samples.append(json.loads(line))
# observed counts
obs={}
for entry in samples:
    ms=entry.get('imix_msg_size')
    if ms:
        obs[ms]=obs.get(ms,0)+1
expected={}
for row in imix_table:
    msg, w = row.split('|',1)
    expected[msg]=int(w)
obj={
  'report_banner': banner,
  'mode': mode,
  'seed': int(seed),
  'imix': {
    'kind': 'eantc',
    'total_weight': int(total_weight),
    'expected_weight': expected,
    'observed_count': obs,
  },
  'generated_at': run_ts,
  'host': host_short,
  'address': '',
  'server_ip': server_ip,
  'server_port': int(server_port),
  'baseline': {
    'tcp_bw': b_bw,
    'tcp_lat': b_lat,
    'iperf_bw': b_iperf,
    'ping_avg': b_avg,
    'ping_jitter': b_jit,
    'mtu': mtu,
  },
  'samples': samples,
}
pathlib.Path(json_out).write_text(json.dumps(obj, indent=2, sort_keys=True), encoding='utf-8')
PY
}

cleanup() {
  write_json || true
}
trap cleanup EXIT INT TERM

start_epoch="$(date +%s)"
end_epoch=$((start_epoch + DURATION_SEC))

while [ "$(date +%s)" -lt "$end_epoch" ]; do
  ts="$(date +%s)"
  ts_iso="$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)"

  msg_size="$(pick_msg_size)"
  OBS_COUNTS["$msg_size"]=$(( OBS_COUNTS["$msg_size"] + 1 ))

  tcp_bw="$(run_qperf_test tcp_bw "$msg_size" | qperf_metric || true)"
  tcp_lat="$(run_qperf_test tcp_lat "$msg_size" | qperf_metric || true)"
  pline="$(ping -c 4 "$SERVER_IP" 2>/dev/null | awk -F'=' '/rtt|round-trip/ {print $2}' | tr -d ' ' || true)"
  pavg="$(printf '%s' "$pline" | cut -d/ -f2)"
  pjit="$(printf '%s' "$pline" | cut -d/ -f4)"

  printf '{"ts_epoch":%s,"ts_iso":"%s","mode":"%s","imix_msg_size":"%s","tcp_bw":"%s","tcp_lat":"%s","ping_avg":"%s","ping_jitter":"%s"}\n' \
    "$ts" "$ts_iso" "$MODE" "$msg_size" "$tcp_bw" "$tcp_lat" "$pavg" "$pjit" >>"$SAMPLES_NDJSON"

  write_json || true
  sleep "$INTERVAL_SEC"
done
