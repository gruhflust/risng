#!/bin/bash
# network_test.sh - Check gateway connectivity and performance
# Usage: network_test.sh <gateway_ip> [iperf_server_ip]

set -euo pipefail

GATEWAY="${1:-}"
IPERF_SERVER="${2:-$GATEWAY}"

if [[ -z "$GATEWAY" ]]; then
  echo "Usage: $0 <gateway_ip> [iperf_server_ip]" >&2
  exit 1
fi

LOGFILE="network_test_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee "$LOGFILE") 2>&1

echo "=== Network connectivity test to $GATEWAY ==="

echo "\n-- Ping --"
ping -c 4 "$GATEWAY"

echo "\n-- Traceroute --"
traceroute "$GATEWAY"

echo "\n-- Nmap Top Ports --"
nmap --top-ports 10 "$GATEWAY"

echo "\n-- iperf3 throughput test (server: $IPERF_SERVER) --"
iperf3 -c "$IPERF_SERVER" || echo "iperf3 test failed"

echo "Results saved in $LOGFILE"