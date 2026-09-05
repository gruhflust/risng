# lp3_repo

RIS8 Phase 2 Quelle: publiziert die LP3-Plattform- und iCAS-Product-RPM-Repots
(~580 MB) von der operator-gelieferten LP3-ISO auf dem RISng-Host.

## Zweck
- NUR die zwei Komponenten-Repots `plattform/repository` + `products/repository`
  werden via `rsync` auf `lp3/icas_phii/{plattform,products}/repository/`
  publiziert (HTTP-Root, über nginx).
- **Keine** 14-GB-ISO-Extraktion, kein `setup.tar.xz`, kein RHEL-Basis.
- **Kein Puppet**: `--exclude=puppet-*.rpm` + nachträgliche `find`-Prüfe
  stellen sicher, dass keine Puppet-RPMs in den publizierten Baum gelangen.
  (Verifiziert: kein anderes LP3-Paket `puppet-agent` als Abhängigkeit braucht.)

## Quellen (automatisch erkannt, Priorität)
1. `lp3_repo_iso_mountpoint` — bereits read-only gemountetes ISO-Verzeichnis
   (z.B. `/mnt/ris7iso`), wenn dort `components/{plattform,products}` existieren.
2. `lp3_repo_iso_path` — ISO-Datei (>1 GB), wird bei Bedarf loop-mounted.

## Platz-Verhalten (89-GB-Test-VM)
| Artefakt | Größe |
|---|---|
| plattform/repository | ~292 MB |
| products/repository | ~290 MB |
| ISO (nur bei Dateisource, loop-mount) | 14 GB (vorhanden, nicht extrahiert) |

## Verwendung
- In `risng-setup.yml` als Rolle `lp3_repo` (Phase-2-Quelle) hinter
  `almalinux98_install`.
- Phase-2-Playbook (`ris8-phase2.yml`, P6) installiert auf den Alma-Client:
  `poco-*`, `plattform-tools`, `python-netsnmpagent`, `disserver`, `default-keys`
  aus `lp3_repo_platform_baseurl` / `lp3_repo_products_baseurl`.
