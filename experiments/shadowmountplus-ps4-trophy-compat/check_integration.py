#!/usr/bin/env python3
"""Verify expected integration after the upstream patch is applied."""
from pathlib import Path
import sys
root = Path(sys.argv[1])
source = (root / 'src/sm_install.c').read_text()
assert '#include "sm_ps4_trophy_compat.h"' in source
assert 'sm_ps4_trophy_stage(title_id, src_sce_sys, dst_base, &ps4_stage)' in source
assert 'if (!copy_optional_trophy_metadata_file(src_sce_sys, dst_base, "param.json"))' in source
assert 'src/sm_*.c' in (root / 'Makefile').read_text()
print('PASS: upstream integration markers and auto-source Makefile')
