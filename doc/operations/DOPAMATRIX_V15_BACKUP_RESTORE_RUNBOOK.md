# DopaMatrix V1.5 Backup / Restore Runbook

## Purpose and authority boundary

This runbook covers an operator-created, tenant-scoped V1.5 backup bundle. A
complete bundle contains one SQLite-consistent tenant database snapshot and
the rendered video files referenced by that snapshot's `TaskHistory` catalog.

A database-only copy is not a complete rebuildable backup. It preserves task,
Ledger, diagnostics, and catalog rows, but future full-file or perceptual
indexing cannot be rebuilt when the rendered files are absent.

The backup tool never scans every file under `output/`. Orphan files left by
authority loss, terminal-persistence failure, or temporary rendering are not
historical truth and must not be promoted into a backup manifest.

## Before creating a backup

1. Identify exactly one canonical tenant label.
2. Choose a new destination directory. The destination must not already exist.
3. Ensure the operator account can read the deployment's `data/` and `output/`
   directories and write the backup parent directory.
4. Do not stop rendering merely to copy the database. The tool uses SQLite's
   online backup API and supports concurrent ordinary database writes.
5. Treat the resulting bundle as tenant-sensitive operational data. It may
   contain prompts, catalog metadata, and rendered business assets.

## Create a backup

From the DopaMatrix installation/project root:

```powershell
.\venv_build\Scripts\python.exe -m src.api.backup_restore backup `
  --tenant <canonical-tenant> `
  --destination <new-backup-directory>
```

For a packaged/operator Python environment, use its Python executable with
the same module and arguments. The command is non-interactive. Success prints
one JSON line with `status: VALID`; failure exits nonzero with a bounded error
code. It never prints the tenant database source path, assignment secret, HMAC
input, SQL, or Reservation owner-attempt identity.

The command stages the bundle beside the destination, verifies the complete
staging bundle, and only then renames it to the requested final directory. An
existing destination is never replaced.

## Bundle contents

```text
<bundle>/
  manifest.json
  tenant.db
  assets/
    ... authoritative rendered videos ...
```

`manifest.json` records the format and application versions, safe tenant
label, UTC creation time, database size and full-file SHA-256, aggregate row
counts, and every included asset's normalized logical reference, size, and
full-file SHA-256. It does not contain the absolute tenant DB source path,
environment values, assignment secrets, raw HMAC values, or SQL.

## Verify without restoring

```powershell
.\venv_build\Scripts\python.exe -m src.api.backup_restore verify `
  --bundle <backup-directory>
```

Verification checks:

- manifest format version and structure;
- safe relative database and asset paths;
- database and asset presence, size, and full-file SHA-256;
- SQLite `integrity_check`;
- complete coverage of every authoritative `TaskHistory.output_assets`
  reference in the database snapshot.

Any failed check means the bundle is not approved for restore or off-machine
retention as a valid backup.

## Restore to isolated staging

Restore is operator/test tooling, not a public mutation endpoint. It only
accepts a destination root that does not exist:

```powershell
.\venv_build\Scripts\python.exe -m src.api.backup_restore restore-to-staging `
  --bundle <backup-directory> `
  --staging-root <new-isolated-root>
```

The command verifies the bundle before copying, verifies the copied bytes,
opens/evolves the restored database through current additive schema checks,
runs Ledger V2 validation and SQLite integrity validation, then atomically
publishes the staging root. It does not overwrite a live tenant root.

Do not point `--staging-root` at the running DopaMatrix installation, its
`data/`, or its `output/`. The command rejects every existing destination, but
the operator remains responsible for selecting a clearly isolated parent.

## Validate restored data

In the isolated root, confirm:

1. `data/dopamatrix_<tenant>.db` opens and passes SQLite integrity checks.
2. Task history can be listed.
3. Every restored `TaskHistory` output reference resolves under `output/`.
4. Task-to-child execution lineage and FP occurrence linkage remain readable.
5. diagnostics, readiness dependencies, and rollout breaker rows remain
   readable without requiring the old deployment's rollout environment.
6. restored asset SHA-256 values match the bundle manifest.

Reservation rows may be present because they were database facts at snapshot
time. Restore does not restart their old heartbeat, renew them, or recreate an
owner process. They naturally expire under the existing UTC lease contract.
Never treat a staging restore as proof that old lease authority resumed.

## Failure meanings

- `INCOMPLETE_BACKUP`: an authoritative catalog asset was missing, unreadable,
  or changed throughout the bounded copy attempts.
- `BACKUP_PATH_SAFETY_VIOLATION`: a catalog or manifest path escaped the
  approved root or used an unsafe absolute/drive form.
- `BACKUP_INTEGRITY_INVALID`: a declared database or asset hash/size failed,
  SQLite was invalid, or the manifest omitted catalog authority.
- `BACKUP_MANIFEST_INVALID`: the manifest structure or version is unsupported.
- destination-exists errors: choose a new destination; never delete or
  overwrite a live root as an automatic recovery step.

A backup failure is isolated from task admission, planning, Reservation
transactions, terminal fencing, and rendering. Do not retry creative work as
a consequence of backup failure.

## Retention and privacy

- Store bundles as tenant-sensitive operational data with access controls
  appropriate for the underlying tenant business content.
- Copy verified bundles to independently protected storage according to the
  operator's retention requirements.
- Re-run `verify` after transport and periodically while retained.
- V1.5 does not automatically encrypt, upload, delete, or rotate bundles.
- Do not invent an automatic destructive retention policy. Removal is an
  explicit operator decision after replacement backups have been verified.

## What not to do

- Do not use `shutil.copy` or Explorer copy on a live SQLite file as the
  correctness mechanism.
- Do not treat WAL sidecar copying as the backup protocol.
- Do not claim a DB-only copy is Historical-Memory rebuildable.
- Do not scan orphan output files into the authoritative catalog.
- Do not rewrite `TaskHistory` to hide missing assets.
- Do not restore over a live tenant or regenerate task, execution, or FP IDs.
- Do not renew Reservation rows found in an offline backup.

