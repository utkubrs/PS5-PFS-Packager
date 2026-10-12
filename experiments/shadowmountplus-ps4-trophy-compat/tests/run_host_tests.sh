#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
exe="$(mktemp /tmp/smps4-test.XXXXXX)"
trap 'rm -f "$exe"' EXIT
cc -Wall -Wextra -Werror -std=gnu11 -I"$repo_root/include" "$repo_root/src/sm_ps4_trophy_compat.c" "$repo_root/tests/test_sm_ps4_trophy_compat.c" -o "$exe"
"$exe"
