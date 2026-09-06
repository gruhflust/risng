# lp3_repo

RIS8 Phase 2 Quelle: publiziert die LP3-Plattform- und iCAS-Product-RPM-Repots
(~580 MB) auf den RISng-Host.

## WICHTIG (2026-09-06)
Die LP3-/RIS7-ISO ist **keine** Abhängigkeit der Ansible-Pipeline. Sie dient
nur der Informationsextraktion im Agent-Workspace (Mount auf der Build-VM)
und wird nie heruntergeladen, nie gemountet und nie auf dem PXE-Host
erwartet. Die Quelle ist ein **operator-gestagter Repo-Baum**.

## Staging-Vertrag (out-of-band, z. B. von der Build-VM)
```
/var/tmp/pxe-build/lp3-staging/          (lp3_repo_staging_root)
  plattform/repository/                   (RPMs + repodata)
  products/repository/                    (RPMs + repodata, ohne puppet-*.rpm)
```
Staging-Beispiel vom ISO-Mount (`/mnt/ris7iso`):
```
mkdir -p /var/tmp/pxe-build/lp3-staging
rsync -a --exclude='puppet-*.rpm' /mnt/ris7iso/components/plattform/repository/ \
     /var/tmp/pxe-build/lp3-staging/plattform/repository/
rsync -a --exclude='puppet-*.rpm' /mnt/ris7iso/components/products/repository/ \
     /var/tmp/pxe-build/lp3-staging/products/repository/
```

## Verhalten
- **Default: AUS** (`lp3_repo_enabled: false`). `feuer` läuft ohne LP3-Quelle
  grün durch.
- Aktiv mit `-e lp3_repo_enabled=true`, wenn der Staging-Baum angelegt ist.
- Publiziert via `rsync` nach `lp3/icas_phii/{plattform,products}/repository/`
  (HTTP-Root, über nginx).
- **Kein Puppet**: `find`-Prüfe nach dem Publish lehnen `puppet-*.rpm` ab.
  (Verifiziert: kein anderes LP3-Paket `puppet-agent` als Abhängigkeit braucht.)
- Ohne Staging-Baum: harte Fehlermeldung mit klarem Staging-Hinweis.

## Platz-Verhalten
| Artefakt | Größe |
|---|---|
| plattform/repository | ~292 MB |
| products/repository | ~290 MB |
| ISO | **0 MB auf dem Host** (nie vorhanden) |

## Verwendung
- In `risng-setup.yml` als Rolle `lp3_repo` (Phase-2-Quelle) hinter
  `almalinux98_install`.
- Phase-2-Playbook (`ris8-phase2.yml`, P6) installiert auf den Alma-Client:
  `poco-*`, `plattform-tools`, `python-netsnmpagent`, `disserver`,
  `default-keys` aus `lp3_repo_platform_baseurl` / `lp3_repo_products_baseurl`.
