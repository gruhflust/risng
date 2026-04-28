# Agent Protocol `risng`

Stand: 2026-04-28, Branch `main`

## Kurzfassung

`risng` ist das Fachrepo für den RISng-Pfad: Bootstrap, Paket-/Mirror-Vorbereitung, PXE-nahe Staging-Logik und vor allem Secondstage-Deployment/Validierung für RIS-Clients.

Im Kontext der anderen Repos ist `risng` die **fachliche RIS-/Secondstage-Schicht**:
- `ironscope` stellt den älteren PXE-/Live-Testpfad bereit.
- `spec` modernisiert den Staginghost auf AlmaLinux 9 und SPEC-Live-Boot.
- `botrepo` liefert Operator-/Agenten-Orchestrierung.
- `risng` bleibt der Ort für RIS-Anforderungen, Client-Baseline, Secondstage und Validierungslogik.

## Umgebung

- Repo: `~/.openclaw/workspace/risng`
- Remote: `git@github.com:gruhflust/risng`
- Branch: `main`
- Rolle: RISng Bootstrap + Secondstage + Validierung

## Wichtige Bereiche

- `ansible/bootstrapvm/` — Bootstrap-/PXE-/Paketvorbereitung
- `ansible/secondstage/` — RISng-Secondstage-Deployment und Validierung
- `Information/` — RIS-Anforderungen, SRD, Aufgaben- und Testdokumente
- `Administration/` — Debug-/Diagnosehilfen für DHCP, DNS, PXE, Redfish
- `python/` — NetBox-/VLAN-/Testdaten-Hilfen

## Wesentliche Commit-Linie

- **`e74c1ce`** — `Merge RISng-Change01: secondstage baseline, validation, and change01 fixes`  
  Bündelt Change01-Secondstage, Validierung und zugehörige Fixes.

- **`12b98a4`** — `fix(change01): remove stale known_hosts entries for plain+bracket host forms before risdeploy`  
  Verhindert SSH-Known-Hosts-Konflikte bei Secondstage-Deployments.

- **`f74d8d9`** — `fix(change01): filter ssh-keyscan comments before known_hosts and keep key registration best-effort`  
  Macht Hostkey-Registrierung robuster und nicht unnötig blockierend.

- **`1ce5414`** — `feat(change01): auto-register new risdeploy targets in RISng known_hosts (ip+hostname)`  
  Automatisiert Known-Hosts-Registrierung für neue RISng-Ziele.

- **`a386fc8`** — `ux(change01): make risdeploy-validation non-blocking by default and print concise failed-host summary`  
  Verbessert Validierungs-UX und verhindert harte Stops bei nichtkritischen Checks.

- **`0f24362`** — `feat(change01): add risdeploy-validation playbook+pytest summary and wire alias`  
  Führt explizite Secondstage-Validierung mit pytest-Zusammenfassung ein.

- **`d376587`** — `docs(change01): update RIS-REQ matrix mapping and add effective client test checklist`  
  Verknüpft RIS-Anforderungen mit Testcheckliste.

- **`552b4df`** — `fix(change01): correct secondstage mirror root resolution so updates/extras repodata lands at expected local paths`  
  Korrigiert Mirror-/Repodata-Pfade für Secondstage-Pakete.

## Kontext zu den Schwesterrepos

- **zu `spec`**: `spec` stabilisiert aktuell den Alma-basierten PXE-Staginghost. Sobald der SPEC-Live-Boot sauber läuft, kann RISng-Secondstage daraus profitieren oder gezielt dagegen validiert werden.
- **zu `ironscope`**: `ironscope` ist der ältere Live-/PXE-Arbeitsstand; viele Bootstrap-Helfer und Diagnosemuster sind verwandt.
- **zu `botrepo`**: `botrepo` ist die übergreifende Operator-Schicht. RISng-Fachänderungen gehören jedoch primär hierher, nicht in `botrepo/risng_code`.

## Aktueller Arbeitsfokus

- Secondstage-Baseline reproduzierbar halten.
- RIS-REQ-Matrix gegen echte Clienttests pflegen.
- Known-Hosts-/SSH-/Validierungslogik nicht unnötig blockierend machen.
- Bootstrap- und PXE-Teile nicht weiter mit veralteten Ironscope-Annahmen vermischen.

## Pflegehinweise

1. RIS-Anforderungen immer mit Commit und Testcheckliste verknüpfen.
2. Secondstage-Änderungen brauchen eine kurze Validierungsnotiz.
3. Bootstrap-Fixes aus `spec` nur übernehmen, wenn sie fachlich RISng betreffen.
4. Historische Inhalte in `OldCode/` nicht als aktuelle Wahrheit behandeln.
