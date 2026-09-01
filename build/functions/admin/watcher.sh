#!/bin/bash
# monitor-services.sh v01
# Watch SSH, TFTP und DHCP Logs auf dem PXE-Server

while true; do
  clear
  ls -l /var/lib/tftpboot/debian-live/live/
  echo "=== DHCP Leases ==="
  tail -n 5 /var/lib/dhcp/dhcpd.leases | grep -v "^#"

  echo ""
  echo "=== DHCP Journal (letzte 5) ==="
  journalctl -n 5 -u isc-dhcp-server --no-pager --output short

  echo ""
  echo "=== TFTP Log (Port 69) mit tcpdump ==="
  timeout 5 tcpdump -ni ens224 port 69 -c 5 2>/dev/null

  echo ""
  echo "=== SSHD Log (letzte 5) ==="
  journalctl -n 5 -u ssh --no-pager --output short


  

  echo ""
  echo "Drücke [Ctrl+C] zum Beenden - Aktualisierung alle 2 Sekunden..."
  sleep 2
done
