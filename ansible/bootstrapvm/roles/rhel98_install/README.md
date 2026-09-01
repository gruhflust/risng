# RHEL 9.8 installer mockup

This role publishes a second BIOS/UEFI PXE menu entry, `RHEL 9.8 AutoInstall`.
It is enabled by default and never downloads Red Hat media.

To enable it, place an entitled RHEL 9.8 DVD ISO at
`/var/tmp/pxe-build/iso/rhel-9.8-x86_64-dvd.iso` on the staging host (or
override `rhel98_iso_path`), then provide these values through encrypted
inventory or extra vars:

- `rhel98_install_enabled=true`
- `rhel98_iso_sha256`

The role validates the ISO checksum, extracts it to the local HTTP tree,
publishes kernel/initrd to TFTP, and renders a RHEL 9 kickstart. Assign the
DHCP boot profile `rhel98` to a test client to preselect the new option.
The initial root and operator passwords are locked. The staged control-host
SSH public key is installed for both accounts, and the `risng` operator gets
passwordless sudo for the first test phase.
