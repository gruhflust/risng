#!/bin/bash
echo "--- /etc/resolv.conf ---"
cat /etc/resolv.conf

echo "--- Aktive resolvectl Konfiguration (falls aktiv) ---"
command -v resolvectl >/dev/null && resolvectl status || echo "resolvectl not available"

echo "--- NSS-Werte in /etc/nsswitch.conf ---"
grep '^hosts:' /etc/nsswitch.conf

echo "--- Systemd-resolved Status ---"
systemctl is-active systemd-resolved && echo "✅ Aktiv" || echo "❌ Inaktiv"
