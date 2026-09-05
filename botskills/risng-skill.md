# botskills/risng-skill.md

## Repo-Info
- **Root:** `~/.openclaw/workspace/risng`
- **Branch:** `IOPC-3412/migration` (based on `main`; intended staging baseline)
- **Remote:** `github-risng:gruhflust/risng` | **Key:** `~/.ssh/risng`
- **Zweck:** RISng Secondstage-PXE + Management-State-UI + Web-Render
- **Status:** Management-State-Entwicklung (Change02), Web-Render-Fehler-Detection

## Verzeichnisstruktur (Kern)
```
ansible/bootstrapvm/roles/
  ironscope/      → Network, Bootloader
  dhcp/           → DHCP-Server
  dns/            → DNS-Server
  pxe_assemble/   → PXE-Dateien
  debian-live/    → Debian-Live-ISO
  netinstall/     → Netinstall-Profile
  webserver/      → Webserver
  management/     → lokale Repo-/PXE-Vorbereitung
  tools/          → Hilfs-Tools
  systemupdate/   → Paket-Updates
  risng/          → ★ RISng Secondstage ★
  risng_install/  → RISng-Installer
  rhel98_install/ → optionaler RHEL-9.8-PXE-Autoinstall-Mockup
  gopass/         → gopass-Integration
ansible/bootstrapvm/
ansible/playbooks/    → 5 Playbooks
ansible/secondstage/  ★ RISng Secondstage-Kern ★
ansible/runtime/      → Runtime-Payloads
ansible/inventory/    → hosts.yml, vlans.yml
ansible/group_vars/
ansible/operator/      → Bashrc-Vorlage und Operator-Werkzeuge
ansible/operator/administration/ → Diagnose- und Verwaltungsfunktionen
ansible/operator/python/ → NetBox-, VLAN- und Testwerkzeuge
docs/requirements/information/Agent-Tasks/ → Agent-Aufgaben
docs/history/          → historische PXE-/Staging-Dokumentation
```

## Migration layout

The repository root is intentionally limited to `README.md`, `ansible/`,
`botskills/`, `build/`, and `docs/`. Deployment material remains below
`ansible/`; non-deployed build helpers are under `build/`; requirements,
history, and architecture documents are below `docs/`.

## Branch archival policy

Historical feature branches are preserved as annotated
`archive/branches/<branch-name>` tags. Active development is limited to
`main` and `IOPC-3412/migration`.

## RISng-Spezifika

### Management-State-System (Change02)
- Persistenter Management-State für Deploy-Target-Routing
- `46f0231` — Add initial persistent management state scaffold
- `4773adc` — Start Change02 management continuity branch
- `aab74ff` — Make assign deploy target-specific with immediate deploying state
- `4ec5095` — Route targeted deploy via management runtime IP
- `05721c8` — Record runtime-vs-assigned IP management observation
- `1dec37f` — Fix reboot path to resolve management runtime IP by MAC

### Web-Render-UI
- `7253042` — Clear deploy and management state when forgetting hosts
- `7f4611b` — Fix UI colors for manageable and deployable states
- `b8a5672` — Rename render-web-ui alias to ris-render-web-ui
- `571a8fc` — Use active operator home for web UI render path resolution

### Bashrc-Aliases (aus ansible/operator/templates/bashrc.j2)
**PXE:** feuer getisos getrispackes pxe pxe-setup pxe-cleanup
**Network:** network-restart network-reset repair-dhcp heal trigger dhcpstatic
**State:** risk-state risk-state-reset risk-state-export risk-state-import
**Deploy:** risk-deploy risk-deploy-dryrun risk-deploy-force risk-deploy-cancel
**Forget:** risk-forget risk-forget-dryrun
**UI:** ris-render-web-ui
**Management:** risk-status risk-manage risk-manage-list risk-manage-clear
**Gopass:** gopass-fetch gopass-push gopass-init
**Git:** iron pnt gitgud
**Sonst:** ginit watcher terror guck status

### RIS7 ISO-Analyse (Doku)
- `docs/requirements/information/RIS7-ISO-Analyse.md` dokumentiert die
  gemountete RIS7-DVD `LP3_iCAS_PhII-RIS_7.0-00_engver202602-rhel9.6-x86_64.iso`
  (Mountpoint `RIS7/` im macagent-Workspace): LP3 3.31.0 auf RHEL 9.6,
  zweistufiges Stage1/Stage2-Modell (pre-/post-script ELF, disserver-3.5.1,
  logPoll.sh-Progress-Reporting), LP3-Repo-Layout (plattform/products/drivers),
  Puppet-Rollen (icwp, itg, atg, epp, disserver, ...) und Vergleich/RIS8-Ableitung.

## RIS8 – 3-Phasen-Umsetzung (aktive Aufgabe, Stand 2026-09-05)

**Auftrag (dto 2026-09-05):** iCAS_PhII-Rollen (icmd/ifdo/isar/…) per PXE auf
Alma 9.8 (fix) automatisch installieren; Rollenausprägung per MAC-Adresse über
Ansible; Fortschrittsanzeige via Webserver auf RISng-Server. **Puppet verboten.**
Kein volles `feuer` auf kleinen Test-VMs (64-GB-VM am 2026-09-05 vollgeschrieben;
neue VM 89 GB: 192.168.188.207).

**Doku (Single Source of Truth):**
`docs/requirements/information/Agent-Tasks/RIS8-3-Phasen-Architektur.md`
(Phasen, ISO-Daten, Paket-Plan P1–P11, offene Punkte)

**Alma 9.8 (fix):** `AlmaLinux-9.8-x86_64-dvd.iso`, 15 151 923 200 B,
SHA-256 `7a392bdc879afd159b30da39a356b7b26c1ddf618b01549164da9aadbc40d814`,
Upstream `https://repo.almalinux.org/almalinux/9.8/` (BaseOS/AppStream/CRB + isos/).

**LP3-Artefakte (RIS7-ISO, Mount im macagent-Workspace `/mnt/ris7iso`):**
- `components/plattform/repository` 292 MB (plattform-tools, poco-1.9.4, disserver-3.5.1,
  dfshwagent*, python-netsnmpagent, default-keys, srvadmin*, **puppet-agent → NICHT installieren**)
- `components/products/repository` 290 MB (iCAS: jre-8, synergy, xfce4-*, libs_hmi_icas, gnuplot …)
- `setup.tar.xz` 442 MB = Produkt-Rootfs-Referenz für Phase 3 (Puppet→Ansible-Quelltext)
- `default-keys` RPM = SSH-Hostkeys + `/root/.ssh/authorized_keys` (Schlüsselhinterlegung)
- `disserver` RPM 3.5.1 = `/disserver/`, `/etc/disserver.cfg`, `dis` CLI, httpd/rsyslog/sudoers

**Rahmenregeln für die Umsetzung:**
- Viele kleine Commits auf `RIS8-mockup`, jeweils `git push -u origin RIS8-mockup`
- Nach jedem Paket: Botskill + Architektur-Doku aktuell halten
- Testsystem: `user@192.168.188.207` (89 GB, Debian 13, PXE-NIC ens19, WAN ens18)
- `risng-setup.yml`-Rollenblock (Phase 01): `almalinux98_install` aktivieren,
  `ris7_install`/`risng_install`/`rhel98_install` deaktivieren (Platz sparen)
- Fortschritt: `webserver`-Rolle (Flask `report_viewer.py`) um `/progress/` erweitern;
  States unter `/var/lib/tftpboot/runtime/` (z.B. `progress_state.json`)
- MAC→Rolle: `/etc/risng/mac_role_map.json` (existiert, `report_viewer.py` nutzt sie)

**Fortschritt Paket-Plan (Stand 2026-07-08, alle DONE-Pakete gepusht nach `origin/RIS8-mockup`):**
- P1 Doku+Botskill: **DONE** `c8101eb` (Architektur-Doku `docs/requirements/information/Agent-Tasks/RIS8-3-Phasen-Architektur.md`)
- P2 `almalinux98_install`-Rolle: **DONE** `4f9ca0d` — `ansible/bootstrapvm/roles/almalinux98_install/`
  - `defaults/main.yml`: fixiert Alma 9.8 (URL+SHA256 `7a392bdc...`), nur BaseOS+AppStream
  - `tasks/fetch_iso.yml`: ISO-Download (getisos-Pfad), SHA256-Verifiziert, Idempotent
  - `tasks/main.yml`: **keine** 15-GB-ISO-Extraktion — Repo-Mirror via `rsync` vom öffentlichen Mirror (`https://repo.almalinux.org/almalinux/9.8/{BaseOS,AppStream}/`), PXE kernel/initrd via loop-mount `images/pxeboot/`, Kickstart + PXE-Fragmente `28-almalinux98.cfg`, Controlhost-Public-Key nach `/bootstrap/controlhost_id_ed25519.pub`
  - `templates/kickstart.cfg.j2`: Phase-1-Basis (rootpw gelocked, SSH-Key, MAC-basierter Fortschritt-POST in %pre/%post, `/etc/risng-role`=ris8-base)
- P3 Progress-API in `webserver`: **DONE** `da6e430` — `report_viewer.py.j2`
  - `POST /progress/` (Form oder JSON: mac, phase 1|2|3, step, status running|success|failed|skipped, hostname, message)
  - `GET /progress/<mac>`, `POST /progress/reset/<mac>`; State `/var/lib/tftpboot/runtime/progress_state.json`
  - Dashboard: neue Spalte "RIS8 Phase" + Status-Override `RIS8_P<n>:<STATUS>`
- P4 wiring + Legacy-Aus: **DONE** `c8bb843` — `risng-setup.yml`/`getisos.yml` integrieren `almalinux98_install`; `ris7_install_enabled: false` und `risng_install_enabled: false` (CentOS 7.8) als Defaults → spart 14 GB + 4.8 GB; Live-RIS (Debian) bleibt aktiv
- P5 `lp3_repo` Rolle (plattform+products Publish, ~580 MB, kein Puppet-RPM): **DONE** `2734d8a` + Wiring `cd22903`
    - `ansible/bootstrapvm/roles/lp3_repo/`: NUR `plattform/`+`products/` via `rsync --exclude=puppet-*.rpm` nach `lp3/icas_phii/{plattform,products}/repository/`; Quelle gemountetes ISO-Dir ODER ISO-Datei (loop-mount ro)
    - **Kein Puppet**: `--exclude=puppet-*.rpm` + `find`-Prüfe (kein anderes LP3-Paket braucht puppet-agent); lokal gegen gemountete RIS7-ISO getestet: 561 MB, jre-8+poco-foundation, 0x puppet — nächste Aufgabe
- P6 Phase-2-Playbook `ris8-phase2.yml` (Basis-RPMs poco*/plattform-tools, User `nor`): **DONE** `f7b4cf8`
    - `ansible/secondstage/ris8-phase2.yml`: Play 1 (bootstrapvm) liest Phase-1-Erfolg aus `progress_state.json` + IP aus DHCP-Lease/management_state, dynam. Gruppe `ris8_phase2_targets`, optional `-e ris8_target_mac=`
    - Play 2 (Ziel): `ris8-lp3.repo` (gpgcheck=0) + `dnf install poco-* plattform-tools python-netsnmpagent disserver default-keys jre-8` + User `nor` (wheel) + `/etc/risng-role` RIS8_PHASE=2 + Progress-POST phase=2; rescue: Failure-POST + Re-Raise; Wrapper `operator/risng-phase2`; **Syntax OK**üst, Fortschritt-POST): TODO
- **Status: P1-P6 DONE (gepusht). Phase 1 (Basis-Install) + Phase 2 (RPMs) komplett. Phase 3 (Rollen, Puppet zu Ansible) steht an (P7-P10).**
- P7 MAC→Inventory-Router (bestehende `mac_role_map.json` + `secondstage`-Mechanik wiederverwenden): TODO
- P8 `icas_base`-Ansible-Rolle (Puppet-Grundgerüst → Ansible): TODO
- P9 Referenzrolle (dto-Auswahl, z.B. `icmd` oder `isar`): TODO
- P10 Phase-3-Fortschritt-Hooks pro Rolle: TODO
- P11 Doku-Final + Validierungs-Checkliste: TODO

**Phase-3-Einstieg (nächster Schritt):** LP3-Rollen liegen als `setup.tar.xz` (442 MB product-rootfs) im RIS7-Mount; Puppet-Manifeste/Module sind der Referenz-Baukasten für die Ansible-Umsetzung. P7 = MAC zu Rollen-Play-Router; P8 = `icas_base`-Rolle (SNMP, DisServer-Client, rsyslog, sudoers, tftp-Layout); P9 = erste konkrete Rolle (dto-Auswahl).

**Resume-Hinweise (wichtig bei Neustart):**
- Repo: `~/.openclaw/workspace/risng`, Branch `RIS8-mockup`, Remote `git@github-risng:gruhflust/risng`.
- Vor jeder Aktion `git pull --rebase`; nach jedem Paket Commit + `git push`.
- RIS7-ISO für LP3-Artefakte (P5/P6): lokal unter `/mnt/ris7iso` (gemountet, falls noch da) — sonst ISO `LP3_iCAS_PhII-RIS_7.0-00_engver202602-rhel9.6-x86_64.iso` im macagent-Workspace neu mounten; LP3-Repo-Quellen: `components/plattform/repository` (292 MB, 18 RPMs) + `components/products/repository` (290 MB, 46 RPMs).
- **Kein Puppet**: `puppet-agent`-RPM muss NICHT installiert werden; LP3-Plattform-RPMs sind OK.
- Test-VM: `user@192.168.188.207` (89 GB, Debian 13, PXE-NIC `ens19`, WAN `ens18`).
- Alma 9.8 fixiert: `https://repo.almalinux.org/almalinux/9.8/isos/x86_64/AlmaLinux-9.8-x86_64-dvd.iso`, SHA256 `7a392bdc879afd159b30da39a356b7b26c1ddf618b01549164da9aadbc40d814`.
- Fortschritt-Endpunkt auf RISng-Server: `POST http://<risng>/progress/` (Phase 1 Kickstart postet bereits; Phase 2/3 posten über Playbook-Task).
- Botskill-Status-Block immer aktuell halten (wie dieser).

## RHEL 9.8 mockup
- Branch `RIS8-mockup` adds the enabled-by-default `rhel98_install` role.
- `getisos` and `feuer` fetch the configured entitled DVD ISO with retries and
  SHA-256 validation. URL/headers/checksum remain external variables, never
  Git content; source mode `local` remains available as an offline fallback.
  Initial access is key-only through the staged control-host public key.
- DHCP profile `rhel98` selects the `RHEL 9.8 AutoInstall` BIOS/UEFI option.

## RIS7 PXE-Quelle (2026-09-04)
- Rolle `ris7_install` (Default `ris7_install_enabled: true`) publiziert die
  operator-supplied ISO `LP3_iCAS_PhII-RIS_7.0-00_engver202602-rhel9.6-x86_64.iso`
  (~14 GB, SHA-256 `d464f72c18c…785709c4`) als komplette PXE-Quelle auf dem
  RISng-Staginghost: `ris/7.0/`-Installer-Tree (HTTP), `images/ris7/` kernel+
  initrd, `kickstart/ris7.cfg` (1:1 ISO-ks.cfg, nur `rootpw --lock` anstatt
  ISO-Secret-Hash), BIOS/UEFI-Menü `RIS7 (iCAS_PhII)` (Fragments `25-ris7.cfg`),
  DHCP-Boot-Profil `ris7`.
- Stage1-Payload (pre-script/post-script/stage1lib/savedata) wird beim Publish
  aus `stage1/stage1.sh` in den Repo-Root entpackt (`cd /`-Pfade der LP3).
  `components/os-updates/.present`-Marker wird nachgelegt (auf ISO abwesend).
- Kickstart `%pre` bleibt LP3-original (DIS-Erkennung am Base-URL, still-fall
  ohne disserver), `%include /tmp/repos.cfg` aktiv (pre-script erzeugt es selbst
  aus `lp_settings.json`).
- Wiring: `risng-setup.yml` (roles), `getisos.yml` (ISO-fetch),
  DHCP-`dhcp_boot_profiles` + `dhcp_boot_menu_defaults`, feuer-Artefakt-Checkliste.
- Doku: `docs/requirements/information/Agent-Tasks/RIS7-PXE-Umsetzungsplanung.md`
  + `docs/requirements/information/RIS7-Rollen-Spec.md` +
  `docs/requirements/information/RIS7-ISO-Analyse.md`.
- Offen: PXE-Boot-Integrationstest auf dem RISng-Staginghost
  (`getisos` → `feuer` → `trigger-pxe-boot`, DHCP-Override `boot_profile: ris7`).

## Wrapper-Funktionen
- `run_risng_playbook [opts] playbook logfile [inventory]` — Auto-detects RISNG_DIR
- Eigenes ansible.cfg: `RISNG_ANSIBLE_CFG="$RISNG_CODE_DIR/ansible/ansible.cfg"`

## ssh/config
- `Host github-risng → ~/.ssh/risng`

## Agent-Protocol-Kontext
RISng teilt PXE/Bootstrap-Mechanik mit ironscope, ergänzt Secondstage- und Anforderungs-/Validierungsschicht.

## Aktueller Staging-Fix 2026-07-06
- `ansible/bootstrapvm/risng-setup.yml` hatte das gleiche Risiko wie SPEC: Der
  GDM3 Display-Manager wurde waehrend des Stagings mit `state: started`
  gestartet. Das kann lokale Konsolen-/Staging-Sessions uebernehmen und den
  Staging-Lauf abbrechen lassen.
- Fix: GDM3 wird fuer den naechsten Boot enabled, aber nicht mehr waehrend des
  Playbooks gestartet. Zusaetzlich werden die systemd-Links fuer
  `/etc/systemd/system/default.target`, `display-manager.service` und
  `graphical.target.wants/display-manager.service` rebootfest gesetzt und
  `daemon_reload` ausgefuehrt.
- `getisos`-Alias-Fehler `ERROR: the playbook ... could not be found` entstand
  aus fragiler Checkout-Erkennung. Die Bashrc-Erkennung darf nur den RISng-
  Checkout `~/risng` akzeptieren, wenn dort `ansible/bootstrapvm/risng-setup.yml`
  existiert; `run_risng_playbook` prueft Playbook und Inventory vor dem
  Ansible-Aufruf und meldet die aufgeloesten Pfade. `risng-setup.yml` darf fuer
  Bootstrap-/Bashrc-Pfade nicht mehr auf alte `botrepo/risng_code`-Layouts
  zeigen, sondern muss den laufenden RISng-Checkout aus `playbook_dir` verwenden
  und `/home/risng/risng` darauf verlinken.
- `getisos`-Downloadfehler `Connection failure: The read operation timed out`
  bei `Download Debian net-install ISO` entstand durch den Ansible-Default von
  10s fuer `get_url`. RISng nutzt jetzt wie ironscope zentrale Defaults
  `iso_download_timeout: 180`, `iso_download_retries: 5`,
  `iso_download_retry_delay: 10` fuer Live-ISO, Netinstall-ISO und Netboot-
  Tarball.
- `ansible/bootstrapvm/recover-system-time.yml` is imported by both
  `risng-setup.yml` and `getisos.yml`, so an isolated ISO prefetch gets the
  same stale-clock recovery and diagnostics as a complete staging run.
- The staged RISng GNOME user receives
  `ansible/artifacts/BackgroundPic.png`. The playbook annotates it root-side,
  sets system dconf defaults, runs `dconf update`, and then applies the value
  through a temporary user D-Bus session. This avoids silent wallpaper failures
  when no graphical user session exists during staging.
