# CHEAP Test-Suite (risng)

**CHEAP = Cloud Host Endpoint Analysis Probe**

Dieses Verzeichnis enthält die Laufzeit-Tools für die `cheap*`-Tests auf risng.

## Überblick

### `cheaplantest`
Vollständiger IMIX/qperf-Reportlauf (servergesteuert):
- startet qperf-Server
- nutzt Zielhosts aus `qperf_targets.yml`
- nutzt IMIX-Profile aus `qperf_imix.yml`
- sammelt Ergebnisse
- rendert Report als JSON/HTML/PDF

Ablage:
- `~/cheaplantest/<timestamp>-testrun.json`
- `~/cheaplantest/<timestamp>-testrun.html`
- `~/cheaplantest/<timestamp>-testrun.pdf`

### `cheaplanwatchserver`
Interaktiver Servermodus für manuelle Paralleltests:
- startet qperf-Server (+ iperf3 für Baseline)
- bereinigt alte Client-Prozesse und deployed aktuelle cheaplanwatch-Payload auf erreichbare Clients
- zeigt Run-ID + Clientscript-Version
- wartet auf ENTER
- stoppt Server + Clientprozesse
- sammelt Client-JSONs und rendert Gesamtbericht (JSON/HTML/PDF)

Ablage:
- `~/cheaplanwatch/<run_id>-testrun.json`
- `~/cheaplanwatch/<run_id>-testrun.html`
- `~/cheaplanwatch/<run_id>-testrun.pdf`

### `cheaplanwatch` (Client)
Live-Messung auf PXE-Clients:
- erwartet laufenden `cheaplanwatchserver`
- schreibt Rohdaten fortlaufend nach `/tmp/cheaplanwatch/<run_id>-<host>.json`
- zeigt Live-Metriken in der Konsole
- unterstützt `CHEAPLANWATCH_MODE=live|imix`
- im IMIX-Modus optional mit `CHEAPLANWATCH_IMIX_SIZES` (CSV, z. B. `1:64K:*2,1:128K:*4`)

### `cheapwatch` (Server, optional)
Separates Beobachtungsskript für Laufzeitdiagnose:
- zeigt qperf-Verbindungen auf Port 19765
- liest `~/cheaplanwatch/current-run.env` (gesetzt von `cheaplanwatchserver`)
- zeigt pro Zielclient eine Live-Zeile mit letztem `tcp_bw`/`tcp_lat` aus Client-Samples
- normalisiert `tcp_bw`-Einheiten (bit/byte) und zeigt eine summierte Gesamt-Rate über alle Clients (`Gbit/s` und `GB/s`)
- zeigt die letzten Zeilen aus `~/cheaplanwatch/cheaplanwatch-qperf.log`
- kann jederzeit parallel zu `cheaplanwatchserver` gestartet/gestoppt werden

---

## Alias-Workflow

Server (risng):
1. `cheaplanwatchserver`
2. Run-ID aus Hinweis übernehmen

Clients (manuell):
1. `CHEAPLANWATCH_RUN_ID=<run_id> cheaplanwatch`

Server (wenn fertig):
- im wartenden `cheaplanwatchserver` einfach ENTER drücken

---

## Manuelle Kommandos (Notfallbetrieb ohne Alias)

## A) cheaplanwatchserver manuell starten

```bash
# qperf server
qperf -lp 19765 > ~/cheaplanwatch/cheaplanwatch-qperf.log 2>&1 &

# iperf3 baseline server
iperf3 -s --one-off > ~/cheaplanwatch/cheaplanwatch-iperf3.log 2>&1 &
```

## B) Client manuell testen

```bash
CHEAPLANWATCH_SERVER_IP=10.228.229.7 \
CHEAPLANWATCH_SERVER_PORT=19765 \
CHEAPLANWATCH_RUN_ID=<run_id> \
/usr/bin/env bash /var/lib/tftpboot/runtime/qperf/cheaplanwatch-client.sh
```

## C) Serverseitig sammeln (minimal)

```bash
# Beispiel für einen Client
scp root@<client-ip>:/tmp/cheaplanwatch/<run_id>-*.json /tmp/
```

Dann JSONs aggregieren oder via Playbook laufen lassen.

---

## qperf-Modus-Hinweis

- `cheaplantest`: **IMIX** gemäß `qperf_imix.yml` (msg_size-Profile)
- `cheaplanwatch`: **Live tcp_bw/tcp_lat** (kein IMIX-Profil)

---

## Wichtige Dateien

- `cheaplantest.yml`
- `cheaplanwatch.yml` (Client-Lauf über Alias/Playbook-Entry)
- `cheaplanwatchserver.yml`
- `cheaplanwatchdeploy.yml`
- `qperf_targets.yml`
- `qperf_imix.yml`
- `files/cheaplantest_report.py`
- `files/cheaplanwatch_report.py`
