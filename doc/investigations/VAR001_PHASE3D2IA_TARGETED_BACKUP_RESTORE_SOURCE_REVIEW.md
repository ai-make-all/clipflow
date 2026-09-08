# VAR-001 Phase 3D-2I-A
# Targeted Backup / Restore Source Review

Review mode: read-only source audit. The implementation report is a PASS
candidate and was read first; it is not production authority.

No production source, tests, or databases were modified. No regression
suites were rerun. No commit, push, or tag was performed.

## 1. Baseline

Captured before this review artifact was created. Working tree was not
altered by the checkpoint commands.

```text
git branch --show-current
feature/var-001-variation-policy

git rev-parse HEAD
7712d54d427794cdc268e435bfbbb8f21e2f5db6

git log -10 --oneline --decorate
7712d54 (HEAD -> feature/var-001-variation-policy, origin/feature/var-001-variation-policy) docs(var-001): audit v1.5 forward compatibility
76d5cd5 (tag: var-001-controlled-canary-v1) feat(var-001): add controlled reservation canary rollout
ca1a4af (tag: var-001-rollout-readiness-v1) feat(var-001): add reservation rollout readiness guardrails
5f73335 (tag: var-001-reservation-observability-v1) feat(var-001): add reservation operational diagnostics
697577a (tag: var-001-public-reservation-enforce-v1) feat(var-001): activate public reservation enforce mode
76a070a refactor(var-001): establish server-owned task identity
ee1b8c3 refactor(var-001): separate reservation owner attempt identity
f179e15 (tag: var-001-reservation-authority-v1) fix(var-001): harden reservation transactions and runtime acceptance
2427038 feat(var-001): add reservation confirmation and terminal fencing
dfb2cb9 feat(var-001): enforce planner reservation conflicts
```

```text
git status --short
 M main.py
 M web_ui/package-lock.json
 M web_ui/package.json
 M web_ui/src-tauri/tauri.conf.json
?? doc/investigations/VAR001_PHASE3D2IA_V15_RC_BACKUP_ACCEPTANCE_REPORT.md
?? doc/operations/
?? src/api/backup_restore.py
?? src/version.py
?? tests/test_var001_v15_backup_restore.py
```

```text
git diff --stat
 main.py                          | 5 +++--
 web_ui/package-lock.json         | 4 ++--
 web_ui/package.json              | 2 +-
 web_ui/src-tauri/tauri.conf.json | 2 +-
 4 files changed, 7 insertions(+), 6 deletions(-)
```

`git diff --stat` does not list untracked files. Untracked production
modules `src/api/backup_restore.py` and `src/version.py` were read
completely.

```text
git diff --check
exit code: 0
```

Warnings are LF-to-CRLF notices, not whitespace errors.

HEAD remains `docs(var-001): audit v1.5 forward compatibility`. Phase
3D-2I-A is uncommitted in the working tree.

## 2. Production Scope

Inspected completely:

- `src/api/backup_restore.py` (new)
- `src/version.py` (new)
- `main.py` (version import/use)
- `web_ui/package.json`
- `web_ui/package-lock.json`
- `web_ui/src-tauri/tauri.conf.json`

Supporting unchanged source consulted only as needed:

- `src/api/database.py` (`canonical_tenant_id`, tenant DB path,
  `initialize_application_schema`)
- `src/api/fingerprint_ledger.py` (`ensure_fingerprint_ledger_schema`,
  `LEDGER_SCHEMA_VERSION = 2`)
- `src/api/models.py` (`TaskHistory.output_assets`)
- Reservation controller modules were grepped for backup imports and
  restore-time construction (none)

Operator documents under `doc/operations/` were not treated as
production authority. Focused tests were read only after production
source review (section 26).

## 3. SQLite Snapshot Connection

Backup source path (`src/api/backup_restore.py:157-160, 391-394`):

```python
canonical, source_database = _tenant_database_path(root, tenant_id)
# canonical_tenant_id(tenant_id)
# root / "data" / f"dopamatrix_{canonical}.db"
if not source_database.is_file():
    raise BackupSourceNotFoundError()
```

No caller-supplied database filename exists. `--project-root` selects
the deployment root; the DB filename is always derived from the
canonical tenant.

Connection (`_sqlite_online_backup`, lines 163-179):

- URI `file:...?...mode=ro` plus `PRAGMA query_only=ON`
- SQLite `mode=ro` does not create a missing file; the `is_file()`
  guard also fails closed first
- `sqlite3.Connection.backup` (`pages=64`) copies into a new
  `tenant.db` in staging
- destination is a different path (`staging_root / "tenant.db"`)
- no WAL/SHM sidecar copy
- no SQLAlchemy Session; dedicated `sqlite3` handles only
- `PRAGMA integrity_check` must return `ok` before the snapshot is
  used

SQLITE_ONLINE_SNAPSHOT_SOURCE_PROVEN: PASS

`VAR3D2IA-SR-01` is not reported.

## 4. Tenant Identity

CLI `--tenant` → `canonical_tenant_id` (the same function as runtime
`src/api/database.py:418-429`, including Windows `os.path.normcase`)
→ `data/dopamatrix_{canonical}.db` under resolved `project_root`.

Runtime engines use `sqlite:///./data/dopamatrix_{canonical}.db`.
Backup uses `Path(project_root).resolve() / "data" / ...`. With the
CLI default `--project-root .`, both are the process working directory
plus `data/`. There is no tenant alias, cross-tenant fallback, or
settings-DB fallback. Unsafe tenant characters are stripped by
`canonical_tenant_id` before interpolation into the filename.

`VAR3D2IA-SR-02` is not reported.

## 5. Snapshot-First Asset Enumeration

`create_backup_bundle` order (lines 403-411):

1. `_sqlite_online_backup(source_database, snapshot_path)`
2. `_snapshot_catalog_and_counts(snapshot_path)`
3. `_enumerate_authoritative_assets(snapshot_path, ...)`

Enumeration opens the snapshot with the same read-only URI and
`SELECT id, output_assets FROM task_history`. It does not query the
live tenant DB afterwards. It does not scan `output/`.

SNAPSHOT_DB_IS_ASSET_CATALOG_AUTHORITY_PROVEN: PASS

`VAR3D2IA-SR-03` is not reported.

## 6. Output Asset Normalization

Each snapshot list element must be a dict (`IncompleteBackupError`
otherwise). Shape selection (`src/api/backup_restore.py` 282-289):

- truthy `file_path` → DSL
- else truthy `path` → LEGACY_MATRIX
- else `IncompleteBackupError`

Catalog `file_hash` / `hash` fields are not read. Locator authority is
the path fields above. Integrity of copied bytes is independent
full-file SHA-256 (section 12), not catalog prefix hashes.

`_decode_output_assets` rejects non-JSON strings and non-lists.
`_resolve_catalog_asset` rejects non-string, empty/whitespace, and
NUL references.

Malformed authoritative entries therefore fail the backup with
`INCOMPLETE_BACKUP` (or `BACKUP_PATH_SAFETY_VIOLATION` for escape).
They are not omitted from a published `VALID` bundle. Verification
additionally requires the snapshot locator set to equal the manifest
locator set (`_snapshot_catalog_contract`).

`VAR3D2IA-SR-04` is not reported.

## 7. Duplicate Asset References

Physical identity for bundling is
`relative_asset_path` under the approved `output/` root.

If two catalog entries resolve to the same relative path and the same
`source_path`, locators are concatenated on one `_AssetSource`
(lines 305-318). One bundle file is stored. All
`task_history:{id}:{index}` locators remain on that manifest entry.

If the same relative path would map to a **different** `source_path`,
`BackupPathSafetyError` is raised (no silent overwrite). If two
locators share one physical file but disagree on catalog shape, merge
keeps the first shape and later `verify_backup_bundle` fails the
locator/shape contract, so the bundle is not published.

`asset_count` is the number of unique physical relative paths, not the
number of catalog locators. Restore copies the snapshot `tenant.db`
byte-for-byte, so TaskHistory catalog rows (including duplicate
references) remain.

DUPLICATE_ASSET_REFERENCE_COVERAGE_PROVEN: PASS

`VAR3D2IA-SR-05` is not reported.

## 8. Source Path Safety

`_resolve_catalog_asset` (lines 221-258):

- Windows drive-relative (`C:foo`) → `BackupPathSafetyError`
- Absolute (POSIX or Windows, including drive-absolute) → resolve, then
  must lie **strictly inside** `asset_root` (`project_root/output`)
- Relative → `(project_root / raw_path).resolve()`, same containment
- `Path.resolve()` follows symlinks; `_is_within` uses
  `relative_to` on resolved paths, so a symlink out of `output/` fails
- `../x`, `output/../../x`, UNC/absolute outside `output/`, and the
  `output` directory itself (`resolved == asset_root`) are rejected

Approved root is `<project-root>/output` only.

`VAR3D2IA-SR-06` is not reported.

## 9. Legacy Absolute Paths

A reference is `legacy_absolute_within_asset_root` when
`Path.is_absolute()` or `PureWindowsPath.is_absolute()` is true, **and**
the resolved file remains strictly under `output/`.

Windows containment uses `resolve()` on both sides, so filesystem
canonical casing is compared after resolution.

Supported compositor/matrix stored authority is
`output/final_{lang}_{file_sid}.mp4` (project-relative). Custom
`output_dir` copies files but does not replace that stored path. This
review found no supported production writer that persists an
authoritative catalog path **outside** `output/`. A path outside the
root fails backup (safety), which matches the frozen 2H catalog
contract rather than rejecting a legitimate current matrix output.

`VAR3D2IA-SR-07` is not reported.

## 10. Bundle Member Safety

`_safe_manifest_relative_path` rejects: non-string, empty, NUL,
backslash, POSIX/Windows absolute, drive letter, `""`, `"."`, `".."`.
Optional `prefix=assets` forces the first part.

`_safe_bundle_member` joins those parts onto `bundle_root.resolve()`
and `resolve()`s again, then `_is_within`. Restore destinations under
staging use the same sanitized relative parts
(`temporary_root / "output" / Path(*target_relative.parts)`). Staging
is a newly created empty tree, so restore does not follow pre-existing
destination symlinks. A symlink **inside the bundle** that resolves
outside the bundle fails `_safe_bundle_member`.

Distinct sources cannot share a backup_path or asset_relative_path
(`seen_backup_paths` / `seen_asset_paths`).

BUNDLE_MEMBER_PATH_CONFINEMENT_PROVEN: PASS

`VAR3D2IA-SR-08` is not reported.

## 11. Copy Consistency

Signature (`_stat_signature`): `(st_size, st_mtime_ns, st_dev, st_ino)`.

Algorithm: stat → full-byte copy+hash → fsync destination → restat
source → independent destination size+SHA-256. Mismatch retries once,
then `INCOMPLETE_BACKUP`. Missing/unreadable source during copy is the
same failure. Staging is deleted; final destination is not published.

This review does not invent a same-size/same-mtime in-place rewrite
blocker. Supported production does not reopen catalogued videos for
replacement after terminal commit (implementation report section 3,
consistent with compositor write-then-history). Deletion/change races
fail closed.

`VAR3D2IA-SR-09` is not reported.

## 12. Full-File SHA-256

`_sha256_file` and `_copy_file_bytes` stream 1 MiB chunks over the
entire file. Empty files hash the empty byte string. Prefix-64KiB MD5
catalog values are never used as integrity. Database SHA-256 is
`_file_integrity` on the snapshot file after backup.

FULL_FILE_SHA256_SOURCE_PROVEN: PASS

## 13. Missing / Unreadable Asset

`not resolved.is_file()` → `IncompleteBackupError`. Copy OSError after
retries → same. `create_backup_bundle` `except` runs
`shutil.rmtree(staging_root)` and does not `os.replace` to the
destination. Source TaskHistory is only read. Operator stderr is the
stable code `INCOMPLETE_BACKUP`.

## 14. Atomic Finalization

Order: create unique sibling staging directory → snapshot DB → copy
assets → atomic manifest `os.replace` of `.manifest.json.tmp` →
`verify_backup_bundle(staging_root)` → `os.replace(staging, final)`.

Existing `final_root` is rejected first. Staging name is
`.{dest.name}.staging-{uuid}` next to the destination, so rename is
same-parent (same-volume) on both Windows and POSIX. Failed staging is
removed and is not a valid bundle directory.

Platform boundary: directory `os.replace` is atomic on the same
filesystem/volume. The sibling layout is what makes that claim hold.
Cross-volume destination is not used because staging is always created
under `final_root.parent`.

`VAR3D2IA-SR-10` is not reported.

## 15. Bundle Verification

`verify_backup_bundle` checks:

- `backup_format_version == 1` (exact)
- `application_version` nonempty, ≤64, no whitespace (not required to
  equal current `APPLICATION_VERSION`)
- canonical tenant already canonical
- DB relative path `tenant.db`, size, SHA-256, `integrity_check`
- every asset: confined paths, unique members, size, SHA-256,
  locators, shape/kind
- snapshot TaskHistory locator/shape contract **equals** the manifest
  locator map

Unreferenced extra files in the bundle directory are **not** walked and
therefore **cannot** become catalog authority. They are tolerated only
in the sense that verification ignores unknown names; historical assets
remain snapshot TaskHistory + listed manifest members only. Source does
not document that extra-file tolerance in a comment; the behavior is
implicit in the absence of a directory listing.

## 16. Restore Isolation

- destination `exists()` → `RESTORE_STAGING_DESTINATION_ALREADY_EXISTS`
- destination nested with bundle (either direction) → path safety error.
  Nesting uses `Path(staging_root).absolute()` against
  `Path(bundle).resolve()`. An existing live tenant directory is still
  rejected by `exists()`. No default live path is inferred.
- no FastAPI/route import of `backup_restore`
- restore writes a new isolated tree
  `staging/data/dopamatrix_{tenant}.db` + `staging/output/...`

RESTORE_CANNOT_OVERWRITE_LIVE_TENANT_BY_DEFAULT_SOURCE_PROVEN: PASS

`VAR3D2IA-SR-11` is not reported.

## 17. Restored Schema Binding

```python
engine = create_engine(f"sqlite:///{database_path.as_posix()}", ...)
initialize_application_schema(engine)
ensure_fingerprint_ledger_schema(engine)
```

(`_validate_restored_database`, lines 620-632)

This does **not** call `get_tenant_engine`, does not use the process
CWD `./data/dopamatrix_*.db` URL, and does not touch `_tenant_engines`.
The engine URL is the restored staging file. Additive schema/Ledger
validation therefore mutates only that copy.

RESTORED_SCHEMA_VALIDATION_BINDS_TO_STAGING_DB_PROVEN: PASS

`VAR3D2IA-SR-12` is not reported.

## 18. Identity Preservation

Restore `shutil.copyfile`s `tenant.db` then runs additive
`create_all` / `ensure_*` / `evolve_schema`. Those helpers add missing
tables/columns; they do not regenerate `task_id`, `execution_id`, FP
digest/identity rows, occurrences, breaker keys, or diagnostics.
Business identity rewrite is not present in this module.

## 19. Reservation Restore Semantics

`backup_restore.py` does not import or construct
`PlannerReservationController`, lease heartbeat, renew, confirm, or
release. `initialize_application_schema` / Ledger ensure are schema
only. Unexpired reservation rows remain inert snapshot facts.

RESTORE_DOES_NOT_REACTIVATE_RESERVATION_AUTHORITY_SOURCE_PROVEN: PASS

`VAR3D2IA-SR-13` is not reported.

## 20. Backup Non-Authority

`backup_restore` is imported by no `src/api` production module except
itself. Grep found no `backup_restore` in:

- `routes.py` / `routes_dsl.py`
- `public_task_admission.py`
- `planner_reservation.py`
- `reservation_lease.py`

Operator CLI (`python -m src.api.backup_restore`) is the only call
surface. Backup failure cannot enter admission, planning, fencing, or
render.

BACKUP_RESTORE_STATE_REMAINS_NON_AUTHORITATIVE_SOURCE_PROVEN: PASS

## 21. Release Version Authority

Classification **B**, not a generated single artifact:

- Backend authority: `src/version.py` `APPLICATION_VERSION = "1.5.0-rc1"`
  imported by `main.py` (FastAPI + `/health`) and backup manifests.
- Manually aligned copies: `web_ui/package.json`, lockfile root
  `packages[""]`, `web_ui/src-tauri/tauri.conf.json` (all `1.5.0-rc1`).
- `web_ui/src-tauri/Cargo.toml` crate `version = "0.1.0"` is the Rust
  package version, not the product/Tauri `tauri.conf.json` version, and
  is not part of the claimed product alignment set.

Drift detection today: focused unittest
`test_release_version_is_single_backend_authority_and_packaging_is_aligned`
compares `APPLICATION_VERSION` to package, lock root, lock
`packages[""]`, and Tauri config. There is no compile-time generator.
That is a test/static check, stated precisely; it is not silent
production backup-version drift because backup reads `version.py`.

`VAR3D2IA-SR-14` is not reported.

## 22. Package Lock

`git diff` for `web_ui/package-lock.json` changes only:

- top-level `"version"`
- `packages[""].version`

from `1.1.0` to `1.5.0-rc1`. `lockfileVersion` remains `3`. Dependency
graph, resolved URLs, and package names are untouched. Root lock
version matches `package.json`.

`VAR3D2IA-SR-15` is not reported.

## 23. Backup Format Compatibility

Verification:

- `backup_format_version` must equal `BACKUP_FORMAT_VERSION` (`1`)
- `application_version` must be a nonempty bounded string; it is **not**
  compared to current `APPLICATION_VERSION`

Unsupported format versions fail `BACKUP_MANIFEST_INVALID`. Older app
labels with format `1` remain verifiable.

BACKUP_FORMAT_VERSION_GATES_COMPATIBILITY_PROVEN: PASS

## 24. CLI Safety

`argparse` subcommands:

- `backup`: required `--tenant`, `--destination`; optional
  `--project-root` (default `.`)
- `verify`: required `--bundle`
- `restore-to-staging`: required `--bundle`, `--staging-root`

Success: JSON on stdout, exit `0`. `BackupRestoreError`: code only on
stderr, exit `2`. No live-overwrite flag. No traceback on the
allowlisted operator error types.

## 25. Privacy

Manifest keys are format/app versions, canonical tenant, UTC time,
relative `tenant.db`, sizes, SHA-256, asset relative paths, catalog
locators, and table counts. Absent: assignment secret, HMAC, owner
attempt ID, env, SQL, absolute source DB path.

CLI success JSON includes the operator destination/staging path (the
path they supplied), not the source tenant file path.

## 26. Focused Test Cross-Check

`tests/test_var001_v15_backup_restore.py` was read after production
review. Tests that actually exercise the source (not names alone):

| Concern | Test |
|---|---|
| File-backed SQLite + online backup | `test_live_writer_and_online_backup_produce_clean_snapshot` |
| Independent live writer | same |
| Orphan exclusion | `test_consistent_snapshot_enumerates_only_authoritative_assets` |
| Path escape | `test_backup_rejects_catalog_path_escape` |
| Manifest traversal | `test_manifest_path_traversal_and_drive_escape_are_rejected` |
| DB/asset corruption | `test_database_corruption_is_rejected_before_restore`, `test_asset_corruption_and_missing_bundle_asset_are_rejected` |
| Missing asset / no final dir | `test_missing_authoritative_asset_makes_backup_incomplete` |
| Copy change race | `test_source_asset_change_during_copy_never_succeeds_silently` |
| Restore staging / no overwrite | `test_restore_to_isolated_root_preserves_identity_and_truth`, `test_restore_never_overwrites_an_existing_destination` |
| Identity preservation | restore test (task, history, execution, FP, breaker) |
| Upgrade preservation | `test_upgrade_existing_tenant_is_additive_and_preserves_sentinels` |
| Older app version | `test_compatible_bundle_from_an_older_application_version_still_verifies` |
| Catalog omission | `test_manifest_cannot_omit_an_authoritative_catalog_reference` |
| Non-authority import | `test_backup_tool_is_not_imported_by_render_authority_paths` |

Coverage gaps (not production defects):

- two TaskHistory locators for one physical file are implemented in
  source but not covered by a focused test
- extra unreferenced files inside a bundle are ignored by source and
  not explicitly tested
- symlink-specific cases rely on `Path.resolve()` + `_is_within`,
  without a dedicated test

## 27. Frozen System Audit

Tracked production diff is `main.py` version wiring only, plus package
/ Tauri version strings. New files are backup/restore, `version.py`,
tests, and docs.

No 2I-A edits to Reservation acquire/renew/heartbeat/confirm/PLANNED/
terminal fence/release, Task Identity, owner-attempt identity, execution
identity, rollout HMAC, breaker, readiness, Historical policy, FP-001,
or Ledger V2 schema.

## 28. Findings

No source-proven `VAR3D2IA-SR-01` … `VAR3D2IA-SR-15` defects.

No `VAR3D2IA-SR-16+` defects added.

## 29. Required Markers

- SQLITE_ONLINE_SNAPSHOT_SOURCE_PROVEN: PASS
- SNAPSHOT_DB_IS_ASSET_CATALOG_AUTHORITY_PROVEN: PASS
- DUPLICATE_ASSET_REFERENCE_COVERAGE_PROVEN: PASS
- BUNDLE_MEMBER_PATH_CONFINEMENT_PROVEN: PASS
- FULL_FILE_SHA256_SOURCE_PROVEN: PASS
- RESTORE_CANNOT_OVERWRITE_LIVE_TENANT_BY_DEFAULT_SOURCE_PROVEN: PASS
- RESTORED_SCHEMA_VALIDATION_BINDS_TO_STAGING_DB_PROVEN: PASS
- RESTORE_DOES_NOT_REACTIVATE_RESERVATION_AUTHORITY_SOURCE_PROVEN: PASS
- BACKUP_FORMAT_VERSION_GATES_COMPATIBILITY_PROVEN: PASS
- BACKUP_RESTORE_STATE_REMAINS_NON_AUTHORITATIVE_SOURCE_PROVEN: PASS

## 30. Final Git Status

Recorded after creating this review artifact. Production source was not
modified by this review.

```text
git branch --show-current
feature/var-001-variation-policy

git rev-parse HEAD
7712d54d427794cdc268e435bfbbb8f21e2f5db6

git status --short
 M main.py
 M web_ui/package-lock.json
 M web_ui/package.json
 M web_ui/src-tauri/tauri.conf.json
?? doc/investigations/VAR001_PHASE3D2IA_TARGETED_BACKUP_RESTORE_SOURCE_REVIEW.md
?? doc/investigations/VAR001_PHASE3D2IA_V15_RC_BACKUP_ACCEPTANCE_REPORT.md
?? doc/operations/
?? src/api/backup_restore.py
?? src/version.py
?? tests/test_var001_v15_backup_restore.py
```

PHASE3D2IA_TARGETED_BACKUP_RESTORE_SOURCE_REVIEW_CLEAN
