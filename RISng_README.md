RISNG

Infrastructure Resilience & Orchestration Network – Scalable Cloud Operations, Provisioning & Evaluation

## Prämisse
Die AVS-NetBox enthält alle relevanten Einträge (z.B. VLANs, Subnetze) aller Umgebungen:

- Umgebung1: AVS
- Umgebung2: RefSys
- Umgebung3: OpSys
- Umgebung4: LabSys
- Umgebung5: NDC
- Umgebung6: Physische PNT-Test-Umgebung

## Meta-Wunsch

Eine zentrale Datei soll alle Umgebungsvariablen enthalten, um harte Codierungen
in Playbooks zu vermeiden.

## Schritt 1: Manuell Debian12-VM installieren

**Umgebung:** AVS

### Voraussetzungen

- Debian12.iso
- Manuelle VM-Installation mit GUI
- Software-Auswahl:
  - Debian Desktop Environment
  - Gnome 
  - SSH-Server 
  - ansible (apt install ansible)

- Netzwerkkonfiguration: eine vNIC mit Internetzugang

## Schritt 2: Per Ansible PNT-Manager-VM konfigurieren

### Auszuführende Playbooks

- `ansible-playbook risng-setup.yml`

## Schritt 3: (in AVS) Python-NetBox-Daten-Import-Script ausführen

## Schritt 4: PNT-Manager-VM in zu testende Umgebung transportieren

- Wenn kleiner als 2 bzw. 4 GB per GitLab möglich, alternativ per USB Stick und
USB-Passthrough in ESXi Jump Host

## Schritt 5: In zu testender Umgebung

- PyTest-Test-Script ausführen (`pytest pnt_pytest.py`)

## Schritt 6: Testergebnisse einsammeln

- Datei: `test_results.json`
# risng_code

Dieses Verzeichnis enthält Ansible-Playbooks und Hilfsskripte für die **risng**-Umgebung. Die Bootstrap-VM stellt damit eine PXE-Infrastruktur bereit, über die Test- und Installationssysteme gebootet werden können.

## Nutzung der Umgebung

Die Management-Rolle installiert eine angepasste `.bashrc`, die zahlreiche Aliase für wiederkehrende Arbeitsschritte bereitstellt. Nach dem Login stehen diese Befehle sofort zur Verfügung und schreiben ihre Ausgaben in Logdateien im Home-Verzeichnis.

Ein typischer Ablauf:

1. `feuer` ausführen, um Systemupdate, Image-Build und PXE-Dienste zu starten.
2. Mit `internet` wieder in den Internetmodus wechseln.
3. Mit `pxe` den PXE-Betrieb erneut aktivieren.

## Playbook-Aliase

| Alias | Playbook | Aufgabe |
|-------|----------|---------|
| `feuer` | `bootstrapvm/risng-setup.yml` | Systemupdate, PXE-Image bauen und DHCP/DNS/TFTP bereitstellen |
| `repair-dhcp` | `bootstrapvm/repair-dhcp.yml` | DHCP-Konfiguration nach Interface-Wechsel reparieren |
| `restage` | `bootstrapvm/network-reset.yml` & `bootstrapvm/risng-setup.yml` | Netz zurücksetzen, Repository aktualisieren und PXE-Stack neu aufbauen |
| `internet` | `bootstrapvm/network-reset.yml` | Zurück in den Internetmodus wechseln und PXE-Dienste stoppen |
| `pxe` | `bootstrapvm/network-restart.yml` | PXE-NIC aktivieren, statische IP setzen und DHCP/TFTP starten |
| `heal` | `bootstrapvm/heal_internet.yml` | DNS/DHCP reparieren und neue IP beziehen |
| `trigger` | `bootstrapvm/trigger-pxe-boot.yml` | Entfernten Server per IPMI neu starten und auf SSH warten |
| `dhcpstatic` | `bootstrapvm/update-dhcp-hosts.yml` | Statische DHCP-Hosteinträge neu anwenden |
| `report_snapshot` | `runtime/report_snapshot/report_clients.yml` | DHCP-Leases lesen, Clients per SSH abfragen, Bericht speichern |
| `unreport` | `playbooks/unreport.yml` | DHCP-Leases und PXE-Logs löschen |
| `ironscrub` | `bootstrapvm/ironscrub.yml` | Temporäre Dateien entfernen |
| `gitgud` | `bootstrapvm/network-reset.yml` & `bootstrapvm/network-restart.yml` | Netzwerk kurz zurücksetzen, Repo aktualisieren und PXE neu starten |
| `teil` | `bootstrapvm/run_parts.yml` | Nur Rolle `management` ausführen |

## Dienst- und Hilfsaliase

- `ginit` – initialisiert Git-Konfiguration (`Administration/gitinit.sh`).
- `watcher` – startet Überwachungsskript (`Administration/watcher.sh`).
- `terror` – führt Troubleshooting-Skript aus (`Administration/terrorize.sh`).
- `iron` / `pnt` – zieht aktuelle Änderungen im Repository.
- `status` – zeigt Status der relevanten Dienste (`tftp`, `dhcp`, `dnsmasq`, `ssh`, `bind9`).
- `guck` – beobachtet das PXE-TFTP-Verzeichnis.
- `netbox` – klont oder aktualisiert NetBox und startet `docker-compose`.
- `netboxuser` – legt einen NetBox-Superuser an.
- `populate` – erzeugt Testdaten (`python/populate_test_data.py`).
- `populaterisng` – schreibt NetBox-Daten direkt in die DHCP-Defaults.
- `nonetbox` – Funktion zum Stoppen und Säubern der NetBox/Docker-Umgebung.
- `guckma` – zeigt Größe und Inhalte der PXE-Verzeichnisse.
- `codedump` – erstellt `code.md` mit allen relevanten Quelltexten.
- `codefromLABtoHUB` – synchronisiert dieses Repository mit der lokalen `risng` Quelle.
- `codefromHUBtoLAB` – spielt die im Spiegel-Repository geänderte Codebasis zurück in das lokale `risng`-Repo.
- `onedrive` – bindet OneDrive in `~/onedrive` ein.
- `zeigma` – Funktion: erstellt Code- und Boot-Konfigurationsdump und kopiert ihn nach OneDrive.
- Standardalias: `ls`, `ll`, `la`, `l` für farbige bzw. erweiterte Verzeichnislisten.
- 

---

## Ergänzung (automatisch erstellt)
_Dokumentationsabschnitt von ChatGPT erstellt._

### risng-Bashrc und Aliase
Die Management-Rolle rollt `roles/management/files/bashrc.md` auf dem risng-Nutzer aus. Die Datei aktiviert farbige Prompts, setzt komfortable Standardaliase und bündelt zentrale Arbeitsabläufe:

- PXE/Bootstrap-Steuerung: `feuer` (voller PXE-Build inkl. DHCP/DNS/TFTP), `restage` (Netz zurücksetzen und PXE neu aufbauen), `internet` (zurück in den Internetmodus), `pxe` (PXE-NIC wieder aktivieren), `heal` (Internet-Heilung), `trigger` (IPMI-PXE-Boot), `dhcpstatic` (statische DHCP-Hosts neu anwenden).
- Repository- und Diagnosehelfer: `iron`/`pnt` (Git-Pull), `gitgud` (kurzer Reset plus Repo-Update), `status` (Dienstestatus), `guck` (TFTP-Verzeichnis beobachten).
- NetBox-Werkzeuge: `netbox`, `netboxuser`, `boxinfo`, `populate`, `populaterisng`, `importnetboxinfo`, `dc-vLAN-test`, `nonetbox`.
- Reporting und Aufräumen: `report_snapshot` (ruft zuerst `enrichtest`, dann `slavelantest` auf und inventarisiert anschließend DHCP-Leases per SSH für PDF/JSON), `unreport` (Berichte/Logs löschen), `ironscrub` (temporäre Dateien entfernen).
- Neue Alias-Erweiterung: `slavelantest` ruft `runtime/report_snapshot/slavelantest.yml` auf und loggt nach `~/slavelantest.log`.
- Helper `enrichtest`: setzt `pingpartner_ip` in `bootstrapvm/roles/dhcp/defaults/main.yml` auf Basis der `inventory/vlans.yml` und schreibt die aktualisierte Datei zurück (Log: `~/enrichtest.log`).

### Playbook `slavelantest`
Das Playbook `runtime/report_snapshot/slavelantest.yml` liest die `dhcp_static_hosts` aus `bootstrapvm/roles/dhcp/defaults/main.yml` aus und filtert alle Einträge mit `extra_nics`. Für jeden Host baut es eine temporäre Inventargruppe auf, verbindet sich als `root` per SSH (Schlüsselverteilung erfolgt bereits über das risng-Setup) und legt auf den passenden physischen Interfaces die angegebenen VLAN-Geräte samt IP-Adressen an. Dabei wird die MAC-Adresse in den lokalen Netzwerkfakten gesucht, VLAN-Interfaces werden nur bei Bedarf erzeugt, und vorhandene IPs werden nicht doppelt gesetzt. Hosts, die nicht erreichbar sind oder bei denen die Ziel-MAC fehlt, erzeugen lediglich Warnungen; der Durchlauf setzt mit den übrigen Clients fort. Die Funktion dient zunächst der getrennten Entwicklung und ist über den Bash-Alias `slavelantest` ausführbar, kann später jedoch vom Reporting-Workflow konsumiert werden.
