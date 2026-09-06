# botskills/risng-skill.md

## Repo-Info
- **Root:** `~/.openclaw/workspace/risng`
- **Branch:** `RIS8-mockup` (aktive RIS8-Umsetzung)
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
  rhel98_install/ → optionaler RHEL-9.8-PXE-Autoinstall-Mockup (**aus**, 2026-09-05 `d605730`)
  almalinux98_install/ → ★ AlmaLinux 9.8 PXE-Autoinstall (RIS8 Phase 1) ★
  lp3_repo/        → LP3-Plattform- + Produkt-RPMs (RIS8 Phase 2 Quelle)
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

### RIS7 ISO-Regel (2026-09-06, dto-Weisung)
- Die mounted RIS7/LP3-ISO (`/mnt/ris7iso`, agent-eigene Mounts) ist **NUR** Informationsquelle fuer mich (LP3-Rollen-Design, Kickstart-Referenz, RPM-Liste). Sie darf **niemals** Teil der Ansible-Pipeline werden: kein Download, kein Mount auf dem PXE-Host, kein ISO-Pfad in Rollen/Playbooks.
- `lp3_repo` (2026-09-06 umbaut): `default(false)`, einzige Quelle ist der operator-gestagte Baum `lp3_repo_staging_root` (default `/var/tmp/pxe-build/lp3-staging`) mit `plattform/repository` + `products/repository`. Ohne Staging-Baum: harte Fehlermeldung inkl. Staging-Hinweis. Aktiv: `-e lp3_repo_enabled=true`.
- `ris7_install` bleibt `default(false)` (operator-supplied ISO, Legacy-RIS7-PXE-Pfad).
- Folge: `getisos` -> `feuer` laeuft ohne LP3-ISO gruene durch (vorher: fatal "No LP3 source found" bei `lp3_repo | Fail when no LP3 source is available`).

## RIS7 ISO-Analyse (Doku)
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

**Fortschritt Paket-Plan (Stand 2026-09-05, alle DONE-Pakete gepusht nach `origin/RIS8-mockup`):**
- P1 Doku+Botskill: **DONE** `c8101eb` (Architektur-Doku `docs/requirements/information/Agent-Tasks/RIS8-3-Phasen-Architektur.md`)
- P2 `almalinux98_install`-Rolle: **DONE** `4f9ca0d` + Fixes `a78b9eb`+`83effde` — `ansible/bootstrapvm/roles/almalinux98_install/`
  - **Stand 2026-09-05:** ISO-basierter Mirror (DVD mount + lokaler `rsync`), Kickstart mit korrekten `repo --baseurl` Direktiven, PXE-Fragmente `28-almalinux98.cfg` (BIOS+UEFI)
  - **Validiert auf `user@192.168.188.207`:** 1184 BaseOS + 6501 AppStream RPMs, vmlinuz+initrd, Kickstart, Bootstrap-Key, HTTP 200 auf alle Endpunkte
- P3 Progress-API in `webserver`: **DONE** `da6e430`
- P4 wiring + Legacy-Aus: **DONE** `c8bb843` + `d605730` (rhel98_install_enabled → false)
- P5 `lp3_repo` Rolle: **DONE** `2734d8a`+`cd22903` — **Validiert auf Test-VM:** 27 plattform + 46 products RPMs, 0 Puppet-RPMs
- P6 Phase-2-Playbook `ris8-phase2.yml`: **DONE** `f7b4cf8`
- P7 MAC→Inventory-Router `ris8-phase3.yml`: **DONE** `6d08b87`

**Status: P1–P7 DONE (gepusht). Phase 1 + Phase 2 + Phase-3-Infrastruktur komplett. Phase 3 konfig (P8–P10) steht an.**
- P8 `icas_base`-Ansible-Rolle (SNMP, DisServer-Client, rsyslog, sudoers, tftp-Layout): TODO
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

## RHEL 9.8 mockup (DEAKTIVIERT 2026-09-05)
- `d605730`: `rhel98_install_enabled` → `false`. Wurde durch `almalinux98_install` ersetzt
  (Alma 9.8 statt RHEL 9.8). Rolle bleibt im Repo als Referenz, läuft standardmäßig nicht mehr.
- DHCP-Profil `rhel98` bleibt definiert, wird aber nicht mehr befüllt.

## AlmaLinux 9.8 (RIS8 Phase 1) – VALIDIERT 2026-09-05
- **Rolle:** `almalinux98_install` (`risng-setup.yml` Reihenfolge: nach `rhel98_install`, vor `lp3_repo`)
- **Strategie:** DVD-ISO (SHA256-verifiziert) einmal ro loop-monten → lokal `rsync` BaseOS+AppStream → PXE kernel/initrd `copy` → Kickstart + PXE-Fragmente rendern → unmount.
  - **Warum:** Debian-13-`rsync` hat kein https-Modul; `rsync-ssl` akzeptiert keine URLs; `wget`-Mirror liefert nur HTML-Indizes. Die DVD-ISO hat das korrekte Anaconda-Layout `<comp>/{repodata,Packages}`.
- **Kickstart:** zwei `repo --baseurl=http://<ip>/almalinux/9.8/{BaseOS,AppStream}` (nicht `url --urlpoint`, das ist kein gültiges Anaconda-Keyword)
- **Validierung `user@192.168.188.207` (2026-09-05):** `ok=42 changed=16 failed=0`; 1184+6501 RPMs, vmlinuz (15 MB) + initrd (223 MB), `28-almalinux98.cfg` (BIOS+UEFI), `bootstrap/controlhost_id_ed25519.pub`, **HTTP 200** auf alle 8 Endpunkte via nginx (root `/var/lib/tftpboot`).
- **Disk-Spitze:** Mirror ~13,6 GB unter `/var/lib/tftpboot/almalinux/9.8/`; ISO 15 GB in `/var/tmp/pxe-build/iso/`. Gesamtdisk-Nutzung auf Test-VM: ~57 GB / 89 GB.

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

## Lokale Entwicklung – Testlauf-Workflow auf .207 (2026-09-06, dto-Weisung)

**Ziel:** Eigenständiger automatisierter Testzyklus auf der Proxmox-Test-VM
`user@192.168.188.207` (Proxmox-Host `192.168.188.92`, Rechte dazu noch offen
beim dto). Der Zyklus:

1. **Snapshot zurücksetzen:** Proxmox-Snapshot `isosLoaded` der VM207
   (ISOs bereits geladen, saubere Basis). Über Proxmox-API/CLI auf
   `192.168.188.92`: `qm rollback 207 isosLoaded` (bzw. `qm rollback 207` +
   `qm start 207`). VM207 = die Test-VM, nicht der Proxmox-Host.
2. **VM starten** und **~60–120 s** warten, bis SSH erreichbar:
   `ssh user@192.168.188.207` (Key-Auth, bereits funktioniert).
3. **Repo aktualisieren:** `cd ~/risng && git pull --rebase` (Branch `RIS8-mockup`).
4. **feuer anstoßen:** `feuer` (Alias → `risng-setup.yml`), läuft min. ~6 min
   (typisch 6–40 min je nach ISO-Cache). Log: `~/feuer.log`.
5. **Ergebnis kontrollieren:**
   - `grep -nE "failed=[1-9]|fatal:" ~/feuer.log | tail`
   - `grep -A2 "PLAY RECAP" ~/feuer.log | tail -3` → `failed=0` = grün.
   - Bei Fehler: `sed -n` um die `fatal:`-Zeile + `TASKS RECAP` für Langzeit.
6. **Bei Fehler:** Log auswerten → Fix im Workspace-Repo
   (`~/.openclaw/workspace/risng`) → commit + push → auf VM `git pull` →
   **Snapshot-Reset** → neuer Lauf. Erst nach grünem Lauf Ergebnis als
   Validierung werten.

**Wichtige Regeln dazu:**
- `feuer` NICHT parallel starten; vor Lauf prüfen, dass kein `ansible-playbook`
   auf der VM läuft: `pgrep -af ansible-playbook`.
- Snapshot `isosLoaded` ist die **einzige** definierte Reset-Basis; keine
   anderen Snapshots anfassen.
- Proxmox-Zugang: erst wenn dto Rechte auf `192.168.188.92` gibt (API-Token
   oder SSH); bis dahin manuell vom dto anstoßen, Rest (SSH auf .207, Log-
   Auswertung, Fix, Push) läuft eigenständig.
- `git dubious ownership` auf der VM: `git config --global --add safe.directory
   /home/user/risng` (einmalig, bereits gesetzt 2026-09-06).

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
