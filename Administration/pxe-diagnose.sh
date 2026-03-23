#!/bin/bash
# 00 pxe-diagnose.sh – PXE Boot State Inspector
# v02 – Real-Time Diagnose für PXE, DHCP, TFTP mit Port-Zustand + Ereignis-Logik

IFACE="ens224"
PORTS=(67 68 69 4011)
TFTPDIR="/var/lib/tftpboot"
FILTER="port 67 or port 68 or port 69 or port 4011"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
MAGENTA='\033[1;35m'
CYAN='\033[1;36m'
NC='\033[0m' # Reset

echo -e "${CYAN}== PXE Diagnose Tool – Live-Protokollanalyse auf $IFACE ==${NC}"
echo -e "${YELLOW}Tracking Ports: ${PORTS[*]} | TFTP Root: $TFTPDIR${NC}"

echo ""
echo -e "${MAGENTA}== Aktive Portüberwachung (netstat/ss) ==${NC}"
for port in "${PORTS[@]}"; do
  ss -ulpn | grep ":$port " && echo -e "${GREEN}[OK] UDP $port offen${NC}" || echo -e "${RED}[FEHLT] UDP $port nicht offen${NC}"
done

echo ""
echo -e "${CYAN}== Live Traffic (tcpdump) mit Highlight ==${NC}"

# Ereignisparser
sudo tcpdump -i "$IFACE" -n -vvv -s 0 -l "$FILTER" 2>/dev/null | while read -r line; do
  case "$line" in
    *"DHCPDISCOVER"*|*"DHCPOFFER"*|*"DHCPREQUEST"*|*"DHCPACK"*)
      echo -e "${GREEN}[DHCP] $line${NC}" ;;
    *"RRQ"*|*"TFTP Read Request"*)
      file=$(echo "$line" | grep -o '".*"' | tr -d '"')
      echo -e "${BLUE}[TFTP] Request: $file${NC}"
      if [[ -f "$TFTPDIR/$file" ]]; then
        echo -e "${GREEN}  → Datei vorhanden auf Server: $TFTPDIR/$file${NC}"
      else
        echo -e "${RED}  → FEHLER: Datei NICHT gefunden im TFTP Root!${NC}"
      fi ;;
    *"ICMP port unreachable"*)
      echo -e "${RED}[ICMP] TFTP fehlgeschlagen: $line${NC}" ;;
    *"PXEClient"*|*"bootp"*)
      echo -e "${YELLOW}[PXE/BOOTP] $line${NC}" ;;
    *)
      echo -e "${MAGENTA}[?] $line${NC}" ;;
  esac
done
