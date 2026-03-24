# RISNG

Infrastructure Resilience & Orchestration Network – Scalable Cloud Operations, Provisioning & Evaluation

## Zweck

RISng ist eine Bootstrap- und Staging-Umgebung für automatisierte Client-Installationen über PXE.
Der RISng-Server stellt dabei die komplette Installationskette lokal bereit:

- DHCP / DNS / TFTP
- Kernel / initrd
- Kickstart
- Stage2
- RPM-Pakete

Die zentrale Randbedingung lautet:

> Ein RISng-Client sieht während der Installation ausschließlich den RISng-Server über die PXE-Schnittstelle.

Also:

- kein Internetzugang auf Clientseite
- keine externen Mirrors
- keine zusätzlichen Paketquellen

## Erreichter Meilenstein

Der aktuelle Stand erreicht eine automatisierte CentOS-7.8-Basisinstallation bis zum Login-Bildschirm.
Das ist der bisherige Durchbruch des RISng-Stagings.

Die entscheidenden technischen Bausteine dafür sind:

- ein RISng-spezifischer Installpfad (`roles/risng_install`)
- eine lokale Kickstart-/Stage2-/RPM-Bereitstellung über RISng
- feste Bindung des Installers an die PXE-NIC
- lokaler HTTP-Export über nginx statt `python -m http.server`
- frühere Validierung des veröffentlichten CentOS-Repos auf RISng

## Komponenten

### `roles/management`
Richtet die Management-Seite des RISng-Servers ein, inklusive Hilfsskripte, Repo-Staging-Helfern und HTTP-Serving.

### `roles/risng_install`
Stellt den eigentlichen RISng-CentOS-Installpfad bereit:

- ISO-Extraktion
- lokaler Repo-Baum
- Kernel / initrd
- Kickstart-Dateien
- PXE-Menüeinträge

### `roles/risng`
Enthält weitere RISng-spezifische Konfigurationsschritte für die Bootstrap-VM selbst.

## Minimaler Vorbereitungsweg auf Debian

Für frische Debian-Zielsysteme existiert ein reduzierter Vorbereitungsweg:

- `workstationprep-minimal`

Dieser installiert nur die notwendige Basisausstattung:

- grafische Anmeldung
- SSH-Zugriff
- `ansible`, `git`, `rsync`
- lokales `botrepo` im Home von `risng`
- RISng-Code liegt unter `~/botrepo/risng_code`
- `.bashrc` verlinkt auf die RISng-Management-Bashrc

Danach ist die Maschine bereit für den ersten `feuer`-Lauf.

## Typischer Arbeitsablauf

1. Debian-Zielsystem mit `workstationprep-minimal` vorbereiten
2. auf RISng `feuer` ausführen
3. PXE-Client booten
4. CentOS 7.8 lokal von RISng installieren
5. anschließend zweite Konfigurationsstufe für die frisch installierten Clients

## Wichtige Aliase

| Alias | Aufgabe |
|-------|---------|
| `feuer` | baut RISng-Staging, PXE-Dienste und Installationspfad auf |
| `getisos` | lädt die für den Build benötigten ISO-Artefakte vorab herunter |
| `repair-dhcp` | repariert DHCP-Konfiguration nach Netzwerk-/Interface-Wechsel |

## Detailliertere technische Dokumentation

Siehe auch:

- `docs/ops/risng-centos7-staging.md`

## Nächste Phase

Die nachgelagerte Konfiguration frisch installierter CentOS-7.8-Clients wird im Folgezweig entwickelt:

- `Projects/IOPC-3412/SecondStage`

Dort werden skalierbare Playbooks für Paketinstallation, Benutzeranlage, Skriptverteilung und Link-Management aufgebaut.
