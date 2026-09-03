# RIS7 ISO-Analyse (LP3 iCAS_PhII-RIS 7.0-00)

> Dokumentiert am 2026-09-03 (macagent, 192.168.64.2) auf Basis der gemounteten
> ISO `LP3_iCAS_PhII-RIS_7.0-00_engver202602-rhel9.6-x86_64.iso` im Workspace
> unter dem Mountpoint `RIS7/`.

## 1. Identifikation

| Feld            | Wert                                              |
|-----------------|---------------------------------------------------|
| Produktname     | LP3 iCAS_PhII-RIS 7.0-00 (EngVer202602)           |
| Basis           | Red Hat Enterprise Linux 9.6 x86_64 (DVD)         |
| Plattform       | LinuxPlattform 3 — Release 3.31.0                 |
| Build-Host      | 811530ffb984                                      |
| Build-Zeit      | Wed Feb 25 15:09:54 UTC 2026 (MEDIUM_RELEASE)     |
| Disk-Timestamp  | 1744157129.811558 (April 2025, .discinfo)         |
| Varianten       | AppStream, BaseOS                                 |
| Arch            | x86_64                                            |

`MEDIUM_RELEASE` und `PLATTFORM_RELEASE` sind Custom-Dateien des LP3-Builds
(auf RHEL-DVDs nicht vorhanden) und tragen die produkt- bzw. plattformspezifischen
Versions- und Build-Informationen.

## 2. Layout der ISO

```
RIS7/
├── AppStream/Packages/        6262 RPM (el9)
├── BaseOS/Packages/           1173 RPM (el9)
├── boot/grub/                 GRUB-Dateien
├── components/                LP3-spezifische Repos
│   ├── plattform/repository/  plattform-tools, dfshwagent, disserver, puppet, ...
│   ├── plattform/drivers/     nvidia 570, dkms, robot-env (dkms/nvidia aktivierbar)
│   └── products/repository/   iCAS-Produkt-Pakete (java, xfce, ntfs-3g, ...)
├── EFI/BOOT/                  UEFI-Boot (BOOTX64.EFI, grubx64.efi)
├── images/                    pxeboot/{vmlinuz,initrd.img}, install.img, efiboot.img
├── isolinux/                  BIOS-Boot
├── ks.cfg                     Anaconda-Kickstart (zweistufige Installation)
├── logPoll.sh                 Fortschritts-Polling für DIS-Server
├── lp_settings.json           LP3-repos-Definition (dnf, stage1/2/production)
├── MEDIUM_RELEASE             Produkt-Version (7.0-00_EngVer202602)
├── PLATTFORM_RELEASE          LP3-Version (REL-3.31.0)
├── setup.tar.xz               ~77 MB — Setup-Partition (RIS-Root, /var/lib/plattform)
├── stage1/
│   └── stage1.sh              Self-extracting Stage1-Binary (pre-script, ELF)
├── extra_files.json           Checksummen der ISO-Zusatzdateien
├── .treeinfo                  productmd (checksums, variants)
├── media.repo                 InstallMedia-Repo-Definition
├── EULA, GPL                  Lizenztexte
└── RPM-GPG-KEY-redhat-{release,beta}
```

## 3. Zweistufige Installationsarchitektur

Die RIS7-Installation folgt dem klassischen LP3-Stufenmodell:

### Stage 1 (Stage1.sh / pre-script)
- `stage1/stage1.sh` ist ein self-extracting-Script:
  `sed -e '1,/^exit$/d' "$0" | tar xf -` entpackt `pre-script` (ELF-Binary)
  und `remotelog/remotelog.sh`.
- `LD_LIBRARY_PATH` wird um `./stage1lib` erweitert, dann `./pre-script` ausgeführt.
- Aufgabe: System-Grundlayout, Partitionierung, `setup.tar.xz` auf die
  Setup-Partition entpacken (bzw. in DIS-Server-Mode von BASEURL laden).

### Stage 2 (post-script / LinuxPlattformStage2.service)
- Das `%post --nochroot`-Skript in `ks.cfg`:
  1. Mountet die Setup-Partition unter `/var/lib/plattform/mnt/setup`.
  2. Entpackt `setup.tar.xz` in die Setup-Partition, wenn noch nicht vorhanden.
  3. Kopiert `/stage2` und `stage2.sh` in das Ziel-System.
  4. Erzeugt `/usr/lib/systemd/system/LinuxPlattformStage2.service`
     (oneshot, After=getty@tty1+network-online, ConditionPathExists=/LinuxPlattformStage2).
  5. Enablet den Service → beim ersten Boot nach Anaconda-Install startet
     `stage2.sh` → `/stage2` mit 10 s Verzögerung (Network-Hiccup-Circumvention)
     → danach Reboot.
  6. Im DIS-Server-Mode: `curl updateMachine bootmethod=harddisk` → Target
     bootet ab dann von der Platte.

### DIS-Server-Mode (PXE)
- `ks.cfg` erkennt `ks=http://...` im Kernel-Parameter und leitet daraus
  `BASEURL`, `DISURL` und `MACHINEID` ab.
- Maschine wird beim DIS-Server registriert (`getMachineId`/`addMachine`).
- `logPoll.sh` liest `/tmp/rpm-script.log` (Fortschritt `CUR/TOTAL`), berechnet
  Prozent und schickt `updateMachine progress=<P>` an `${DISURL}/dis/`.
- Fortschritts-Werte sind diskret (10,12,24,35,42,52,60,68,72,74,100) —
  nicht kontinuierlich.

## 4. Kickstart (ks.cfg) — Kerninhalte

```
authselect select minimal
rootpw --iscrypted <md5-hash>       # ← im Kickstart als Klartext-Hash
%packages
@base
poco-{foundation,util,xml,json,net,encodings}
python-netsnmpagent
puppet-agent
plattform-tools
-dracut-config-rescue
%end
%pre --erroronfail
  # BASEURL/DISURL/MACHINEID-Erkennung
  # wget stage1.sh, setup.tar.xz, logPoll.sh
  # logPoll.sh im Hintergrund starten
  # stage1.sh ausführen (chvt 6, Terminal-Wechsel für Selector)
  # /tmp/partition wird von stage1.sh erzeugt → %include
%post --nochroot --erroronfail
  # setup.tar.xz → Setup-Partition
  # stage2 + stage2.sh + LinuxPlattformStage2.service installieren
  # GPG-Key RPM-GPG-KEY-LinuxPlattform-3 importieren
  # DIS-Server: bootmethod=harddisk
```

**Hinweis:** `rootpw --iscrypted` verwendet einen MD5-Hash (`$1$...`), der
im Klartext auf der ISO liegt. In einer RIS8-Installation wäre dies zu
prüfen (sha512, keine Hashes auf ISO, Passwort-Variation pro Ziel-System).

## 5. LP3-Repositories (lp_settings.json)

| Repo                    | Pfad                          | Priority | GPG          | stage1 | stage2 |
|-------------------------|-------------------------------|----------|--------------|--------|--------|
| InstallSource-BaseOS    | BaseOS                        | 50       | redhat       | ✓      | ✓      |
| InstallSource-AppStream | AppStream                     | 50       | redhat       | ✓      | ✓      |
| LinuxPlattform          | components/plattform/repository | 10     | LP3          | ✓      | ✓      |
| LinuxPlattformDrivers   | components/plattform/drivers  | 20       | LP3          | ✗      | ✗      |
| Products                | components/products/repository| 30       | (off)        | ✓      | ✓      |
| os-updates              | components/os-updates         | 40       | (off)        | ✗      | ✗      |

## 6. LP3-Paket-Übersicht (ausgewählt)

### components/plattform/repository (aktiv, priority 10)
- `plattform-tools-0.4` — LP3-Core-Tooling
- `disserver-3.5.1` — DIS-Server (PXE-Installations-Orchestrierung)
- `dfshwagent-1.1.2` / `dfshwmib-2.7` / `dfshwstatus-1.1.2` — DFS-HW-Monitoring
- `puppet-agent-7.27.0` — Konfigurationsmanagement
- `poco-*` (foundation, net, xml, json, encodings, util) — C++-Bibliothek
- `python-netsnmpagent` — SNMP-Agent
- `puppet-agent` + `puppet` (im AppStream)
- `amtterm_ssl`, `Arcconf`, `lnvgy_utl_lxcer` — HW-Tools (Dell/Lenovo)
- `storcli`, `perccli` — RAID-Management (Dell PERC, Broadcom)
- `srvadmin-*` (idracadm7, hapi) — Dell iDRAC-CLI

### components/plattform/drivers (deaktiviert, priority 20)
- `nvidia-x11-drv-570.153.02` + `kmod-nvidia-570.153.02` — GPU-Treiber
- `robot-env-4.1.3` / `6.1.1` — Robotik-Umgebungen
- `dkms-3.0.12` — dynamische Kernel-Module

### components/products/repository (aktiv, priority 30)
- `libs_hmi_icas-1-20240918` — iCAS-HMI-Bibliothek
- `jre-8u202-linux-x64` — Oracle JRE 8
- `gnuplot-5.4.3` — Plotting
- `xfce4-terminal`, `xfwm4`, `libxfce4*` — XFCE-Desktop
- `synergy-1.14.3.5` — Multi-Maus/Tastatur (CWP-Setup)
- `ntfs-3g`, `fuse-sshfs` — Dateisystem-Tools
- `screen-4.8.0`, `meld-3.22.3`, `collectl-4.3.2`, `etic-3.2.2`
- `xorg-x11-server-Xorg-1.20.11-28.0.1dfs.el9` — DFS-patchter X-Server
- `pugixml`, `libcerf`, `perl-*` — Bibliotheken

### AppStream/BaseOS (RHEL 9.6 Standard)
- 6262 + 1173 RPMs, u. a. `anaconda-34.25.5.17`, `ansible-core-2.14.18`,
  `puppet` (AppStream), `python3`, `kernel`, `gdm`

## 7. setup.tar.xz (Setup-Partition, ~77 MB)

Enthält das Root-Dateisystem der LP3-Setup-Partition (auf Ziel-System
unter `/var/lib/plattform`):
- `etc/` — Konfigurationsdateien (centos-release, grub2, dracut, ...)
- `usr/bin/` — Utilities (cpio, db_*, locale, ...)
- `var/lib/plattform/` — LP3-Bibliotheken und Skripte
- `stage1lib/` — Laufzeitbibliotheken für `pre-script`
- `remotelog/remotelog.sh` — Remote-Logging-Setup
- `pre-script` — ELF-Binary (Stage1-Installation)
- `post-script` — ELF-Binary (Stage2-Aufruf)

Die Setup-Partition ist die persistent installierte Basis, von der `stage2`
beim ersten Boot gestartet wird.

## 8. Produkt-Rollen (Puppet, components/products/repository)

Die `setup.tar.xz` enthält die vollständige Puppet-Manifest-Struktur
`puppet/products/iCAS_PhII/modules/`. Definierte Rollen:

| Rolle       | Zweck                                        |
|-------------|----------------------------------------------|
| `icwp`      | iCAS Command Workstation (CWP)               |
| `isar`      | iSAR Workstation                             |
| `itg`       | iTG (Terminal Group)                         |
| `corrp`     | CORRP (Corporate Role)                       |
| `fdps`      | iFDPS (Flight Data Processing System)        |
| `drf`       | iDRF                                         |
| `atg`       | ATG (ATC Ground)                             |
| `epp`       | EPP                                          |
| `fls`       | FLS (Flight Log System)                      |
| `smp`       | SMP (Shared Management Platform)             |
| `cmd`       | iCMD (Command)                               |
| `fdo`       | iFDO                                         |
| `itapclient`| iTAP-Client                                  |
| `itapserver`| iTAP-Server                                  |
| `install`   | RIS-Installations-Server (DIS-Server-Mode)   |
| `disserver` | DIS-Server (PXE-Orchestrierung + DHCP)       |
| `smws`      | SMWS (System Management Workstation)         |

### Gängige Profile (alle Rollen)
- `profile::icas::network`, `profile::icas::ip_address_concept`
- `profile::icas::kdump` (kernel-crash-dumps)
- `profile::icas::chrony` (NTP: icas_lan, corrp_fdps, sws_lan)
- `profile::icas::dfshwagent` (HW-Monitoring)
- `profile::icas::obm` (out-of-band management: iDRAC/IPMI/AMT)
- `profile::icas::serial_console` (Grub2 serial, ttyS0/ttyS1)
- `profile::icas::snmp_{isim,fdps_corrp,other}` (SNMP je nach Rolle)
- `profile::icas::bioscfg` (BIOS-Konfiguration: Dell CCM, syscfg.ini)
- `profile::icas::dconf` (Gnome/dconf-Settings)
- `profile::icas::users::nor` (UID 501, Group nor)
- `profile::icas::sudo::*` (Sudo-Roles)
- `profile::icas::gdm::custom_conf_*` (Display-Manager je Rolle)
- `profile::icas::autologin` (GDM-Autologin)
- `profile::security::pwpolicy` (PAM-pwquality)
- `profile::icas::selinux::disabled` (SELinux aus, außer disserver: permissive)
- `profile::icas::ssh` (iCAS-SH-Hardening: Ciphers, MACs)
- `profile::icas::nvidia::{always,auto}` (GPU)
- `profile::icas::prepare_raid` (RAID-Setup für disserver/drf/itapserver)
- `profile::icas::disks` (Platten-Layout)
- `profile::icas::facts::make_facts` (Custom Facter-Facts)
- `idrac::network::passthrough` (iDRAC-Netzwerk)
- `python::config` (python → python3 Symlink)

## 9. Vergleich RIS7 vs. RIS8-Mockup (RISng)

| Aspekt             | RIS7 (LP3, RHEL 9.6)                        | RIS8-Mockup (RISng)                     |
|--------------------|---------------------------------------------|-----------------------------------------|
| Basis              | RHEL 9.6 DVD + LP3-Overlay                  | RHEL 9.8 (bzw. RISng-Base)              |
| Stufenmodell       | Stage1 (pre-script ELF) → Stage2 (ELF)      | Secondstage (Ansible-RISng)             |
| Konfiguration      | Puppet + Hiera                              | Ansible (RISng-Playbooks)               |
| DIS-Server         | disserver-3.5.1 RPM, /dis/ Webservice       | RISng-Management-State (Change02)       |
| Progress-Reporting | logPoll.sh → DIS-Server curl                | (offen: Analog?)                        |
| GPG                | RPM-GPG-KEY-LinuxPlattform-3 (extern)       | (RISng: eigene Keys, gopass-Integration)|
| Repo-Struktur      | 3 LP3-Repos + RHEL BaseOS/AppStream         | RISng-Boot-Repos + Debian/RHEL          |
| Root-Passwort      | MD5-Hash in ks.cfg (auf ISO)                | (RISng: keine Klartext-Hashes)          |
| PXE-Profil         | DHCP-Profil mit ks=http://...               | RISng: DHCP-Profile (debian, rhel98)    |

### Relevante Unterschiede für RIS8
1. **Kein LP3-Overlay**: RIS8-Mockup nutzt die RHEL-9.8-Installation
   direkt; das LP3-Stufenmodell (stage1/pre-script, stage2/ELF) wird durch
   RISng-Secondstage-Playbooks ersetzt.
2. **Puppet → Ansible**: RIS7 nutzt Puppet/Hiera für Roll-Konfiguration;
   RIS8 nutzt Ansible-Playbooks und group_vars.
3. **DIS-Server-Anbindung**: RIS7 registriert Maschinen beim DIS-Server
   (`/dis/` Webservice). RIS8 hat das Management-State-System (Change02)
   mit persistenter State-Aufbewahrung — die DIS-Server-Anbindung muss
   für RIS8-Targets nachgeahmt oder ersetzt werden.
4. **Fortschritts-Meldung**: `logPoll.sh` ist spezifisch für das DIS-
   Server-Protokoll; in RIS8 wäre ein analoges Reporting im
   Management-State zu implementieren.
5. **Root-Passwort-Sicherheit**: RIS7 lagert den MD5-Hash in `ks.cfg` auf
   der ISO; RIS8 sollte `rootpw` nur über gopass/Secrets verwalten.

## 10. Offene Punkte für RIS8

- [ ] RIS8-DHCP-Profil `rhel98` muss die RIS7-Kickstart-Parameter
      (`ks=http://.../ks.cfg`, `inst.ks=`) für Kompatibilität verstehen
      oder durch eigene Boot-Parameter ersetzen.
- [ ] DIS-Server-Protokoll (`/dis/` Webservice: `getMachineId`,
      `addMachine`, `updateMachine`) muss in RISng-Management-State
      abgebildet oder als externer Service dokumentiert werden.
- [ ] Fortschritts-Meldung (`logPoll.sh`-Analog) für RIS8-Secondstage
      definieren.
- [ ] `RPM-GPG-KEY-LinuxPlattform-3`-Import in RIS8 (falls LP3-Pakete
      weiterhin installiert werden).
- [ ] `setup.tar.xz`-Analog in RISng: Welche Komponenten werden auf der
      Setup-Partition (bzw. im RISng-Secondstage-Image) benötigt?
- [ ] `logPoll.sh`-Fortschrittswerte (diskret: 10-100) in RISng-
      Management-State-Mapping übertragen.
