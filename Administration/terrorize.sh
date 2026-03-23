#!/bin/bash
# 00 terrorize.sh – PXE Client Boot Monitor (Loop Mode)
# v03 – Endlosschleife mit Break via Ctrl+C

SERVER="192.168.100.100"
TFTP_PATHS=(
  "/debian-live/live/vmlinuz"
  "/debian-live/live/initrd.img"
  "/debian-live/live/filesystem.squashfs"
)
INTERVAL=10  # Sekunden zwischen den Durchläufen

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m' # Reset

# Spinner
spinner() {
  local pid=$1
  local delay=0.1
  local spinstr='|/-\'
  while ps -p $pid &>/dev/null; do
    local temp=${spinstr#?}
    printf " [%c]  " "$spinstr"
    local spinstr=$temp${spinstr%"$temp"}
    sleep $delay
    printf "\b\b\b\b\b\b"
  done
}

check() {
  local desc=$1
  shift
  local cmd=("$@")
  printf "%-45s" "$desc"
  ("${cmd[@]}" &>/dev/null) &
  local pid=$!
  spinner $pid
  wait $pid && echo -e "${GREEN}[OK]${NC}" || echo -e "${RED}[FAIL]${NC}"
}

# Kopfzeile
clear
echo -e "${YELLOW}PXE Client Boot Monitor – Terrorize Loop Mode v3${NC}"
echo "Target Server: $SERVER"
echo "Refresh every ${INTERVAL}s – Press Ctrl+C to abort."
echo ""

# Endlosschleife
while true; do
  echo -e "\n${CYAN}== $(date '+%Y-%m-%d %H:%M:%S') - Live-Check ==${NC}"

  check "Ping erreichbar" ping -c 1 -W 1 $SERVER
  check "SSH Port 22 offen" nc -z -w1 $SERVER 22
  check "DNS Port 53 offen" nc -z -u -w1 $SERVER 53
  check "UDP Port 67 (DHCP Server) offen" nc -z -u -w1 $SERVER 67
  check "UDP Port 69 (TFTP Server) offen" nc -z -u -w1 $SERVER 69

  for path in "${TFTP_PATHS[@]}"; do
    check "TFTP Abruf: $path" timeout 2 tftp $SERVER -c get "$path"
  done

  echo -e "${YELLOW}Warte ${INTERVAL}s ...${NC}"
  sleep $INTERVAL
done
