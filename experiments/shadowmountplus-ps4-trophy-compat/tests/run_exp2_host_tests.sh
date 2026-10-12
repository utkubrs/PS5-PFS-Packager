#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
binary="$(mktemp /tmp/smp-exp2-diag.XXXXXX)"
trap 'rm -f "$binary"' EXIT
cc -std=gnu11 -Wall -Wextra -Werror -I"$root/include" \
  "$root/src/sm_ps4_trophy_diag.c" \
  "$root/tests/test_sm_ps4_trophy_diag.c" -lsqlite3 -o "$binary"
"$binary"
