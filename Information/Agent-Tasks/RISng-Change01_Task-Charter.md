# RISng-Change01 – Task Charter

Ausgangsbasis: `Projects/IOPC-3412/SecondStage`  
Arbeitsbranch: `RISng-Change01`

## Ziel dieses Changes
Den ersten gruppierten Common-Block aus der Umsetzungsplanung operativ umsetzen und
**auf denselben Stand** bringen für:

1. RISng-Staging-Automatik (`feuer`)
2. RISdeploy-Client-Staging-Automatik (`risdeploy` / `risdeploy-dryrun` Transparenz)

## Geltende Regeln
- `Information/Agenten-Handlungsanweisung-SecondStage.md`
- `Information/RIS_REQ_Commit_Matrix.md`

## Zugeordnete RIS-REQs (Change01)
- RIS-REQ-0021
- RIS-REQ-0023
- RIS-REQ-0024
- RIS-REQ-0026
- RIS-REQ-0029

## Pflicht-Ergebnisse
- Umsetzung in Ansible-Rollen/Playbooks für Stagingpfad
- Sichtbarkeit der umgesetzten Inhalte im `risdeploy-dryrun`-Plan (wo sinnvoll)
- Matrix-Pflege mit 1:n Commit-Zuordnung
- Commit-Messages mit `RIS-REQ:`-Liste

## Arbeitsreihenfolge (kurz)
1. Paket-/Komponentenmodell für Change01 in Staging definieren
2. Installation im `feuer`-Pfad idempotent umsetzen
3. `risdeploy`/`risdeploy-dryrun` auf denselben Stand heben (Transparenz + Deploymentpfad)
4. Validierung (Syntax, Dryrun, Laufprotokolle)
5. Matrix aktualisieren
