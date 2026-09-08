# VAR-001 Phase 3D-2I-A
# V1.5 RC Engineering & Backup / Restore Safety Report

## 1. Baseline

- Branch: `feature/var-001-variation-policy`
- HEAD: `7712d54d427794cdc268e435bfbbb8f21e2f5db6`
- HEAD commit: `docs(var-001): audit v1.5 forward compatibility`
- Controlled Canary milestone `76d5cd5` and the 3D-2H forward-compatibility audit commit are present.
- Initial `git status --short` was empty.
- Initial `git diff --check` passed.
- No reset, checkout, restore, clean, stash, commit, push, or tag was performed.

## 2. 2H Constitution Recovery

`doc/investigations/VAR001_PHASE3D2H_V15_FORWARD_COMPATIBILITY_AUDIT.md`
was read completely before editing. Current source did not contradict its
frozen conclusions:

- V1.6 must not require clearing V1.5 tenant data.
- Task, execution, FP-001, and Ledger V2 identities remain frozen.
- Historical Memory remains non-authoritative.
- `TaskHistory` is the authoritative completed-output catalog.
- DB-only backup is insufficient for future full-file/perceptual rebuildability.
- Tenant SQLite and authoritative rendered assets must be recoverable together.
- Orphan output files must not become historical truth.

No V1.6/L3 Historical feature was implemented.

## 3. Asset Immutability Audit

The hard gate passed.

DSL rendering writes execution-derived output names before terminal history
commit. Each normal child uses a UUID-derived `file_sid`; subsequent worker
attempts receive new execution identities. The custom `output_dir` path is a
copy and does not replace the path stored as terminal history authority.

The legacy matrix flow also writes its `TaskHistory` row only after rendering
and asset collection. No supported post-terminal render path was found that
opens an authoritative catalogued video for in-place replacement.

The approval deletion flow is explicit lifecycle deletion: it stages a file
with `os.replace`, commits approval/status metadata, then removes the
tombstone. It does not substitute different bytes at the historical path and
does not replace the `path`/`file_path` value. A concurrent deletion can make
the catalogued asset missing; backup treats that as `INCOMPLETE_BACKUP` rather
than claiming success.

Conclusion: successful rendered assets are effectively immutable after
authoritative terminal commit, apart from explicit removal. Copy-time stat and
hash checks cover the remaining removal/change race.

No `VAR3D2IA-RF-04` was found.

## 4. SQLite Snapshot Design

`src/api/backup_restore.py` uses a dedicated read-only SQLite source connection
and Python's SQLite online backup API. The destination is a new standalone
`tenant.db`; `PRAGMA integrity_check` must return `ok` before the bundle can be
published.

It does not use raw live-file copy, does not require application shutdown, and
does not depend on copying WAL/SHM sidecars.

`V15_SQLITE_CONSISTENT_BACKUP_PROVEN: PASS`

## 5. Tenant Boundary

Backup accepts an explicit tenant label, applies the existing
`canonical_tenant_id` contract, and derives exactly one source database as:

`<project-root>/data/dopamatrix_<canonical-tenant>.db`

There is no public endpoint, request-body database path, cross-tenant bundle,
or fallback to the global settings DB. Operator `--project-root` selects the
deployment root, not an arbitrary database file.

## 6. Authoritative Asset Enumeration

The database snapshot is created first. Asset enumeration then reads
`task_history.output_assets` from that snapshot.

- DSL shape: `file_path` (catalog `file_hash` is not trusted for integrity).
- Legacy matrix shape: `path` (catalog `hash` is not trusted for integrity).
- Every catalog element receives a stable snapshot locator.
- Bundle verification reads the snapshot again and proves every catalog
  locator is represented in the manifest, preventing silent manifest omission.

`V15_AUTHORITATIVE_ASSET_BACKUP_PROVEN: PASS`

## 7. Orphan Output Exclusion

The implementation never scans `output/`. A focused orphan file placed beside
authoritative videos was absent from the bundle and manifest.

`V15_ORPHAN_OUTPUT_EXCLUSION_PROVEN: PASS`

## 8. Path Safety

One resolver handles persisted asset references. Relative references resolve
against the project root and must remain beneath `<project-root>/output`.
Legacy absolute references are accepted only when their resolved target is
beneath that same approved asset root and are classified as
`legacy_absolute_within_asset_root`.

The resolver and verifier reject parent escape, absolute outside-root paths,
Windows drive-relative tricks, absolute manifest members, backslashes in
portable bundle paths, and any manifest member whose resolved target escapes
the bundle.

`V15_BACKUP_PATH_SAFETY_PROVEN: PASS`

## 9. Backup Bundle Format

The durable V1 directory format is:

```text
bundle/
  manifest.json
  tenant.db
  assets/
    <authoritative relative output paths>
```

`backup_format_version` is `1`. Compression and remote upload are not required
for correctness and were not added.

## 10. Backup Manifest

The manifest contains:

- backup format and application release versions;
- canonical tenant label and UTC creation time;
- relative database path, byte size, and SHA-256;
- authoritative physical asset count;
- for each asset: safe backup path, normalized logical reference, reference
  classification, catalog shape/locators, byte size, and SHA-256;
- safe counts for TaskHistory, VideoTask, FP identities/occurrences,
  diagnostics, and rollout breakers.

It does not include the absolute source DB path, assignment secret, raw
environment, SQL, owner-attempt ID, or HMAC value. A focused test seeds an
owner-attempt ID and proves it is absent from serialized manifest metadata.

## 11. Full-File Integrity

Database and assets are hashed over all bytes with SHA-256. The focused asset
exceeds 64 KiB and proves manifest SHA-256 equals the complete file hash and is
not the existing prefix-MD5 catalog value.

`V15_FULL_FILE_BACKUP_INTEGRITY_PROVEN: PASS`

## 12. Missing Asset Semantics

If the snapshot references a file that is missing or unreadable, bundle
creation raises the stable `INCOMPLETE_BACKUP` category. No final destination
directory is published and TaskHistory is not rewritten.

Verification also rejects a removed bundle asset. A DB-only restore is never
reported as a fully rebuildable backup.

`V15_BACKUP_INCOMPLETE_ASSET_DETECTION_PROVEN: PASS`

## 13. Copy Consistency

Each asset copy captures a source stat signature, copies and hashes all bytes,
flushes/fsyncs the destination, rechecks the source signature, and independently
rehashes the destination. A changed source is retried once; persistent change
becomes `INCOMPLETE_BACKUP`.

The injected live-change test modifies the source after every copy attempt and
proves no bundle is silently finalized.

## 14. Atomic Bundle Finalization

Backup writes to a uniquely named staging sibling, writes the manifest through
an atomic file replacement, verifies the complete staging bundle, and only
then atomically renames the directory to the requested destination. Existing
destinations are rejected. Failed staging directories are removed and are not
indistinguishable from valid bundles.

## 15. Backup Non-Authority

The source database connection is read-only. Backup does not update VideoTask,
TaskHistory, Ledger, Reservation, diagnostics, breaker, approvals, or rendered
assets. Focused tests compare business counts and asset hashes before/after two
backups.

The module is not imported by routes, public task admission, planner
Reservation, or lease authority modules. Backup failure therefore cannot enter
task admission, planning, confirmation, terminal fencing, or rendering.

`V15_BACKUP_DOES_NOT_MUTATE_AUTHORITY_PROVEN: PASS`

`V15_BACKUP_FAILURE_DOES_NOT_BREAK_RENDERING_PROVEN: PASS`

## 16. Restore Isolation

Restore is an operator/module command only. There is no public restore
endpoint. `restore-to-staging` requires a destination that does not exist and
rejects a destination nested with the bundle. It stages, validates, and
atomically publishes an isolated root; it never overwrites a live tenant by
default.

`V15_RESTORE_TO_ISOLATED_ROOT_PROVEN: PASS`

## 17. Restore Verification

Before restore, verification checks manifest structure/version, safe paths,
database and asset presence/size/SHA-256, SQLite integrity, and complete
TaskHistory catalog coverage. Copied DB and asset bytes are checked again.

The restored database is then opened through current application additive
schema validation and Ledger V2 validation, followed by another SQLite
integrity check. Only after all checks pass is the staging root published.

`V15_RESTORE_INTEGRITY_VERIFICATION_PROVEN: PASS`

## 18. Identity Preservation

Restore copies facts and never regenerates IDs. Focused runtime evidence proves
preservation of:

- public task UUID and VideoTask terminal status;
- TaskHistory and output catalog;
- child execution ID and child index;
- FP-001 identity digest and RENDERED occurrence;
- Reservation owner-attempt/execution values as snapshot facts;
- Reservation diagnostics and rollout breaker generation/reason.

`V15_RESTORE_IDENTITY_PRESERVATION_PROVEN: PASS`

## 19. Reservation Lease Restore Semantics

A snapshot can contain an unexpired Reservation row. Restore preserves that
database fact but creates no controller, heartbeat, worker, renew call, or
owner process. The old attempt cannot be resumed by the restore tool and the
row naturally expires under the existing UTC lease contract. The isolated
staging copy is not evidence of live authority and must not be promoted over a
running tenant.

No `VAR3D2IA-RF-13` was found.

## 20. Fresh Install

A brand-new file-backed tenant DB initializes without manual preparation.
Focused acceptance proves creation/readability of application task/history,
rollout metadata, diagnostics, breaker, FP identity/occurrence, Reservation,
and Ledger schema-version tables.

`V15_FRESH_INSTALL_ACCEPTANCE_PROVEN: PASS`

## 21. Existing Tenant Upgrade

A realistic server-owned-task/B2/2E-era schema with Reservation mode and
planning-policy columns but without 2F/2G rollout metadata was evolved through
the actual current initializer. The process used additive columns/tables and
Ledger validation; it did not delete or rebuild the tenant database.

`V15_UPGRADE_EXISTING_TENANT_NO_RESET_PROVEN: PASS`

## 22. Upgrade Data Preservation

The predecessor fixture contained a known task, completed VideoTask lifecycle,
TaskHistory output reference and prompt details, child execution linkage, FP
identity, and RENDERED occurrence. After upgrade, all sentinel values remained
exactly readable; ENFORCE source was truthfully backfilled as
`EXPLICIT_ENFORCE`. New diagnostics/breaker tables were additive.

`V15_UPGRADE_PRESERVES_EXISTING_TENANT_TRUTH_PROVEN: PASS`

## 23. V1.6 Lineage Smoke

From the isolated restore, the test enumerates TaskHistory output assets,
parses child execution linkage, joins the RENDERED occurrence to its FP
identity, and computes a new full-file SHA-256 from the restored video. No L3
table, policy, perceptual signature, or historical guard was implemented.

`V15_V16_LINEAGE_SMOKE_PROVEN: PASS`

## 24. Corruption Injection

Changing copied `tenant.db` bytes causes hash verification and restore to fail
before a destination is published. Changing a bundled video likewise causes
asset hash verification to fail. Removing an asset fails presence/integrity
verification.

## 25. Path Traversal

Mutated manifest members using `../`, POSIX absolute paths, and Windows drive
absolute paths are rejected. Source-catalog tests reject parent escape,
absolute outside-root paths, and drive-relative forms.

## 26. Live SQLite Snapshot

A real writer thread used an independent SQLite connection and committed rows
while an 8 MiB file-backed tenant snapshot was created. The resulting backup
opened independently, passed `integrity_check`, and contained a consistent
committed probe count. The writer terminated cleanly with no lock residue.

## 27. Release Version

The prior source had conflicting backend `0.5.0` and desktop `1.1.0` values.
This phase establishes `src/version.py` as the backend release authority with
`1.5.0-rc1`, uses it in FastAPI and health responses, and aligns package-lock,
package metadata, and Tauri application metadata. The backup manifest imports
that authority.

Verification accepts older nonempty bundle application versions when the
backup format remains supported, preserving backup durability across release
upgrades. `VAR3D2IA-RF-01` is closed.

## 28. Operator Backup Command

```text
python -m src.api.backup_restore backup --tenant TENANT --destination NEW_DIR
```

The command requires explicit tenant and destination, is non-interactive,
prints bounded JSON on success, and exits nonzero with a stable sanitized code
on validation failure.

## 29. Verify Command

```text
python -m src.api.backup_restore verify --bundle BUNDLE_DIR
```

This performs complete verification without restoring or mutating tenant
truth.

## 30. Restore-to-Staging Command

```text
python -m src.api.backup_restore restore-to-staging --bundle BUNDLE_DIR --staging-root NEW_ROOT
```

The destination must not exist. A live overwrite path is not provided.

## 31. Backup Runbook

Created:

`doc/operations/DOPAMATRIX_V15_BACKUP_RESTORE_RUNBOOK.md`

It documents complete backup contents, DB-only insufficiency, commands,
verification, isolated restore, failure meanings, privacy, operator-managed
retention, and prohibited orphan scanning/live overwrite behavior.

## 32. Philippine Seed Canary Runbook

Created:

`doc/operations/DOPAMATRIX_V15_PHILIPPINE_SEED_CANARY_RUNBOOK.md`

It defines the future 2I-B procedure: tenant/policy selection,
backup-before-canary, readiness/kill-switch/breaker checks, explicit manual
stages, observations, rollback criteria, kill-switch drill, breaker/re-arm
drill, restart drill, incident notes, and production exit criteria.

`V15_PHILIPPINE_SEED_RUNBOOK_READY: PASS`

## 33. Seed Acceptance Template

Created:

`doc/operations/DOPAMATRIX_V15_SEED_ACCEPTANCE_TEMPLATE.md`

It includes every required aggregate field and explicitly excludes task IDs,
prompts, sensitive content, assignment/HMAC secrets, owner-attempt identities,
and tenant DB paths.

`V15_SEED_ACCEPTANCE_TEMPLATE_READY: PASS`

## 34. Product Release vs Rollout

The canary runbook states that V1.5 product release status is not a tenant's
Reservation canary percentage. A tenant may deliberately remain at 10%, 25%,
or 50%; universal 100% Default-ON is not required for V1.5 GA.

The conceptual 5% -> 10% -> 25% sequence is runbook guidance only, not a
production default or automatic ramp.

## 35. Kill-Switch Drill

The runbook requires proof that, while normal canary assignment would select
ENFORCE, enabling the existing kill switch makes the next omitted request OFF,
leaves explicit ENFORCE under existing B2 semantics, and does not cancel
already-running tasks. Disablement occurs only through normal operator config.

## 36. Rollback Drill

The runbook requires a safe staging/seed threshold drill proving breaker latch,
future omitted OFF decisions, no automatic recovery re-arm, and a new rollout
generation before re-arm. It forbids damaging real seed creative work merely
to manufacture failure.

## 37. Restart Drill

The runbook requires restart with persisted rollout/breaker state, then proves
tenant DB/TaskHistory readability, breaker persistence, no silent rollout
reset, backup path resolution, and no resumed historical heartbeat authority.

## 38. Focused Run 1

`tests.test_var001_v15_backup_restore`: `20/20 PASS` (`22.909s`).

## 39. Focused Run 2

`tests.test_var001_v15_backup_restore`: `20/20 PASS` (`23.390s`).

## 40. Focused Run 3

`tests.test_var001_v15_backup_restore`: `20/20 PASS` (`21.497s`).

All three final runs passed with no observed SQLite lock residue, thread leak,
flake, or temporary staging leak.

`V15_BACKUP_REPEATABILITY_PROVEN: PASS`

## 41. 2G Regression

`tests.test_var001_reservation_rollout_control`: `36/36 PASS`.

## 42. 2F Regression

`tests.test_var001_reservation_rollout_readiness`: `15/15 PASS`.

## 43. 2E Regression

`tests.test_var001_reservation_diagnostics`: `19/19 PASS`.

## 44. B2 Regression

`tests.test_var001_public_reservation_activation`: `21/21 PASS`.

Combined 2G/2F/2E/B2: `91/91 PASS`.

## 45. Reservation Regression

- Runtime acceptance: `21/21 PASS`
- Terminal: `12/12 PASS`
- Planner Reservation: `24/24 PASS`
- Lease: `25/25 PASS`
- Reservation public activation: `12/12 PASS`

Combined: `94/94 PASS`.

`PUBLIC_RESERVATION_AUTHORITY_SEMANTICS_UNCHANGED: PASS`

## 46. Task Regression

- Clean task identity: `18/18 PASS`
- Public lifecycle guard: `9/9 PASS`

Combined: `27/27 PASS`.

## 47. Historical Regression

- Historical integration: `20/20 PASS`
- Historical policy: `21/21 PASS`

Combined: `41/41 PASS`. No Historical ENFORCE or L3 behavior was added.

## 48. Ledger Regression

- Fingerprint Ledger: `26/26 PASS`
- Phase 3C Ledger: `24/24 PASS`

Combined: `50/50 PASS`.

`FP001_IDENTITY_PRESERVED: PASS`

`LEDGER_SCHEMA_V2_PRESERVED: PASS`

## 49. VAR Regression

Full `test_var001*.py` discovery, including the new focused suite:
`378/378 PASS` (`110.771s`).

## 50. INV Regression

Full `test_inv001*.py` discovery: `85/85 PASS` (`0.802s`).

## 51. FP Regression

Full `test_fp001*.py` discovery: `42/42 PASS` (`0.173s`).

## 52. Static / Build

- `py_compile`: PASS for `main.py`, `src/version.py`,
  `src/api/backup_restore.py`, and the focused suite.
- Operator CLI parser/help: PASS; all three commands are present.
- Version metadata JSON parse/alignment: PASS (`1.5.0-rc1`).
- `git diff --check`: PASS; only informational LF-to-CRLF warnings appeared.
- `npm` was not available on PATH, so no npm command result is claimed.
  Dependency/frontend code was unchanged; a strict Python JSON check validated
  package, lock, Tauri, and backend version alignment instead.

## 53. Production Diff Audit

Production/release changes are limited to:

- new `src/api/backup_restore.py` operator module;
- new `src/version.py` release authority;
- `main.py` use of the version authority;
- aligned package/package-lock/Tauri version metadata;
- focused backup/restore acceptance tests;
- three operator documents and this investigation report.

No route or public mutation API was added. No change was made to Reservation
acquire/renew/heartbeat/confirm/PLANNED/fence/release, Task Identity,
owner-attempt identity, execution identity, Historical policy, Coverage,
rollout assignment/HMAC/readiness/breaker semantics, FP-001, or Ledger schema.

## 54. Findings

No source/runtime-proven `VAR3D2IA-RF-02` through `VAR3D2IA-RF-15` remains.
The initial release-version inconsistency matching `VAR3D2IA-RF-01` was fixed
within the allowed release-engineering scope and is covered by focused/static
alignment evidence.

Required proof markers:

- `V15_SQLITE_CONSISTENT_BACKUP_PROVEN: PASS`
- `V15_AUTHORITATIVE_ASSET_BACKUP_PROVEN: PASS`
- `V15_ORPHAN_OUTPUT_EXCLUSION_PROVEN: PASS`
- `V15_FULL_FILE_BACKUP_INTEGRITY_PROVEN: PASS`
- `V15_BACKUP_PATH_SAFETY_PROVEN: PASS`
- `V15_BACKUP_INCOMPLETE_ASSET_DETECTION_PROVEN: PASS`
- `V15_RESTORE_INTEGRITY_VERIFICATION_PROVEN: PASS`
- `V15_RESTORE_IDENTITY_PRESERVATION_PROVEN: PASS`
- `V15_RESTORE_TO_ISOLATED_ROOT_PROVEN: PASS`
- `V15_FRESH_INSTALL_ACCEPTANCE_PROVEN: PASS`
- `V15_UPGRADE_EXISTING_TENANT_NO_RESET_PROVEN: PASS`
- `V15_UPGRADE_PRESERVES_EXISTING_TENANT_TRUTH_PROVEN: PASS`
- `V15_V16_LINEAGE_SMOKE_PROVEN: PASS`
- `V15_BACKUP_REPEATABILITY_PROVEN: PASS`
- `V15_BACKUP_DOES_NOT_MUTATE_AUTHORITY_PROVEN: PASS`
- `V15_BACKUP_FAILURE_DOES_NOT_BREAK_RENDERING_PROVEN: PASS`
- `V15_PHILIPPINE_SEED_RUNBOOK_READY: PASS`
- `V15_SEED_ACCEPTANCE_TEMPLATE_READY: PASS`
- `PUBLIC_RESERVATION_AUTHORITY_SEMANTICS_UNCHANGED: PASS`
- `FP001_IDENTITY_PRESERVED: PASS`
- `LEDGER_SCHEMA_V2_PRESERVED: PASS`

## 55. Philippine Production Acceptance Status

`PHILIPPINE_REAL_PRODUCTION_ACCEPTANCE_NOT_YET_EXECUTED`

This phase provides local technical, upgrade, backup/restore, and runbook
evidence only. It does not claim that a Philippine seed tenant has been
observed, drilled, or accepted in production. That work remains Phase 3D-2I-B.

## 56. Final Git Status

The final working tree intentionally contains the uncommitted Phase 3D-2I-A
implementation, tests, runbooks, version metadata, and this report. No commit,
push, or `dopamatrix-v1.5-rc1` tag was created.

VAR001_PHASE3D2IA_V15_RC_TECHNICALLY_READY_FOR_SEED_CANARY
