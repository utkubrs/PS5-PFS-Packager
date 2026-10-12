#ifndef SM_PS4_TROPHY_COMPAT_H
#define SM_PS4_TROPHY_COMPAT_H

#include <stdbool.h>

typedef struct {
  bool is_ps4;
  unsigned copied;
  unsigned preserved;
  unsigned absent;
} sm_ps4_trophy_stage_result_t;

/*
 * Experimental PS4-only *metadata* staging, not a trophy registration fix.
 * Never writes into the source tree and never replaces destination files.
 * destination is the already-created /system_data/priv/appmeta/CUSAxxxxx.
 * Returns 0 for successful staging/skipping, -1 for an I/O or path error.
 */
int sm_ps4_trophy_stage(const char *title_id, const char *source_sce_sys,
                        const char *destination,
                        sm_ps4_trophy_stage_result_t *result);

#endif
