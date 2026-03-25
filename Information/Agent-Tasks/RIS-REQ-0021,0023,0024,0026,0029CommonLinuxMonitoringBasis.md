# Agent Task: RIS-REQ-0021,0023,0024,0026,0029 – Common Linux Monitoring-Basis

## Ziel
Umsetzung eines ersten, sinnvoll gebündelten Common-Linux-Pakets aus der Umsetzungsplanung:

- RIS-REQ-0021
- RIS-REQ-0023
- RIS-REQ-0024
- RIS-REQ-0026
- RIS-REQ-0029

Fokus: **Monitoring-/Diagnose-Basis auf dem RISng-Staging-Host** reproduzierbar bereitstellen.

---

## Inhaltliche Ableitung aus Umsetzungsplanung
Aus `Information/Umsetzungsplanung.md` ergeben sich für diesen Task insbesondere:

- SNMP-Grundpakete und zugehörige Perl XML/IO-Module
- `collectl` inkl. Plugin-Basis
- `tk`
- Wireshark-Pakete (`wireshark`, `wireshark-gnome`)

---

## Umsetzungsumfang (Branch: Projects/IOPC-3412/SecondStage)

### 1) Paketdefinition zentralisieren
- Ergänze/prüfe in den bootstrap-relevanten Rollen eine klar deklarierte Paketliste für diese RIS-REQ-Gruppe.
- Vermeide verstreute, doppelte Paketdefinitionen.

### 2) Idempotente Installation
- Stelle sicher, dass die Installation idempotent über vorhandene Playbooks (`feuer`) läuft.
- Keine Seiteneffekte auf PXE-Staging-Logik.

### 3) Basisvalidierung ergänzen
- Nach der Installation eine schlanke Verifikation (z. B. `package_facts`/`rpm -q`-äquivalent für Debian-Paketnamen via `dpkg-query`) für die definierten Pakete.
- Fehlerbild muss klar im Log sichtbar sein.

### 4) Dokumentation + Traceability
- `Information/RIS_REQ_Commit_Matrix.md` für diese RIS-REQs auf `IN_PROGRESS`/`DONE` pflegen.
- Umsetzungsartefakte + Commit-Hashes + Validierung ergänzen.

---

## Nicht Teil dieses Tasks
- Proprietäre Pakete / hardware-spezifische Dell-Teile
- Shellscript-Migrationen aus den späteren Planblöcken
- SecondStage-Clientdeployment (`risdeploy`) selbst

---

## Akzeptanzkriterien (Definition of Done)
- [ ] Alle fünf RIS-REQs sind durch konkrete Paket-/Task-Änderungen abgedeckt.
- [ ] `feuer` läuft ohne Regressionen im bestehenden Setup.
- [ ] Paketprüfung ist im Log nachvollziehbar.
- [ ] Matrix-Einträge gepflegt (`Commits`, `Umsetzungsartefakte`, `Validierung`).
- [ ] Commit-Message enthält exakt die zugeordneten RIS-REQ IDs.

---

## Vorgeschlagenes Commit-Schema

```text
feat(secondstage): implement common linux monitoring package baseline

RIS-REQ: RIS-REQ-0021, RIS-REQ-0023, RIS-REQ-0024, RIS-REQ-0026, RIS-REQ-0029
```

