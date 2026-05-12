# botskills/risng-skill.md

## Repo-Info
- **Root:** `~/.openclaw/workspace/risng`
- **Branch:** `main`
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
  management/     → Bashrc deployen
  tools/          → Hilfs-Tools
  systemupdate/   → Paket-Updates
  risng/          → ★ RISng Secondstage ★
  risng_install/  → RISng-Installer
  gopass/         → gopass-Integration
ansible/bootstrapvm/
ansible/playbooks/    → 5 Playbooks
ansible/secondstage/  ★ RISng Secondstage-Kern ★
ansible/runtime/      → Runtime-Payloads
ansible/inventory/    → hosts.yml, vlans.yml
ansible/group_vars/
Information/Agent-Tasks/  → Agent-Aufgaben
logs/                 → Runtime-Logs
Administration/redfish/ → Redfish-Diagnose
```

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

### Bashrc-Aliases (aus bashrc.md + bashrc-root-risng)
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

## Wrapper-Funktionen
- `run_risng_playbook [opts] playbook logfile [inventory]` — Auto-detects RISNG_DIR
- Eigenes ansible.cfg: `RISNG_ANSIBLE_CFG="$RISNG_CODE_DIR/ansible/ansible.cfg"`

## ssh/config
- `Host github-risng → ~/.ssh/risng`

## Agent-Protocol-Kontext
RISng teilt PXE/Bootstrap-Mechanik mit ironscope, ergänzt Secondstage- und Anforderungs-/Validierungsschicht.
