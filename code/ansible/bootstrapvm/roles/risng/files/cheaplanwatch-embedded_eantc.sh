#!/usr/bin/env bash
# Embedded fallback for cheaplanwatch_eantc (used if runtime fetch is unavailable).
# This is intentionally a minimal wrapper that runs the EANTC client defaults.

export CHEAPLANWATCH_MODE="${CHEAPLANWATCH_MODE:-imix}"
export CHEAPLANWATCH_IMIX_SIZES="${CHEAPLANWATCH_IMIX_SIZES:-60:60:*5243,132:132:*861,296:296:*273,468:468:*233,557:557:*230,952:952:*127,1010:1010:*151,1500:1500:*2882,8800:8800:*2}"

# Prefer qperf server from env defaults
exec /usr/bin/env bash /var/lib/tftpboot/runtime/qperf/cheaplanwatch-client_eantc.sh "$@"
