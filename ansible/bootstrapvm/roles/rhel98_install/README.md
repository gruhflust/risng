# RHEL 9.8 installer mockup

This role publishes a second BIOS/UEFI PXE menu entry, `RHEL 9.8 AutoInstall`.
It is disabled by default and never downloads Red Hat media.

To enable it, place an entitled RHEL 9.8 DVD ISO at
`/var/tmp/pxe-build/iso/rhel-9.8-x86_64-dvd.iso` on the staging host (or
override `rhel98_iso_path`), then provide these values through encrypted
inventory or extra vars:

- `rhel98_install_enabled=true`
- `rhel98_iso_sha256`
- `rhel98_root_password_hash`
- `rhel98_operator_password_hash`

The role validates the ISO checksum, extracts it to the local HTTP tree,
publishes kernel/initrd to TFTP, and renders a RHEL 9 kickstart. Assign the
DHCP boot profile `rhel98` to a test client to preselect the new option.
