#!/bin/bash
echo "--- INTERFACES ---"
ip -brief addr show

echo "--- ROUTING ---"
ip route

echo "--- RESOLV.CONF ---"
cat /etc/resolv.conf

echo "--- TEST: getent hosts deb.debian.org ---"
/usr/bin/getent hosts deb.debian.org || echo "FAILED"

echo "--- TEST: dig deb.debian.org ---"
/usr/bin/dig +short deb.debian.org || echo "FAILED"

echo "--- TEST: nslookup deb.debian.org ---"
/usr/bin/nslookup deb.debian.org || echo "FAILED"

echo "--- TEST: curl port 80 ---"
/usr/bin/curl -s --head http://deb.debian.org | head -n 1 || echo "FAILED"

echo "--- SYSTEMD-RESOLVED ---"
systemctl is-active systemd-resolved && resolvectl status || echo "Not active"
