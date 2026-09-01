#!/bin/bash
#
# erwartet hostliste und prüft Maschinen über refish Schnittstelle

USERNAME="root"
PASSWORD="Fitylibutyli22!"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <hostliste.txt>"
  exit 1
fi

HOSTLIST="$1"

echo "Redfish Systemcheck"

while IFS= read -r HOST; do
	echo ">>>Prüfe host: $HOST"
	SYSINFO=$(curl -s -k -u "$USERNAME:$PASSWORD" "https://$HOST/redfish/v1/



done < "$HOSTLIST"
