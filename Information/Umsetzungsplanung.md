# Aktualisierte Planung für Ansible-Playbooks zur rollenbasierenden Installation basierend auf SRD RIS 5.10-03

## Übersicht und Annahmen
Diese aktualisierte Planung basiert vollständig auf den extrahierten Informationen aus dem SRD-Dokument "SRD RIS 5.10-03 V1.3.txt". Alle Pakete, Pfade, Links, Scripts, Konfigurationen und sonstigen Komponenten werden abgebildet. Referenzen zu Anforderungsnummern (RIS-REQ-XXXX) sind explizit angegeben, wo sie im Dokument erwähnt sind. Die Playbooks bleiben disjunkt und rollenbasierend.

### Annahmen (unverändert)
- **Grundinstallationszustand**: Basis-RHEL 7.8, Ansible verfügbar.
- **Disjunkte Playbooks**: 4 separate Playbooks, empfohlene Reihenfolge: 1. Common Linux, 2. Proprietär, 3. Shellscripte, 4. Sonstiges.
- **Rollenbasierung**: Ansible-Rollen mit Filtern nach Facts (z.B. `role`, `product_name`).
- **Variablen und Facts**: Verwende Facts für Rollen/Hardware; Variablen in `group_vars`/`host_vars`.
- **Fehlerbehandlung**: Prüfe Voraussetzungen (z.B. Hardware-Kompatibilität).
- **Repository-Zugang**: Repositories konfiguriert oder via Playbook hinzugefügt.
- **Test und Validation**: Validierung nach jedem Playbook.
- **Umfang**: Vollständige Abbildung – Tasks sind detailliert, aber grob (für LLM-Umsetzung).

### Gesamtstruktur (unverändert)
- **4 Playbooks**: Eines pro Gruppe.
- **Rollen-Verzeichnis**: `roles/` mit `tasks/main.yml`.
- **Inventory**: Gruppiere Hosts nach Rollen.
- **Ausführung**: `ansible-playbook playbook_<gruppe>.yml -i inventory.ini`.

## 1. Playbook: Common Linux (playbook_common_linux.yml)
**Zweck**: Vollständige Installation von Standard-Linux-Paketen und grundlegenden Konfigurationen.

**Zielhosts**: Alle Maschinen.
**Rollen**:
- `role_common_linux_all`: Für alle Maschinen.
- `role_common_linux_disserver`: Spezifisch für disserver.
- `role_common_linux_smws`: Spezifisch für SMWS.
- `role_common_linux_dms`: Spezifisch für DMS.
- `role_common_linux_itapclient`: Spezifisch für iTAP Client.
- `role_common_linux_itg`: Spezifisch für iTG.

**Vollständige Tasks pro Rolle** (in `roles/<rolle>/tasks/main.yml`):
- `role_common_linux_all`:
  - `yum: name={{ item }} state=present` für Pakete: net-snmp (>= 5.7.2-43.el7.1), net-snmp-agent-libs, net-snmp-libs, net-snmp-utils (RIS-REQ-0021).
  - `yum: name={{ item }} state=present` für Pakete: wireshark, wireshark-gnome (RIS-REQ-0026).
  - `yum: name=tk state=present` (RIS-REQ-0024).
  - `yum: name=collectl state=present` und `copy: src=collectl_plugin dest=/path/to/plugin` (Plugin von Indra) (RIS-REQ-0023, RIS-REQ-0029).
  - `yum: name={{ item }} state=present` für Pakete: perl-XML-Parser, perl-XML-Twig, perl-IO-Compress (RIS-REQ-0021).
  - `yum: name={{ item }} state=present` für JAVA JDK/JRE und `file: src=/usr/java/jdk path=/usr/bin/java state=link` (RIS-REQ-0340, RIS-REQ-0362).
  - `yum: name={{ item }} state=present` für SSHfs (RIS-REQ-0333, RIS-REQ-0365).
  - `service: name={{ item }} enabled=yes` für httpd, docker (nur auf relevanten Rollen) (RIS-REQ-5243, RIS-REQ-5244).
  - `yum: name=nautilus state=present` (für SMWS und iTAP Client) (RIS-REQ-5028, RIS-REQ-5093).
  - `yum: name={{ item }} state=present` für cups-pdf, cups filter hpps (RIS-REQ-5094, RIS-REQ-5240).
  - `yum: name=xpra state=present` (RIS-REQ-5267).
  - `yum: name={{ item }} state=present` für motif, xorg-x11-fonts (RIS-REQ-5016, RIS-REQ-5017).
  - `yum: name={{ item }} state=present` für firefox 3.0, JDK 1.6.0_2, JRE 1.4.2_09, Ingres 10.1 (RIS-REQ-5128, RIS-REQ-5125, RIS-REQ-5126, RIS-REQ-5127).
  - `copy: src=firefox_profile dest=/home/dms/.mozilla` md5sum: 034199fadf4988ffbb9895475711c48a, containing list "firefox_profile-RIS_5.10-03-contents.md5" mit md5sums aller im tar archive enthaltenen Dateien (RIS-REQ-5178, RIS-REQ-5179).
  - `yum: name=genisoimage state=present` (RIS-REQ-0173).
  - `yum: name=squashfs-tools state=present` (RIS-REQ-0173).
  - `yum: name=amtterm state=present` (für Install Server und SMWS) (RIS-REQ-0079, RIS-REQ-0579).
  - `yum: name=command-configure state=present` (für Workstations) (RIS-REQ-0539).
  - `yum: name=edac-utils state=present` (RIS-REQ-0540).
  - `assert: that rpm -q {{ item }}` für Validierung.

- `role_common_linux_disserver`: Wie oben, plus spezifische für disserver.
- `role_common_linux_dms`: Wie oben, plus firefox, JDK, etc.
- `role_common_linux_itapclient`: Wie oben, plus cups-pdf, xpra.
- `role_common_linux_itg`: Wie oben, plus motif, xorg-x11-fonts.

## 2. Playbook: Proprietär (playbook_proprietary.yml)
**Zweck**: Vollständige Installation proprietärer Pakete.

**Zielhosts**: Alle Maschinen.
**Rollen**:
- `role_proprietary_all`: Für alle (außer dms, itapserver, itapclient).
- `role_proprietary_disserver`: Spezifisch für disserver.
- `role_proprietary_dms`: Spezifisch für DMS.
- `role_proprietary_workstations`: Für Workstations.

**Vollständige Tasks pro Rolle**:
- `role_proprietary_all`:
  - `yum: name={{ item }} state=present` für dfshwstatus (>= 0.9.1.1), dfshwmib (>= 2.6), dfshwagent (>= 0.9.1.1), dfssmimib (>= 1.2), python-netsnmpagent (>= 0.5.3) (RIS-REQ-0540).
  - `copy: src=dfshwagent.conf.template dest=/etc/dfshwagent.conf.template` mit Hardware-spezifischen md5sums:
    - PowerEdge R720 (drf): md5sum 8fa1557a0b801545b7d13c235ee720dd (RIS-REQ-5211)
    - PowerEdge R740 (drf): md5sum b52918dd1fced4d8ac179159a8130b69 (RIS-REQ-5212)
    - PowerEdge R720 (corrp/fdps): md5sum cb2f9206946b6f252984d64b2156e451 (RIS-REQ-5213)
    - PowerEdge R740 (corrp/fdps): md5sum 152af5cca259ad19cd43286b7bf30f46 (RIS-REQ-5214)
    - PowerEdge R720 (install): md5sum 141814e1ee2ecde2a0cdde20ed5eddb1 (RIS-REQ-5215)
    - PowerEdge R740 (install): md5sum 69c2a5c9ac19447db79d04f0e770ff35 (RIS-REQ-5216)
    - Precision 7820 Tower (icwp): md5sum c7bbdcf20721df7f269180196a73b8fc (RIS-REQ-5219)
    - Precision R7610 (icwp): md5sum 9999d0c98d78660adff8bf8c9fcbb19f (RIS-REQ-5220)
    - Precision 7820 Tower (cmd/fdo): md5sum b24d7e72d6d4347c4fbd82eca13de9ff (RIS-REQ-5221)
    - Precision R7610 (cmd/fdo): md5sum 7480a303793960ff5e8c19315febef45 (RIS-REQ-5222)
    - SMWS (Mayflower G1820TE): md5sum 26d224f2082ccdc328a34925b8ebf68f, Content: '{"sensors": []}' (RIS-REQ-5225)
    - Empty Known HW (atg, epp, fls, isar, itg, smp): md5sum 26d224f2082ccdc328a34925b8ebf68f, Content: '{"sensors": []}' (RIS-REQ-5227)
  - `file: path=/root/.config state=directory mode=0755` (RIS-REQ-0544).
  - `modprobe: name=coretemp state=present` (RIS-REQ-0545).
  - `service: name=lm_sensors enabled=yes` (RIS-REQ-0546).
  - `yum: name={{ item }} state=present` für Dell-Pakete (srvadmin-*, dell-system-update, etc.) nur bei Hardware-Match (RIS-REQ-0538).
  - `yum: name=perl-MailTools state=present` etc. (RIS-REQ-0539).
  - `yum: name=wsmancli state=present` (RIS-REQ-0664).

- `role_proprietary_dms`:
  - `yum: name=destroydbva state=present` (RIS-REQ-5098).

- `role_proprietary_workstations`:
  - `yum: name=amtterm state=present` (RIS-REQ-0539).
  - `yum: name=command-configure state=present` (RIS-REQ-0539).

## 3. Playbook: Shellscripte (playbook_shellscripts.yml)
**Zweck**: Vollständige Installation und Konfiguration von Shell-Scripts.

**Zielhosts**: Spezifische Rollen.
**Rollen**:
- `role_shellscripts_workstations`: Für Workstations.
- `role_shellscripts_disserver`: Für disserver.
- `role_shellscripts_amt`: Für AMT-Hardware.

**Vollständige Tasks pro Rolle**:
- `role_shellscripts_workstations`:
  - `copy: src=f_remove_virtual_interfaces.sh dest=/root/bin/f_remove_virtual_interfaces.sh` md5sum: 3b7a96388c87d1e73b178d1e0c60d82f (RIS-REQ-0512).
  - `copy: src=query_iptables.sh dest=/root/bin/query_iptables.sh` md5sum: f8aa2fa2bd2f426f36430bcf801d33b4 (RIS-REQ-0513).
  - `copy: src=f_copy_kernel_logs.sh dest=/root/bin/f_copy_kernel_logs.sh` md5sum: 0e84e7164de732b012f1220f31625458 (RIS-REQ-0514).
  - `lineinfile: path=/etc/sudoers line='nor ALL=(root) NOPASSWD: /root/bin/query_iptables.sh'` (RIS-REQ-0183).
  - `lineinfile: path=/etc/sudoers line='nor ALL=(root) NOPASSWD: /root/bin/f_remove_virtual_interfaces.sh'` (RIS-REQ-0184).
  - `lineinfile: path=/etc/sudoers line='nor ALL=(root) NOPASSWD: /root/bin/f_copy_kernel_logs.sh'` (RIS-REQ-0185).

- `role_shellscripts_amt`:
  - **Für Precision 7820 Tower** (RIS-REQ-5113):
    - `copy: src=amt.sh dest=/opt/plattform/amt/amt.sh mode=0554 owner=root group=root` md5sum: feeae9634d86791653c1a12af520e609.
    - `copy: src=MicroLMS dest=/opt/plattform/amt/MicroLMS mode=0554 owner=root group=root` md5sum: 5723a605fbab8772de3b4b6cd137a0b3.
    - `copy: src=ReadMe.txt dest=/opt/plattform/amt/ReadMe.txt mode=0444 owner=root group=root` md5sum: 45220749cc205f630a0f48f4822e78ca.
  - **Für Precision T7600, R7610, Tower 7810** (RIS-REQ-5114):
    - `copy: src=amt.sh dest=/opt/plattform/amt/amt.sh mode=0550 owner=root group=root` md5sum: 88aa30653e34bfb4469d3462c0c856e3.
    - `copy: src=amt_con dest=/opt/plattform/amt/amt_con mode=0550 owner=root group=root` md5sum: b7afc18922f6b72887e3a9e734233bdc.
    - `copy: src=amt_mei dest=/opt/plattform/amt/amt_mei mode=0550 owner=root group=root` md5sum: 2c547008879ab46b43f4309efcd60429.

## 4. Playbook: Sonstiges (playbook_misc.yml)
**Zweck**: Vollständige Installation von MIBs, Konfigurationen usw.

**Zielhosts**: Alle Maschinen.
**Rollen**:
- `role_misc_all`: Für alle.
- `role_misc_disserver`: Für disserver.
- `role_misc_workstations`: Für Workstations.

**Vollständige Tasks pro Rolle**:
- `role_misc_all`:
  - `copy: src=libnetsnmp dest=/usr/local` (RIS-REQ-0164).
  - `template: src=icas.conf.j2 dest=/etc/icas.conf` mit Variablen role und icas_install (RIS-REQ-0161).
  - `template: src=rc.config.j2 dest=/etc/rc.config` mit Inhalt: INIT_RUNLEVEL3_LIST="", DESKTOP="GNOME", SET_PERFORMANCE="CWP DRF FDPS LP CMD FDO", ICASUSERNAME="nor", PROJECT="icas", ORACLE_VERSION="12.2.0", P1_TYPE="FDPS" (RIS-REQ-0160).
  - `copy: src=icas_environment.sh dest=/etc/profile.d/icas_environment.sh` Version 2.2.6 (created 2023-11-27) (RIS-REQ-0169).
  - `yum_repository: name=epel` für EPEL (RH 7) Repository - Pakete: gparted, htop, iftop, keepassx2, lsyncd, ntfs-3g, perl-Tk, rlwrap (RIS-REQ-0570).
  - `yum_repository: name=xpra url=https://xpra.org/trac/wiki/Download#Linux` für XPRA Repository - Paket: xpra (RIS-REQ-0571).
  - `yum_repository: name=SysMan url=http://icoback3/data/smrepo state=absent` (disabled) auf Rollen dms und smws (RIS-REQ-5092).

- `role_misc_workstations`:
  - `copy: src=CMS_ICAS_MIB.mib dest=/usr/share/snmp/mibs/CMS_ICAS_MIB.mib` md5sum: 0b56d8bc0ead0de0185c3bdf4dc003e7, mode=0664, owner=root group=root (RIS-REQ-0030) auf Rollen cmd, corrp, drf, fdo, fdps, icwp.

## Empfohlene Ausführungsreihenfolge und Validierung (unverändert)
Diese Planung ist nun vollständig – ein LLM-Assistent kann sie direkt in YAML umsetzen. Wenn zusätzliche Details benötigt werden, gib Bescheid!

## Legacy: Disserver-Rollen (Verlagerung auf RISng Controlhost)

Da die Rolle disserver als Legacy betrachtet wird, werden alle zugehörigen Aufgaben nicht mehr auf der Disserver-Maschine selbst ausgeführt. Stattdessen werden diese auf dem **RISng Controlhost im Projekt** verlagert und dort als lokale Verwaltungsaufgaben implementiert.

**Verlagerung der Perl-Skripte und Management-Aufgaben:**
- `bios_update.pl` → `/opt/RISng/controlhost/scripts/` (RIS-REQ-5037)
- `bios_check.pl` → `/opt/RISng/controlhost/scripts/` (RIS-REQ-5038)
- `prepare_raid` → `/opt/RISng/controlhost/scripts/` (RIS-REQ-0528)
- `bios_update` (Bootloader) → `/opt/RISng/controlhost/boot_images/` (RIS-REQ-5040)
- `fd10_R7610A14.iso` → `/opt/RISng/controlhost/firmware_images/` (RIS-REQ-5039)

Die Paketinstallationen (ramt, asterix, docker, dis-diff-patch, sshil, Dell-Firmware) und NFS-Mount-Konfigurationen werden nicht mehr als Ansible-Tasks ausgeführt, sondern als Referenzmaterial für historische Dokumentation archiviert.

### Frühere Disserver-Tasks (archiviert):

### Aus Playbook: Common Linux
- `role_common_linux_disserver`: Wie oben, plus spezifische für disserver.

### Aus Playbook: Proprietär
- `role_proprietary_disserver`:
  - `yum: name=ramt-1.1.0-0.noarch state=present` sha1sum: d26d327ef76efd825bbdc74f936e879e (RIS-REQ-0563).
  - `yum: name=asterix-1.8.0.x86_64 state=present` (nur im Repository, nicht installiert) (RIS-REQ-5024).
  - `yum: name=docker state=present` (RIS-REQ-5046).
  - `yum: name=dis-diff-patch state=present` (RIS-REQ-5090).
  - `yum: name=sshil state=present` (RIS-REQ-5088).
  - `yum: name={{ item }} state=present` für Dell-Firmware-RPMs (Version 16.10.00, 22.02.25, etc.) (RIS-REQ-0537).

### Aus Playbook: Shellscripte
- `role_shellscripts_disserver`:
  - `copy: src=prepare_raid dest=/root/bin/prepare_raid` (RIS-REQ-0528).
  - `copy: src=bios_update.pl dest=/opt/HwPdM/bios_update/bios_update.pl` (RIS-REQ-5037).
  - `copy: src=bios_check.pl dest=/opt/HwPdM/bios_update/bios_check.pl` (RIS-REQ-5038).
  - `copy: src=fd10_R7610A14.iso dest=/disserver/tftpboot` (RIS-REQ-5039).
  - `copy: src=bios_update dest=/disserver/tftpboot/pxelinux.cfg/bios_update` (RIS-REQ-5040).

### Aus Playbook: Sonstiges
- `role_misc_disserver`:
  - `mount: src=... fstype=nfs opts=rw,sync,no_root_squash path=/data/smws` (RIS-REQ-5197).
  - `mount: src=... fstype=nfs opts=rw,sync,no_root_squash path=/data/users` (RIS-REQ-5197).