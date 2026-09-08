# VAR-001 Phase 3D-2I-A
# Restore Path Alias Hardening Fix Report

## 1. Handoff Recovery

- Branch: `feature/var-001-variation-policy`
- HEAD: `7712d54d427794cdc268e435bfbbb8f21e2f5db6`
- The handoff and all three required 2I-A investigation artifacts were read completely before editing.
- The existing uncommitted 2I-A implementation was preserved. No reset, checkout, restore, clean, stash, commit, push, or tag was performed.
- Initial `git diff --check` passed with only informational LF-to-CRLF warnings for previously modified tracked files.

## 2. SR-16

Confirmed finding `VAR3D2IA-SR-16`, `RESTORE_STAGING_NESTING_CHECK_IS_LEXICAL_NOT_PHYSICAL`, was closed.

The prior implementation resolved the bundle physically but used `Path.absolute()` for the requested restore staging path. A missing child below a junction/symlink parent could therefore pass the lexical containment test and be created physically inside the source bundle.

## 3. Frozen Restore Isolation Contract

The fix preserves the accepted operator-only restore contract:

- restore publishes only to a new isolated destination;
- an existing destination is rejected;
- bundle and destination may not physically contain one another in either direction;
- there is no project-root inference, live tenant overwrite, HTTP restore endpoint, force flag, or overwrite option.

No backup format, manifest, SQLite snapshot, catalog, identity, Reservation, rollout, Historical, FP-001, or Ledger behavior was redesigned.

## 4. Physical Destination Canonicalization

`restore_backup_to_staging()` now computes the destination with:

```python
final_root = Path(staging_root).resolve(strict=False)
```

This resolves every existing prefix component, including Windows junctions and POSIX symlinks, while allowing the final child and other trailing components not to exist. The same canonical `final_root` is then used for the existence check, nesting check, parent creation, temporary sibling placement, final `os.replace`, and returned `RestoreResult`.

`RESTORE_DESTINATION_PHYSICAL_CANONICALIZATION_PROVEN: PASS`

## 5. Bundle Nesting Guard

The resolved bundle root and resolved destination are passed through the existing `_is_within` check in both directions. A destination physically inside the bundle and a bundle physically inside the destination are rejected before verification or destination-side creation.

`RESTORE_PHYSICAL_NESTING_GUARD_PROVEN: PASS`

## 6. Windows Junction / Alias Test

A real Windows directory junction was created with `mklink /J`, pointing an alias parent at the real backup bundle. The requested child below the junction did not exist. Restore raised `BackupPathSafetyError`; no final child and no `.restore-*` temporary sibling appeared inside the bundle. The junction was explicitly removed during test cleanup.

`WINDOWS_ALIAS_PARENT_REJECTION_PROVEN: PASS`

## 7. POSIX Symlink Coverage

An analogous real POSIX directory-symlink regression is present and uses `Path.symlink_to(..., target_is_directory=True)`. It is platform-gated and was not executed on this Windows host; the focused runs report one explicit `POSIX symlink regression` skip. No POSIX runtime proof is claimed from the Windows run.

## 8. Bundle Non-Mutation

The alias regression snapshots the complete bundle entry set and full SHA-256 of every bundle file before restore. After rejection it proves:

- `manifest.json` and `tenant.db` bytes are unchanged;
- the complete asset set and every asset byte hash are unchanged;
- the complete bundle tree is unchanged;
- no temporary restore directory remains;
- no final staging child exists inside the bundle.

`RESTORE_ALIAS_REJECTION_DOES_NOT_MUTATE_BUNDLE_PROVEN: PASS`

## 9. Normal Restore Regression

A safe destination containing a lexical `missing-component/..` segment is accepted after physical normalization and restores to the canonical unrelated sibling. The unused lexical component is not created. Existing isolated restore and identity-preservation tests also remain green.

`NORMAL_ISOLATED_RESTORE_REGRESSION_PROVEN: PASS`

## 10. Focused Run 1

`tests.test_var001_v15_backup_restore`: 23 tests run, 22 PASS, 1 platform skip (`POSIX symlink regression`), 0 failures, 0 errors (`26.020s`).

## 11. Focused Run 2

`tests.test_var001_v15_backup_restore`: 23 tests run, 22 PASS, 1 platform skip, 0 failures, 0 errors (`23.511s`).

## 12. Focused Run 3

`tests.test_var001_v15_backup_restore`: 23 tests run, 22 PASS, 1 platform skip, 0 failures, 0 errors (`22.254s`).

All three runs created and exercised the Windows junction successfully. No SQLite lock, temporary restore directory, junction residue, thread leak, or flake was observed.

## 13. 2G Regression

`tests.test_var001_reservation_rollout_control`: `36/36 PASS`.

## 14. 2F Regression

`tests.test_var001_reservation_rollout_readiness`: `15/15 PASS`.

## 15. 2E Regression

`tests.test_var001_reservation_diagnostics`: `19/19 PASS`.

## 16. B2 Regression

`tests.test_var001_public_reservation_activation`: `21/21 PASS`.

Combined 2G/2F/2E/B2: `91/91 PASS`.

## 17. Reservation Regression

- Runtime acceptance: `21/21 PASS`
- Terminal: `12/12 PASS`
- Planner Reservation: `24/24 PASS`
- Lease: `25/25 PASS`
- Reservation public activation: `12/12 PASS`

Combined: `94/94 PASS`.

`PUBLIC_RESERVATION_AUTHORITY_SEMANTICS_UNCHANGED: PASS`

## 18. Task Regression

- Clean task identity: `18/18 PASS`
- Public task lifecycle guard: `9/9 PASS`

Combined: `27/27 PASS`.

## 19. Historical Regression

- Historical integration: `20/20 PASS`
- Historical policy: `21/21 PASS`

Combined: `41/41 PASS`.

## 20. Ledger Regression

- Fingerprint Ledger: `26/26 PASS`
- Phase 3C Ledger: `24/24 PASS`

Combined: `50/50 PASS`.

`FP001_IDENTITY_PRESERVED: PASS`

`LEDGER_SCHEMA_V2_PRESERVED: PASS`

## 21. VAR Regression

Full `test_var001*.py` discovery: 381 tests run, 380 PASS, 1 platform skip, 0 failures, 0 errors (`113.026s`). The only skip is the POSIX-only symlink branch on Windows.

## 22. INV Regression

Full `test_inv001*.py` discovery: `85/85 PASS` (`0.846s`).

## 23. FP Regression

Full `test_fp001*.py` discovery: `42/42 PASS` (`0.174s`).

## 24. Static

- `py_compile`: PASS for `main.py`, `src/version.py`, `src/api/backup_restore.py`, and `tests/test_var001_v15_backup_restore.py`.
- `git diff --check`: PASS; only informational LF-to-CRLF warnings appeared for pre-existing tracked 2I-A modifications.
- Frontend source/metadata was untouched by this hardening fix, so no frontend build was required.

Additional preserved markers:

- `V15_RESTORE_INTEGRITY_VERIFICATION_PRESERVED: PASS`
- `V15_RESTORE_IDENTITY_PRESERVATION_PRESERVED: PASS`
- `BACKUP_RESTORE_STATE_REMAINS_NON_AUTHORITATIVE: PASS`

## 25. Findings

No source- or runtime-proven `VAR3D2IA-ALIAS-FIX-RF-01` through `VAR3D2IA-ALIAS-FIX-RF-05` remains.

The production hardening change is limited to destination physical canonicalization in `src/api/backup_restore.py`. Focused test changes are limited to `tests/test_var001_v15_backup_restore.py`. Existing uncommitted 2I-A implementation and artifacts remain preserved.

## 26. Final Git Status

The working tree intentionally remains uncommitted. It contains the complete prior 2I-A implementation plus this narrow restore hardening fix, focused regression additions, and this report. No commit, push, tag, or Phase 3D-2I-A2 work was performed.

VAR001_PHASE3D2IA_RESTORE_ALIAS_FIX_PASS
