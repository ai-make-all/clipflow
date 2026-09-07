# VAR-001 Phase 3D-2H
# V1.5 Forward Compatibility & Upgrade Safety Audit

Review mode: read-only architecture audit, source collection, and upgrade
compatibility review.

No production source, tests, or databases were modified. No expensive
regression suites were run. No commit or push was performed. No L3 / V1.6
implementation was started.

Evidence priority used: current source > git > current schema >
investigation artifacts > inference.

## 1. Baseline

```text
git branch --show-current
feature/var-001-variation-policy

git rev-parse HEAD
76d5cd50c2f866add4d5f73041c268fa4bd73311

git status --short
(empty)

git log -15 --oneline --decorate
76d5cd5 (HEAD -> feature/var-001-variation-policy, tag: var-001-controlled-canary-v1, origin/feature/var-001-variation-policy) feat(var-001): add controlled reservation canary rollout
ca1a4af (tag: var-001-rollout-readiness-v1) feat(var-001): add reservation rollout readiness guardrails
5f73335 (tag: var-001-reservation-observability-v1) feat(var-001): add reservation operational diagnostics
697577a (tag: var-001-public-reservation-enforce-v1) feat(var-001): activate public reservation enforce mode
76a070a refactor(var-001): establish server-owned task identity
ee1b8c3 refactor(var-001): separate reservation owner attempt identity
f179e15 (tag: var-001-reservation-authority-v1) fix(var-001): harden reservation transactions and runtime acceptance
2427038 feat(var-001): add reservation confirmation and terminal fencing
dfb2cb9 feat(var-001): enforce planner reservation conflicts
d4338c7 feat(var-001): add renewable reservation lease foundation
affa39b feat(var-001): add historical novelty advisory integration
8d0be4a feat(var-001): add historical novelty policy contracts
24ae153 feat(var-001): add historical lookup and atomic reservations
2cd0cd4 feat(var-001): add fingerprint ledger shadow foundation
163177b (tag: var-001-coverage-explainability-v1) feat(var-001): add coverage explainability ux

git diff --check
(empty, exit 0)

git describe --tags --exact-match HEAD
var-001-controlled-canary-v1
```

Production working tree is clean. Expected branch, 2G commit, and tag
`var-001-controlled-canary-v1` are present.

Prior artifacts consulted (not architectural authority over current source):

- `doc/investigations/VAR001_PHASE3D2G_GENERATION_INVARIANT_FIX_REPORT.md`
- `doc/investigations/VAR001_PHASE3D2G_CONTROLLED_CANARY_REPORT.md`
- `doc/investigations/VAR001_PHASE3D2G_TARGETED_SOURCE_REVIEW.md`
- `doc/investigations/VAR001/phase3/VAR001_PHASE3D2F_TARGETED_SOURCE_REVIEW.md`

Temporary Agent Handoff documents were not used as architectural authority.

## 2. V1.5 Release Constitution

Frozen for this audit and for future V1.6 design:

1. V1.6 MUST NOT require clearing V1.5 tenant data.
2. Existing business truth must retain its meaning: `task_id`, execution
   identity, FP identity, Fingerprint Ledger occurrence, `TaskHistory`,
   `VideoTask` lifecycle.
3. L3 should attach new historical-memory tables/indexes to existing truth.
4. Schema migration and historical backfill are separate operations.
5. Incomplete historical backfill must not prevent new creative production.
6. Missing historical perceptual index means UNKNOWN / NOT_INDEXED, never
   `duplicate = false`.
7. Historical Memory must not become Reservation Authority.

Preferred upgrade model: additive schema + background backfill +
feature-gated historical rollout.

## 3. Current Data Model Map

Tenant physical store: `./data/dopamatrix_{canonical_tenant}.db`
(`src/api/database.py:441-443`). Application ORM (`Base`) and Fingerprint
Ledger (`FingerprintLedgerBase`) share that tenant engine.

### `video_tasks` / `VideoTask`

- PK: `id` integer autoincrement
- Unique: `task_id` string (server-owned public UUID)
- Lifecycle: `status`, `created_at`, `finished_at`
- Planning: `planning_policy`, `reservation_conflict_mode`,
  `reservation_mode_source`, optional rollout columns
- Relationship: `assets` → `VideoAsset` (`cascade="all, delete-orphan"`)
- No FK to Ledger, `TaskHistory`, or execution identity

### `video_assets` / `VideoAsset`

- PK: `id`
- FK: `task_id` → `video_tasks.id` (integer, ON DELETE CASCADE)
- Fields: `file_path`, `language`, `file_hash` (MD5, indexed),
  `perceptual_hash` (present, currently written as `""` on insert),
  `manifest_data`, `created_at`
- No `execution_id`, no FP digest, no SHA-256 column
- Production INSERT site: `src/api/services.py` only (legacy
  `POST /tasks/submit` matrix job). DSL coordinator does not write this
  table.

### `task_history` / `TaskHistory`

- PK: `id`
- Unique: `task_id` (public UUID, same identifier as `VideoTask.task_id`)
- Fields: `prompt`, `batch_size`, `duration`, `output_assets` JSON NOT NULL,
  `prompt_details` TEXT nullable, `created_at`
- No SQL FK to `video_tasks` (logical correlation by `task_id` string)
- DSL writer: `_build_task_history_record` / `_persist_task_history` /
  reservation fenced terminal (`src/api/routes_dsl.py`)
- Matrix writer: `src/api/services.py` (does not populate `prompt_details`)

`output_assets` element shapes are mixed:

- DSL: `file_path`, `file_hash`, `cover_path`, optional social fields
- Matrix: `path`, `hash`, `cover_path`, `cover_url`, `download_url`

Existing readers already accept both hash keys
(`src/api/routes_history.py:33`, `src/api/routes_matrix.py:102`).

### `variant_approvals` / `VariantApproval`

- Unique: `(task_id, asset_hash)` where `task_id` is public UUID and
  `asset_hash` is `TaskHistory` output hash
- `file_path`, `cover_path`, approval status, social fields, `created_at` /
  `updated_at`

### Ledger V2 (`src/api/fingerprint_ledger.py`, `LEDGER_SCHEMA_VERSION = 2`)

`fingerprint_identities`

- PK: `id`
- Unique: `(fingerprint_type, fingerprint_version, fingerprint_digest)`
- Payload: `digest_algorithm`, `source_hash_algorithm`, `canonical_payload`,
  `created_at`

`fingerprint_occurrences`

- PK: `id`
- Unique event: `(fingerprint_identity_id, task_id, execution_id, child_index, lifecycle_event)`
- Indexes: identity+lifecycle+`occurred_at`; `task_id`+`execution_id`
- FK: `fingerprint_identity_id` → identities (CASCADE)
- Fields: `lifecycle_event` ∈ `{PLANNED, RENDERED, FAILED}`, `occurred_at`,
  `provenance`
- No asset path, no file hash, no SHA-256

`fingerprint_reservations`

- PK: `fingerprint_identity_id`
- Lease/authority: `owner_task_id` (owner-attempt identity, not public
  `task_id`), `owner_slot_index`, expiry/confirm timestamps, optional
  `execution_id`

`fingerprint_ledger_schema_version`

- PK: `component`; `schema_version` integer

### Other tenant tables (not Historical Memory authority)

- `reservation_run_diagnostics`: unique public `task_id`; observational
- `reservation_rollout_breakers`: rollout control latch
- `local_assets_inventory`: DAM inputs, not rendered outputs
- `variant_status_audits`: approval audit

No `CreativeArtifact` table exists.

## 4. Task Lineage

Public DSL admission generates a server UUID, INSERTs `VideoTask`
(`queued`), then dispatches the worker with that `task_id`
(`src/api/public_task_admission.py`, `src/api/routes_dsl.py`).

Coordinator then:

1. allocates child executions (`_create_child_executions`)
2. renders children
3. on at least one success, persists one `TaskHistory` row keyed by the
   same public `task_id`
4. optionally records Ledger occurrences with that `task_id`
5. transitions `VideoTask.status` to `completed` / `failed`

Diagnostics (`ReservationRunDiagnostic`) are also keyed by public
`task_id` and are observational.

Durable relation for “all rendered outputs of this public task”:

- `TaskHistory.task_id == public task_id` → `output_assets` list
- additionally, DSL `prompt_details.children[].output_assets`
- legacy matrix also `VideoAsset` via integer `VideoTask.id`

Zero-success batches do **not** write `TaskHistory` (explicit
`if succeeded_count` in fenced terminal and `elif succeeded_count` on
the non-Reservation path). That is correct: there is no rendered
historical artifact.

Can a future V1.6 process start from a historical public `task_id` and
locate every rendered output belonging to that task?

**YES**, for tasks that persisted `TaskHistory` (the supported successful
or partial-success catalog). Enumeration is `TaskHistory` by `task_id`,
not websocket replay.

V15_TASK_LINEAGE_FOR_HISTORICAL_MEMORY_PROVEN: PASS

## 5. Execution Lineage

Child identity is created in `_create_child_executions`
(`src/api/routes_dsl.py:2451-2484`):

- `execution_id = str(uuid.uuid4())` (must differ from `task_id`)
- `file_sid = execution_uuid.hex[:8]`
- `child_index` is the batch slot

These values are held in memory for the worker process, then persisted
on successful/partial coordinator finalization inside
`TaskHistory.prompt_details.children[]`
(`child_index`, `execution_id`, `file_sid`, `outcome`, per-child
`output_assets`).

Ledger `fingerprint_occurrences.execution_id` / `child_index` persist
the same identifiers for exact/balanced coordinator-approved FPs.

Reservation `fingerprint_reservations.execution_id` is lease state, not
an artifact catalog.

`VideoAsset` has no execution column. Legacy `/tasks/submit` has no
child-execution allocator.

Survive restart: **yes** for DSL tasks that wrote `TaskHistory` (JSON
children) and/or Ledger occurrences. Runtime-only execution IDs that
never reached terminal persist (authority-lost / history-write failure)
are not historical truth.

V1.6 can distinguish two child executions inside one DSL batch using
`execution_id` (unique UUID) and/or `(task_id, child_index)` on Ledger
and `prompt_details.children`.

V15_EXECUTION_LINEAGE_FOR_HISTORICAL_MEMORY_PROVEN: PASS

(Scope: DSL coordinator path. Legacy matrix jobs have no child
execution identity; their artifact grain is task + language/file.)

## 6. FP Lineage

FP-001 contract is computed from the coordinator-approved main-visual
tuple, then recorded as `FingerprintIdentity` + occurrence
(`_fingerprint_ledger_occurrence_record`, provenance
`coordinator_authoritative_fp001`).

Chain:

candidate planning FP
→ identity unique on `(type, version, digest)`
→ `PLANNED` occurrence (Reservation confirm fence, ENFORCE)
→ `RENDERED` or `FAILED` occurrence at terminal
→ `task_id` + `execution_id` + `child_index`

`lookup_historical_exact` already answers whether identity X has prior
occurrences, including `rendered_count` and `last_rendered_at`, without
mutating policy (`src/api/fingerprint_ledger.py:657-716`).

A future historical index can answer “this rendered artifact came from
FP X” when:

- the child was planned under exact/balanced policy **and**
- a Ledger occurrence for that `execution_id` exists

Join: `TaskHistory.prompt_details.children.execution_id`
= `fingerprint_occurrences.execution_id` (+ `task_id`).

Not available:

- legacy `planning_policy='legacy'` (no FP-001)
- Ledger shadow/terminal write failure with history still present
  (asset exists; FP link missing)
- occurrence rows have no file path (must join TaskHistory)

FP-001 identity semantics are not required to change. Scope/recency/GEO
are policy dimensions, not digest inputs.

V15_FP_LINEAGE_FOR_HISTORICAL_MEMORY_PROVEN: PASS

## 7. Rendered Asset Provenance

Successful DSL child collection (`src/api/routes_dsl.py:2954-2969`)
persists into `TaskHistory.output_assets` and per-child
`prompt_details` after coordinator commit — not only websocket.

A. Every successful rendered child that reaches coordinator success
   persist has a durable path+hash in `TaskHistory`. Children that
   fail, or batches that lose Reservation authority / terminal persist,
   are not catalogued (see section 15).

B. The reference is persisted (`task_history.output_assets` JSON).
   Websocket duplicates a runtime view. `VideoAsset` is an additional
   persist path for legacy matrix only.

C. After restart, `GET /history/` and `GET /tasks/today` rehydrate from
   `TaskHistory` (`src/api/routes_history.py`).

D. Mapping:

   | Link | DSL | Legacy matrix |
   |---|---|---|
   | task | `TaskHistory.task_id` | `TaskHistory.task_id` and `VideoAsset.task_id` → `VideoTask.id` |
   | execution | `prompt_details.children[].execution_id` | none (no child executions) |
   | FP | join Ledger on `task_id`+`execution_id` | none |

E. One task can contain N independently addressable assets (batch
   children × language variants). They are list elements, not a single
   blob.

DSL `file_hash` is MD5 of the first 64 KiB (`read(65536)`), same helper
as compositor WS hashing. It is a display/catalog token, not a full-file
SHA-256. V1.6 render-hash backfill must hash the file bytes, not trust
this prefix MD5 as cryptographic identity.

V15_RENDERED_ASSET_PROVENANCE_PROVEN: PASS

## 8. Asset Path Durability

DSL compositor stores project-relative paths:

```text
output/final_{language}_{file_sid}.mp4
output/master_video_{file_sid}.mp4
```

(`src/nodes/compositor.py:82-91`, written unchanged into
`context.variants[].final_video`).

Optional `context.config["output_dir"]` copies the file to a possibly
absolute custom directory but **does not replace** the stored
`final_video` path used by history.

`VideoAsset.file_path` comment claims project-relative; matrix jobs may
pass worker paths through. `LocalAsset.file_path` is documented as a
local absolute DAM path (inputs, not outputs).

Classification: **ACCEPTABLE_FOR_V1.5**

- Restart with the same application working directory: paths remain
  valid.
- Moving the application directory, changing drive letter, or restoring
  DB without the `output/` tree: stored references become stale.
- Not STRONG (not opaque IDs / content-addressed URIs).
- Not BLOCKING for V1.5→V1.6 additive upgrade.

V15_RENDERED_ASSET_PROVENANCE_PROVEN remains PASS because durability is
relative-to-deployment, not “websocket only”.

## 9. Ledger Sufficiency

Ledger V2 provides immutable tenant-local facts for Historical Exact
Planning Guard:

- FP identity (type/version/digest/canonical payload)
- outcome (`PLANNED` / `RENDERED` / `FAILED`)
- timestamps (`occurred_at`, aggregable `last_rendered_at`)
- task + execution + child_index provenance
- tenant boundary = physical DB

It does **not** store artifact paths or file hashes.

Classify: **SUFFICIENT_WITH_EXTERNAL_LINEAGE**

External lineage required: `TaskHistory` (and optionally `VideoAsset`)
for rendered files. Do not introduce Ledger V3 for V1.6 Historical
Memory.

LEDGER_SCHEMA_V2_CAN_REMAIN_FROZEN: PASS

V15_HISTORICAL_EXACT_BACKFILL_FEASIBLE: PASS

## 10. Historical Exact Planning Feasibility

V1.6 can, without changing FP-001:

1. compute candidate FP X under the frozen contract
2. `lookup_historical_exact` on the tenant Ledger
3. if `rendered_count > 0`, apply a future recency/scope **policy**
   using `last_rendered_at` / occurrence rows

Missing durable fields that are **not** FP identity:

- GEO / platform / campaign — not on Ledger; must be policy/scope
  metadata if ever needed, or remain UNAVAILABLE
- asset path — join TaskHistory; not required for “FP X was rendered”

Current `historical_novelty_mode` is already `OFF | OBSERVE | ADVISORY`
and independent of `reservation_conflict_mode` on the public request
surface (`src/api/schemas.py`).

## 11. Exact Render Hash Backfill Feasibility

A future additive `RenderFingerprint` (artifact reference, sha256,
algorithm_version, created_at) can be populated by:

1. enumerating `TaskHistory.output_assets` (plus `VideoAsset` for matrix)
2. resolving `file_path` / `path` against the current working tree
3. hashing file bytes
4. storing the result in a **new** table keyed by existing identities

Safe when the file still exists. Missing file → `ASSET_MISSING`, not a
Ledger rewrite.

Existing prefix MD5 is **not** sufficient as the SHA-256 value.

V15_RENDER_HASH_BACKFILL_FEASIBLE: PASS

## 12. Perceptual Signature Backfill Feasibility

Same enumeration as section 11. `VideoAsset.perceptual_hash` is unused
(`""` on matrix insert; DSL has no row). V1.6 should use a new
`PerceptualSignature` table, not overload Reservation/Ledger.

Idempotent walk: unique `TaskHistory.task_id` + per-asset path/hash +
`algorithm_version`. `os.path.exists` gates compute vs `ASSET_MISSING`.

V15_PERCEPTUAL_BACKFILL_FEASIBLE: PASS

## 13. Creative Artifact Identity

No first-class `CreativeArtifact` table exists.

Closest current entities:

- `TaskHistory.output_assets[]` (authoritative completed-output catalog
  for DSL and matrix)
- `VideoAsset` (matrix-only ORM row)
- `VariantApproval` (task_id + asset_hash overlay)

V1.5 is **not** missing a critical identity that MUST be added before
release. V1.6 can introduce `CreativeArtifact` and backfill from
`TaskHistory` (+ children execution fields, + `VideoAsset` where
present).

Do not redefine `task_id` to mean artifact.

## 14. One Task / Many Artifacts

`batch_size` ≥ 1. Coordinator creates `child_count` executions. Each
successful child may emit multiple language files.

`VideoTask` is a batch. `task_id` alone is **not** an artifact primary
key.

Safest durable child/artifact correlation keys already producible:

- DSL: `(task_id, execution_id, file_path)` or
  `(task_id, execution_id, file_sid, language-implied basename)`
- Matrix: `(task_id, file_hash or path, language)`

`file_sid` is a function of `execution_id` (first 8 hex chars), so it
is a filename token, not a second authority.

## 15. Partial / Failed Task Semantics

| Case | Historical rendered truth |
|---|---|
| All children succeed | `TaskHistory` with all assets; Ledger `RENDERED` for FP children |
| Partial success | `TaskHistory.output_assets` = successful children only; failed children appear in `prompt_details.children` with `outcome=failed` and empty assets; Ledger `FAILED` vs `RENDERED` per child |
| All failed / zero success | No `TaskHistory`; no catalogued outputs |
| Reservation authority lost | History not persisted; WS assets cleared; on-disk files may remain — **not** authoritative |
| Terminal persist failure | Same as authority-lost for catalog purposes |
| Ledger shadow failure (OFF path) | `TaskHistory` may still exist; FP occurrence may be missing |

Future backfill must use `TaskHistory` / fenced terminal success, never
“file exists under `output/`”.

## 16. Authoritative Backfill Eligibility

Safe source of truth (current):

1. `TaskHistory` rows with non-empty `output_assets`
2. optionally confirm `VideoTask.status == 'completed'` by public
   `task_id` when the task row still exists
3. for FP attachment, Ledger `RENDERED` occurrences joined by
   `task_id` + `execution_id`
4. `VideoAsset` rows as a supplemental matrix catalog

Unsafe / non-authoritative:

- leftover `output/*.mp4` without `TaskHistory`
- websocket logs
- in-memory `_ChildResult`
- `LocalAsset` DAM files
- Reservation lease rows

## 17. Tenant Boundary

`request_tenant_id` → `canonical_tenant_id` → `get_tenant_engine` →
one SQLite file. Ledger schema is installed on that same engine
(`ensure_fingerprint_ledger_schema`). History, assets, diagnostics, and
breakers are tenant-local.

V1.6 Historical Memory can remain tenant-local. No cross-tenant global
Creative Memory is required.

V15_TENANT_BOUNDARY_PRESERVED: PASS

## 18. Existing Schema Evolution Mechanics

`initialize_application_schema` (`src/api/database.py:399-408`):

1. fail-closed `session_id` identity check (incompatible pre-B1R DBs
   only)
2. `Base.metadata.create_all` (creates **missing** tables; does not
   drop)
3. `ensure_video_task_rollout_metadata_schema` (ALTER ADD COLUMN +
   startup consistency scan; 2F/2G evidence)
4. `evolve_schema` (additive columns on existing tables; errors logged,
   not thrown)
5. repeat identity + rollout verification
6. Ledger `ensure_fingerprint_ledger_schema` (create_all + version
   table; V1→V2 additive reservation table historically)

Patterns already used without tenant reset: CREATE TABLE for new
models, ALTER ADD COLUMN, CREATE INDEX IF NOT EXISTS, application
startup scans, Ledger version row.

## 19. New Table Safety

A V1.6 process opening an existing V1.5 tenant DB can
`CREATE TABLE` via `create_all` / an `ensure_*` helper, in the same
startup transaction style as Ledger and application schema.

Existing rows are untouched. Failure of a **new** Historical Memory
ensure function should fail closed for that feature or follow the
documented `evolve_schema` “log and continue” pattern for non-authority
tables — V1.6 design choice. It does not require wiping V1.5 data.

V15_ADDITIVE_SCHEMA_UPGRADE_PROVEN: PASS

## 20. New Index Safety

`CREATE INDEX IF NOT EXISTS` is already used (readiness and canary
cohort indexes). Future FP historical, SHA-256, and backfill-status
indexes can be added the same way.

SQLite will lock writers while building a large index. This audit has
no production scale measurements; treat long `CREATE INDEX` as an
operational concern for unusually large seed DBs, not a reset
requirement.

## 21. Additive Column Safety

Technically possible via `evolve_schema` and dedicated `ensure_*`
scans (2G `rollout_generation` is the recent example).

L3 should **prefer new tables** over expanding
`fingerprint_reservations`, Reservation lease columns, or `VideoTask`
authority fields.

## 22. Background Backfill Capability

There is **no** reusable historical-index job framework.

Existing async tools: FastAPI `BackgroundTasks` (request-scoped render
and zip export), in-process render workers, websocket flood test.

V1.6 can add a dedicated enumerator/worker. It is not present today.
Rendering is already decoupled from optional Ledger shadow writes;
a future indexer can similarly avoid the Reservation transaction.

V15_BACKGROUND_BACKFILL_IDEMPOTENCE_FEASIBLE: PASS for **identity
sufficiency**. Framework reuse: none; must be built in V1.6.

## 23. Backfill Idempotence

Stable inputs current source can produce:

- public `task_id`
- DSL `execution_id` / `child_index` / `file_sid`
- stored relative `file_path` or matrix `path`
- catalog `file_hash` / `hash` (prefix MD5; usable as weak correlator)
- `algorithm_version` (V1.6 constant, not a V1.5 column)

Recommended future idempotency key (not implemented):

`(task_id, execution_id or '', relative_path, algorithm_version)`

Do not invent an artifact UUID that V1.5 never stored. Do not use
prefix MD5 as the only key.

## 24. Backfill Progress

Feasible in a **new operational table**, e.g. status
`NOT_INDEXED | INDEXED | FAILED_RETRYABLE | ASSET_MISSING`, without
writing Reservation or Ledger authority rows.

`VideoTask.status` and occurrence `lifecycle_event` must not be reused
as index-progress flags.

## 25. Partial Backfill Semantics

Nothing in the V1.5 data model forces “missing perceptual row ⇒ not a
duplicate”. `lookup_historical_exact` is exact-FP occurrence counting,
a different question.

V1.6 can run with a mix of indexed and unindexed artifacts if lookups
return `NO_MATCH` vs `NOT_FULLY_INDEXED` / `UNKNOWN` from the new index
tables.

V15_PARTIAL_BACKFILL_COMPATIBILITY_PROVEN: PASS

## 26. Feature-Gated Historical Rollout

`historical_novelty_mode` is already a separate public control from
`reservation_conflict_mode`. Policy module
`src/api/historical_novelty_policy.py` has no Reservation acquire /
lease imports.

Future OFF / OBSERVE / WARN / SELECTIVE_BLOCK can extend that policy
surface without changing Reservation public semantics.

## 27. Reservation Non-Dependence

Reservation authority modules (`planner_reservation.py`,
`reservation_lease.py`, Ledger reservation rows) do not read
`TaskHistory.output_assets`, perceptual hashes, or rollout breakers as
lease truth.

L3 tables can be written in separate sessions after terminal commit,
mirroring current non-authority diagnostics and OFF-path Ledger shadow
writes.

No current hard coupling forces Historical Memory into acquire /
heartbeat / confirm / PLANNED fence / terminal fence / release /
breaker/canary transactions.

V16_HISTORICAL_MEMORY_CAN_REMAIN_NON_AUTHORITATIVE: PASS

## 28. Task Identity Non-Dependence

Historical Memory can use the existing server-owned `task_id` and
child `execution_id`. Owner-attempt identity remains Reservation-only.

If V1.6 wants a dedicated artifact PK, add an artifact layer; do not
redefine task identity.

V15_TASK_LINEAGE… and execution lineage markers above remain PASS.

## 29. FP-001 Non-Dependence

L3 can consume `fingerprint_digest` / identity id as an **input**.
GEO, platform, recency, and performance stay policy/scope. No silent
FP-001 field injection is required for V1.6.

FP001_IDENTITY_CAN_REMAIN_FROZEN: PASS

## 30. Legacy V1.5 Row Compatibility

A V1.5 row with no L3 columns/tables is valid production data.

- `create_all` adds empty new tables
- missing index rows mean NOT_INDEXED
- `TaskHistory` without `prompt_details` (matrix) still has
  `output_assets`
- `VideoAsset.perceptual_hash == ""` means not indexed, not “unique”
- pre-exact-policy tasks have no FP occurrences

Startup must not treat “no Historical Memory rows” as migration
failure.

## 31. Backup / Restore

To preserve Historical Memory **rebuildability**:

1. tenant SQLite `data/dopamatrix_{tenant}.db` (tasks, history, ledger,
   DAM inventory metadata, approvals)
2. rendered output tree `output/` (and any custom output copies the
   operator actually uses)
3. DAM media files referenced by `LocalAsset.file_path` if those inputs
   must remain playable (not required to rebuild **output** hashes if
   `output/` is present)
4. optional `dopamatrix.db` settings DB (not tenant creative truth)

DB-only restore preserves Ledger + `TaskHistory` paths but **cannot**
recompute SHA-256 / perceptual signatures if files are gone.

Do not promise backfill after a DB-only restore.

## 32. Data Reset Audit

| Location | Behavior | Class |
|---|---|---|
| `initialize_application_schema` / `create_all` | create missing tables | production, additive |
| `evolve_schema` | ADD COLUMN only | production, additive |
| `verify_video_task_identity_schema` | reject pre-task_id `session_id` DBs | production fail-closed; not a V1.5→V1.6 wipe |
| `ensure_fingerprint_ledger_schema` | create/migrate Ledger to V2 | production additive |
| `build_backend.py` `_safe_rmtree` | packaging `build/` `dist/` | developer utility |
| `routes_matrix.py` `os.remove` | zip tmp/failed files | explicit export cleanup |
| `approval_service.py` tombstone unlink | approval filesystem helper | explicit user/approval flow |
| `asset_provider.py` clip unlink | download cache | DAM helper |
| tests (not executed here) | temp DBs | test-only |

Ordinary V1.5 → V1.6 application startup does not delete tenant DBs,
truncate creative tables, or clear `output/`.

V15_NO_DATABASE_RESET_REQUIRED_PROVEN: PASS

## 33. Proposed V1.6 Additive Model

Architecture recommendation only. Not code.

### CreativeArtifact (optional catalog)

- Why: stable PK for N assets per task without overloading `task_id`.
- References: `task_id`; optional `execution_id` / `child_index`;
  stored relative path; catalog hash keys.
- Backfill: YES from `TaskHistory` (+ `VideoAsset`).
- Observational catalog, not Reservation authority.

Not mandatory before V1.5; composite keys already exist.

### RenderFingerprint

- Why: full-file SHA-256 exact-render index.
- References: artifact composite key or future `CreativeArtifact` id;
  `algorithm_version`; `sha256`; `created_at`.
- Backfill: YES if file exists.
- Observational index.

### PerceptualSignature

- Why: similarity memory without changing FP-001.
- References: same artifact key; `signature_version`; blob; `indexed_at`.
- Backfill: YES, async.
- Observational. Missing row = NOT_INDEXED.

### HistoricalBackfillState

- Why: checkpoint/resume; `NOT_INDEXED` / `INDEXED` /
  `FAILED_RETRYABLE` / `ASSET_MISSING`.
- References: artifact key + `algorithm_version`.
- Not authority.

### HistoricalPolicyObservation

- Why: optional durable OBSERVE/WARN decisions.
- References: candidate FP identity id + task/execution + policy mode.
- Can wait; `historical_novelty` diagnostics already land in
  `prompt_details` today.
- Must not write Reservation rows.

Skip implementing these now.

## 34. Pre-V1.5 Fix Gate

| Topic | Gate |
|---|---|
| New Historical Memory tables/indexes | A. NO FIX REQUIRED BEFORE V1.5 |
| SHA-256 / perceptual columns on V1.5 tables | A |
| CreativeArtifact table | A (backfillable) |
| execution_id already in `prompt_details.children` | A |
| VideoAsset unused on DSL path | A (`TaskHistory` is the catalog) |
| Prefix MD5 vs SHA-256 | A (rehash files in V1.6) |
| Relative `output/` paths | A operational backup rule, not a schema fix |
| Ledger V2 / FP-001 / task_id / Reservation | A do not change |
| Destructive rebuild | not required |

No source-proven **B** (lossy without a V1.5 field) or **C** (release
blocker) items.

Optional non-blocking hygiene for V1.6 parsers: normalize
`path` vs `file_path` and `hash` vs `file_hash` when reading
`output_assets`. That is a reader concern, not a missing identity.

## 35. Critical Questions

Q1. Can V1.5 be released and V1.6 Historical Memory added without
    clearing tenant DBs? **YES.**

Q2. Can old V1.5 rendered videos be enumerated after restart? **YES**,
    from `TaskHistory` (and `VideoAsset` for matrix).

Q3. Can each old rendered video be linked to task? **YES.**

Q4. Can each old rendered video be linked to child execution? **YES**
    for DSL coordinator history with `prompt_details.children`;
    **N/A** for legacy matrix (no child executions).

Q5. Can each old rendered video be linked to FP-001? **YES** when a
    Ledger occurrence exists for that `task_id`+`execution_id`;
    **NO** for legacy policy / missing shadow write (no FP was
    authoritative).

Q6. Can exact SHA256 historical indexes be backfilled? **YES** if
    files remain at stored paths.

Q7. Can future perceptual signatures be backfilled? **YES**, same
    enumeration.

Q8. Can backfill be idempotent? **YES**, from existing
    task/execution/path identities plus algorithm version.

Q9. Can V1.6 run while backfill is incomplete? **YES**, if lookups
    distinguish NOT_INDEXED from NO_MATCH.

Q10. Does any missing lineage require a narrow V1.5 fix before
     release? **NO.**

Q11. Would any ordinary V1.6 schema evolution require destructive
     rebuild/reset? **NO** under the existing create_all / ALTER ADD /
     CREATE INDEX IF NOT EXISTS patterns.

Q12. What must be backed up to preserve Historical Memory
     rebuildability? **Tenant SQLite + `output/` tree** (plus DAM files
     only if input media must remain playable). DB-only is insufficient
     for hash/perceptual backfill.

## 36. Findings

No source-proven `VAR3D2H-RF-01` … `VAR3D2H-RF-15` defects.

Watched IDs and disposition:

| ID | Disposition |
|---|---|
| RF-01 RENDERED_ASSET_NOT_DURABLY_ADDRESSABLE | not found (`TaskHistory` persist) |
| RF-02 ASSET_CANNOT_BE_LINKED_TO_CHILD_EXECUTION | not found on DSL history path |
| RF-03 ASSET_CANNOT_BE_LINKED_TO_FP_IDENTITY | not found when Ledger occurrence exists; absence for legacy is expected |
| RF-04 ONE_TASK_MANY_ASSETS_AMBIGUOUS | not found; list + execution/path keys exist |
| RF-05 BACKFILL_WOULD_INDEX_STALE_NONAUTHORITATIVE_OUTPUT | not found if backfill uses `TaskHistory`, not disk scrape |
| RF-06 V15_SCHEMA_EVOLUTION_REQUIRES_DESTRUCTIVE_RESET | not found |
| RF-07 V15_ASSET_PATH_NOT_RESTART_DURABLE | not found for same-CWD restart; classify ACCEPTABLE_FOR_V1.5 |
| RF-08 BACKFILL_CANNOT_BE_IDEMPOTENT_FROM_EXISTING_IDENTITIES | not found |
| RF-09 PARTIAL_BACKFILL_CANNOT_BE_REPRESENTED_SAFELY | not found |
| RF-10 HISTORICAL_MEMORY_WOULD_REQUIRE_RESERVATION_REDESIGN | not found |
| RF-11 HISTORICAL_MEMORY_WOULD_REQUIRE_TASK_IDENTITY_REDESIGN | not found |
| RF-12 HISTORICAL_MEMORY_WOULD_REQUIRE_FP001_REDEFINITION | not found |
| RF-13 TENANT_BOUNDARY_INSUFFICIENT_FOR_HISTORICAL_MEMORY | not found |
| RF-14 BACKUP_RESTORE_CANNOT_PRESERVE_REBUILDABILITY | not found if DB+`output/` are both restored |
| RF-15 NARROW_PROVENANCE_FIELD_REQUIRED_BEFORE_V15 | not found |

Required future operator rule (not a code finding): backfill eligibility
must ignore orphan files after authority-lost / terminal-persist
failure.

## 37. V1.5 Release Recommendation

V1.5 (L1 uniqueness + L2 Reservation / controlled Default-ON) can ship
without adding Historical Memory tables, artifact IDs, SHA-256, or
pHash.

V1.6 Historical Creative Memory can attach additively to tenant DBs
using `TaskHistory` + Ledger V2 + relative `output/` files, with
feature-gated policy independent of Reservation.

Do not start L3 implementation in this phase.

## 38. Final Git Status

Recorded after creating this audit artifact. Production source remains
unmodified.

```text
git rev-parse HEAD
76d5cd50c2f866add4d5f73041c268fa4bd73311

git status --short
?? doc/investigations/VAR001_PHASE3D2H_V15_FORWARD_COMPATIBILITY_AUDIT.md
```

Marker summary:

- V15_TASK_LINEAGE_FOR_HISTORICAL_MEMORY_PROVEN: PASS
- V15_EXECUTION_LINEAGE_FOR_HISTORICAL_MEMORY_PROVEN: PASS
- V15_FP_LINEAGE_FOR_HISTORICAL_MEMORY_PROVEN: PASS
- V15_RENDERED_ASSET_PROVENANCE_PROVEN: PASS
- V15_HISTORICAL_EXACT_BACKFILL_FEASIBLE: PASS
- V15_RENDER_HASH_BACKFILL_FEASIBLE: PASS
- V15_PERCEPTUAL_BACKFILL_FEASIBLE: PASS
- V15_BACKGROUND_BACKFILL_IDEMPOTENCE_FEASIBLE: PASS
- V15_PARTIAL_BACKFILL_COMPATIBILITY_PROVEN: PASS
- V15_ADDITIVE_SCHEMA_UPGRADE_PROVEN: PASS
- V15_NO_DATABASE_RESET_REQUIRED_PROVEN: PASS
- V15_TENANT_BOUNDARY_PRESERVED: PASS
- V16_HISTORICAL_MEMORY_CAN_REMAIN_NON_AUTHORITATIVE: PASS
- FP001_IDENTITY_CAN_REMAIN_FROZEN: PASS
- LEDGER_SCHEMA_V2_CAN_REMAIN_FROZEN: PASS

VAR001_PHASE3D2H_V15_FORWARD_COMPATIBILITY_PASS
