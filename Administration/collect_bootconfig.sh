#!/bin/bash
# 01 collect_bootconfig_v04 – erweitert um pxelinux.cfg/default und optionale Ausgabe-Dateiangabe
# -----------------------------------------------------------------------------
# Dieses Skript sammelt alle relevanten Dateien der PXE‑Bootumgebung unterhalb
# von $TFTPROOT und schreibt einen Markdown‑Bericht. Neu in v04:
#   • Einbeziehen von pxelinux.cfg/default (wichtig für BIOS‑Menü‑Debugging)
#   • Übergabe eines alternativen Ausgabepfads als erstes Argument möglich
#   • Robustere Fehlerbehandlung (set -euo pipefail) & Fallback, falls »tree« fehlt
# -----------------------------------------------------------------------------

set -euo pipefail

# ----------------------------------------------------------------------------
# Konfiguration
# ----------------------------------------------------------------------------
OUTPUT="${1:-$HOME/bootconfig.md}"   # 1. Argument oder ~/bootconfig.md
TFTPROOT="/var/lib/tftpboot"          # Wurzel des TFTP‑Baums
EXTRA_FILES=(                          # Zusatzdateien ohne *.cfg‑Endung
  "$TFTPROOT/pxelinux.cfg/default"
)

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
echo "# PXE Boot Configuration Dump"        >  "$OUTPUT"
echo "## Hostname: $(hostname)"              >> "$OUTPUT"
echo "## Timestamp: $(date)"                 >> "$OUTPUT"
echo ""                                       >> "$OUTPUT"

# ----------------------------------------------------------------------------
# Verzeichnisstruktur
# ----------------------------------------------------------------------------
echo "## Directory tree under $TFTPROOT"     >> "$OUTPUT"
echo '```'                                   >> "$OUTPUT"
if command -v tree >/dev/null; then
  tree -a "$TFTPROOT"                       >> "$OUTPUT" 2>/dev/null
else
  find "$TFTPROOT" -print                  >> "$OUTPUT"
fi
echo '```'                                   >> "$OUTPUT"

# ----------------------------------------------------------------------------
# Konfigurationsdateien einsammeln
# ----------------------------------------------------------------------------
CFG_FILES=$(find "$TFTPROOT" -type f -name "*.cfg" | sort)

# Zusatzdateien ergänzen, falls vorhanden
for extra in "${EXTRA_FILES[@]}"; do
  [[ -f "$extra" ]] && CFG_FILES+=$'\n'"$extra"
done

# Abschnittsüberschrift
echo ""                                       >> "$OUTPUT"
echo "## Configuration Files and Contents"   >> "$OUTPUT"

# Dateiinhalte dumpen
while IFS= read -r file; do
  rel_path="${file#$TFTPROOT/}"
  echo ""                                     >> "$OUTPUT"
  echo "### File: $rel_path"                  >> "$OUTPUT"
  echo '```'                                  >> "$OUTPUT"
  cat "$file"                                >> "$OUTPUT"
  echo '```'                                  >> "$OUTPUT"
done <<< "$CFG_FILES"

# ----------------------------------------------------------------------------
# Duplikate von GRUB‑set‑Zeilen finden
# ----------------------------------------------------------------------------
echo ""                                       >> "$OUTPUT"
echo "## Duplicate GRUB 'set' commands check" >> "$OUTPUT"
echo '```'                                   >> "$OUTPUT"
while IFS= read -r file; do
  grep -E '^set (default|timeout)' "$file" 2>/dev/null | sort | uniq -c |
    awk -v f="$file" '$1 > 1 {print "Duplicate in: " f " → " $0}'
done <<< "$CFG_FILES"                       >> "$OUTPUT"
echo '```'                                   >> "$OUTPUT"

# ----------------------------------------------------------------------------
# Checksummen
# ----------------------------------------------------------------------------
echo ""                                       >> "$OUTPUT"
echo "## SHA256 checksums for configuration files" >> "$OUTPUT"
echo '```'                                   >> "$OUTPUT"
sha256sum $(echo "$CFG_FILES") 2>/dev/null   >> "$OUTPUT"
echo '```'                                   >> "$OUTPUT"

echo "✅ PXE‑Bootanalyse geschrieben nach: $OUTPUT"
