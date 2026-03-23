# risng-Setup (Role `risng`)

Diese Rolle baut ein PXE-bootbares risng-Image aus einem Debian-Live-ISO und einem chroot, das per debootstrap erzeugt wird. Die Task-Bezeichnungen ("Task IR-XX") sind bewusst fortlaufend und mit dem Rollen-Prefix versehen, damit sie global eindeutig und auch in Playbooks mit mehreren Rollen klar zuordenbar bleiben.

## Task-Nummerierung und Module

Alle Tasks unterhalb der Rolle sind global eindeutig nummeriert und ohne Dopplungen von **IR-01** bis **IR-86**. Die Nummern steigen dateiübergreifend fortlaufend an und markieren klar, in welcher Datei der jeweilige Schritt liegt:

- `tasks/main.yml`: IR-01–24, IR-49–50, IR-63–67, IR-73–83
- `tasks/customise_root.yml`: IR-25–48
- `tasks/install_tools.yml`: IR-51–61
- `tasks/vlan_support.yml`: IR-62
- `tasks/20_network_persistence.yml`: IR-68–72
- `tasks/bootloader_generation.yml`: IR-84–86

## Gesamtüberblick

1. **Bootstrap und ISO-Vorbereitung**
   * Task IR-01–02: Grundlegende Variablen setzen und Arbeitsverzeichnisse anlegen.
   * Task IR-03–15: Debian-Live-ISO validieren, laden und die Kernelversion der ISO ermitteln.
2. **Rootfs-Bootstrap**
   * Task IR-16–21: debootstrap ausführen und sicherstellen, dass systemd vorhanden ist.
   * Task IR-22–24: Hilfsdateien in das Chroot kopieren.
3. **Systemanpassungen im Chroot**
   * Tasks IR-25–IR-48 (aus `tasks/customise_root.yml`): Benutzer, SSH, Hostname, Systemd-Links, Locale und Tastaturlayout setzen.
4. **Paket- und Kernelvorbereitung**
   * Task IR-49–50: Kernelpakete definieren und die Installationliste zusammenstellen.
   * Tasks IR-51–IR-61 (aus `tasks/install_tools.yml`): Paketquellen prüfen, Kernel-Fallback wählen, Pakete installieren.
   * Task IR-62 (aus `tasks/vlan_support.yml`): Autoload für 8021q aktivieren.
   * Tasks IR-63–IR-67: Installierte Kernelmodule im Chroot ermitteln und sicherstellen, dass 8021q für die gewählte Kernelversion geladen werden kann.
5. **Netzwerkkonfiguration**
   * Tasks IR-68–IR-72 (aus `tasks/20_network_persistence.yml`): Persistente Netzwerkkonfiguration schreiben und systemd-Links setzen.
6. **Abbild und Boot-Artefakte bauen**
   * Tasks IR-73–IR-75: Prüfen, ob das 8021q-Modul tatsächlich im Rootfs liegt, und SquashFS erzeugen.
   * Tasks IR-76–IR-81: Kernel und initrd auswählen (ISO vs. chroot), prüfen und in das PXE-Ziel kopieren, damit Kernel und Module zusammenpassen.
7. **Bootloader-Einträge und -Binaries**
   * Tasks IR-82–IR-83: PXELINUX- und GRUB-Menüeinträge generieren.
   * Tasks IR-84–IR-86 (aus `tasks/bootloader_generation.yml`): PXELINUX-Binaries bereitstellen und prüfen.

## Warum Kernel/Module jetzt zusammenpassen

* Task IR-63 sammelt die im Chroot vorhandenen `lib/modules`-Versionen. Task IR-64/65 wählen daraus die effektiv zu validierende Kernelversion (entweder die vom ISO oder die im Chroot installierte Version).
* Task IR-66/67 prüfen, dass die Kernelmodule für diese Version existieren und dass `modprobe -n -S <version> 8021q` erfolgreich aufgelöst werden kann.
* Task IR-76–IR-79 wählen Kernel und initrd standardmäßig aus dem ISO, schwenken aber automatisch auf die Chroot-Artefakte um, sobald sich die Kernelversion unterscheidet. Dabei wird die Existenz der Dateien geprüft, bevor sie in Task IR-80/81 kopiert werden.
* Durch diese Kopplung bootet der Client mit genau dem Kernel, zu dem die Module im SquashFS (Task IR-75) passen. Das verhindert fehlende VLAN-Unterstützung wie bei einem Versions-Mismatch zwischen ISO-Kernel und Chroot-Modulen.

## Aliase und Hilfsfunktionen für ISO-Downloads und Playbooks

* Die Management-Rolle liefert eine `.bashrc` aus (`roles/management/templates/bashrc.j2`), die die risng-Aliase bereitstellt. Wer die Aliase vorab lokal nutzen möchte, kann den bestehenden Helfer `./getrisngbashrc.sh` aus dem Repository-Stamm ausführen; das Skript kopiert die Bashrc-Vorlage ins Home-Verzeichnis und entfernt Windows-Zeilenenden.
* Der Alias `getisos` ruft `bootstrapvm/getisos.yml` mit denselben Tasks auf, die auch im vollständigen Setup verwendet werden, lädt jedoch ausschließlich die ISO-Artefakte vor. Das ist hilfreich, wenn die Images vor dem eigentlichen Build aktualisiert werden sollen.
* Der Alias `report_snapshot` startet `runtime/report_snapshot/report_clients.yml`, sammelt DHCP-Leases, fragt die Clients per SSH ab und schreibt JSON/PDF-Berichte ins Home-Verzeichnis. Über `unreport` (Playbook `playbooks/unreport.yml`) können diese Berichte sowie PXE-Logs wieder bereinigt werden.
* Der Alias `slavelantest` führt `runtime/report_snapshot/slavelantest.yml` aus, um VLAN-Interfaces und IPs auf vorhandenen PXE-Clients anzulegen. Das Playbook nutzt die in `bootstrapvm/roles/dhcp` hinterlegten `dhcp_static_hosts` und protokolliert seinen Lauf in `~/slavelantest.log`.
* Relevante Arbeitsaliase sind aktuell vor allem `feuer`, `getisos` und `repair-dhcp`. `getisos` lädt die benötigten ISO-Artefakte vorab, `feuer` baut den RISng-Stagingpfad auf und `repair-dhcp` korrigiert DHCP-seitige Folgeschäden nach Interface- oder Netzwechseln.

## Technical architecture: bind9, DHCP, and PXE control plane

The PXE stack in this repository is intentionally split into cooperating services:

1. **DHCP (`isc-dhcp-server`)** assigns addresses on the PXE LAN and hands out boot metadata:
   - `next-server` (TFTP server address)
   - BIOS boot file (for PXELINUX)
   - UEFI boot file (for GRUB EFI)
   - DNS resolver address (`option domain-name-servers`)

2. **TFTP (`tftpd-hpa`)** serves first-stage boot artifacts (`pxelinux.0`, `bootx64.efi`, GRUB/PXELINUX configs, kernels/initrds).

3. **DNS (`bind9`)** provides authoritative name resolution for the isolated PXE network and optional recursive forwarding upstream.

### Why bind9 matters for DHCP/PXE environments

PXE clients can fetch their very first bootloader stage without complex DNS usage if DHCP options are complete. However, DNS becomes critical immediately after that stage:

- installers and live systems need consistent resolver behavior
- hostnames used in automation, logs, and diagnostics must resolve predictably
- reverse DNS (PTR) should match the active provisioning subnet to avoid misleading diagnostics and tooling issues

In short: DHCP/TFTP gets clients to boot, but DNS quality determines how reliable the provisioning environment is during and after boot.

### Implementation details in this codebase

- Forward zone and reverse zone are rendered from templates in `roles/dns/templates/`.
- Reverse zone naming is derived from `dhcp_network_prefix` so it follows the active PXE subnet.
- PTR for `bootstrapvm` is derived from `dns_bootstrap_ip` (last octet), avoiding hard-coded `192.168.100` assumptions.
- `named.conf.options` supports optional upstream resolvers via `dns_forwarders`; no self-forwarding is configured by default.

### Operational sequence

In `bootstrapvm/risng-setup.yml` (offline phase), roles run in this order:

1. `pxe_assemble`
2. `dns`
3. `dhcp`

This order ensures that DNS is already available when DHCP starts handing out resolver information to PXE clients.
