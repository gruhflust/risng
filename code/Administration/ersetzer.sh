#!/bin/bash

# replacements.sh – ersetzt bestimmte Strings rekursiv und loggt jede Änderung

# Setze die beiden Ersetzungen
declare -A REPLACEMENTS=(
  ["risng"]="risng"
  ["risng"]="risng"
)

# Durchsuche alle regulären Dateien rekursiv
find . -type f -exec grep -Iq . {} \; -print | while read -r file; do
  modified=false

  for key in "${!REPLACEMENTS[@]}"; do
    value=${REPLACEMENTS[$key]}

    if grep -q "$key" "$file"; then
      # Erstelle eine Sicherungskopie (optional: entfernen, wenn nicht nötig)
      cp "$file" "$file.bak"

      # Führe die Ersetzung durch
      sed -i "s/${key}/${value}/g" "$file"
      echo "Replaced '${key}' with '${value}' in $file"
      modified=true
    fi
  done

  # Entferne Backup, wenn keine Änderungen gemacht wurden
  if [ "$modified" = false ]; then
    [ -f "$file.bak" ] && rm "$file.bak"
  fi
done
