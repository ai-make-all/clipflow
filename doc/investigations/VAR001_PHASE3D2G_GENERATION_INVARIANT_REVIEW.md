# VAR-001 Phase 3D-2G
# Rollout Generation Existing-DB Invariant Review

Review mode: ultra-narrow, read-only follow-up.

The rest of `VAR001_PHASE3D2G_TARGETED_SOURCE_REVIEW.md` remains accepted
and is not reopened.

Inspected production source:

- `src/api/models.py`
- `src/api/database.py`
- `src/api/public_task_admission.py`

`src/api/reservation_rollout_control.py` was consulted only to prove
whether supported `ROLLOUT_CANARY` writes copy the backend config
generation after `_SAFE_GENERATION` validation.

No production source was modified. No tests were run. No database was
opened or mutated. No commit or push was performed.

## 1. Scope

This review answers only whether existing / additively evolved
`VideoTask` schemas fully enforce the persisted `rollout_generation`
invariant at column DDL, fresh-schema CHECK, startup scan, and
application admission.

## 2. Frozen Generation Contracts

Config validation and persisted-task validation are **not** identical.

### A. Backend rollout CONFIG generation

`ReservationRolloutControlConfiguration.__post_init__`
(`src/api/reservation_rollout_control.py:224-228`) requires:

```python
_SAFE_GENERATION = re.compile(r"[A-Za-z0-9._-]{1,64}")
```

and rejects the configuration unless
`_SAFE_GENERATION.fullmatch(self.rollout_generation)` succeeds.

Config contract:

- type `str`
- length `1..64`
- character set `[A-Za-z0-9._-]` only

### B. Persisted `VideoTask.rollout_generation`

Task-layer source does **not** reuse `_SAFE_GENERATION`.

| Layer | Non-null when canary | Non-empty when canary | Maximum length | Safe characters |
|---|---|---|---|---|
| Fresh ORM column `String(64)` | nullable column | no | annotation only; SQLite does not enforce | no |
| Fresh CHECK `ck_video_tasks_rollout_metadata_consistency` | yes | `length(...) > 0` | no | no |
| Additive `ADD COLUMN` | nullable `TEXT` | no | no | no |
| Startup consistency scan | yes (canary) | `length(...) = 0` is invalid | no | no |
| `_validate_rollout_metadata` | yes (canary) | truthy `str` | `len(...) > 64` rejected | no |

Authoritative persisted-task contract that is actually implemented,
taken only from task schema / admission / startup source:

- non-canary sources: `rollout_generation` must be `NULL`
- `ROLLOUT_CANARY`: must be a non-null, non-empty string
- supported admission additionally requires `isinstance(..., str)` and
  `len(...) <= 64`
- **no** persisted-task CHECK, scan, or admission validator requires
  `[A-Za-z0-9._-]`

## 3. Fresh Schema

`VideoTask.rollout_generation` (`src/api/models.py:121`):

```python
rollout_generation = Column(String(64), nullable=True)
```

SQLAlchemy `String(64)` becomes SQLite `VARCHAR(64)` / `TEXT`. SQLite
does **not** enforce that declared length. The column annotation is
not a persisted length constraint.

`ck_video_tasks_rollout_metadata_consistency`
(`src/api/models.py:55-80`) is the only fresh-schema CHECK that
mentions `rollout_generation`. Complete generation predicates inside
that CHECK:

```sql
-- ROLLOUT_CANARY branch
rollout_generation IS NOT NULL
AND length(rollout_generation) > 0

-- EXPLICIT_ENFORCE branch
rollout_generation IS NULL

-- DEFAULT_OFF / EXPLICIT_OFF branch
rollout_generation IS NULL
```

There is **no** fresh-schema CHECK of the form
`length(rollout_generation) <= 64` and **no** character-class CHECK.

## 4. Additive Existing-DB Column

When the column is missing, `ensure_video_task_rollout_metadata_schema`
(`src/api/database.py:239` and `254-262`) executes:

```sql
ALTER TABLE "video_tasks" ADD COLUMN "rollout_generation" TEXT
```

The additive definition is the bare string `"TEXT"`.

It does **not** include a CHECK for:

- non-empty if non-null
- maximum length
- safe characters

By contrast, the sibling additive columns `rollout_bucket` and
`rollout_canary_basis_points` do carry per-column range CHECKs.
`rollout_generation` is the unconstrained TEXT sibling.

Post-add type verification (`src/api/database.py:309-319`) only
requires the inspector type to be `String`. It does not inspect length
or a CHECK.

Existing pre-2G rows are not given a canary generation. The only
backfill UPDATE is `reservation_mode_source = 'EXPLICIT_ENFORCE'` for
pre-existing `ENFORCE` rows (`src/api/database.py:263-269`).

## 5. Startup Consistency Scan

Complete generation-related predicates in the same
`SELECT 1 FROM video_tasks WHERE ...` scan
(`src/api/database.py:343-390`):

```sql
-- invalid canary generation:
reservation_mode_source = 'ROLLOUT_CANARY'
AND (
    ...
    OR rollout_generation IS NULL
    OR length(rollout_generation) = 0
    ...
)

-- invalid non-canary generation presence:
reservation_mode_source = 'EXPLICIT_ENFORCE'
AND ( ... OR rollout_generation IS NOT NULL ... )

reservation_mode_source IN ('DEFAULT_OFF', 'EXPLICIT_OFF')
AND ( ... OR rollout_generation IS NOT NULL ... )
```

Elsewhere in **that same** startup validation there is:

- no `length(rollout_generation) > 64`
- no `length(rollout_generation) <= 64`
- no `GLOB` / `LIKE` / regex / character-class test
- no Python-side walk of generation strings after the SQL

The scan therefore enforces only: canary generation present and
non-empty; non-canary generation absent.

## 6. Application Admission Validation

Exact `_validate_rollout_metadata` generation checks
(`src/api/public_task_admission.py:107-127`):

For `ROLLOUT_CANARY`, rejection occurs when any of:

```python
not isinstance(decision.rollout_generation, str)
or not decision.rollout_generation
or len(decision.rollout_generation) > 64
```

`not decision.rollout_generation` rejects `""` (and would reject
whitespace-only only if the string were falsy; a space is truthy and
would pass).

Supported production admission therefore enforces:

| Check | Enforced |
|---|---|
| type `str` | yes |
| non-empty (truthy) | yes |
| maximum length `<= 64` | yes |
| character set `[A-Za-z0-9._-]` | **no** |

For non-canary sources, any non-`None` `rollout_generation` is
rejected (`src/api/public_task_admission.py:130-131`).

This admission function runs only on the insert path. It is not
invoked by `ensure_video_task_rollout_metadata_schema`.

## 7. Config vs Task Generation on the Supported Write Path

Supported `ROLLOUT_CANARY` construction is only:

```python
return PublicTaskReservationModeDecision(
    reservation_conflict_mode="ENFORCE",
    reservation_mode_source="ROLLOUT_CANARY",
    rollout_generation=configuration.rollout_generation,
    rollout_bucket=bucket,
    rollout_canary_basis_points=basis_points,
)
```

(`src/api/reservation_rollout_control.py:743-749`)

`configuration` is a `ReservationRolloutControlConfiguration` instance
that has already passed `_SAFE_GENERATION.fullmatch`.

Public DSL explicit OFF / explicit ENFORCE and legacy `/tasks/submit`
never pass `reservation_mode_source="ROLLOUT_CANARY"` and never supply
a generation.

Therefore every **supported** `ROLLOUT_CANARY` task generation
originates exclusively from
`ReservationRolloutControlConfiguration.rollout_generation` after
`_SAFE_GENERATION` validation.

That write-path fact does not create an existing-DB read-path
constraint.

## 8. Manual / Corrupted Existing DB

Specified row on an additively evolved database:

- `reservation_mode_source = 'ROLLOUT_CANARY'`
- `reservation_conflict_mode = 'ENFORCE'`
- `rollout_generation` = an overlong or unsafe string
- bucket / basis otherwise valid

Startup evaluation against `src/api/database.py:359-371`:

- source is an allowed value
- mode is `ENFORCE`
- generation is not `NULL`
- `length(rollout_generation) = 0` is false
- bucket / basis predicates pass

Application startup **accepts** the row.

Answer: **B. accept it.**

An overlong string is accepted because the scan has no maximum-length
predicate. An unsafe-character string is accepted because the scan has
no character-class predicate. The additive `TEXT` column cannot reject
either. The fresh-schema CHECK, even if it were present on that
evolved table, also lacks those two predicates.

## 9. Classification

VAR3D2G-RF-35
EXISTING_DB_STARTUP_SCAN_DOES_NOT_FULLY_ENFORCE_ROLLOUT_GENERATION_CONTRACT

Severity: **hardening-only issue**.

Not an authority correctness blocker:

- `rollout_generation` is not consumed by Planner Reservation,
  acquire, heartbeat, confirmation, terminal fencing, or release.
- A corrupted generation string cannot equal a currently loaded config
  generation, because a loaded config generation must match
  `_SAFE_GENERATION`. Current-generation cohort, latch, and breaker
  lookups use exact equality to that config value.

Not a rollout-control correctness blocker for the supported write path:

- supported canary INSERTs copy a `_SAFE_GENERATION`-validated label
- admission additionally caps length at 64

It is a persisted-metadata integrity hardening gap:

- existing-DB startup will boot with a `ROLLOUT_CANARY` row whose
  generation would be illegal as config and, if overlong, illegal as
  admission input
- additive column DDL and the startup scan are weaker than both the
  config contract and the admission length contract

Minimal correction scope (not applied in this review):

1. Extend the startup scan canary branch with
   `length(rollout_generation) > 64` and, if the persisted contract is
   intentionally aligned to config, a SQLite-expressible safe-character
   predicate equivalent to `[A-Za-z0-9._-]`.
2. Optionally add the same predicates to
   `ck_video_tasks_rollout_metadata_consistency` for fresh schemas and
   to the additive `rollout_generation` column definition.
3. Optionally add `_SAFE_GENERATION.fullmatch` to
   `_validate_rollout_metadata` so the insert path and the persisted
   contract match.

Do not rebuild tenant databases. Do not change Reservation authority.
Do not change Ledger V2.

## 10. Stop

No fix. No test. No database mutation. No commit. No push.
