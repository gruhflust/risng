# ris8-phase2.yml

RIS8 Phase 2: Installiert die nicht-Alma-nativen LP3- und iCAS-RPMs auf
Phase-1-erfolgreichen Alma-9.8-Client-Maschinen. Kein Puppet, keine
stage1.sh, kein setup.tar.xz.

## Ablauf
1. **Play 1 (bootstrapvm)**: liest `/var/lib/tftpboot/runtime/progress_state.json`
   und selektiert alle MACs mit `phase=1` + `status=success`. IP kommt aus den
   DHCP-Leases (awk-Parser) oder `management_state.json` als Fallback.
   `add_host` baut die dynamische Gruppe `ris8_phase2_targets`.
2. **Play 2 (ris8_phase2_targets)**:
   - `dnf`-Repo-Datei `/etc/yum.repos.d/ris8-lp3.repo` (gpgcheck=0: LP3-ISO
     enthält keinen Repo-Signing-Key, nur Red-Hat-Beta-Keys).
   - `dnf install poco-* plattform-tools python-netsnmpagent disserver
     default-keys jre-8`.
   - User `nor` (wheel) anlegen.
   - `/etc/risng-role` auf `RIS8_PHASE=2` setzen.
   - Success-/Failure-POST an `http://<risng>/progress/`.

## Aufruf
```bash
# vom RISng-Host
ansible-playbook -i ansible/inventory/hosts.yml ansible/secondstage/ris8-phase2.yml

# auf eine einzelne MAC beschränken
ansible-playbook ... -e ris8_target_mac=aa:bb:cc:dd:ee:ff
```

## Voraussetzung
- Phase 1 erfolgreich: Client hat per Kickstart `%post` an `/progress/`
  `phase=1` + `status=success` gemeldet.
- `lp3_repo`-Rolle hat `lp3/icas_phii/{plattform,products}/repository/`
  auf dem RISng-HTTP-Root publiziert (P5).
- SSH-Schlüssel des Controlhosts ist in `/root/.ssh/authorized_keys` des
  Clients (Kickstart `%post` hat es aus `/bootstrap/controlhost_id_ed25519.pub`
  übernommen).
