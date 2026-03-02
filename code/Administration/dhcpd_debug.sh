#!/bin/bash
echo "=== DHCPD DEBUG CHECK ==="

echo
echo "--> Prüfe Rechte auf /var/lib/dhcp:"
ls -ld /var/lib/dhcp

echo
echo "--> Prüfe Rechte auf dhcpd.leases:"
ls -l /var/lib/dhcp/dhcpd.leases

echo
echo "--> Ist Datei schreibbar für dhcpd?"
sudo -u dhcpd test -w /var/lib/dhcp/dhcpd.leases && echo "✔ dhcpd kann schreiben" || echo "❌ dhcpd kann NICHT schreiben"

echo
echo "--> Versuche, mit dhcpd zu starten:"
/usr/sbin/dhcpd -f -d -cf /etc/dhcp/dhcpd.conf
