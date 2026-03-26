# Agenten-Handlungsanweisung – RISng SecondStage (SRD-traceable)

Diese Datei operationalisiert `Information/Umsetzungsplanung.md` in konkrete Arbeitsregeln für Agenten.

## Ziel

Alle Umsetzungen im Branch `Projects/IOPC-3412/SecondStage` müssen **vollständig auf SRD-Anforderungen (RIS-REQ-XXXX) rückführbar** sein.

- **1:n-Zuordnung ist Pflicht**:
  - eine RIS-REQ kann über mehrere Commits umgesetzt werden,
  - ein Commit kann mehrere RIS-REQs adressieren.
- **Keine "freien" Commits** ohne RIS-REQ-Bezug (außer rein technische Chores mit expliziter Begründung).

---

## Verbindlicher Arbeitsablauf pro Umsetzung

1. **Anforderung wählen**
   - Starte immer aus `Information/RIS_REQ_Commit_Matrix.md`.
   - Wähle eine oder mehrere `RIS-REQ-*` mit Status `OPEN` / `IN_PROGRESS`.

2. **Umsetzung planen**
   - Leite aus `Information/Umsetzungsplanung.md` konkrete Tasks ab.
   - Benenne betroffene Dateien/Rollen vorab.

3. **Implementieren**
   - Kleine, nachvollziehbare Commits.
   - Keine Vermischung fachfremder Anforderungen.

4. **Commit-Regel (Pflicht)**
   - Commit-Message muss die zugeordneten RIS-REQs enthalten.
   - Format:

```text
<type>(secondstage): <kurzbeschreibung>

RIS-REQ: RIS-REQ-XXXX, RIS-REQ-YYYY
```

5. **Trace-Matrix aktualisieren (Pflicht)**
   - In `Information/RIS_REQ_Commit_Matrix.md` die betroffenen Zeilen pflegen:
     - `Status`
     - `Commits` (Hash-Liste)
     - `Umsetzungsartefakte`
     - `Validierung`

6. **Definition of Done je RIS-REQ**
   - Implementierung vorhanden
   - in Matrix mit Commit-Hash referenziert
   - Validierung dokumentiert (z. B. Playbook-Syntaxcheck, Dryrun, Laufprotokoll)

---

## Commit-/Traceability-Regeln

### R1 – Vollständigkeit
Jede in `Umsetzungsplanung.md` vorkommende `RIS-REQ-*` muss in der Matrix vorhanden sein.

### R2 – Rückverfolgbarkeit
Jeder fachliche Commit muss mindestens eine `RIS-REQ-*` referenzieren.

### R3 – 1:n-Abbildung
Wenn eine RIS-REQ über mehrere Commits umgesetzt wird, müssen **alle Hashes** in der Matrixzeile stehen.

### R4 – Statusdisziplin
Erlaubte Stati: `OPEN`, `IN_PROGRESS`, `DONE`, `BLOCKED`.

### R5 – Merge-Gate
Kein Merge in `main`, solange für betroffene RIS-REQs kein `DONE` + Commit-Referenz + Validierung in der Matrix steht.

---

## Schnellcheck vor Push

- [ ] Commit enthält `RIS-REQ:`-Zeile
- [ ] Matrix wurde aktualisiert
- [ ] Alle referenzierten Hashes sind im Branch vorhanden
- [ ] Validierung ist eingetragen

---

## Scope

Diese Handlungsanweisung gilt für alle Agentenarbeiten im Kontext:

- Repository: `risng`
- Branch: `Projects/IOPC-3412/SecondStage`
- Planungsquelle: `Information/Umsetzungsplanung.md`
