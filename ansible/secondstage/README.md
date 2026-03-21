# RISng SecondStage

SecondStage configures already installed CentOS 7.8 clients after the base PXE installation succeeded.

## Two-step model

SecondStage intentionally has two separate phases:

1. **Package provisioning on RISng**
   - implemented in the normal `feuer` path
   - downloads / mirrors additional package content to the RISng control host
   - keeps package origin and purpose documented in a manifest

2. **Package deployment to clients**
   - implemented by `risdeploy`
   - installs selected components on already installed clients
   - clients still consume packages only from RISng, never from the Internet

## Current component model

Components are catalog-driven.
Each component defines:

- description
- purpose
- required local repo sets on RISng
- yum groups
- explicit packages
- services to enable

The initial component is:

- `graphics-gnome`

## Operational flow

1. mark a client in `roles/dhcp/defaults/main.yml` with:
   - `secondstage_enabled: true`
   - `secondstage_components:`
2. run `feuer` on RISng so the required package sets are mirrored locally
3. run `risdeploy` to install the selected components on matching clients

## Transparency

RISng writes a generated manifest to:

```text
/var/lib/tftpboot/kickstart/secondstage-package-sources.yml
```

This manifest documents for each enabled component:

- package source / upstream URL
- local path on RISng
- short purpose text
- yum groups
- explicit packages

The goal is to keep the package supply chain understandable and later renderable into human-readable package lists.
