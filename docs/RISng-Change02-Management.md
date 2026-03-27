# RISng-Change02-Management

## Goal
Make RISng keep reliable management continuity for each client across discovery, install, reboot, deploy, and validation.

The server must know not only the desired target configuration, but also how to reach the host **right now**.

## Core principles

1. **runtime_ip != assigned_ip**
   - `runtime_ip`: the IP currently observed/usable for management
   - `assigned_ip`: the desired target IP used for install/static/DHCP planning

2. **Stage-1 key continuity**
   - The initial RISng server management key used during discovery/live stage must remain valid after base installation until explicitly replaced.
   - Root access continuity matters more than aesthetic account transitions.

3. **Management-first state model**
   Every host should carry enough state to answer:
   - how is it reachable now?
   - with which user?
   - with which key?
   - when was it last seen?

4. **Actions must use the correct path**
   - Discovery/live reboot -> `root@runtime_ip`
   - Planning/install -> `assigned_ip` as desired state only
   - Deploy/validation -> explicit, current management path

## Proposed per-host state

For each MAC / host record, RISng should gradually track:

- `mac`
- `name`
- `role`
- `runtime_ip`
- `last_runtime_ip`
- `assigned_ip`
- `management_user`
- `management_key_source`
- `reachable`
- `last_seen`
- `phase`

## Immediate work items

1. Introduce persistent management-state storage beside existing web UI state.
2. Update discovery flow to persist current runtime IP and last_seen.
3. Ensure first-stage root key is retained after base installation.
4. Make reboot/deploy/validation always choose explicit management path from state.
5. Surface runtime IP vs assigned IP clearly in the UI.

## Non-goals for this branch

- Large UI redesign
- OBM/Redfish/IPMI automation
- Complex multi-user auth model

## Motivation from Change01

`RISng-Change01-GUI-discoverscript` proved the UI/discovery/deploy flow can work.
The remaining fragility is mainly management continuity:
- runtime IP drift
- host reachable via root but UI/state not fully aligned
- first-stage key continuity not modeled explicitly enough
- deploy/reboot behavior depends too much on implicit assumptions

## Confirmed live observation

- A freshly discovered/live-booted client remained reachable for root/key management on its runtime IP `10.228.229.101` even while the assigned install IP differed.
- Manual reboot via `ssh -i /home/risng/.ssh/id_ed25519 root@10.228.229.101 'nohup sh -c 'sleep 1; /sbin/reboot || /usr/sbin/reboot || reboot' >/dev/null 2>&1 &'` worked.
- Therefore the model must explicitly separate:
  - `runtime_ip` for immediate management actions like reboot
  - `assigned_ip` for planning/install/static target configuration


## Management path transition

RISng management is explicitly phase-dependent.

### Phase 1: LIVE / pre-install
- management IP = `runtime_ip`
- management user = `root`
- auth = stage-1 key
- used for discovery, early reboot, live-state management

### Phase 2: INSTALLED_BASE / deployable
- when the freshly installed client comes up on its new post-install IP, that IP becomes the new `runtime_ip`
- management user switches to `nor`
- `nor` is passwordless sudo and must be used for deployment
- root is no longer assumed after successful base installation

### UI requirement
The current management/deploy user must be displayed in the UI as a non-editable informational field.
The operator should always see:
- runtime IP
- assigned IP
- management user

## Immediate next coding goals

1. Persist `management_user` in management state.
2. Promote management path from `root@live-runtime-ip` to `nor@installed-runtime-ip` when the post-install host becomes reachable there.
3. Use `runtime_ip + management_user` consistently for actions.
4. Keep `assigned_ip` strictly as plan/install target unless promoted by verified reachability.
5. Show management user read-only in the UI.
