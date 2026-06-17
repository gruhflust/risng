# RISng

RISng ist die PXE-/SecondStage-Plattform fuer reproduzierbare Client-Installationen und nachgelagerte Konfiguration. Der RISng-Server stellt DHCP, DNS, TFTP, Boot-Artefakte, lokale Repos und Management-Wrapper bereit; Clients sollen ihre Installations- und SecondStage-Pakete aus dem RISng-Umfeld beziehen, nicht direkt aus dem Internet.

Vor Arbeit an diesem Repo zuerst lesen:

```bash
git status --short --branch
git remote -v
sed -n '1,260p' botskills/risng-skill.md
```

## Kernpfade

| Pfad | Zweck |
| --- | --- |
| `ansible/bootstrapvm/risng-setup.yml` | Haupt-Playbook fuer Bootstrap/PXE-Staging |
| `ansible/bootstrapvm/roles/risng/` | RISng-spezifische Bootloader-/Network-/Root-Anpassungen |
| `ansible/bootstrapvm/roles/risng_install/` | lokaler CentOS-Installpfad, Kickstart, Stage2, RPM-Staging |
| `ansible/bootstrapvm/roles/management/` | Management-Bashrc, Helper, lokale Repo-/SecondStage-Vorbereitung |
| `ansible/secondstage/` | `risdeploy`, Dryrun und Validierung fuer installierte Clients |
| `ansible/runtime/` | Report-, Doxygen- und Runtime-Helfer |
| `Information/Agent-Tasks/` | aufgabenbezogene Requirements-/Change-Dokumente |

## Operativer Einstieg

Auf dem RISng-Server:

```bash
feuer
getisos
getrispackets
repair-dhcp
```

SecondStage:

```bash
risdeploy-dryrun
risdeploy
risdeploy-validation
```

State-/Management-UI, sofern im aktuellen Profil verfuegbar:

```bash
risk-status
risk-manage-list
ris-render-web-ui
```

## SecondStage-Modell

`ansible/secondstage/` arbeitet komponentenbasiert:

1. Zielclient in `roles/dhcp/defaults/main.yml` mit `secondstage_enabled: true` und `secondstage_components:` markieren.
2. `feuer` ausfuehren, damit benoetigte lokale Paketquellen und Manifest-Artefakte vorbereitet werden.
3. `risdeploy-dryrun` pruefen. Der Plan landet unter `~/risdeploy-dryrun-plan.yml`.
4. `risdeploy` ausfuehren.
5. `risdeploy-validation` pruefen. Zusammenfassungen landen unter `~/risdeploy-validation-summary.{json,yml}`.

Das generierte Paketquellen-Manifest liegt auf dem RISng-Server unter:

```text
/var/lib/tftpboot/kickstart/secondstage-package-sources.yml
```

## Aktueller fachlicher Stand

- Der historische Meilenstein ist die automatisierte CentOS-7.8-Basisinstallation bis zum Login.
- Der aktive Ausbau liegt im Management-State-System und der SecondStage-Validierung.
- `risdeploy` installiert komponentengetrieben Pakete/Services auf bereits installierten Clients.
- `risdeploy-validation` liefert PASS/FAIL-Zusammenfassungen und kann per pytest als Gate genutzt werden.
- Web-/Render-Arbeit ist als Operator-UI gedacht; Fehler im Renderpfad sollen sichtbar werden statt still zu verschwinden.

## Detaillierte Doku

- `RISng_README.md` beschreibt den urspruenglichen PXE-/CentOS-Staging-Durchbruch.
- `ansible/secondstage/README.md` beschreibt das aktuelle SecondStage-Modell.
- `botskills/risng-skill.md` ist die verbindliche Kurzreferenz fuer Pfade, Aliases und aktuelle Fallstricke.
