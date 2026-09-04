# RIS7 (LP3 iCAS_PhII 7.0-00) PXE autoinstall

This role publishes the operator-supplied RIS7 ISO
(`LP3_iCAS_PhII-RIS_7.0-00_engver202602-rhel9.6-x86_64.iso`, ~14 GB,
Red Hat / Lindorfer build artifact) as a complete PXE source on the RISng
staging host. It is modeled after `rhel98_install` and `risng_install` and
never downloads or stores the ISO inside this repository.

## Layout after `feuer`

```
/var/tmp/pxe-build/iso/ris7.iso            ISO cache (checksum-verified)
/var/tmp/pxe-build/ris7-iso/               bsdtar extract workspace (reset on rebuild)
/var/lib/tftpboot/
  images/ris7/{vmlinuz,initrd.img}         PXE kernel/initrd
  ris/7.0/                                installer tree (nginx HTTP root)
    BaseOS/ AppStream/
    components/{plattform,products,os-updates}/   (os-updates: empty + .present marker)
    stage1/stage1.sh  setup.tar.xz  logPoll.sh
    pre-script  post-script  stage2  obmcli  plattform  stage1lib/  savedata/
    ks.cfg  media.repo  lp_settings.json  extra_files.json
    RPM-GPG-KEY-redhat-{release,beta}
    images/pxeboot/  isolinux/  boot/grub/  EFI/
  kickstart/ris7.cfg                      adapted kickstart (rootpw --lock)
  pxelinux.cfg/25-ris7.cfg                BIOS menu fragment
  boot/grub/25-ris7.cfg                   UEFI menu fragment
```

## Boot flow

1. PXE menu `RIS7 (iCAS_PhII)` (or DHCP boot profile `ris7` for a
   per-MAC preselection via `dhcp_static_hosts`).
2. Kernel args: `inst.stage2=http://<tftp>/ris/7.0`,
   `inst.repo=http://<tftp>/ris/7.0`, `ks=http://<tftp>/kickstart/ris7.cfg`,
   `lp.product=iCAS_PhII inst.gpt inst.text`.
3. Kickstart `%pre` (LP3 logic, unchanged): detects a DIS server at the
   base URL (silent no-op without one), downloads `stage1/stage1.sh`,
   runs the self-extracting stage1 (pre-script: slots, partitioning,
   `/tmp/repos.cfg`, `/tmp/partition`).
4. Anaconda installs from the HTTP repo; `%post` sets up the stage2 flow
   (LinuxPlattformStage2.service) and reboots.

## Configuration

- `ris7_install_enabled` (default `true`) — gate for `feuer`/`getisos`.
- `ris7_iso_source_mode` — `local` (default; ISO must already be at
  `ris7_iso_path`) or `url` with `ris7_iso_url`, `ris7_iso_headers` and
  `ris7_iso_sha256` supplied outside Git.
- `ris7_repo_rebuild_always` — force ISO extract + rsync on every `feuer`
  (default `false`: only rebuilds when artifacts are missing).

## Deviations from the ISO kickstart

- `rootpw --lock` — the secret hash from the ISO `ks.cfg` is not
  replicated (see `docs/requirements/information/RIS7-Rollen-Spec.md` §8).
- Everything else (packages, `%pre`/`%post`, DIS protocol, stage2 setup)
  is 1:1 from `products/iCAS_PhII/ks.cfg` of the ISO.
