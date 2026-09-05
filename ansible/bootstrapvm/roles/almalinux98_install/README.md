# almalinux98_install

RIS8 Phase 1: AlmaLinux 9.8 (fixed) PXE base install.

## Zweck
- Lädt die fixierte AlmaLinux 9.8 DVD-ISO (public mirror, SHA-256 verifiziert)
  via `getisos` (`tasks/fetch_iso.yml`).
- Publiziert auf dem RISng-Staginghost:
  - Repo-Mirror `BaseOS` + `AppStream` unter `almalinux/9.8/` (HTTP-Root,
    **ohne** ISO-Extraktion → kein 15-GB-Disk-Spike; CRB/HA/NFV/RT bleiben
    aussortiert)
  - PXE `vmlinuz`/`initrd.img` (loop-mount, nur `images/pxeboot/`)
  - Kickstart `kickstart/almalinux98.cfg` (Phase 1: Basis-OS, root gelocked,
    SSH-Key-Hinterlegung, Progress-POST an `/progress/`)
  - BIOS/UEFI-Menüfragmente `28-almalinux98.cfg`

## Platz-Verhalten (89-GB-Test-VM)
| Artefakt | Größe |
|---|---|
| DVD-ISO (Cache, nur für PXE-Artefakte) | 15,1 GB |
| BaseOS-Mirror | ~5 GB |
| AppStream-Mirror | ~8 GB |
| PXE kernel+initrd | ~70 MB |

## Phasen-Vertrag
- **Phase 1** (diese Rolle): Alma 9.8 läuft, SSH-key-only, `/etc/risng-role` = `ris8-base`.
- **Phase 2** (`lp3_repo` + `ris8-phase2.yml`, folgt): LP3-RPMs (plattform+products),
  User `nor`, GPG-Keys, SNMP-Grundgerüst.
- **Phase 3** (Rollen `icas_*`, folgt): MAC-gebundene Rollenausprägung,
  kein Puppet.

## Variablen (Kern)
| Variable | Default |
|---|---|
| `almalinux98_install_enabled` | `true` |
| `almalinux98_iso_url` | `https://repo.almalinux.org/almalinux/9.8/isos/x86_64/AlmaLinux-9.8-x86_64-dvd.iso` |
| `almalinux98_iso_sha256` | `7a392bdc879afd159b30da39a356b7b26c1ddf618b01549164da9aadbc40d814` |
| `almalinux98_repo_root` | `{{ pxe_tftp_dir }}/almalinux/9.8` |
| `almalinux98_target` | `{{ pxe_tftp_dir }}/images/almalinux98` |
| `almalinux98_repo_rebuild_always` | `false` |

## Abgrenzung zu bestehenden Rollen
- `rhel98_install`: entgeltlich (Operator-ISO, URL extern) → wird für RIS8
  deaktiviert; diese Rolle nutzt den öffentlichen Alma-Mirror.
- `ris7_install`: LP3-ISO-1:1-Publish → wird für RIS8 deaktiviert;
  LP3-Artefakte kommen in Phase 2 über die eigene `lp3_repo`-Rolle
  (selektiv, ohne 14-GB-Extraktion).
