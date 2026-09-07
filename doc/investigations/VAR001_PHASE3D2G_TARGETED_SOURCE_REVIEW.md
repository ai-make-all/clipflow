# VAR-001 Phase 3D-2G
# Targeted Controlled Canary Source Review

Review mode: targeted source review, read-only except for this requested artifact.

Reviewed production scope:

- `src/api/database.py`
- `src/api/models.py`
- `src/api/public_task_admission.py`
- `src/api/reservation_rollout_control.py`
- `src/api/reservation_rollout_readiness.py`
- `src/api/routes.py`
- `src/api/routes_dsl.py`
- `src/api/routes_reservation_diagnostics.py`
- `src/api/schemas.py`

Supporting unchanged source was inspected only where required to prove
tenant identity, task-ID generation, lease preflight, worker dispatch,
lifecycle updates, Reservation controller construction, and Ledger V2.

No tests were run. No database was opened or mutated. No production source
or test source was modified. No commit, push, canary-percentage change,
full Default-ON activation, or next-phase start was performed.

## A. Baseline

Recorded before creating this review artifact:

```text
git branch --show-current
feature/var-001-variation-policy

git rev-parse HEAD
ca1a4af6d5166c3b70943e786feade9d42291a34

git log -1 --format=%s
feat(var-001): add reservation rollout readiness guardrails
```

```text
git status --short
 M src/api/database.py
 M src/api/models.py
 M src/api/public_task_admission.py
 M src/api/reservation_rollout_readiness.py
 M src/api/routes.py
 M src/api/routes_dsl.py
 M src/api/routes_reservation_diagnostics.py
 M src/api/schemas.py
 M tests/test_inv001_execution_isolation.py
 M tests/test_inv001_planning_policy.py
 M tests/test_inv001_variant_planning.py
 M tests/test_var001_fingerprint_ledger.py
 M tests/test_var001_historical_novelty_integration.py
 M tests/test_var001_public_reservation_activation.py
?? doc/investigations/VAR001_PHASE3D2G_CONTROLLED_CANARY_REPORT.md
?? src/api/reservation_rollout_control.py
?? tests/test_var001_reservation_rollout_control.py
```

`git diff --stat` does not list untracked files. The untracked production
module `src/api/reservation_rollout_control.py` was read completely and is
reviewed below. Test and implementation-report files were not treated as
production authority.

```text
git diff --stat
 src/api/database.py                                | 110 ++++++++++++++++++-
 src/api/models.py                                  |  97 ++++++++++++++++
 src/api/public_task_admission.py                   | 122 ++++++++++++++++++++-
 src/api/reservation_rollout_readiness.py           |   4 +-
 src/api/routes.py                                  |   1 +
 src/api/routes_dsl.py                              |  97 ++++++++++++++--
 src/api/routes_reservation_diagnostics.py          | 100 ++++++++++++++++-
 src/api/schemas.py                                 |  12 ++
 tests/test_inv001_execution_isolation.py           |   7 +-
 tests/test_inv001_planning_policy.py               |  28 +++--
 tests/test_inv001_variant_planning.py              |   7 +-
 tests/test_var001_fingerprint_ledger.py            |   7 +-
 .../test_var001_historical_novelty_integration.py  |   7 +-
 tests/test_var001_public_reservation_activation.py |   9 +-
 14 files changed, 570 insertions(+), 38 deletions(-)
```

```text
git diff --check
exit code: 0
```

The warnings are line-ending notices (`LF will be replaced by CRLF`), not
whitespace errors.

Unchanged Reservation / Ledger production files that would have appeared in
`git status --short` if 2G had edited them — and did not:

- `src/api/planner_reservation.py`
- `src/api/reservation_lease.py`
- `src/api/fingerprint_ledger.py`
- historical / coverage / FP production modules

## B. Omission Semantics

Public DSL admission is centralized in
`routes_dsl._admit_dsl_public_task_admission` (`src/api/routes_dsl.py:216-266`).

Exact detection:

```python
explicit_mode = (
    "reservation_conflict_mode" in payload.model_fields_set
)
```

This is source-preserved Pydantic field explicitness, not value equality
against `"OFF"`. An omitted field remains absent from `model_fields_set`
even though the model default is `"OFF"`.

Resulting branches:

| Request shape | Detection | Admission call |
|---|---|---|
| omitted | `explicit_mode is False` | `admit_public_task(..., reservation_conflict_mode=OFF, reservation_mode_source=DEFAULT_OFF, reservation_mode_resolver=...)` |
| explicit `OFF` | `explicit_mode is True` and value `OFF` | `admit_public_task(..., reservation_conflict_mode=OFF, reservation_mode_source=EXPLICIT_OFF)` with **no** resolver |
| explicit `ENFORCE` | `explicit_mode is True` and value `ENFORCE` | `admit_public_task(..., reservation_conflict_mode=ENFORCE, reservation_mode_source=EXPLICIT_ENFORCE)` with **no** resolver |

The omitted resolver is attached only when
`_requests_authoritative_main_visual(payload)` is true
(`exact_main_visual` or `exact_main_visual_balanced`). Legacy omitted
requests keep `DEFAULT_OFF` and never call rollout control.

All three public DSL submission routes pass the FastAPI-injected
`RenderDSLRequest` object itself into `_admit_dsl_public_task_admission`
without `model_copy`, `model_validate`, or `RenderDSLRequest(**dump)`:

- `submit_dsl` (`src/api/routes_dsl.py:4376`, admission at `4499-4503`)
- `submit_manual` (`src/api/routes_dsl.py:4557`, admission at `4615-4619`)
- `render_dsl` (`src/api/routes_dsl.py:4666`, admission at `4759-4763`)

`_admit_dsl_public_task` (`src/api/routes_dsl.py:269-279`) is a
compatibility helper that also forwards the same `payload` object. The
three public routes do not use it.

`VAR3D2G-RF-23 PUBLIC_ROUTE_LOSES_MODE_EXPLICITNESS` is not reported.

Legacy `POST /tasks/submit` (`src/api/routes.py:85-92`) is not a DSL
omission path. It hard-codes `OFF` / `DEFAULT_OFF` / `legacy` and never
consults a client mode field.

## C. Explicit OFF

When `"reservation_conflict_mode" in payload.model_fields_set` and the
value is not `ENFORCE`, the function returns immediately through
`admit_public_task` with:

- `reservation_conflict_mode=payload.reservation_conflict_mode` (`OFF`)
- `reservation_mode_source="EXPLICIT_OFF"`
- no `reservation_mode_resolver`
- no `rollout_generation` / `rollout_bucket` / `rollout_canary_basis_points`

Therefore explicit OFF never:

- loads rollout control configuration
- evaluates readiness
- queries or trips a breaker
- computes canary health
- runs HMAC assignment

`resolve_omitted_reservation_mode` is imported at
`src/api/routes_dsl.py:117` and referenced only inside the omitted
closure at `src/api/routes_dsl.py:243-257`.

Atomic admission then persists `OFF` + `EXPLICIT_OFF` + null rollout
fields (`public_task_admission._claim_one`, lines 153-166). Application
validation (`_validate_rollout_metadata`, lines 130-139) rejects any
non-null rollout field on `EXPLICIT_OFF`.

## D. Explicit ENFORCE

The explicit branch also skips resolver construction. Explicit ENFORCE
therefore does not:

- enter `resolve_omitted_reservation_mode`
- load rollout control configuration
- read `ReservationRolloutBreaker`
- read readiness
- consult `kill_switch`

It still executes the existing B2 pre-admission contract. All three
public DSL routes call `_preflight_public_reservation_policy(payload)`
before admission:

- `submit_dsl` at `src/api/routes_dsl.py:4404`
- `submit_manual` at `src/api/routes_dsl.py:4565`
- `render_dsl` at `src/api/routes_dsl.py:4682`

`_preflight_public_reservation_policy` (`src/api/routes_dsl.py:414-437`):

1. returns immediately only when `payload.reservation_conflict_mode == OFF`
   (explicit OFF and omitted default OFF);
2. for ENFORCE, rejects non-authoritative policies with `422`;
3. calls `load_reservation_lease_configuration().require_configured()`;
4. on `ReservationLeaseConfigurationError`, raises `503` with
   `_RESERVATION_LEASE_CONFIGURATION_REQUIRED`.

There is no OFF fallback on this path. Invalid lease configuration
remains an authoritative B2 failure.

`VAR3D2G-RF-31 EXPLICIT_ENFORCE_READS_ROLLOUT_BREAKER_OR_KILL_SWITCH`
is not reported.

## E. Resolver Integration

Exact omitted call ordering for an authoritative-policy request:

1. FastAPI binds `RenderDSLRequest`; `model_fields_set` is preserved.
2. Route resolves `tenant_id = _authoritative_request_tenant(payload, request)`
   (`request_tenant_id` → `canonical_tenant_id`).
3. Route runs `_preflight_public_reservation_policy(payload)`.
   Omitted default `OFF` returns immediately (no B2 reject).
4. Route calls `_admit_dsl_public_task_admission(db, payload, tenant_id=tenant_id)`.
5. Omission is detected; a resolver closure is built that calls
   `resolve_omitted_reservation_mode(db.get_bind(), canonical_tenant=tenant_id, planning_policy=..., task_id=task_id)`.
6. `admit_public_task` validates the default `OFF` / `DEFAULT_OFF` decision,
   then enters the UUID claim loop (`_SERVER_ID_CLAIM_ATTEMPTS = 4`).
7. Each attempt:
   - `task_id = generator()` (`new_task_id()` → `str(uuid.uuid4())`);
   - `reservation_mode_resolver(task_id)` is invoked **with that candidate**;
   - `resolve_omitted_reservation_mode` evaluates config, allowlists,
     breaker, metrics, readiness, rollback, HMAC, then lease preflight;
   - `_validate_rollout_metadata` accepts or the resolver exception
     path falls back to `DEFAULT_OFF`;
   - `_claim_one` constructs one `VideoTask` and `session.commit()`.
8. On unique `video_tasks.task_id` collision, `_claim_one` rolls back,
   returns `0`, and the loop repeats from step 7 with a new ID.
9. On success, `PublicTaskAdmission` is returned with the **final**
   effective mode and source.
10. Route overwrites worker kwargs with
    `admission.reservation_conflict_mode`.
11. `_dispatch_claimed_public_task` registers `render_batch_worker`
    with `public_task_admitted=True` **after** the INSERT committed.

`VAR3D2G-RF-24` is evaluated in section F.

## F. Effective Mode Dispatch

Critical overwrite sites, all after admission:

```python
# submit_dsl  src/api/routes_dsl.py:4505-4507
_worker_kw["reservation_conflict_mode"] = (
    admission.reservation_conflict_mode
)

# submit_manual  src/api/routes_dsl.py:4621-4623
worker_kwargs["reservation_conflict_mode"] = (
    admission.reservation_conflict_mode
)

# render_dsl  src/api/routes_dsl.py:4765-4767
_worker_kw["reservation_conflict_mode"] = (
    admission.reservation_conflict_mode
)
```

Each route initially seeds kwargs from
`payload.reservation_conflict_mode` (the omitted default `OFF`), then
**replaces** that value with the admitted effective mode before
`_dispatch_claimed_public_task`.

`_dispatch_claimed_public_task` (`src/api/routes_dsl.py:282-296`)
forwards `**worker_kwargs` unchanged into `render_batch_worker`.

`render_batch_worker` (`src/api/routes_dsl.py:3971`) uses the
`reservation_conflict_mode` argument — not the request payload — to
decide ENFORCE controller construction (`src/api/routes_dsl.py:4084`).

No other public DSL submit/render route exists. There is no supported
path that dispatches request/default `OFF` after the admission row
recorded `ENFORCE`.

`VAR3D2G-RF-24 CANARY_EFFECTIVE_MODE_LOST_BEFORE_WORKER` is not reported.

## G. Fail-Safe Boundary

`admit_public_task` (`src/api/public_task_admission.py:209-252`):

```python
_validate_rollout_metadata(planning_policy, default_decision)  # not swallowed
for _ in range(_SERVER_ID_CLAIM_ATTEMPTS):
    task_id = generator()  # outside resolver try
    decision = default_decision
    if reservation_mode_resolver is not None:
        try:
            resolved = reservation_mode_resolver(task_id)
            ...
            _validate_rollout_metadata(planning_policy, resolved)
            decision = resolved
        except Exception:
            decision = default_decision
    video_task_id = _claim_one(...)  # outside resolver try
```

The `except Exception` wraps **only** resolver execution and resolver
result validation. It does **not** wrap:

- default-decision validation
- candidate ID generation
- `VideoTask` INSERT (`session.add` / `session.commit`)
- non-task-ID `IntegrityError` (re-raised by `_claim_one` at line 174)
- session / commit failure
- exhausted UUID collisions (`PUBLIC_TASK_ID_GENERATION_COLLISION`)

`_claim_one` (`src/api/public_task_admission.py:168-174`) rolls back and
returns `0` only for the exact SQLite string
`UNIQUE constraint failed: video_tasks.task_id`. Every other
`IntegrityError` and every non-`IntegrityError` commit failure
propagates.

The omitted route closure (`src/api/routes_dsl.py:246-257`) also
converts resolver exceptions to `DEFAULT_OFF`. That is still inside the
optional control layer.

`VAR3D2G-RF-25 ROLLOUT_FAILSAFE_OFF_MASKS_TASK_ADMISSION_FAILURE`
is not reported.

`VAR3D2G-RF-32 ROLLOUT_FAILSAFE_OFF_MASKS_NONROLLOUT_FAILURE`
is not reported.

## H. Resolver Validation

Accepted combinations enforced by
`_validate_rollout_metadata` (`src/api/public_task_admission.py:89-139`)
and by the fresh-schema CHECK
`ck_video_tasks_rollout_metadata_consistency`:

| source | effective mode | generation | bucket | basis points |
|---|---|---|---|---|
| `DEFAULT_OFF` | `OFF` | `NULL` | `NULL` | `NULL` |
| `EXPLICIT_OFF` | `OFF` | `NULL` | `NULL` | `NULL` |
| `EXPLICIT_ENFORCE` | `ENFORCE` | `NULL` | `NULL` | `NULL` |
| `ROLLOUT_CANARY` | `ENFORCE` | non-empty `str` `len<=64` | `int` `0..9999` | `int` `1..10000` and `bucket < basis` |

Additional rejects:

- unknown mode / source / policy
- `ENFORCE` + `legacy`
- bool used as an integer
- any non-null rollout field on a non-canary source

Invalid resolver output raises `PUBLIC_TASK_ROLLOUT_METADATA_INVALID`,
which `admit_public_task` converts to the already-validated
`default_decision` (`OFF` / `DEFAULT_OFF` / null metadata). Malformed
canary metadata cannot be committed through this admission path.

`resolve_omitted_reservation_mode` itself only constructs either
`_default_off_decision()` or a full canary tuple
(`ENFORCE`, `ROLLOUT_CANARY`, generation, bucket, basis).

## I. Atomic Admission

`_claim_one` constructs **one** `VideoTask` with every admission field
before the single `commit()`:

```python
task = VideoTask(
    task_id=task_id,
    prompt=prompt,
    batch_size=batch_size,
    status="queued",
    reservation_conflict_mode=decision.reservation_conflict_mode,
    planning_policy=planning_policy,
    reservation_mode_source=decision.reservation_mode_source,
    rollout_generation=decision.rollout_generation,
    rollout_bucket=decision.rollout_bucket,
    rollout_canary_basis_points=decision.rollout_canary_basis_points,
)
session.add(task)
session.commit()
```

There is no post-commit UPDATE of rollout fields in admission, routes,
control, or lifecycle. Dispatch happens only after `_claim_one`
returns a non-zero primary key.

ATOMIC_ROLLOUT_ADMISSION_SOURCE_PROVEN

## J. UUID Retry

Collision path (`src/api/public_task_admission.py:168-174` and `211-250`):

1. Candidate ID A is generated.
2. Resolver is called with A (HMAC input includes A).
3. `_claim_one` INSERTs A + decision A.
4. Unique `video_tasks.task_id` violation → `session.rollback()` → return `0`.
5. Loop continues: candidate ID B is generated.
6. Resolver is called with B (HMAC recomputed; bucket/generation decision
   from A is not reused).
7. Only B's metadata can commit.

`decision = default_decision` is reset at the start of every loop
iteration. A previous canary decision cannot leak into the next attempt
unless the resolver returns it again for the new ID.

## K. Metadata Immutability

Global production writes after admission:

| Field | Production writers |
|---|---|
| `reservation_conflict_mode` | INSERT in `_claim_one` only |
| `planning_policy` | INSERT in `_claim_one` only |
| `reservation_mode_source` | INSERT in `_claim_one`; additive backfill `UPDATE` only when the column is first added (section AG) |
| `rollout_generation` | INSERT in `_claim_one` only |
| `rollout_bucket` | INSERT in `_claim_one` only |
| `rollout_canary_basis_points` | INSERT in `_claim_one` only |

`transition_public_task_status` (`src/api/public_task_admission.py:273-285`)
updates only `status` and `finished_at`.

No breaker/rollback path updates an admitted task. No cancellation API
was added.

`VAR3D2G-RF-33 ROLLOUT_METADATA_MUTABLE_AFTER_ADMISSION` is not reported.

## L. Client Control Boundary

`RenderDSLRequest.reject_client_reservation_authority`
(`src/api/schemas.py:460-467`) rejects any request dict containing a
key from `_CLIENT_RESERVATION_AUTHORITY_FIELDS`
(`src/api/schemas.py:23-44`):

- `rollout_enabled`
- `rollout_generation`
- `tenant_allowlist`
- `canary_basis_points`
- `rollout_canary_basis_points`
- `assignment_secret`
- `rollout_bucket`
- `breaker_state`
- `breaker_tripped`
- `breaker_reset`
- `rollback_thresholds`
- `rollout_kill_switch`

plus the pre-existing Reservation authority identity/lease fields.

`reservation_mode_source` is not a declared request field and is not
read from the payload by any route. Admission sets it server-side from
`model_fields_set` or from the resolver. A client-supplied extra key is
not bound onto `RenderDSLRequest` (Pydantic default extra ignore) and
cannot become the admission source.

`RenderDSLRequest.reservation_conflict_mode` remains the only client
mode field and is still `Literal["OFF", "ENFORCE"]`. No public `AUTO`
mode exists.

## M. Rollout Configuration

Loader: `load_reservation_rollout_control_configuration`
(`src/api/reservation_rollout_control.py:338-404`).

All-or-none: if no `_ENVIRONMENT_KEYS` are present, return `None`
(rollout disabled). If a proper subset is present, raise
`ReservationRolloutControlConfigurationError`. There are no production
numeric defaults in the loader.

`ReservationRolloutControlConfiguration.__post_init__` then requires:

- `enabled` / `kill_switch` are real `bool` (not int)
- `rollout_generation` matches `_SAFE_GENERATION`
  (`[A-Za-z0-9._-]{1,64}`)
- tenant allowlist is a `frozenset[str]` of already-canonical IDs
- `assignment_secret` is a non-empty `str` (`repr=False`)
- window ∈ `{1h, 24h, 7d}`
- both canary basis-point fields are non-bool `int` in `0..10000`
- `minimum_canary_task_count` is non-bool `int` `>= 1`
- every rate is finite and in `0..1`

`_parse_tenant_allowlist` canonicalizes each entry and **rejects** any
raw token that is not already canonical
(`canonical_tenant_id(raw) != raw`). Empty allowlist is valid
(`""` → `frozenset()`), which makes every tenant ineligible.

Absent config: `resolve_omitted_reservation_mode` returns
`DEFAULT_OFF`. Invalid config is raised by the loader and caught by the
resolver's outer `except Exception` → `DEFAULT_OFF`. Explicit ENFORCE
never calls the loader.

## N. Deterministic Assignment

`deterministic_rollout_bucket` (`src/api/reservation_rollout_control.py:407-430`):

```python
message = "\x1f".join(
    (
        "reservation-rollout-v1",
        canonical_tenant,
        planning_policy,
        task_id,
        rollout_generation,
    )
).encode("utf-8")
digest = hmac.new(
    assignment_secret.encode("utf-8"),
    message,
    hashlib.sha256,
).digest()
return int.from_bytes(digest, "big") % 10000
```

Inputs and why `\x1f` boundaries cannot collide (`a|bc` ≠ `ab|c`):

| Component | Source | Allowed characters |
|---|---|---|
| domain/version | literal `reservation-rollout-v1` | no `U+001F` |
| canonical tenant | `canonical_tenant_id` | `[A-Za-z0-9_-]` after sanitization, then `normcase` |
| policy | resolver allowlist | `exact_main_visual` or `exact_main_visual_balanced` |
| server task ID | `str(uuid.uuid4())` | hex + hyphen |
| generation | config `_SAFE_GENERATION` | `[A-Za-z0-9._-]{1,64}` |

No component can contain the unit-separator byte, so join encoding is
unambiguous without extra length framing.

No `hash()`, no RNG, no timestamps. HMAC-SHA256 only.

Secret use (global search of `src/`):

- config field + loader (`assignment_secret=raw(...)`)
- HMAC key in `deterministic_rollout_bucket`

Not written to ORM, not included in status/readiness responses, not
interpolated into logs (`_safe_warning` logs only
`type(exc).__name__[:64]`), and excluded from dataclass `repr`
(`field(repr=False)`).

## O. Tenant Canonicalization

```python
# src/api/database.py:416-427
def canonical_tenant_id(tenant_id: str | None) -> str:
    raw_tenant_id = tenant_id or "default"
    safe_tenant_id = "".join(
        character
        for character in raw_tenant_id
        if character.isalnum() or character in ("_", "-")
    )
    return os.path.normcase(safe_tenant_id or "default")
```

`request_tenant_id` (`src/api/database.py:430-432`) is
`canonical_tenant_id(X-Local-User or "default")`.

`get_tenant_engine` (`src/api/database.py:435-457`) uses that same
canonical string as:

- `_tenant_engines` cache key
- physical path `./data/dopamatrix_{safe_tenant_id}.db`

`get_db` stores `db.info["tenant_id"] = tenant_id` after
`request_tenant_id`.

Rollout-control uses of tenant identity:

| Use | Source |
|---|---|
| omitted resolver `canonical_tenant` | route `_authoritative_request_tenant` → `request_tenant_id` |
| allowlist membership | config IDs must already equal `canonical_tenant_id(raw)` |
| HMAC input | same `canonical_tenant` argument |
| breaker / metrics / readiness queries | tenant-bound Engine/Session from that canonical identity |
| status API | `request_tenant_id(request)` (`src/api/routes_reservation_diagnostics.py:246`) |

No public DSL rollout decision uses raw `X-Local-User` after
canonicalization. Legacy `/tasks/submit` still copies the raw header
into the worker `tenant_id` argument, but that route never enters
rollout control and `get_tenant_engine` re-canonicalizes before any
engine open.

Platform `os.path.normcase` behavior after sanitization (only
`[A-Za-z0-9_-]` remain, so path-separator conversion cannot occur):

- Windows / case-insensitive paths: `normcase` lowercases.
  `TenantA` and `tenanta` become one cache key, one path string, and
  therefore one Engine. They cannot be two logical identities pointing
  at the same physical SQLite file.
- POSIX / case-sensitive paths: `normcase` is identity on those
  characters. `TenantA` and `tenanta` remain distinct files, matching
  the filesystem.

Existing Windows DB created as `dopamatrix_TenantA.db` is the same
physical file as `dopamatrix_tenanta.db`. The path-string case fold
does not redirect to a different database. POSIX path strings are
unchanged, so existing mixed-case files are not retargeted.

`VAR3D2G-RF-26 TENANT_CANONICALIZATION_PHYSICAL_DB_BOUNDARY_REGRESSION`
is not reported.

## P. Breaker Model

`ReservationRolloutBreaker` (`src/api/models.py:186-227`):

- table `reservation_rollout_breakers`
- unique identity: `(planning_policy, rollout_generation)`
- columns: `id`, `planning_policy`, `rollout_generation`,
  `reason_code`, `tripped_at`
- policy CHECK: exact / balanced only
- reason CHECK: the ten allowlisted codes in section R

Storage is tenant-local because the table lives in the tenant SQLite
file opened by `get_tenant_engine`. There is no tenant column and no
Reservation owner/execution identity.

## Q. Breaker Ordering

`resolve_omitted_reservation_mode` (`src/api/reservation_rollout_control.py:659-749`)
order after config/eligibility/`basis_points > 0`:

1. open a fresh `SessionLocal(bind=tenant engine)`
2. `_find_breaker(...)`
3. if breaker exists → `return _default_off_decision()` **before**
   metrics, readiness promotion, rollback evaluation, or HMAC
4. only then: metrics, generation-started count, readiness, rollback,
   then (after the session closes) HMAC and lease preflight

There is no DELETE/reset of an existing same-generation breaker.
Recovery cannot ignore it.

## R. Breaker Failure

Trip sites, both followed by an unconditional OFF return:

- readiness lost after the generation has started → `READINESS_LOST`
- `_rollback_reason(...)` non-`None` → that allowlisted reason

`_trip_breaker` (`src/api/reservation_rollout_control.py:607-641`):

- `INSERT ... ON CONFLICT DO NOTHING`
- `commit()`
- any exception → rollback (itself guarded) + `_safe_warning` +
  `return False`

The caller never inspects the boolean. Both call sites then
`return _default_off_decision()`. HMAC assignment is **after** the
`with SessionLocal()` block and is unreachable once a trip path
returns.

If the `with` block itself raises (session open/close), the outer
`except Exception` (`src/api/reservation_rollout_control.py:750-755`)
returns `DEFAULT_OFF`. Logger failure is absorbed by `_safe_warning`.

Current OFF is not conditional on successful persistence.

BREAKER_FAILURE_CANNOT_REENABLE_CURRENT_REQUEST_SOURCE_PROVEN

`VAR3D2G-RF-30 BREAKER_FAILURE_CAN_FALL_THROUGH_TO_CANARY_ASSIGNMENT`
is not reported.

Breaker persistence uses the short `SessionLocal` created inside
`resolve_omitted_reservation_mode`, bound to the tenant Engine. It is
not the `VideoTask` admission session in `_claim_one` and not a
`PlannerReservationController` session.

Allowlisted reason codes only (model CHECK + `_ROLLBACK_REASONS` +
`READINESS_LOST`). No raw exception text is stored; `_safe_warning`
logs only the exception class name.

## S. Generation Latch

`_find_breaker` keys solely on `(planning_policy, rollout_generation)`.
An existing row forces OFF for that generation. There is no production
`DELETE` / update / reset of `reservation_rollout_breakers`.

A new generation is a distinct unique key. The old breaker row remains.
Metrics recovery cannot unlatch the current generation.

## T. Canary Cohort

Authoritative query root is `VideoTask`
(`src/api/reservation_rollout_control.py:448-486`):

```python
.select_from(VideoTask)
.outerjoin(
    ReservationRunDiagnostic,
    ReservationRunDiagnostic.task_id == VideoTask.task_id,
)
.where(
    VideoTask.reservation_mode_source == "ROLLOUT_CANARY",
    VideoTask.planning_policy == planning_policy,
    VideoTask.rollout_generation == configuration.rollout_generation,
    VideoTask.created_at >= start,
    VideoTask.created_at <= end,
)
```

Explicit ENFORCE rows (`EXPLICIT_ENFORCE`) are excluded by
`reservation_mode_source == "ROLLOUT_CANARY"`.

`ReservationRunDiagnostic.task_id` is `unique=True`
(`src/api/models.py:157`), so the outer join is 1:1 and
`canaryTaskCount = len(rows)` equals the VideoTask cohort size.

## U. Diagnostic Intersection

Every rollback numerator is reduced from columns on those joined rows.
There is no independent `select(ReservationRunDiagnostic)` for
coverage, quality, or safety inside rollout control.

`VAR3D2G-RF-27 ROLLBACK_NUMERATOR_NOT_BOUND_TO_CANARY_COHORT`
is not reported.

## V. Rollback Denominators

`_rate(numerator, denominator)` returns `numerator / denominator` if
`denominator` else `None` (`src/api/reservation_rollout_control.py:433-434`).

Exact formulas from `_canary_metrics`:

| Metric | Formula | Zero denominator |
|---|---|---|
| `diagnosticRunCoverageRate` | `diagnostic_id is not None` / `canaryTaskCount` | `None` when `canaryTaskCount == 0` |
| `planningObservationCoverageRate` | `planning_observed` / `canaryTaskCount` | `None` when `canaryTaskCount == 0` |
| `terminalObservationCoverageRate` | terminal diagnostic ∩ terminal task / authoritative terminal canary tasks | `None` when no terminal canary tasks |
| `zeroPlanConflictRate` | `zero_plan_conflict` / planning observed | `None` when planning observed is 0 |
| `partialPlanRate` | `partial_plan` / planning observed | `None` when planning observed is 0 |
| `authorityLossRate` | `authority_lost` / `canaryTaskCount` | `None` when `canaryTaskCount == 0` |
| `terminalPersistFailureRate` | `terminal_persist_failed` / `canaryTaskCount` | `None` when `canaryTaskCount == 0` |
| `workerLeaseConfigFailureRate` | `worker_lease_config_failed` / `canaryTaskCount` | `None` when `canaryTaskCount == 0` |
| `cleanupWarningRate` | `cleanup_warning` / `canaryTaskCount` | `None` when `canaryTaskCount == 0` |

`_rollback_reason` returns `None` when `canaryTaskCount == 0`. A `None`
rate is skipped (`continue`) and is never compared as a numeric PASS.

`conflictTaskRate` and `reservationConflictCount` do not appear in
`reservation_rollout_control.py`. They are not rollback gates.

## W. Warm-Up

Status (`src/api/reservation_rollout_control.py:875-881`):

```python
state = (
    "WARMING_UP"
    if metrics["canaryTaskCount"] < configuration.minimum_canary_task_count
    else "CANARY_ACTIVE"
)
```

This is reached only after enabled, not kill-switched, allowlisted,
`basis_points > 0`, no breaker, readiness `READY_FOR_CONTROLLED_CANARY`,
and `_rollback_reason is None`.

Control-path promotion is stricter than the label: `_rollback_reason`
still evaluates whenever `canaryTaskCount > 0`, including below
`minimum_canary_task_count`. A present failing completeness/safety rate
trips the breaker and returns OFF. A missing (`None`) rate is not
treated as a healthy numeric PASS.

## X. Continuous Readiness

`_generation_canary_task_count` (`src/api/reservation_rollout_control.py:552-568`)
counts `ROLLOUT_CANARY` rows for the current policy + generation with
**no** `created_at` window. The Session is tenant-bound.

Resolver contract
(`src/api/reservation_rollout_control.py:709-717`):

- generation never started (`count == 0`) and readiness not READY →
  `DEFAULT_OFF`, **no** breaker insert
- generation has at least one historical/current canary and readiness
  not READY → `_trip_breaker(..., reason_code="READINESS_LOST")` then
  `DEFAULT_OFF`

## Y. Canary Preflight

After HMAC selects the canary bucket (`bucket < basis_points`):

```python
try:
    load_reservation_lease_configuration().require_configured()
except ReservationLeaseConfigurationError:
    return _default_off_decision()
```

(`src/api/reservation_rollout_control.py:739-742`)

Final omitted decision is `OFF` / `DEFAULT_OFF` with null canary
metadata. No ENFORCE `VideoTask` row is created.

Explicit ENFORCE never reaches this fallback; route `_preflight` still
surfaces `503 RESERVATION_LEASE_CONFIGURATION_REQUIRED`.

## Z. Rollout Fail-Safe

Omitted-request OFF fallback coverage:

| Failure | Path |
|---|---|
| absent config | `configuration is None` → OFF |
| disabled / kill switch / not allowlisted / unknown policy / `basis_points == 0` | early OFF |
| invalid config | loader raise → outer `except` → OFF |
| breaker query / metrics / readiness / assignment / preflight | outer `except` or explicit OFF return |
| breaker write / rollback / logger | `_trip_breaker` / `_safe_warning`; current request still OFF |
| resolver exception in admission | `admit_public_task` → `default_decision` |

Not covered — remain authoritative failures:

- general request validation (`RenderDSLRequest`, tenant mismatch, DSL parse)
- `_preflight` for explicit ENFORCE
- `VideoTask` INSERT / schema / non-ID IntegrityError / commit
- unrelated worker failures after dispatch

## AA. Status API

`GET /diagnostics/reservation/rollout-status`
(`src/api/routes_reservation_diagnostics.py:228-276`):

1. `load_reservation_rollout_control_configuration()`
2. `reservation_rollout_status(db, canonical_tenant=request_tenant_id(request), ...)`
3. validate into `ReservationRolloutStatusResponse`

`reservation_rollout_status` (`src/api/reservation_rollout_control.py:785-881`)
only reads configuration, `_canary_metrics`, `_find_breaker`, and
readiness. It never calls `_trip_breaker`, never INSERTs, never updates
tasks, and never writes environment/config.

Config/query failures return `503` with stable codes
`RESERVATION_ROLLOUT_CONTROL_CONFIGURATION_INVALID` or
`RESERVATION_ROLLOUT_STATUS_UNAVAILABLE`. Logs contain only exception
class names.

`VAR3D2G-RF-28 ROLLOUT_STATUS_QUERY_HAS_CONTROL_SIDE_EFFECT`
is not reported.

## AB. Status States

Deterministic precedence in `reservation_rollout_status`:

1. `configuration is None` → `DISABLED` (sparse payload, no generation)
2. `not configuration.enabled` → `DISABLED`
3. `kill_switch` → `KILL_SWITCHED`
4. tenant not allowlisted **or** `canaryBasisPoints == 0` → `NOT_ELIGIBLE`
5. breaker present → `AUTO_ROLLED_BACK`
6. readiness ≠ `READY_FOR_CONTROLLED_CANARY` → `NOT_ELIGIBLE`
7. `_rollback_reason is not None` → `NOT_ELIGIBLE` (read-only; no trip)
8. `canaryTaskCount < minimum` → `WARMING_UP`
9. else → `CANARY_ACTIVE`

There is no `DEFAULT_ON_FULL` state in the Literal or the function.

Clarifications:

- enabled rollout with 0 basis points → `NOT_ELIGIBLE`
- not-allowlisted tenant → `NOT_ELIGIBLE`
- non-READY readiness (and no breaker) → `NOT_ELIGIBLE`
- breaker present → `AUTO_ROLLED_BACK` (before readiness)

## AC. Kill Switch

`configuration.kill_switch` is consulted only inside
`resolve_omitted_reservation_mode` and `reservation_rollout_status`.
Explicit ENFORCE never loads this configuration.

A true kill switch returns `DEFAULT_OFF` for omitted automatic
promotion. Already admitted tasks are not queried or rewritten.

## AD. Running Task Preservation

Breaker/rollback only inserts a control row and returns OFF for
**subsequent omitted** requests. No production code updates
`reservation_conflict_mode` or rollout metadata on an existing
`VideoTask`. No task-cancellation path was introduced.

Lifecycle may move `queued → processing → completed|failed` only.

## AE. Readiness Boundary

Global production imports of `reservation_rollout_readiness`:

- `src/api/reservation_rollout_control.py` (resolver + status)
- `src/api/routes_reservation_diagnostics.py` (read-only GET `/readiness`)

`src/api/reservation_rollout_readiness.py` docstring states readiness
may feed rollout control and is never consumed by Planner or
Reservation authority.

No import exists in `planner_reservation.py`, `reservation_lease.py`,
confirmation, terminal fence, or release modules.

READINESS_TO_ROLLOUT_ONLY_SOURCE_PROVEN

## AF. Rollout Non-Authority

Global production reads of breaker / bucket / generation / mode source /
canary basis points are confined to:

- rollout control
- public admission persistence/validation
- additive schema / startup scan
- status API
- request-field rejection in `schemas.py`

`src/api/planner_reservation.py` and `src/api/reservation_lease.py`
contain no matches.

Downstream Reservation is constructed only after effective-mode
dispatch (`src/api/routes_dsl.py:4131-4135`) with
`logical_task_id=task_id`, a tenant session factory, and lease
configuration. It receives the effective mode implicitly (controller
created only when effective mode is `ENFORCE`) plus the server task ID.

ROLLOUT_CONTROL_STATE_NON_AUTHORITATIVE_SOURCE_PROVEN

`VAR3D2G-RF-34 READINESS_OR_ROLLOUT_STATE_ENTERS_RESERVATION_AUTHORITY`
is not reported.

## AG. Additive Task Schema

Fresh-schema table CHECK
`ck_video_tasks_rollout_metadata_consistency`
(`src/api/models.py:55-81`) encodes the four-way relationship in
section H.

Additive existing-DB evolution
(`ensure_video_task_rollout_metadata_schema`,
`src/api/database.py:208-287`):

- `ALTER TABLE ... ADD COLUMN` only
- new `reservation_mode_source` default `DEFAULT_OFF`
- if the source column was missing:
  `UPDATE video_tasks SET reservation_mode_source = 'EXPLICIT_ENFORCE' WHERE reservation_conflict_mode = 'ENFORCE'`
- OFF rows keep the column default `DEFAULT_OFF`
- rollout generation/bucket/basis remain NULL
- indexes created with `IF NOT EXISTS`

No destructive rebuild. No canary fabrication.

SQLite cannot attach the table-level cross-column CHECK to an already
created table through this additive path. Application validation plus
the startup scan (section AH) are the existing-DB invariant authority.

## AH. Startup Consistency Scan

Complete predicate (`src/api/database.py:344-390`):

```sql
SELECT 1 FROM video_tasks
WHERE reservation_conflict_mode IS NULL
   OR reservation_conflict_mode NOT IN ('OFF', 'ENFORCE')
   OR planning_policy IS NULL
   OR planning_policy NOT IN (
        'legacy', 'exact_main_visual', 'exact_main_visual_balanced'
      )
   OR reservation_mode_source IS NULL
   OR reservation_mode_source NOT IN (
        'DEFAULT_OFF', 'EXPLICIT_OFF',
        'EXPLICIT_ENFORCE', 'ROLLOUT_CANARY'
      )
   OR (
        reservation_mode_source = 'ROLLOUT_CANARY'
        AND (
            reservation_conflict_mode != 'ENFORCE'
            OR rollout_generation IS NULL
            OR length(rollout_generation) = 0
            OR rollout_bucket IS NULL
            OR rollout_bucket < 0 OR rollout_bucket >= 10000
            OR rollout_canary_basis_points IS NULL
            OR rollout_canary_basis_points <= 0
            OR rollout_canary_basis_points > 10000
            OR rollout_bucket >= rollout_canary_basis_points
        )
      )
   OR (
        reservation_mode_source = 'EXPLICIT_ENFORCE'
        AND (
            reservation_conflict_mode != 'ENFORCE'
            OR rollout_generation IS NOT NULL
            OR rollout_bucket IS NOT NULL
            OR rollout_canary_basis_points IS NOT NULL
        )
      )
   OR (
        reservation_mode_source IN ('DEFAULT_OFF', 'EXPLICIT_OFF')
        AND (
            reservation_conflict_mode != 'OFF'
            OR rollout_generation IS NOT NULL
            OR rollout_bucket IS NOT NULL
            OR rollout_canary_basis_points IS NOT NULL
        )
      )
LIMIT 1
```

This is the full cross-column relationship, not only per-column ranges.
Any hit raises `TaskRolloutMetadataSchemaError`.

`VAR3D2G-RF-29 ADDITIVE_SCHEMA_STARTUP_SCAN_MISSES_CROSS_COLUMN_INVARIANT`
is not reported.

## AI. Breaker Schema

`ReservationRolloutBreaker` is an application ORM table created by
`ModelBase.metadata.create_all` inside
`initialize_application_schema` (`src/api/database.py:397-406`).
Existing tenant DBs receive the new table additively. `evolve_schema`
only adds missing columns; it does not rebuild Reservation or Ledger
tables.

`src/api/fingerprint_ledger.py` still defines `LEDGER_SCHEMA_VERSION = 2`.
2G does not edit that module.

## AJ. Privacy

Public / operator surfaces reviewed:

- rollout-status response: generation label, basis points, aggregate
  rates, boolean `breakerTripped`, allowlisted `breakerReason`
- status/config errors: stable codes only
- control logs: exception class name, max 64 chars
- `VideoTaskResponse` / `VideoTaskStatusResponse`: no rollout bucket,
  source, generation, or secret
- `DSLSubmitResponse`: existing public `task_id` only

Forbidden items not present on the status API or control logs:

- assignment secret
- raw HMAC / digest
- per-task rollout bucket
- task IDs in aggregate status
- owner / execution IDs
- fingerprints
- SQL
- DB paths
- raw env values

## AK. No Auto Ramp

No production write assigns environment keys or mutates
`exact_main_visual_canary_basis_points` /
`exact_main_visual_balanced_canary_basis_points`. Successful canary
outcomes do not change percentage. Basis points change only when an
operator changes backend configuration.

## AL. Ledger V2 / Frozen Authority

`git status --short` shows no production edits to Planner Reservation
acquire / heartbeat / confirmation / terminal fencing / release,
Fingerprint Ledger, Historical policy, Coverage, or FP modules.

`LEDGER_SCHEMA_VERSION = 2` remains the ledger authority.

2G production edits are the rollout-control layer, additive task/breaker
schema, omitted-request admission/dispatch wiring, client-field
rejection, and the read-only status route. Reservation authority still
receives only effective mode plus the server task identity.

## AM. Findings

Watched IDs and source disposition:

| ID | Disposition |
|---|---|
| VAR3D2G-RF-23 PUBLIC_ROUTE_LOSES_MODE_EXPLICITNESS | not found |
| VAR3D2G-RF-24 CANARY_EFFECTIVE_MODE_LOST_BEFORE_WORKER | not found |
| VAR3D2G-RF-25 ROLLOUT_FAILSAFE_OFF_MASKS_TASK_ADMISSION_FAILURE | not found |
| VAR3D2G-RF-26 TENANT_CANONICALIZATION_PHYSICAL_DB_BOUNDARY_REGRESSION | not found |
| VAR3D2G-RF-27 ROLLBACK_NUMERATOR_NOT_BOUND_TO_CANARY_COHORT | not found |
| VAR3D2G-RF-28 ROLLOUT_STATUS_QUERY_HAS_CONTROL_SIDE_EFFECT | not found |
| VAR3D2G-RF-29 ADDITIVE_SCHEMA_STARTUP_SCAN_MISSES_CROSS_COLUMN_INVARIANT | not found |
| VAR3D2G-RF-30 BREAKER_FAILURE_CAN_FALL_THROUGH_TO_CANARY_ASSIGNMENT | not found |
| VAR3D2G-RF-31 EXPLICIT_ENFORCE_READS_ROLLOUT_BREAKER_OR_KILL_SWITCH | not found |
| VAR3D2G-RF-32 ROLLOUT_FAILSAFE_OFF_MASKS_NONROLLOUT_FAILURE | not found |
| VAR3D2G-RF-33 ROLLOUT_METADATA_MUTABLE_AFTER_ADMISSION | not found |
| VAR3D2G-RF-34 READINESS_OR_ROLLOUT_STATE_ENTERS_RESERVATION_AUTHORITY | not found |

Required source markers:

- ATOMIC_ROLLOUT_ADMISSION_SOURCE_PROVEN
- BREAKER_FAILURE_CANNOT_REENABLE_CURRENT_REQUEST_SOURCE_PROVEN
- READINESS_TO_ROLLOUT_ONLY_SOURCE_PROVEN
- ROLLOUT_CONTROL_STATE_NON_AUTHORITATIVE_SOURCE_PROVEN

PHASE3D2G_TARGETED_SOURCE_REVIEW_CLEAN
