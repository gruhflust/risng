#!/usr/bin/env bash
set -euo pipefail

# EANTC IMIX mix (from botbrain traffic-mix-eanc.png)
# We apply qperf's msg_size mix to tcp_bw/tcp_lat probes to emulate the distribution.

SERVER_IP="${1:?server ip missing}"
SERVER_PORT="${2:?server port missing}"
DURATION="${3:-60}"
INTERVAL="${4:-2}"
OUT_JSON="${5:?out json missing}"
OUT_LOG="${6:?out log missing}"

# qperf msg_size mix (min=max:*repeat entries)
EANTC_MSG_SIZE_MIX="60:60:*5243,132:132:*861,296:296:*273,468:468:*233,557:557:*230,952:952:*127,1010:1010:*151,1500:1500:*2882,8800:8800:*2"

mkdir -p "$(dirname "$OUT_JSON")"

qnum(){ awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+(\.[0-9]+)?$/){print $i; exit}}'; }

baseline_tcp_bw_raw="$(qperf -lp "$SERVER_PORT" "$SERVER_IP" tcp_bw -oo msg_size:"$EANTC_MSG_SIZE_MIX" 2>/dev/null || true)"
baseline_tcp_lat_raw="$(qperf -lp "$SERVER_PORT" "$SERVER_IP" tcp_lat -oo msg_size:"$EANTC_MSG_SIZE_MIX" 2>/dev/null || true)"
baseline_tcp_bw="$(printf '%s\n' "$baseline_tcp_bw_raw" | qnum)"
baseline_tcp_lat="$(printf '%s\n' "$baseline_tcp_lat_raw" | qnum)"

ping_line="$(ping -c 8 "$SERVER_IP" 2>/dev/null | awk -F'=' '/rtt|round-trip/ {print $2}' | tr -d ' ' || true)"
base_ping_avg="$(printf '%s' "$ping_line" | cut -d/ -f2)"
base_ping_jitter="$(printf '%s' "$ping_line" | cut -d/ -f4)"
if ping -M do -s 1472 -c 1 "$SERVER_IP" >/dev/null 2>&1; then mtu_status="ok"; else mtu_status="failed"; fi

end_ts=$(( $(date +%s) + DURATION ))

echo "[cheaplanwatch_eantc] host=$(hostname -s) server=$SERVER_IP:$SERVER_PORT duration=${DURATION}s interval=${INTERVAL}s msg_size_mix=$EANTC_MSG_SIZE_MIX" | tee "$OUT_LOG"

tmp_samples="${OUT_JSON}.samples"
: > "$tmp_samples"
while [ "$(date +%s)" -lt "$end_ts" ]; do
  ts="$(date +%s)"
  tbw="$(qperf -lp "$SERVER_PORT" "$SERVER_IP" tcp_bw -oo msg_size:"$EANTC_MSG_SIZE_MIX" 2>/dev/null | qnum || true)"
  tlat="$(qperf -lp "$SERVER_PORT" "$SERVER_IP" tcp_lat -oo msg_size:"$EANTC_MSG_SIZE_MIX" 2>/dev/null | qnum || true)"
  pline="$(ping -c 4 "$SERVER_IP" 2>/dev/null | awk -F'=' '/rtt|round-trip/ {print $2}' | tr -d ' ' || true)"
  pavg="$(printf '%s' "$pline" | cut -d/ -f2)"
  pjit="$(printf '%s' "$pline" | cut -d/ -f4)"

  printf '{"ts":%s,"tcp_bw":"%s","tcp_lat":"%s","ping_avg":"%s","ping_jitter":"%s","mode":"eantc-imix"}\n' "$ts" "$tbw" "$tlat" "$pavg" "$pjit" >> "$tmp_samples"
  line="ts=${ts} tcp_bw=${tbw:-n/a} tcp_lat=${tlat:-n/a} ping_avg=${pavg:-n/a} ping_jitter=${pjit:-n/a} mode=eantc-imix"
  echo "$line" | tee -a "$OUT_LOG"
  if [ -w /dev/tty1 ]; then echo "$line" > /dev/tty1 || true; fi
  sleep "$INTERVAL"
done

python3 - <<'PY' "$tmp_samples" "$OUT_JSON" "$baseline_tcp_bw" "$baseline_tcp_lat" "$base_ping_avg" "$base_ping_jitter" "$mtu_status" "$EANTC_MSG_SIZE_MIX"
import json, sys, pathlib
samples_path, out_json, b_bw, b_lat, b_avg, b_jit, mtu, mix = sys.argv[1:]
samples=[]
for line in pathlib.Path(samples_path).read_text(encoding='utf-8').splitlines():
    if line.strip():
        samples.append(json.loads(line))
obj={
  'report_banner':'risng - Cloud Host Endpoint Analysis Probe',
  'host': pathlib.Path('/etc/hostname').read_text().strip(),
  'baseline': {'mtu1500': mtu, 'tcp_bw': b_bw, 'tcp_lat': b_lat, 'ping_avg': b_avg, 'ping_jitter': b_jit},
  'mix': {'name': 'eantc-imix-with-jumbo', 'qperf_msg_size': mix},
  'samples': samples,
}
pathlib.Path(out_json).write_text(json.dumps(obj, indent=2), encoding='utf-8')
PY

echo "[cheaplanwatch_eantc] done: $OUT_JSON" | tee -a "$OUT_LOG"
