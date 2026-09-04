# RIS7 Systemrollen-Spezifikation (Quelle: RIS7-ISO, puppet/products/iCAS_PhII)

Extrahiert am 2026-09-03 aus `RIS7/stage1/stage1.sh` (selbst-entpackender Bootstrap, enthält den
gesamten Puppet-Tree) und `RIS7/{ks.cfg,logPoll.sh}`. Extraktions-Tree: `/tmp/ris7-extract/`.

> **Hinweis:** `setup.tar.xz` enthält NUR das Kickstart-Root-FS (CentOS7-Base), KEIN Puppet.
> Der Puppet-Tree, `pre-script`, `post-script`, `stage1lib/`, `remotelog/`, `obmcli`, `stage2`
> liegen im Self-Extracting-Skript `stage1/stage1.sh`.
> `pre-script`/`post-script` sind ELF-Binaries (x86-64, ~1.2 MB / ~1.1 MB), nicht interpretierbar —
> deren Logik (Rollenzuweisung via nodes-Hiera, RAID-Vorbereitung, OBM-Setup) muss bei RIS8
> in Ansible neu implementiert bzw. als Blackbox übernommen werden.

## 1. Rollen-Übersicht

Alle Rollen: `role::icas::<rolle>` (17 Rollen in `modules/role/manifests/icas/`), delegiert an
Legacy-`icas::roles::<rolle>` + `profile::icas::*` Profile.

| Rolle | GUI/headless | Autologin | icas::roles::* (Legacy) | icas.service (DMN) | OBM | SNMP-Conf | Serial | RAID | Chrony | Java |
|---|---|---|---|---|---|---|---|---|---|---|
| icwp | GUI (graphical) | ja (nor) | workstation + icwp | ja | ipmi/amt | snmpd.conf | ja | nein | icas_lan | JRE 1.8.0_202 |
| isar | GUI | nein | workstation | nein | ipmi/amt | snmpd.conf | ja | nein | icas_lan | JRE 1.8.0_202 |
| itg | **headless** (multi_user) | nein | — | nein | ipmi/amt | **keine** | ja | nein | **keine** | JRE 1.8.0_111 |
| atg | **headless** (multi_user) | nein | atg | nein | ipmi/amt | snmpd.conf.isim | ja | nein | icas_lan | JDK 1.8.0_202 (purge links) |
| epp | GUI | ja (nor) | common_epp_smp | nein | ipmi/amt | snmpd.conf.isim | ja | nein | icas_lan | JDK-purge + libs |
| smp | GUI | ja (nor) | common_epp_smp | nein | ipmi/amt | snmpd.conf.isim | ja | nein | icas_lan | JDK-purge + libs |
| fdps | GUI | nein | base | ja | ipmi/xcc | snmpd.conf.stby | ja | nein | corrp_fdps | JRE 1.8.0_202 |
| corrp | GUI | nein | base | ja | ipmi/xcc | snmpd.conf.stby | ja | nein | corrp_fdps | JRE 1.8.0_202 |
| drf | GUI | nein | base | ja | ipmi/xcc | snmpd.conf | ja | **ja** | icas_lan | JRE 1.8.0_202 |
| fls | GUI | ja (nor) | workstation | nein | ipmi/amt | snmpd.conf | ja | nein | icas_lan | JRE 1.8.0_202 |
| cmd | GUI | ja (nor) | workstation | ja | ipmi/amt | snmpd.conf | ja | nein | icas_lan | JRE 1.8.0_202 |
| fdo | GUI | ja (nor) | fdo | ja | ipmi/amt | snmpd.conf | ja | nein | icas_lan | JRE 1.8.0_202 |
| itapclient | GUI | nein | itapclient | nein | ipmi/amt | **keine** | ja | nein | sws_lan | JDK-purge (alles) |
| itapserver | GUI | nein | itapserver | nein | ipmi/xcc | snmpd.conf | ja | **ja** | sws_lan | JDK-purge + xlwt |
| disserver | GUI | nein | base | nein | ipmi/xcc | snmpd.conf | ja | **ja** | sws_lan | JRE 1.8.0_202 |
| install | GUI | nein | base | nein | ipmi/amt | snmpd.conf | ja | **ja** | icas_lan | JRE 1.8.0_202 |
| smws | GUI | nein | base | nein | ipmi/amt | snmpd.conf | ja | nein | icas_lan | JRE 1.8.0_202 |

Legende OBM: `ipmi` = iDRAC/IPMI (PowerEdge R730/R740, ThinkSystem SR650 V2, Precision 7920 Rack);
`amt`/`xcc` = Intel AMT (Precision 7810/7820 Tower) bzw. Lenovo XClarity OneCli (ThinkSystem).
Serial: IPMI-SOL-Setup für Server, iAMT-Serial für Towers (Precision/ThinkStation P5).

## 2. Gemeinsame Profile (alle/most Rollen)

| Profil | Wirkung |
|---|---|
| `profile::icas::users::nor` | User `nor` (UID 501, GID 501, grp `wireshark`, home /home/nor, bash). **rootpw-Hash und nor-Passwort-Hash existieren im Manifest — NICHT in RIS8 übernehmen, nur Platzhalter** |
| `profile::icas::groups::nor` / `groups::wireshark` | GID 501 bzw. Gruppe wireshark |
| `profile::icas::limits::nor` | /etc/security/limits.d/20-nproc.conf: nor - nproc 16384 |
| `profile::icas::network` + `icas_network` | Bonding/Interfaces aus Hiera-Keys `nodes.<host>.icas_network` + `defaults.icas_network` (deep-merge, Default: bond3=OBM eth6/7 mode4, bond0=CORE eth2/3 mode1, bond2=STBY eth8/9 mode1, eth0=iMAS-A, eth1=iMAS-B, eth5=FBS, ethtool `wol d`) |
| `profile::icas::ip_address_concept` | Symlink `ip_address_concept` → `resources/{DFS,DFS_LEGACY,INDRA,LVNL}_ip_address_concept` (Hiera-Parameter `type`) |
| `profile::icas::install_server::isclient` | IS-Client auf allen Nicht-Server-Rollen |
| `profile::icas::kdump::icas` (bzw. `::disserver`) | kdump-Setup |
| `profile::security::pwpolicy` | pwquality/login.defs: algo=md5, minlen=6, maxdays=99999, mindays=0, keine Komplexitäts-Pflicht, enforce_for_root=false (Defaults in data/defaults.yaml) |
| `profile::icas::keyboard` | Tastatur (de) |
| `profile::icas::sysctl` | /etc/sysctl.d iCAS-Parameter (TCP/UDP Buffers 16MB, ipfrag-Thresh, somaxconn 4096, …; Rollen-Override z.B. icwp.yaml: msgmnb/msgmax 500000) |
| `profile::icas::selinux::disabled` (disserver: `::permissive`) | SELINUX=disabled, SELINUXTYPE=targeted |
| `profile::icas::ssh` | sshd.conf-Quelle: `profile/icas/sshd.service` + Module `ssh` |
| `profile::icas::login::default` / `::icwp` | /etc/systemd/logind.conf.d/ris_logind_{default,icwp}.conf; ICWP: zusätzlich getty@tty3–6.enable |
| `profile::icas::rename` | Hostname-Rename (skripte `rename*.sh`) |
| `profile::icas::disks` | Mapping slots→disks (`icas::slots_to_disks`) → /usr/local/bin/icas-ris-slots_to_disks |
| `profile::icas::bioscfg` | Hiera `icas::bioscfg::filename` → /etc/syscfg.ini (R730) oder /etc/cctk.ini (Precision 7810) + root-Bash-Aliase (configbios/rstbios/chkbios) |
| `profile::icas::obm` | Hardware-Dispatch: R730/R740/7920/SR650→`obm::ipmi`; Precision-Towers→AMT (Paket amtterm), keine OBM-Konfig; Lenovo→xcc/OneCli |
| `profile::serial_console::serial_console` | IPMI-SOL (Server) oder iAMT (Towers): grub2 serial, serial-getty, securetty; Defaults: 9600-8N1, ttyS0, tty0_console=yes, getty=yes, root-login nein |
| `profile::icas::dfshwagent` | /etc/dfshwagent.conf.template aus `dfshwagent/templates/<product>-<role>-dfshwagent.conf.template` (41 Templates: R730/R740/7810/7820/P5/SR650 × rollen); Plugin-Kette Coretemp/IPMITool/SmartCtl/MegaCli/Edac |
| `profile::icas::facts::make_facts` | eigene Facter-Funktionen |
| `profile::icas::setcap::nmap` | nmap Cap_NET_RAW für alle Nutzer (nor) |
| `profile::icas::dconf` | GNOME-dconf-Regeln (idlescreensaver, metacity, icas_workstation_gnome_extensions, …; je Rolle data/<rolle>/<rolle>.yaml) |
| `profile::icas::sudo::basic` | /etc/sudoers.d/icas, root ALL ALL (passwd) |
| `profile::icas::sudo::operational_roles_rules` (icwp/fdps/corrp/drf/cmd/fdo) | nor: `systemctl start/stop icas` |
| `profile::icas::sudo::broadcaster` (nur icwp) | nor: `/root/bin/replace_broadcaster.sh` ohne passwd |
| `profile::icas::sudo::timeout_rule` (nur smws) | nor: `/usr/bin/timeout` |
| `profile::icas::sudo::common_rules` | (siehe common_rules.pp) |
| `profile::icas::prepare_raid` (drf/itapserver/disserver/install) | `/root/bin/prepare_raid` + `prepare_raid_for_images`, Exec `prepare_raid -n` (RAID-Erkennung/Mount) |
| `profile::icas::chrony::*` | chrony.conf via plattform: `icas_lan` (servers aus Hiera `profile::icas::tref.iCAS LAN.*`), `corrp_fdps` (+peers, local stratum 10), `sws_lan` (SWS-LAN) |
| `profile::icas::nvidia::auto`/`::always` | xorg/nvidia-Modul (icwp: always, andere: auto) |
| `profile::icas::gdm::custom_conf_*` | GDM custom.conf: icwp (AutomaticLogin nor), atg, epp_smp, cmd_fdo, itapclient, standard (WaylandEnable=false, DisallowTCP) |
| `profile::icas::autologin` (icwp/epp/smp/fls/cmd/fdo) | GDM-Autologin `nor` (augeas) |
| `tuned`, `storage_manager`, `python::config`, `xorg`, `icc/xfce`, `audio` (icwp: pulseaudio) | Plattform-Bausteine |

## 3. Rollenspezifisch

### icwp
- Pakete: rhel96::common, rhel96::perlauthensasl, product::dell, rhel86::pulseaudio,
  product::xfwm4_18, product::cms_icas_mib, product::gtk2_engines, product::xorg_x11_utils
- `icas::roles::icwp` → workstation + icwp-Dateien: `icwp/icwp-session.sh`,
  `icwp/icwp.desktop`, `icwp/etc-X11-Xresources`, `nor.accountsservice`
- `profile::icas::icwp::phoenix_hb` (eth5 phoenix-heartbeat), `profile::icas::icwp::xorg`
  (`icwp/13-eGalaxEXC3000.xorg.conf`), `icwp::synergy` (`profile/icas/icwp/synergy.conf`)
- `icwp_tid` (TID-Dateien `icwp-config-headless/{mdw,sdd,tid}.bin`, `xorg.conf.headless`)
- `icas_dmn::icas_service` (icas.service + systemctl enable), `profile::icas::sudo::broadcaster`
- GUI, autologin, selinux disabled

### isar / fls
- `icas::roles::workstation`, JRE 1.8.0_202; fls: + `product::gnuplot`, `product::libzstd`
- GDM standard (isar) bzw. custom_conf_standard + autologin (fls), nvidia auto

### atg
- `icas::roles::atg`, `profile::icas::snmp_isim` (snmpd.conf.isim), `jasperlibs`, `libzstd`,
  `jdk18_202_purge_java_jdk_link`, GDM `custom_conf_atg`, **headless** (multi_user_target),
  xorg.conf: `atg_default_xorg.conf`

### epp / smp (common_epp_smp)
- `icas::roles::common_epp_smp` → workstation + EPP-Artifakte: `iSIM/EPP/{autofs,auto.master,
  auto_ssh.gta,dmrc,Xclients}`, `var_lib_AccountsService_users_nor`, nouveau-blacklist,
  ksh→bash-Symlink, ssh-keygen nor (passwortlos), `profile::icas::usermount` (epp,
  `profile/icas/usermount.sh`)
- `snmp_isim`, jasperlibs, libzstd, xfwm4_18, GDM `custom_conf_epp_smp`, autologin

### fdps / corrp
- `icas::roles::base`, `xcc` (Lenovo OneCli), `product::cms_icas_mib`, `libzstd`,
  `snmp_fdps_corrp` (snmpd.conf.stby), `chrony::corrp_fdps` (NTP-peers!), `icas_dmn::icas_service`,
  `sudo::operational_roles_rules`, GUI + nvidia (fdps ja, corrp implizit xorg)

### drf
- `profile::icas::drf` (eigene Manifest-Klasse), `product::log4cpp`, `prepare_raid`,
  `snmp_other`, `sudo::operational_roles_rules`

### cmd / fdo
- `product::lib_hmi_icas`, `product::cms_icas_mib`, GDM `custom_conf_cmd_fdo`,
  `profile::icas::wm::mutter_cmd_fdo` (GNOME-shell → mutter), cmd: `product::xfce_terminal`,
  `fdo`: `icas::roles::fdo` (`metacity-theme-1.xml_fdo`, `fdo_nor_config_gtk-3.0_gtk.css`),
  `icas_dmn::icas_service` bei beiden

### itapclient / itapserver
- itapclient: `product::itapclient`, GDM `custom_conf_itapclient`, `jdk18_202_purge_java_jdk`,
  `chrony::sws_lan`
- itapserver: Oracle-Stack aus `icas/itap/*`: `create_tomcat_instances.sh`, `dbca122.rsp`,
  `dbora`, `netca122.rsp`, `ora122se2inst.rsp`, `oracle-database-server-12cR2-preinstall.conf`,
  `orainstall(.service)`, `select_instance.sh`, `start_tomcat.sh`, `stop_tomcat.sh`,
  `tomcat.service`, `ifdo_fonts`, `itap_fonts`, `product::xlwt` (whl `xlwt-1.3.0-py2.py3-none-any.whl`),
  `prepare_raid`, `chrony::sws_lan`, `xcc`

### disserver (RIS-Server, PXE/DIS)
- `profile::icas::disserver` → `disserver`-Modul mit `disserver_ip` = Hiera
  `nodes.<host>.icas_network.ip_sws`
- `plattform::public::dhcpserver::service` + `dhcpd::config` +
  `profile::icas::dhcpserver::subnets` (Hiera `nodes.<host>.dhcpserver.config.subnets`),
  `product::amtterm`, `rhel86::wsmancli`, `profile::icas::kdump::disserver`
  (dedicated), `profile::icas::xorg::server_conf` (`xorg.conf`), `selinux::permissive`
  (einzige Rolle mit permissive), `prepare_raid`, `profile/icas/updateDis.sh`,
  `disserver/files/dell/{.md5sums (fd10_T7810A31.iso),HwPdM/bios_update/{bios_check,bios_update}.pl}`,
  `disserver/files/backup_ris_sshkeys.sh`
- TFTP-/Boot-Dateien in `images/pxeboot`, `isolinux/`, `boot/grub` (ISO)

### install (ISD-Server)
- `profile::icas::install_server::isd` → `install_server` Modul `type=isd_and_smsf`,
  `product::ntfs`, `product::amtterm`, `rhel86::wsmancli`, `prepare_raid`, `xcc`

### smws
- `packages::plattform::smws`, `packages::product::smws`, `rhel86::smws`,
  `rhel96::{perlauthensasl,perlnetdns}`, `install_server::smsf` (SMSF-Server), `product::amtterm`,
  `sudo::timeout_rule`

## 4. Hiera-Struktur & relevante Keys

- **Produkt-Hiera** (`products/iCAS_PhII/hiera.yaml`, hieria v5, datadir `.`, Globen nach
  `facts.icas_site/facts.role/facts.hostname/facts.productname`): 8 Ebenen von
  host+hardware-spezifisch bis global `ris.d/*.yaml`. Site-Dirs: bre_isim, bre_opsys,
  indra_ph2, indra_sat, ka_opsys, langen_tuv, langen_vm, lvnl, muc_isim, muc_opsys.
  Node-DB: `ris.d/10_nodes.yaml` (Key `nodes`), Lookup-Beispiel:
  `puppet lookup --merge deep --render-as json nodes.$HOSTNAME`.
- **Profile-Hiera** (`modules/profile/hiera.yaml`): `%{facts.role}/%{facts.role}.yaml`
  (Rollen-Defaults in `modules/profile/data/<rolle>/<rolle>.yaml`, 17 Rollen) → `defaults.yaml`.
- **Site-Common** (`products/iCAS_PhII/ris.d/common.yaml`) relevante Keys:
  - `profile::security::pwpolicy::*` (Defaults s.o.)
  - `obm::apply_config: false`, `obm::ipv4_{address,netmask,def_gw}: 0.0.0.0`
  - `ipmi::{password, channel: 1, user_id: 2, user_name: root}` — **Password-Default im Repo, NICHT nach RIS8 übernehmen**
  - `icas::slots_to_disks` (slot→disk-Mapping, Hash)
- **Rollen-Data-Keys (Beispiele):** `profile::icas::sysctl::parameters` (Override),
  `profile::icas::dconf::parameters` (GNOME), `profile::icas::tref.{iCAS LAN,CORRP FDPS,SWS LAN}.{allow,ntpservers,ntppeers}` (chrony),
  `profile::icas::limits::nor::data` (nproc 16384)
- **Netzwerk-Lookups:** `nodes.<host>.icas_network` + `defaults.icas_network` (deep-merge),
  Keys: `dev_obm/slvs/opt (bond3, eth6/7, mode=4)`, `dev_core (bond0, eth2/3, mode=1)`,
  `dev_stby (bond2, eth8/9, mode=1)`, `dev_imasa eth0`, `dev_imasb eth1`, `dev_fbs eth5`,
  `ip_*`/`nm_*`, `ethtool_opts 'wol d'`, `opt_sws 'mode=4 miimon=100'`
- **Andere Lookups:** `icas::bioscfg::filename` (Default `none`), `icas::slots_to_disks`,
  `nodes.<host>.dhcpserver.config.subnets` (disserver), `nodes.<host>.icas_network.ip_sws`
  (disserver_ip), `profile::icas::ip_address_concept::type` (DFS|DFS_LEGACY|INDRA|LVNL)

## 5. Für Ansible-Port relevante Konfigurationsdateien (puppet:///modules/… = zu portierende Quelle)

### profile-Modul (87 Dateien in files/+templates/):
**snmp/**: `snmpd.conf` (other-Rollen), `snmpd.conf.isim` (atg/epp/smp), `snmpd.conf.stby`
(fdps/corrp), `snmpd.options`, `snmptrapd.{conf,options,service}`, `snmpd.service`,
`snmp.conf`, `ceth0`, `ceth1`, `ldipmi_devintf.modules`
**dfshwagent/**: `server-dfshwagent.conf`, `workstation-dfshwagent.conf`, `CMS_ICAS_MIB.mib`,
**41 Templates** `templates/<Product>-<Role>-dfshwagent.conf.template` (R730/R740/7810/7820/P5/SR650 ×
corrp,disserver,drf,fdps,install,itapserver / atg,cmd,epp,fdo,fls,icwp,isar,smp)
**resources/**: `DFS_ip_address_concept`, `DFS_LEGACY_ip_address_concept`,
`INDRA_ip_address_concept`, `LVNL_ip_address_concept`
**bioscfg/**: `muc/…` (Datei je Hardware)
**icwp/**: `synergy.conf`
**Skripte:** `prepare_raid`, `prepare_raid_for_images`, `rename.sh`, `rename_icas.sh`,
`rename_slot.sh`, `rename_pre_product.sh`, `rename_product.sh`, `rename_product_do.sh`,
`rename-ssh-key-files.sh`, `ris_functions.sh`, `common_functions`,
`image.sh`, `image_pre_product.sh`, `updateDis.sh`, `usermount.sh`, `sshd.service`,
`dfs-parse-puppet-nodes-file.sh`, `xlwt-1.3.0-py2.py3-none-any.whl`
**templates/icas/icwp/**: (Xorg/synergy-Templates)

### icas-Modul (site-/rollen-Dateien, `modules/icas/`):
- `rc.config`, `rcmgr`, `collectl.conf`, `ifdo_fonts`, `itap_fonts`, `nor.accountsservice`
- **per-Site Hosts:** `<site>.hosts` + `<site>.shosts.<rolle>` (bre_isim, bre_opsys, …)
- `RIS/users/{nor,oracle,root,tomcat}.{bash_profile,bashrc,profile}`
- `RIS/users/start_ITAP_build_slot_{1..5}.sh`
- `icwp/{icwp-session.sh,icwp.desktop,etc-X11-Xresources,icwp.local.conf,13-eGalaxEXC3000.xorg.conf}`
- `icwp-config-headless/{mdw.bin,sdd.bin,tid.bin,xorg.conf.headless,xorg.conf.lenovo.headless}`
- `iSIM/EPP/{autofs,auto.master,auto_ssh.gta,dmrc,Xclients,var_lib_AccountsService_users_nor}`
- `itap/{create_tomcat_instances.sh,dbca122.rsp,dbora,netca122.rsp,ora122se2inst.rsp,
  oracle-database-server-12cR2-preinstall.conf,orainstall,orainstall.service,
  itapserver-orainstall.service,select_instance.sh,start_tomcat.sh,stop_tomcat.sh}`
- `atg_default_xorg.conf`, `10-touchscreens-blacklist.xorg.conf`, `11-3m.xorg.conf`, `xorg.conf`
- `69-ata.rules`, `home-nor-.gtkrc-2.0`, `metacity-theme-1.xml_fdo`,
  `fdo_nor_config_gtk-3.0_gtk.css`, `RIS/cups/ppd`
- GNOME-Extension: `gnome_extensions/icas_workstation_gnome_extensions/{extension.js,metadata.json}`
- `logind_default.conf`, `logind_icwp.conf`, `rename-icas.service`, `tomcat.service`
- Skripte: `backup_knownhosts.sh`, `backup_sshhostkeys.sh`, `recover_{knownhosts,lib,sshhostkeys}.sh`,
  `change_snmp_identity.sh`, `f_copy_kernel_logs.sh`, `f_remove_virtual_interface.sh`,
  `query_iptables.sh`, `ris_machine_check`, `ris_set_patch_label.sh`, `ris_library_routines`,
  `df.ph`, `icas_environment.sh`, `icas_histtimeformat.sh`, `libnetsnmp.tgz`, `postinstall`,
  `Karlsruhe/{itec_releases,itec_strings_def}`, `Slider`
- **icas_dmn:** `icas.service`

**Summe: ~200 zu portierende Datei-/Template-Quellen** (87 im profile-Modul + ~110 im
icas-/icas_dmn-/disserver-Modul, davon 41 dfshwagent-Templates).

## 6. PXE/DIS-Server-Protokoll (ks.cfg + logPoll.sh)

### Ablauf (Kickstart `%pre`, `ks=http://…/ks.cfg`)
1. `BASEURL` aus `ks=`-Option; MAC aus `BOOTIF=01-…` in /proc/cmdline (Trenner → `:`)
2. `DISURL` = `<schema://host:port>/` aus BASEURL (alles bis 1. Pfadsegment)
3. DIS-Erkennung: `curl` HTTP-Status `200` auf `${DISURL}/dis/` (sonst: kein DIS, weiter wie DVD)
4. Maschineneintrag:
   - `curl -F "command=getMachineId" -F "macaddr=<MAC>" ${DISURL}/dis/` → JSON `{"id": …}`
   - falls leer: `curl -F "command=addMachine" -F "keys=macaddr\=<MAC>" ${DISURL}/dis/`
5. Fortschritt setzen: `curl --data 'command=updateMachine&data={"id":"<MID>","stage":"install","progress":"5"}' ${DISURL}/dis/`
   (progress ist STRING im JSON)
6. Download: `stage1/stage1.sh`, `setup.tar.xz`, `components/os-updates/.present`, `logPoll.sh`
   (alle via `wget --retry-connfailed`)
7. `logPoll.sh &` (Background-Poll, Fortschritts-Updates)
8. stage1.sh ausführen (tty6), danach `%include /tmp/partition`

### Fortschritts-Mapping (logPoll.sh)
- Quelle: letzte Zeile `/tmp/rpm-script.log`, Feld 2 `(.../N)` → `CURRENT`, `TOTAL`,
  `PERCENT = 100*CURRENT/TOTAL`, Poll-Intervall 5 s, Start-Verschiebung 10 s
- Mapping Prozent→progress-Wert (stufenförmig, nicht linear):

| RPM-Paket-Fortschritt (100er-Treffer) | progress |
|---|---|
| Start (vor RPM-Phase) | 5 (via ks.cfg) |
| 0–9 % | 10 |
| 10–19 | 12 |
| 20–29 | 24 |
| 30–39 | 35 |
| 40–49 | 42 |
| 50–59 | 52 |
| 60–69 | 60 |
| 70–79 | 68 |
| 80–89 | 72 |
| 90–99 | 74 |
| 100 | `exit 0` (keine weitere Sendung) |

### Nachinstall-Phase (ks.cfg `%post --nochroot`)
1. Setup-Partition `blkid -L setup` mounten → `/var/lib/plattform/mnt/setup`;
   falls kein `var/lib/plattform`: `setup.tar.xz` hineinentpacken
2. `post-script` (ELF, `LD_LIBRARY_PATH=./stage1lib`)
3. `stage2` → `/mnt/sysimage/stage2`, `stage2.sh` (Banner + `sleep 10` + `/stage2 | tee -a
   /var/log/plattform/plattform.log`)
4. `LinuxPlattformStage2.service` (oneshot, tty1, `ExecStartPost: rm /LinuxPlattformStage2`,
   rm no-login-prompt, rm getty-Condition, `reboot`), `chcon bin_t` auf stage2*
5. GPG-Key `RPM-GPG-KEY-LinuxPlattform-3` importieren
6. `rsyslog.d/log_to_dis.conf` (slotno-Patch via /tmp/SLOTNO) für Stage-2-Logweiterleitung
7. `DISURL`/`MACHINEID` → `$NEWROOT/var/lib/plattform/`
8. Bootmethode: `curl --data 'command=updateMachine&data={"id":"<MID>","bootmethod":"harddisk"}' ${DISURL}/dis/`
   **vor** Reboot

### DIS-Webservice-Endpunkt (Zusammenfassung)
- Basis: `${DISURL}/dis/` (HTTP, `curl`)
- Felder: `command` ∈ {`getMachineId`, `addMachine`, `updateMachine`};
  `updateMachine` nimmt `data` = JSON-string mit `{id, stage?, progress?, bootmethod?}`
- `addMachine`/`getMachineId` via `multipart -F`, Antwort JSON `{"id": …}`
- `progress` ist immer String; `stage="install"` beim Start; `bootmethod="harddisk"` am Ende

## 7. Binary-Bestandstage (stage1-Payload, NICHT als Text portierbar)
- `pre-script` (1.2 MB, ELF, nicht stripped): Bootstrapping, Rollen-Zuweisung, RAID, OBM
- `post-script` (1.1 MB, ELF): post-install
- `obmcli` (560 KB, ELF): OBM-Kommunikation (IPMI/AMT)
- `stage2` (ELF): Stage-2-Bootstrap nach Reboot
- `stage1lib/libPoco{Encodings,Foundation,JSON,Net,Util,XML}.so.64`: Laufzeit der Binaries
- `remotelog/remotelog.sh`: Remote-Log-Setup (vor pre-script)

## 8. Sicherheitshinweis für RIS8-Port
- **Passwort-Hashes** in `users/nor.pp` (nor) und `roles/base.pp` (root) sowie `ipmi::password`
  in `ris.d/common.yaml` (Default-Wert vorhanden) existieren im RIS7-Repo.
  In RIS8/Ansible **niemals replizieren** — nur Platzhalter-Variables (`nor_password`,
  `ipmi_password`) und gezielte Secret-Management-Integration.
