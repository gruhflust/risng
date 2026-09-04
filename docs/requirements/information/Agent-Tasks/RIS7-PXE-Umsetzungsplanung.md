# RIS7 PXE-Umsetzungsplanung (risng-Methodik)

Stand: 2026-09-04, Branch `RIS8-mockup`
Quellen: `docs/requirements/information/RIS7-ISO-Analyse.md`, `RIS7-Rollen-Spec.md`,
gemountete ISO `LP3_iCAS_PhII-RIS_7.0-00_engver202602-rhel9.6-x86_64.iso` (Workspace,
SHA-256 `d464f72c18c46142a7b3be7be7b990a6ce51af1ef518a32e00c19347885709c4`).

## Ziel

Die RIS7-ISO (LinuxPlattform 3 3.31.0, RHEL 9.6) als vollständige PXE-Quelle im
RISng-Staginghost servieren: BIOS + UEFI, alle nötigen Artefakte (Installer-Repo,
LP3-Components, Stage1, Kickstart), per `feuer`/`getisos` idempotent aufgebaut,
als eigenes PXE-Menü `RIS7 (iCAS_PhII)` wählbar und per DHCP-Boot-Profil
`ris7` vorwählbar. Damit steht die RIS7-Referenzinstallation reproduzierbar als
PXE-Quelle bereit und dient als Referenz für die RIS8-Secondstage-Arbeit.

## Architektur (analog `rhel98_install` + `risng_install`)

```
Staginghost (Debian 13, RISng-Bootstrap-VM)
├── /var/tmp/pxe-build/iso/ris7.iso                  # geprüfte ISO (14 GB)
├── /var/tmp/pxe-build/ris7-iso/                     # bsdtar-Extrakt (temporär)
└── /var/lib/tftpboot/
    ├── images/ris7/                                 # vmlinuz, initrd.img
    ├── ris/7.0/                                     # Installer-Repo (HTTP via nginx)
    │   ├── BaseOS/  AppStream/
    │   ├── components/{plattform,products,os-updates}/
    │   ├── stage1/stage1.sh  setup.tar.xz  logPoll.sh
    │   ├── pre-script  post-script  stage2  obmcli  plattform
    │   ├── stage1lib/  savedata/  remotelog/        # stage1-Payload-Artefakte (cd /-Pfade)
    │   ├── ks.cfg  (angepasst: rootpw --lock; %include /tmp/repos.cfg aktiv)
    │   ├── media.repo  lp_settings.json  extra_files.json
    │   ├── RPM-GPG-KEY-redhat-{release,beta}
    │   └── images/pxeboot/  isolinux/  boot/grub/  EFI/
    └── pxelinux.cfg/25-ris7.cfg  +  boot/grub/25-ris7.cfg   # Menü-Fragmente
```

Boot-Kette (PXE, BIOS + UEFI identisch):
1. Menü `RIS7 (iCAS_PhII)` → `images/ris7/vmlinuz` + `initrd.img`
2. `inst.stage2=http://<tftp>/ris/7.0` `inst.repo=http://<tftp>/ris/7.0`
   `ks=http://<tftp>/kickstart/ris7.cfg` `lp.product=iCAS_PhII` `inst.gpt inst.text`
3. `ks.cfg` `%pre`: DIS-Erkennung via `${DISURL}/dis/` (ohne disserver: still
   weiter), `stage1/stage1.sh` → pre-script (slots, partition, repos.cfg, /tmp/partition)
4. `%include /tmp/partition`, Install aus HTTP-Repo, `%post` → stage2-Setup + Reboot

## Anpassungen gegenüber der ISO-Original-ks.cfg

- `%include /tmp/repos.cfg` bleibt **aktiv** (geprüft: pre-script erzeugt
  `/tmp/repos.cfg` selbst aus `lp_settings.json` + `detect_baseurl()`, daher
  vorhanden im DVD- und im PXE-Fall).
- `stage1/stage1.sh` entpackt `pre-script` in den **aktuellen Arbeitssatz**
  (`cd /` → `/pre-script`), `%post` ruft `/post-script` mit
  `LD_LIBRARY_PATH=./stage1lib` auf. Beide Pfade werden deshalb zusätzlich
  im HTTP-Repo-Root gepublished (wie auf der DVD-Root vorhanden).
- Root-Passwort: `rootpw --lock` statt geheimer Hash (Hash aus ISO-ks.cfg
  wird NICHT übernommen, vgl. RIS7-Rollen-Spec §8).
- Alles andere 1:1 (keyboard de, lang en, UTC, @packages-Liste, GPG-Key-Import).

## Phasen / Commits

| # | Phase | Artefakte |
|---|-------|-----------|
| 1 | Planung (dieses Dokument) | `docs/requirements/information/Agent-Tasks/RIS7-PXE-Umsetzungsplanung.md` |
| 2 | Role-Scaffold + Defaults | `ansible/bootstrapvm/roles/ris7_install/defaults/main.yml`, `README.md` |
| 3 | Fetch-ISO (getisos) | `tasks/fetch_iso.yml` (url/local, SHA-256, getisos-Wiring) |
| 4 | Publish-Repo (feuer) | `tasks/publish_repo.yml` (Extrakt→rsync, os-updates, Validierung) |
| 5 | Kickstart + Boot | `tasks/kickstart_and_boot.yml`, `templates/kickstart.cfg.j2`, `templates/bootentry-{pxelinux,grub}.cfg.j2` |
| 6 | Menü- + DHCP-Integration | `roles/dhcp/defaults/main.yml` (Profil `ris7`), `risng-setup.yml` (Role + Artefakt-Checklist), `getisos.yml` |
| 7 | Validierung + Doku | Ansible-Syntax, Template-Render-Test, `README.md` (Repo), `botskills/risng-skill.md` |

## Validierungsstrategie

- **Statisch:** `ansible-playbook --syntax-check` auf `risng-setup.yml` + `getisos.yml`;
  Template-Render via `ansible localhost -m template` mit Test-Var-Set (tftp_server_ip, Pfade).
- **Lokal-funktional (diese VM):** Publish-Pfad gegen einen lokalen
  `/var/lib/tftpboot`-Mock ausführen ist zu riskant für die laufenden Dienste;
  stattdessen: `bsdtar`-Extrakt-Test in einen Temp-Pfad + rsync-Preview (nichts
  in `/var/lib` der laufenden Bootstrap-VM schreiben). Voll-Integrationstest
  (PXE-Boot Testclient) auf dem realen RISng-Staginghost via `feuer`.
- **Auf dem Staginghost:** `getisos` → `feuer` → `trigger-pxe-boot` mit
  DHCP-Host-Override `boot_profile: ris7`; Boot-Fortschritt auf TTY des Clients;
  DIS-Client-Verhalten ohne disserver (Still-Fall) beobachten.

## Offene Punkte (Bewusstsein, keine Blocker)

- `components/os-updates/` fehlt auf der ISO → wird bei Publish mit leerem
  Verzeichnis + `.present` angelegt (ks.cfg toleriert das: `wget ... || true`
  via `&& mv`-Kette ohne `set -e`-Break).
- LP3-Kernel-Parameter `lp.slot=1`/`lp.ondisk=disk0` sind DVD-Slot-Logik;
  PXE-Default-Boot erhält sie bewusst NICHT (frische Slot-1-Installation).
- `lp.cleardevices=disk0` wird im PXE-Fall weggelassen (erstmalige Installation
  auf leerer Zielfestplatte; gezielte Slot-Wechsel kommen später als
  zusätzliche Menüeinträge `RIS7 slot2` etc.).
- `stage1lib/`, `pre-script`, `post-script`, `obmcli`, `stage2`, `plattform`,
  `savedata/`, `remotelog/` werden im Repo-Root gepublished (Entpack-Artefakte
  des stage1-Payloads; `LD_LIBRARY_PATH=./stage1lib` + `cd /`-Pfade).
