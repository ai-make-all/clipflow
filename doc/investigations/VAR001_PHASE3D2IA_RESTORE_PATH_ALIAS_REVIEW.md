# VAR-001 Phase 3D-2I-A
# Restore Path Alias Safety Review

Review mode: ultra-narrow, read-only. The prior Targeted Backup /
Restore Source Review remains accepted except for restore staging
physical-path alias safety.

No production source, tests, or databases were modified. No regression
suites were run. No commit, push, or tag was performed. 2I-A2 was not
started.

Python used to confirm pathlib documentation (not project tests):
CPython 3.12.10.

## 1. Scope

Inspected only restore/path construction in `src/api/backup_restore.py`:

- `restore_backup_to_staging`
- CLI `--staging-root` / `--bundle`
- `_is_within`
- `Path.absolute` vs `Path.resolve`
- temporary restore directory
- `os.replace` publish

Focused tests were read after production source. Backup destination
`create_backup_bundle` also uses `.absolute()`; that is out of scope
for this review.

## 2. Current Restore Path Flow

CLI (`main`, `restore-to-staging`):

`--bundle` and `--staging-root` are required strings. They are passed
unchanged into `restore_backup_to_staging`.

Exact production flow (`src/api/backup_restore.py` 635-690):

1. `bundle_root = Path(bundle).resolve()`
   Physical/canonical bundle path. Symlinks and junctions on existing
   bundle components are resolved. `.` / `..` are normalized.

2. `final_root = Path(staging_root).absolute()`
   Absolute lexical path only. CPython 3.12 documents this as:
   prepend cwd if needed; **no normalization; no symlink resolution**.

3. Existence: `if final_root.exists()`
   `Path.exists()` uses `os.stat`, which **follows** existing Windows
   reparse points / POSIX symlinks for components that exist. An
   existing live directory reached through an alias is rejected
   (`RESTORE_STAGING_DESTINATION_ALREADY_EXISTS`). A missing final
   child returns false even when its parent is an alias.

4. Nesting: `_is_within(final_root, bundle_root) or _is_within(bundle_root, final_root)`
   `_is_within` is `path.relative_to(root)` (default `walk_up=False`).
   That compares the **stored path parts**, not the physical open path.
   One side is resolved (`bundle_root`); the other is only
   `.absolute()` (`final_root`).

5. `verify_backup_bundle(bundle_root)` runs **before** any staging
   directory is created. Bundle member paths later use
   `_safe_bundle_member`, which `resolve()`s the member under the
   already-resolved bundle root.

6. `final_root.parent.mkdir(parents=True, exist_ok=True)`
   Parent is `Path.absolute().parent` (lexical). If that parent is a
   junction/symlink, `mkdir` on an existing alias is a no-op and later
   creates children **through** the alias.

7. `temporary_root = final_root.parent / f".{final_root.name}.restore-{uuid}"`
   then `temporary_root.mkdir()`.
   The temporary directory is a sibling of the requested child, under
   the **unresolved** parent. If the parent aliases into the bundle,
   this `mkdir` creates a directory **physically inside the bundle**.

8. Copy `tenant.db` and assets into `temporary_root` (`data/`, `output/`).
   Source members are resolved via `_safe_bundle_member`. Destination
   writes use the temporary path, not a second canonicalization.

9. `_validate_restored_database(restored_database)` binds SQLAlchemy
   to the file under `temporary_root` (out of scope for this alias
   question).

10. `os.replace(temporary_root, final_root)`
    Publishes to the lexical `final_root`. On Windows this follows the
    existing parent reparse point, so the published name appears under
    the physical parent.

11. On any exception: `shutil.rmtree(temporary_root)`. Failed staging
    is removed. A successful publish leaves the new child at the
    physical location of `final_root`.

No later `resolve()` is applied to `staging_root`, its parent, or
`final_root`. Publication is not re-checked against a canonical dest.

## 3. absolute() vs resolve()

CPython 3.12 `Path.absolute()` (runtime docstring):

> Return an absolute version of this path by prepending the current
> working directory. No normalization or symlink resolution is
> performed. Use resolve() to get the canonical path to a file.

CPython 3.12 `Path.resolve(strict=False)` (default):

> Make the path absolute, resolving all symlinks on the way and also
> normalizing it.

`resolve(strict=False)` uses `os.path.realpath` and does **not**
require the final child to exist. Existing prefix components,
including Windows junctions and POSIX symlinks, are canonicalized;
missing remainder components are appended.

The restore destination therefore remains a **lexical** absolute path.
The bundle root is a **physical** path. Nesting compares those two
different kinds of path.

## 4. Existing Parent Canonicalization

The source does **not** resolve the nearest existing parent of the
requested staging destination.

For a non-existent child `alias_parent/new-child` the code does **not**
compute:

```text
canonical_target = alias_parent.resolve() / "new-child"
```

nor the equivalent `Path(staging_root).resolve(strict=False)`.

It uses:

```text
final_root = Path(staging_root).absolute()
temporary_root = final_root.parent / ".{name}.restore-{uuid}"
```

`final_root.parent` is the lexical parent of the absolute path, not
`parent.resolve()`.

## 5. Bundle Nesting

Intended rule: bundle and restore destination must not contain one
another, on **physical** paths.

### A. Restore destination physically inside the bundle

Proven bypass when the destination child does not exist and the parent
is an alias into the bundle.

POSIX:

```text
/real/bundle                 (actual bundle, exists)
/link -> /real/bundle
staging: /link/new-stage     (does not exist)
```

Windows (junction or directory symlink):

```text
C:\real\bundle
C:\alias -> C:\real\bundle
staging: C:\alias\new-stage
```

Then:

- `bundle_root` becomes `...\real\bundle`
- `final_root` remains `...\alias\new-stage`
- `exists()` is false
- `_is_within` fails both directions because the strings/parts differ
- temporary dir is created as `...\alias\.new-stage.restore-...`
  which is physically `...\real\bundle\.new-stage.restore-...`
- `os.replace` publishes `...\real\bundle\new-stage`

Direction A is **not** enforced on physical paths.

### B. Bundle physically inside the restore destination

A restore destination that is an **existing** ancestor of the bundle
(direct or via alias) is rejected by `exists()`, because ancestors
already exist and `exists()` follows reparse points.

A **new** missing child cannot be a current ancestor of an existing
bundle. After publication the new directory is empty of the original
bundle path; the bundle is not moved under it.

Direction B is therefore already covered by the existence check for
the realistic ancestor case. The alias hole is direction A.

Lexical `..` in an unresolved `.absolute()` path can make `_is_within`
a **false positive** (rejecting a sibling such as
`bundle\..\other-new-dir` because `bundle` is a prefix of the parts).
That is not an alias bypass.

## 6. Live Tenant Alias Risk

Restore has no `--project-root` and does not know live `data/` or
`output/`. Protection against live trees is only:

- destination must not already exist (`exists()` follows aliases)

Distinguish:

**Existing live tenant paths** (project root, `data/`, `output/`,
tenant DB file, `output/*.mp4`): if the operator's staging path
aliases an existing directory/file, `exists()` is true and restore
refuses. This review does **not** prove overwrite of live tenant
SQLite or existing catalog assets.

**Non-existent child under an alias into a live tree:** restore will
create a **new** subdirectory through that alias, for example
`data/<new-name>/data/dopamatrix_*.db`. That is contamination of the
live tree with an isolated extra directory, not replacement of
`data/dopamatrix_<tenant>.db`.

**Source backup bundle:** direction A **does** write a new directory
(and, during the operation, a temporary directory) physically inside
the bundle. Authoritative bundle members `tenant.db`, `manifest.json`,
and `assets/` already exist, so they cannot be chosen as
`staging_root` (`exists()`). Extra sibling directories are not
catalog authority (verify does not scan unknown names). The bundle
directory tree is still mutated.

No default live-tenant destination is inferred. Risk requires an
operator-supplied `--staging-root` whose parent is a symlink/junction.

## 7. Windows Semantics

Development environment: Windows, CPython 3.12.10.

| Input | Source behavior | Alias relevance |
|---|---|---|
| Directory symlink / junction parent | `.absolute()` keeps the alias; `exists()` / `mkdir` / `os.replace` follow the reparse point | Direction A bypass |
| File symlink as staging_root | If it exists, restore refuses | No overwrite |
| Drive casing (`C:\Real` vs `C:\real`) | Windows `Path` equality is case-insensitive, so `_is_within` can still match once parts are the same path | Not a separate bypass when both sides share lexical identity |
| Drive-relative `C:foo` | `.absolute()` does not perform `resolve()`; not claimed as a junction bypass | Out of scope unless combined with an alias parent |
| UNC | Same lexical-vs-`realpath` split if a share path aliases the bundle parent | Same finding if an alias exists |

This is not a Windows-only defect. POSIX symlink parents have the
same lexical nesting hole. Windows is the current development OS and
junctions are the practical alias type.

Do not treat ordinary already-canonical paths as blocked. Two
unrelated resolved directories still nest-check correctly.

## 8. Existing Test Coverage

`tests/test_var001_v15_backup_restore.py`:

- `test_restore_to_isolated_root_preserves_identity_and_truth` — new
  sibling directory, no alias
- `test_restore_never_overwrites_an_existing_destination` — existing
  real directory, no alias
- CLI restore uses a fresh path string

No focused test creates a symlink or junction parent pointing at the
bundle (or at `data/` / `output/`) and restores a missing child through
that alias.

## 9. Finding

### VAR3D2IA-SR-16
RESTORE_STAGING_NESTING_CHECK_IS_LEXICAL_NOT_PHYSICAL

A symlink or junction parent can bypass the intended
bundle/destination nesting rule for a **non-existent** child.

Severity: **RESTORE_HARDENING_ONLY**

It can:

- mutate the source backup bundle by creating a new subdirectory
  (and a temporary restore directory) physically inside the bundle

It cannot, from this source:

- overwrite live tenant truth for paths that already exist
- overwrite `tenant.db` / `manifest.json` / `assets/` as the restore
  destination (those names exist)

It is therefore an isolation/hygiene and bundle-tree contamination
defect, not a live-tenant overwrite hole.

### Minimal correction scope (do not implement in this phase)

Canonicalize the requested non-existent destination through its
existing parent **before** existence, nesting, mkdir, and publish.
Do not use `resolve(strict=True)`, which requires the child to exist.

Preferred shape:

```text
resolved_parent = Path(staging_root).absolute().parent.resolve()
canonical_target = resolved_parent / Path(staging_root).name
```

Equivalent for a single missing leaf:
`Path(staging_root).resolve(strict=False)` (CPython 3.12 default).
That form also canonicalizes multiple missing trailing components.

Then:

- existence check on `canonical_target`
- physical `_is_within` both directions against `bundle_root`
- create the temporary sibling under `canonical_target.parent`
- `os.replace` onto `canonical_target`

Restore currently has no project-root, so live `data/` / `output/`
cannot be compared unless a protected-root argument is added later.
Bundle-root containment is the required check for this finding.

Add a focused Windows junction (and POSIX symlink) regression test:
missing child under an alias into the bundle must raise
`BackupPathSafetyError` and must not create entries inside the bundle.

## 10. Classification

VAR3D2IA-SR-16
RESTORE_STAGING_NESTING_CHECK_IS_LEXICAL_NOT_PHYSICAL

Severity: RESTORE_HARDENING_ONLY

## 11. Final Git Status

HEAD unchanged. Production source unchanged. This review added only
this artifact.

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
?? doc/investigations/VAR001_PHASE3D2IA_RESTORE_PATH_ALIAS_REVIEW.md
?? doc/investigations/VAR001_PHASE3D2IA_TARGETED_BACKUP_RESTORE_SOURCE_REVIEW.md
?? doc/investigations/VAR001_PHASE3D2IA_V15_RC_BACKUP_ACCEPTANCE_REPORT.md
?? doc/operations/
?? src/api/backup_restore.py
?? src/version.py
?? tests/test_var001_v15_backup_restore.py
```
