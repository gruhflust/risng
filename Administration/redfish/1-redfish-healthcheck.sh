#!/bin/bash

# ==============================================
# Script: redfish-healthcheck.sh
# Zweck:  System-Health von Dell-Servern via Redfish abfragen
# Autor:  Torsten & ChatGPT
# ==============================================

USERNAME="root"
PASSWORD="Fitylibutyli22!"
TIMEOUT=10

if [[ $# -ne 1 ]]; then
  echo "Nutzung: $0 <hostliste.txt>"
  exit 1
fi

HOSTLIST="$1"

if [[ ! -f "$HOSTLIST" ]]; then
  echo "Fehler: Datei '$HOSTLIST' nicht gefunden!"
  exit 2
fi

if ! command -v jq &>/dev/null; then
  echo "Fehler: 'jq' ist nicht installiert. Bitte mit 'apt install jq' oder 'yum install jq' installieren."
  exit 3
fi

echo -e "\n\033[1;34m=== Redfish System Health Check ===\033[0m"

while IFS= read -r HOST || [[ -n "$HOST" ]]; do
  [[ -z "$HOST" ]] && continue
  echo -e "\n\033[1;33m>>> Host: $HOST\033[0m"

  SYSINFO=$(curl -s -k -u "$USERNAME:$PASSWORD" --max-time $TIMEOUT \
    "https://$HOST/redfish/v1/Systems/System.Embedded.1")

  if [[ -z "$SYSINFO" ]] || ! echo "$SYSINFO" | jq . &>/dev/null; then
    echo -e "\033[0;31mFehler: Keine gültige Antwort von $HOST\033[0m"
    continue
  fi

  MODEL=$(echo "$SYSINFO" | jq -r '.Model // "N/A"')
  SERIAL=$(echo "$SYSINFO" | jq -r '.SerialNumber // "N/A"')
  STATUS=$(echo "$SYSINFO" | jq -r '.Status.Health // "N/A"')
  HEALTHROLLUP=$(echo "$SYSINFO" | jq -r '.Status.HealthRollup // "N/A"')

  echo -e " Modell:        \033[1m$MODEL\033[0m"
  echo -e " Seriennummer:  $SERIAL"
  echo -e " Systemstatus:  $STATUS"
  echo -e " Rollup:        $HEALTHROLLUP"

  # ===============================
  # CPUs
  # ===============================
  CPUINFO=$(curl -s -k -u "$USERNAME:$PASSWORD" --max-time $TIMEOUT \
    "https://$HOST/redfish/v1/Systems/System.Embedded.1/Processors")
  CPUCOUNT=$(echo "$CPUINFO" | jq '.Members | length')

  echo -e " CPUs:          $CPUCOUNT Stück"

  for (( i=0; i<CPUCOUNT; i++ )); do
    CPULINK=$(echo "$CPUINFO" | jq -r ".Members[$i][\"@odata.id\"]")
    [[ -z "$CPULINK" ]] && continue

    CPUDATA=$(curl -s -k -u "$USERNAME:$PASSWORD" --max-time $TIMEOUT "https://$HOST$CPULINK")
    CPUNAME=$(echo "$CPUDATA" | jq -r '.Name // "Unbekannt"')
    CPUHEALTH=$(echo "$CPUDATA" | jq -r '.Status.Health // "N/A"')

    echo -e "  → $CPUNAME – Status: $CPUHEALTH"
  done

  # ===============================
  # Netzwerk-Interfaces (NICs)
  # ===============================
  NICDATA=$(curl -s -k -u "$USERNAME:$PASSWORD" --max-time $TIMEOUT \
    "https://$HOST/redfish/v1/Systems/System.Embedded.1/EthernetInterfaces")

  NICCOUNT=$(echo "$NICDATA" | jq '.Members | length')
  echo -e "\n Netzwerk-Interfaces: $NICCOUNT gefunden"

  for (( j=0; j<NICCOUNT; j++ )); do
    NICLINK=$(echo "$NICDATA" | jq -r ".Members[$j][\"@odata.id\"]")
    [[ -z "$NICLINK" ]] && continue

    NICINFO=$(curl -s -k -u "$USERNAME:$PASSWORD" --max-time $TIMEOUT "https://$HOST$NICLINK")
    NICNAME=$(echo "$NICINFO" | jq -r '.Name // "N/A"')
    MACADDR=$(echo "$NICINFO" | jq -r '.MACAddress // "N/A"')
    LINKSTATUS=$(echo "$NICINFO" | jq -r '.LinkStatus // "N/A"')
    SPEED=$(echo "$NICINFO" | jq -r '.SpeedMbps // "?"')

    echo -e "  → $NICNAME | MAC: $MACADDR | Link: $LINKSTATUS | Speed: ${SPEED}Mbps"
  done

  # ===============================
  # Chassis-Thermal (Temperatur)
  # ===============================
  THERMALDATA=$(curl -s -k -u "$USERNAME:$PASSWORD" --max-time $TIMEOUT \
    "https://$HOST/redfish/v1/Chassis/System.Embedded.1/Thermal")

  echo -e "\n Temperatur-Sensoren:"
  echo "$THERMALDATA" | jq -r '.Temperatures[] | "  → \(.Name): \(.ReadingCelsius) °C (Status: \(.Status.Health))"' 2>/dev/null || echo "  [keine Sensoren abrufbar]"

  echo -e "\n Lüfterstatus:"
  echo "$THERMALDATA" | jq -r '.Fans[] | "  → \(.Name): \(.Reading) RPM (Status: \(.Status.Health))"' 2>/dev/null || echo "  [keine Lüfter abrufbar]"

done < "$HOSTLIST"

