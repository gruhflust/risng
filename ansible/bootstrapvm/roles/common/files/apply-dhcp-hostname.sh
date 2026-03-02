#!/bin/sh
set -eu

LEASE_DIR=/var/lib/dhcp

: "${APPLY_DHCP_HOSTNAME_ATTEMPTS:=12}"
: "${APPLY_DHCP_HOSTNAME_SLEEP:=5}"

find_target() {
  TARGET=""

  if [ -d "$LEASE_DIR" ]; then
    # Iterate over most recent lease files first
    if LEASE_LIST=$(ls -1t "$LEASE_DIR"/dhclient*.leases 2>/dev/null); then
      for file in $LEASE_LIST; do
        if [ ! -f "$file" ]; then
          continue
        fi
        NAME=$(awk '
          $1 == "option" && $2 == "host-name" {
            gsub(/"/, "", $3)
            gsub(/;$/, "", $3)
            hostname=$3
          }
          END { if (hostname) print hostname }
        ' "$file")
        if [ -n "$NAME" ]; then
          TARGET="$NAME"
          break
        fi
      done
    fi
  fi

  printf '%s\n' "$TARGET"
}

TARGET=""
ATTEMPT=0
while [ "$ATTEMPT" -lt "$APPLY_DHCP_HOSTNAME_ATTEMPTS" ]; do
  TARGET=$(find_target)
  if [ -n "$TARGET" ]; then
    break
  fi
  ATTEMPT=$((ATTEMPT + 1))
  if [ "$ATTEMPT" -lt "$APPLY_DHCP_HOSTNAME_ATTEMPTS" ]; then
    sleep "$APPLY_DHCP_HOSTNAME_SLEEP"
  fi
done

if [ -z "$TARGET" ]; then
  exit 0
fi

CURRENT=$(hostnamectl --static 2>/dev/null || hostname 2>/dev/null || true)
if [ "$CURRENT" = "$TARGET" ]; then
  exit 0
fi

if ! hostnamectl set-hostname "$TARGET" 2>/dev/null; then
  hostname "$TARGET" 2>/dev/null || true
fi

# Ensure 127.0.1.1 entry reflects the chosen hostname
if [ -w /etc/hosts ]; then
  if grep -q "^127\.0\.1\.1" /etc/hosts 2>/dev/null; then
    sed -i "s/^127\.0\.1\.1.*/127.0.1.1\t$TARGET/" /etc/hosts
  else
    printf '127.0.1.1\t%s\n' "$TARGET" >> /etc/hosts
  fi
fi

exit 0
