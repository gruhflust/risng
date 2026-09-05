# RIS8 – 3-Phasen-Architektur (Alma 9.8, Ansible-only, MAC-gebunden)

Stand: 2026-09-05
Branch: `RIS8-mockup`
Entscheidungen: dto 2026-09-05 (Paketstruktur, viel committen, Botskill als Resume-Basis)

## Ziel

iCAS_PhII-Zielmaschinen (Rollen wie `icmd`, `ifdo`, `isar`, …) automatisch per PXE
installieren und per MAC-Adresse rollenspezifisch deployen – **ohne Puppet**.

## Grundlagen (aus RIS7-ISO-Analyse, siehe `RIS7-ISO-Analyse.md`)

| Artefakt | Größe | Herkunft | Verwertung in RIS8 |
|---|---|---|---|
| `components/plattform/repository` | 292 MB (18 RPM) | RIS7-ISO | Phase 2 (Repo-Publish + Install) |
| `components/products/repository` | 290 MB (46 RPM) | RIS7-ISO | Phase 2 (Repo-Publish + Install) |
| `components/plattform/drivers` | 455 MB (optional) | RIS7-ISO | Phase 2 (nur wenn Rolle braucht) |
| `setup.tar.xz` | 442 MB (Produkt-Rootfs) | RIS7-ISO | Referenz für Phase 3 (Ansible-Übersetzung) |
| `default-keys` RPM | SSH-Hostkeys + `/root/.ssh/authorized_keys` | LP3 noarch | Phase 1 (Kickstart-`%post`/Phase-2-Task) |
| `disserver` RPM 3.5.1 | 76 Dateien (`/disserver`, `/etc/disserver.cfg`, `dis` CLI, httpd-conf, rsyslog, sudoers) | LP3 x86_64 | Phase 2/3 (DisServer-Instanz auf RISng-Server) |
| `stage1/stage1.sh` | 77 MB ELF-Bundle | LP3 | **nicht** mehr verwendet (Ansible ersetzt) |
| `puppet-agent` RPM | 7.27.0 | LP3 | **nicht** installiert (Puppet verboten) |

**Alma 9.8 Basis-ISO** (fix, vom Upstream):
- URL: `https://repo.almalinux.org/almalinux/9.8/isos/x86_64/AlmaLinux-9.8-x86_64-dvd.iso`
- Größe: 15 151 923 200 Bytes
- SHA-256: `7a392bdc879afd159b30da39a356b7b26c1ddf618b01549164da9aadbc40d814`
- Basis-URL für Kickstart: `http://<risng>/almalinux/9.8/` (lokal gemirrt) oder direkt `https://repo.almalinux.org/almalinux/9.8/`

## 3-Phasen-Modell

### Phase 1 – Basisinstallation (Anaconda-Kickstart, automatisch)
1. PXE-Boot (BIOS: `pxelinux.0`, UEFI: `bootx64.efi`) → Alma-9.8 `vmlinuz`+`initrd.img` vom RISng-Server.
2. Kernel-Args: `inst.ks=http://<risng>/kickstart/ris8-base.cfg inst.repo=http://<risng>/almalinux/9.8/ ip=dhcp inst.waitfornet=60 inst.text`
3. Kickstart `ris8-base.cfg`:
   - `url --urlpoint=http://<risng>/almalinux/9.8/`
   - `part /boot` + LVM `/` (oder `autopart --type=lvm`)
   - `%packages`: `@core @base python3 dnf-utils cronie rsyslog` (schlank, Produkt-Teile in Phase 2)
   - `%pre --logs`: MAC aus `BOOTIF`/`/sys/class/net` → Fortschritts-POST an `http://<risng>/progress/` (DisServer-Web-API, bestehende Webserver-Rolle)
   - `%post --nochroot`: SSH-Hostkeys (default-keys-Inhalt) + `authorized_keys` (dto-Schlüssel) + `rootpw --lock`
   - Reboot
4. Ergebnis: Alma 9.8 läuft, SSH erreichbar, Fortschritt im Web sichtbar.

### Phase 2 – Produkt-RPMs (Ansible, nach Basisinstallation)
1. RISng-Server publiziert LP3-Repo (292 MB plattform + 290 MB products) unter `http://<risng>/lp3/…`.
2. Ansible-Run (via MAC-Inventory oder SSH-Discovery):
   - dnf-repo `lp3-plattform`, `lp3-products`
   - Install: `plattform-tools` `poco-*` `python-netsnmpagent` `dfshwagent*` `disserver` (nur DisServer-Rolle) `default-keys`
   - **kein** `puppet-agent` (aus Repo-Blacklist oder `exclude`)
   - Grundkonfiguration: User `nor`, GPG-Keys, SNMP-Grundgerüst, chrony
3. Ergebnis: Produkt-Fundament installiert, keine Rollenausprägung.

### Phase 3 – Rollen-Deployment (Ansible, MAC-gebunden)
1. `mac_role_map.json` auf RISng-Server: `AA:BB:CC:… → icmd | ifdo | isar | …`
2. Ansible-Rolle `icas_<rolle>` pro Endrolle (Übersetzung aus Puppet-Manifests in `setup.tar.xz`):
   - gemeinsame Basis: `nor`-User (uid 501), sudo-Regeln, SSH-Hardening, serial-console, GRUB-serial, display-manager/autologin, Java (Rolle-spezifisch), sysctl, kdump, RAID
   - rollen-spezifisch: SNMP-Conf, DF-SH, BIOS-Config (iDRAC/AMT), Pakete
3. Fortschritt: jedes Playbook-Task/Role-Ende POSTet an `/progress/` (Webserver)
4. Ergebnis: Endgerät rollenspezifisch konfiguriert.

## Web/Fortschritt (bestehend, wiederverwendet)
- `webserver`-Rolle: Flask `report_viewer.py` + nginx, `deploy_state.json`, `mac_role_map.json`
- Neue Endpunkte: `POST /progress/` (Phase-1/2/3-Update), `GET /progress/<mac>` (Status)
- DHCP-Rolle: `boot_profile` pro Host (MAC → Phase-1-Boot)
- `pxe_assemble`: BIOS/UEFI-Fragments `NN-*.cfg`

## Platz-Plan (Testsystem 89 GB)
| Artefakt | GB |
|---|---|
| Alma 9.8 DVD-ISO (gemirrt) | 15,1 |
| LP3 plattform+products Repo (lokal) | 0,6 |
| tftpboot (PXE, kernel/initrd) | <0,1 |
| OS-Grundlage + Web-Stack | ~8 |
| **Puffer** | ~50 |

Keine 14-GB-ISO-Extraktion, kein Live-Squashfs-Build, kein CentOS → passt mit Reserve.

## Paket-Plan (Commits auf `RIS8-mockup`)

P1  Architektur-Doku + Botskill-Update (dieses Commit)
P2  `almalinux98_install` Rolle: defaults (URL/Checksum), fetch_iso, publish mirror, kickstart `ris8-base.cfg`, PXE-Fragments, DHCP-Profil `ris8`
P3  Progress-API in `webserver`-Rolle: `/progress/` Endpunkte + `progress_state.json`
P4  `getisos` + `risng-setup` wiring: `almalinux98_install` (default on), `ris7_install` + `risng_install` (CentOS) deaktiviert
P5  `lp3_repo` Rolle: LP3-Repo-Publish (plattform+products, kein drivers) + `default-keys`
P6  Phase-2-Playbook `ris8-phase2.yml`: Basis-RPMs + `nor` + GPG + SNMP-Grundgerüst (Ansible)
P7  `mac_role_map` + MAC→Inventory-Auflösung (Phase 2/3-Routing)
P8  Phase-3-Grundgerüst: gemeinsame Ansible-Rolle `icas_base` (nor, sudo, ssh, serial, grub, display)
P9  Erste Referenzrolle (dto-Auswahl, z.B. `icmd` oder `ifdo`) als Ansible-Rolle
P10 Fortschritt: Phase-3-Task-Hooks → `/progress/`
P11 Doku + Botskill-Final, Validierungs-Checkliste

## Offene Punkte (dto)
- [ ] Phase 3: welche Rolle als Referenz zuerst? (`icmd`, `ifdo`, `isar`?)
- [ ] DisServer: kommt als `disserver`-RPM auf dem RISng-Server oder als reine Ansible-Web-Rolle? (Empfehlung: RPM, es bringt `/dis` API + httpd-Config)
- [ ] Testsystem: 89-GB-VM ist bereit (192.168.188.207), PXE-NIC ens19 noch ohne Kabel
