#ifndef SM_PS4_TROPHY_DIAG_H
#define SM_PS4_TROPHY_DIAG_H

/*
 * EXP2 READ-ONLY DIAGNOSTICS.
 * Never installs titles, writes app.db, creates mounts, or changes trophies.
 * This is deliberately observability-only, not a trophy registration patch.
 */
void sm_ps4_trophy_diag_snapshot(const char *title_id, const char *phase,
                                 const char *source_sce_sys);

/* Host-testable entrypoint; runtime calls the above using APP_DB_PATH. */
void sm_ps4_trophy_diag_snapshot_db(const char *title_id, const char *phase,
                                    const char *source_sce_sys,
                                    const char *database_path);

#endif
