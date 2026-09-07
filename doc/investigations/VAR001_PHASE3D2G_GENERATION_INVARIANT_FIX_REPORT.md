# VAR-001 Phase 3D-2G
# Rollout Generation Persisted Invariant Fix-Up Report

## 1. Handoff Recovery

- Branch: `feature/var-001-variation-policy`
- Recovered HEAD: `ca1a4af6d5166c3b70943e786feade9d42291a34`
- The existing Phase 3D-2G working tree was preserved. No reset, restore, clean, stash, commit, or push was performed.
- The handoff and generation-invariant source review were read in full before source changes.
- Evidence priority was current source, current diff, and runtime/test evidence over handoff artifacts.

## 2. RF-35

Confirmed finding:

`VAR3D2G-RF-35 — EXISTING_DB_STARTUP_SCAN_DOES_NOT_FULLY_ENFORCE_ROLLOUT_GENERATION_CONTRACT`

The rollout configuration already enforced `[A-Za-z0-9._-]{1,64}`, but application admission, the fresh-schema constraint, and the existing-database startup scan did not all enforce that complete domain. The implementation now aligns all three persisted-metadata boundaries with the authoritative configuration contract.

## 3. Frozen Contract

For `ROLLOUT_CANARY`, `rollout_generation` must:

- be a string;
- contain 1 through 64 characters;
- contain only ASCII letters, digits, `.`, `_`, and `-`;
- match exactly `[A-Za-z0-9._-]{1,64}`.

For every non-canary `reservation_mode_source`, `rollout_generation` must remain `NULL`. No unsafe value is normalized. It is rejected.

## 4. Application Validation

`src/api/public_task_admission.py` now uses a frozen full-match regular expression equivalent to the rollout-control configuration domain. `_validate_rollout_metadata` rejects empty, overlong, and unsafe-character canary generations before a Task insert can commit.

No dependency from public task admission to rollout-control was introduced, avoiding a new dependency cycle. Existing mode/source/bucket/basis validation remains unchanged.

`ROLLOUT_GENERATION_PERSISTED_DOMAIN_PROVEN: PASS`

## 5. Fresh Schema

`src/api/models.py` strengthens `ck_video_tasks_rollout_metadata_consistency` for `ROLLOUT_CANARY` with all of the following:

- `rollout_generation IS NOT NULL`
- `length(rollout_generation) BETWEEN 1 AND 64`
- `rollout_generation NOT GLOB '*[^A-Za-z0-9._-]*'`

The negated SQLite `GLOB` character class rejects a row if any character lies outside the complete allowed set. The explicit length predicate is required because SQLite does not enforce the declared `VARCHAR(64)` length.

## 6. Existing-DB Startup Scan

`src/api/database.py` now marks an existing tenant database inconsistent when a canary generation is:

- `NULL`;
- empty;
- longer than 64 characters; or
- contains any character outside `[A-Za-z0-9._-]`.

The scan continues to validate `ENFORCE`, bucket, basis points, and `bucket < basis_points`. Non-canary rows must still have `rollout_generation IS NULL`.

`EXISTING_DB_GENERATION_DOMAIN_SCAN_PROVEN: PASS`

## 7. Additive Schema

The additive existing-database column remains `rollout_generation TEXT`. No table rebuild or destructive migration was introduced. Existing databases receive full enforcement through supported application admission and startup consistency validation; fresh databases additionally receive the table-level CHECK constraint.

## 8. Backfill Safety

No historical rollout generation was fabricated.

- Existing OFF rows remain `DEFAULT_OFF` with `rollout_generation = NULL`.
- Existing explicit ENFORCE rows remain `EXPLICIT_ENFORCE` with `rollout_generation = NULL`.
- Only genuine `ROLLOUT_CANARY` decisions carry a validated generation.

## 9. Valid Generation

Application, fresh-database, existing-database, and config/task-alignment tests accept:

- `generation-1`
- `generation_1`
- `generation.1`
- `ABC_xyz-123`

`VALID_CANARY_GENERATION_REGRESSION_PROVEN: PASS`

## 10. Invalid Character

Focused tests reject:

- `generation 1`
- `generation/1`
- `../generation`
- `generation:1`
- backslash-containing input
- newline-containing input
- tab-containing input
- other punctuation such as `@`

Application rejection occurs before Task commit. Direct fresh-schema inserts fail the CHECK constraint. Existing-database startup validation rejects invalid persisted metadata.

## 11. Overlong Generation

A 65-character generation is rejected by:

- rollout configuration validation;
- supported Task admission;
- the fresh SQLite CHECK constraint; and
- the existing-database startup consistency scan.

No Task row is admitted through the supported application path.

## 12. Fresh DB Enforcement

A real fresh SQLite database was exercised with direct inserts that bypass application validation. Valid generations committed; unsafe and overlong generations raised the expected database integrity failure.

`FRESH_DB_GENERATION_DOMAIN_CHECK_PROVEN: PASS`

## 13. Existing DB Enforcement

Pre-2G-style databases were evolved through the actual additive initialization path. Otherwise-valid canary rows containing an unsafe generation or a generation longer than 64 characters caused startup consistency validation to raise `TaskRolloutMetadataSchemaError`. A valid `generation-7` row passed startup validation.

`EXISTING_DB_INVALID_GENERATION_REJECTED_AT_STARTUP_PROVEN: PASS`

## 14. Contract Alignment

The rollout-control configuration and Task admission use the same complete generation domain. Values accepted by configuration are accepted by persistence validation; values rejected for format or length are rejected before supported Task admission.

`ROLLOUT_CONFIG_TASK_GENERATION_CONTRACT_ALIGNED_PROVEN: PASS`

## 15. Focused Tests

The seven new/affected generation-invariant tests passed: `7/7`.

One preliminary expanded test run exposed only an order-dependent test assertion for an unordered SQL result. The assertion was corrected to compare without ordering; it was not a production or runtime defect. The final affected run passed `7/7`.

## 16. Focused Run 1

Complete `tests.test_var001_reservation_rollout_control`: `36/36 PASS` (`19.722s`).

## 17. Focused Run 2

Complete `tests.test_var001_reservation_rollout_control`: `36/36 PASS` (`19.867s`).

## 18. Focused Run 3

Complete `tests.test_var001_reservation_rollout_control`: `36/36 PASS` (`20.137s`).

All three consecutive final runs passed without a SQLite lock residue, thread leak, heartbeat leak, or observed flake.

## 19. 2F Regression

`tests.test_var001_reservation_rollout_readiness`: `15/15 PASS`.

## 20. 2E Regression

`tests.test_var001_reservation_diagnostics`: `19/19 PASS`.

## 21. B2 Regression

`tests.test_var001_public_reservation_activation`: `21/21 PASS`.

The combined 2F/2E/B2 regression result was `55/55 PASS`.

## 22. Reservation Regression

- Reservation runtime acceptance: `21/21 PASS`
- Reservation terminal: `12/12 PASS`
- Planner Reservation: `24/24 PASS`
- Reservation lease: `25/25 PASS`
- Reservation public activation: `12/12 PASS`

Combined: `94/94 PASS`.

`PUBLIC_RESERVATION_AUTHORITY_SEMANTICS_UNCHANGED: PASS`

## 23. Task Regression

- Clean task identity: `18/18 PASS`
- Public task lifecycle guard: `9/9 PASS`

Combined Task regression: `27/27 PASS`.

## 24. Historical Regression

- Historical novelty integration: `20/20 PASS`
- Historical novelty policy: `21/21 PASS`

Combined Historical regression: `41/41 PASS`.

## 25. Ledger Regression

- Fingerprint Ledger: `26/26 PASS`
- Phase 3C Ledger: `24/24 PASS`

Combined Ledger regression: `50/50 PASS`.

`LEDGER_SCHEMA_V2_PRESERVED: PASS`

## 26. VAR Regression

Full `test_var001*.py` discovery: `358/358 PASS`.

## 27. INV Regression

Full `test_inv001*.py` discovery: `85/85 PASS`.

## 28. FP Regression

Full `test_fp001*.py` discovery: `42/42 PASS`.

## 29. Static

- `py_compile`: PASS for the affected production and focused test modules.
- `git diff --check`: PASS. Git emitted only informational LF-to-CRLF working-tree warnings.
- Frontend was unchanged; no frontend build was required.

`ROLLOUT_CONTROL_SEMANTICS_UNCHANGED: PASS`

## 30. Findings

RF-35 is closed by source and runtime evidence. No source/runtime-proven instance remains of:

- `VAR3D2G-FIX-RF-01`
- `VAR3D2G-FIX-RF-02`
- `VAR3D2G-FIX-RF-03`
- `VAR3D2G-FIX-RF-04`
- `VAR3D2G-FIX-RF-05`
- `VAR3D2G-FIX-RF-06`
- `VAR3D2G-FIX-RF-07`
- `VAR3D2G-FIX-RF-08`

The fix did not change omitted/explicit OFF behavior, explicit ENFORCE, allowlists, readiness, kill switch, HMAC assignment or input, basis points, breaker semantics, generation re-arm, fail-safe OFF, canary fallback, status API, Reservation authority, Task Identity, Historical policy, Coverage, FP-001, INV-001, or Ledger V2.

## 31. Final Git Status

The working tree intentionally remains uncommitted. It contains the pre-existing Phase 3D-2G work, this RF-35 fix, focused tests, and this report. No commit or push was performed.

Final tracked diff summary before adding this report: `14 files changed, 578 insertions(+), 38 deletions(-)`. Untracked Phase 3D-2G source, tests, reviews, handoffs, and this report remain visible to Git.

Required proof summary:

- `ROLLOUT_GENERATION_PERSISTED_DOMAIN_PROVEN: PASS`
- `FRESH_DB_GENERATION_DOMAIN_CHECK_PROVEN: PASS`
- `EXISTING_DB_GENERATION_DOMAIN_SCAN_PROVEN: PASS`
- `EXISTING_DB_INVALID_GENERATION_REJECTED_AT_STARTUP_PROVEN: PASS`
- `ROLLOUT_CONFIG_TASK_GENERATION_CONTRACT_ALIGNED_PROVEN: PASS`
- `VALID_CANARY_GENERATION_REGRESSION_PROVEN: PASS`
- `ROLLOUT_CONTROL_SEMANTICS_UNCHANGED: PASS`
- `PUBLIC_RESERVATION_AUTHORITY_SEMANTICS_UNCHANGED: PASS`
- `LEDGER_SCHEMA_V2_PRESERVED: PASS`

VAR001_PHASE3D2G_GENERATION_INVARIANT_FIX_PASS
