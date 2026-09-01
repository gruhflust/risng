# RISng-Change01 – Client Runtime Test Checklist (0021/0023/0024/0026/0029)

Ziel: Nachweis auf **echtem Client**, dass der Common-Monitoring-Baseline-Block installiert wurde.

## 1) Vorbedingungen
- Client wurde mit `risdeploy` auf Change01-Stand ausgerollt.
- Client ist per SSH erreichbar.

## 2) Paketnachweis (CentOS/RHEL 7.8)
Auf dem Client ausführen:

```bash
rpm -q net-snmp net-snmp-agent-libs net-snmp-libs net-snmp-utils collectl tk wireshark wireshark-gnome
```

Erwartung: Keine "is not installed" Meldung.

## 3) Reponachweis (lokal gespiegelt)
```bash
yum repolist all | egrep 'risng-(base|updates|extras|epel|monitoring)'
```

Erwartung:
- `risng-base` aktiv
- `updates/extras/epel` dürfen vorhanden sein, aber bei fehlenden Mirrors nicht als Hard-Fail den Lauf abbrechen.

## 4) Funktionsnachweis collectl (RIS-REQ-0023/0029)
```bash
collectl -h >/dev/null && echo OK_collectl
```
Optional Plugin-Pfad prüfen (falls projektspezifisch ausgeliefert):
```bash
ls -la /opt/RISng/plugins /usr/local/lib/collectl 2>/dev/null
```

## 5) Funktionsnachweis wireshark/tk
```bash
wireshark --version | head -n1
python - <<'PY2'
import tkinter
print('OK_tkinter')
PY2
```

## 6) Ergebnisprotokoll (kurz)
- Host/IP
- Datum/Uhrzeit
- Ausgabe von Abschnitt 2–5
- Abweichungen/Fehler

## 7) Rückfluss in Matrix
Wenn Abschnitt 2–5 auf mindestens einem repräsentativen Client grün ist:
- Matrixeinträge 0021/0023/0024/0026/0029 von `IN_PROGRESS` auf `IMPLEMENTED` hochziehen
- Validierungsspalte mit Host/Datum ergänzen
