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
