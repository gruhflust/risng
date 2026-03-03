# RISng gopass role

Purpose:
- Prepare a controlhost-local gopass/GPG base for RISng key/password material.
- Keep implementation modular so it can be ported to ironscope with minimal changes.

Current scope (phase 1):
- install gopass from upstream GitHub release binary (robust for Debian 13/trixie where no apt package may exist)
- install gnupg2 + qrencode prerequisites
- create dedicated RISng controlhost GPG identity (optional, default enabled)
- write integration metadata to `~/.config/risng/gopass/integration.env`
- optional minimal store bootstrap via `.gpg-id` (disabled by default)

Out of scope (later phases):
- client key distribution workflows
- role/user access policy materialization
- cross-machine trust graph and periodic rotation orchestration
