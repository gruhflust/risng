# Build assets

This directory keeps generated and non-deployed build assets separate from the
Ansible delivery tree.

- `container/` contains container build inputs.
- `legacy/` contains retained historical playbooks.
- `logs/` contains checked-in sample runtime output.
- `runtime/` contains local runtime placeholders.

Operator tools and the canonical Bashrc template are in `ansible/operator/`.
Ansible collection requirements are in `ansible/requirements.yml`.
