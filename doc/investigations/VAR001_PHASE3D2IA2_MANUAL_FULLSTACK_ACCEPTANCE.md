# VAR-001 Phase 3D-2I-A2
# V1.5 Local Full-Stack Manual Acceptance Report

Role: read-only acceptance evidence consolidator. Production code, tests,
SQLite, assets, environment, and git history were not modified. Services
were not started. The only repository write is this artifact.

## 1. Executive Result

Local V1.5 RC full-stack manual acceptance **passed**.

Ordinary Vue AI-draft submissions omit `reservation_conflict_mode`.
That omission is the Controlled Canary input. With test-only backend
governance, an eligible omitted request was promoted to durable
`ROLLOUT_CANARY` / `ENFORCE`. With the kill switch on, a later omitted
request stayed `DEFAULT_OFF` / `OFF`, did not enter the ENFORCE
diagnostic cohort, and did not join the canary cohort.

Forced concurrent ENFORCE on a one-candidate fingerprint space admitted
two public tasks and allowed **exactly one** authoritative producer.

This is **not** Philippine seed acceptance, V1.5 GA authorization, or
100% global rollout approval.

**VAR001_PHASE3D2IA2_LOCAL_FULLSTACK_MANUAL_ACCEPTANCE_FINAL_PASS**

| Gate | Scenario | Expected | Observed | Result |
|---|---|---|---|---|
| Gate 1 | L1 same-batch UI smoke | Omitted UI, batch 2, balanced, unique children, real render | HTTP 202, server `task_id`, requested=2, accepted=2, `REQUEST_SATISFIED`, two FPs, two outputs, UI completed | PASS |
| Gate 2 | Explicit ENFORCE basic success | Reused payload + `ENFORCE` renders | HTTP 202, ENFORCE diagnostics cohort 1/1/0 conflicts | PASS |
| Gate 3 | Concurrent same-FP ENFORCE | One winner, one exhausted, no duplicate authority | Two 202s; accepted 1 vs 0; `RESERVATION_CONFLICT_EXHAUSTED`; diagnostics conflict=1, zero-plan=1 | PASS |
| Gate 4A | Readiness not configured | `NOT_CONFIGURED` / `KEEP_EXPLICIT_ONLY` | HTTP 200, empty gates, null uncomputed metrics | PASS |
| Gate 4B | Configured readiness | `READY_FOR_CONTROLLED_CANARY` from local ENFORCE evidence | 13 gates PASS, enforce=3, conflict=1, zero-plan rate ≈ 0.333 | PASS |
| Gate 5 | Ordinary UI omitted → canary | Promotion ON, durable `ROLLOUT_CANARY` | Task `a24a3922-…` completed ENFORCE / `ROLLOUT_CANARY` / gen `v15-gate5-local-001` / bucket 6425 / bps 10000; status `WARMING_UP` → `CANARY_ACTIVE` | PASS |
| Gate 6 | Kill switch omitted → OFF | Fail-safe OFF, no canary metadata, not in ENFORCE/canary cohorts | Task `28a9522a-…` completed OFF / `DEFAULT_OFF` / null rollout fields; diagnostics still enforce=4; status `KILL_SWITCHED`; canaryTaskCount=1 | PASS |

## 2. Scope

This report consolidates **already performed** Gate 1–6 manual runtime
evidence and cross-checks durable claims against:

1. current source
2. tenant SQLite `data/dopamatrix_v15_acceptance.db` (URI `mode=ro`)
3. existing final phase artifacts
4. the operator evidence manifest in the 2I-A2 prompt

It is **not** a re-audit of frozen Reservation architecture, lease
renewal, expiry takeover, fencing, or SQLite writer contention.

Prior artifacts read for boundary, not re-litigation:

- `doc/investigations/VAR001_PHASE3D2IA2_UI_API_WIRING_AUDIT.md`
- `doc/investigations/VAR001_PHASE3D2G_CONTROLLED_CANARY_REPORT.md`
- `doc/investigations/VAR001_PHASE3D2G_TARGETED_SOURCE_REVIEW.md`
- `doc/investigations/VAR001_PHASE3D2G_GENERATION_INVARIANT_FIX_REPORT.md`
- `doc/investigations/VAR001/phase3/VAR001_PHASE3D2F_TARGETED_SOURCE_REVIEW.md`
- `doc/investigations/VAR001_PHASE3D2H_V15_FORWARD_COMPATIBILITY_AUDIT.md`
- `doc/investigations/VAR001_PHASE3D2IA_V15_RC_BACKUP_ACCEPTANCE_REPORT.md`
- `doc/operations/DOPAMATRIX_V15_PHILIPPINE_SEED_CANARY_RUNBOOK.md`

## 3. Frozen Architecture Boundaries

Unchanged and not reopened:

- Reservation acquire / renew / heartbeat / confirm / terminal fence /
  release
- Task Identity, owner-attempt identity, execution identity
- FP-001 and Ledger V2
- Historical novelty remains non-authoritative (not L3)
- Public admission `model_fields_set` omission vs explicit OFF/ENFORCE
- Readiness feeds **rollout control only**, not Reservation authority
- Vue ordinary workflow has no rollout controls (intentional)

## 4. Environment and Evidence Method

- Tenant: `v15_acceptance`
- Physical DB: `data/dopamatrix_v15_acceptance.db` (WAL present; opened
  `file:...?mode=ro` plus `PRAGMA query_only=ON`)
- Planning policy used throughout gates: `exact_main_visual_balanced`
- UI path: Matrix Factory / Workspace → AI Draft → Tactical Board →
  Confirm and Render → `POST /api/v1/tasks/submit-dsl`
- HEAD at artifact time: `a518aa1` (`feat(var-001): prepare v1.5 rc backup and restore safety`)
- Lease / readiness / rollout values used in the manual session were
  **process-local TEST-ONLY**. They are not production defaults.

SQLite cross-check was performed with the backend not started by this
phase. Durable rows for the two named Gate 5/6 task IDs match the
manifest. No assignment secret is recorded.

## 5. Gate 1 — L1 Same-Batch UI Smoke

Manual: ordinary Vue, `batch_size=2`,
`variant_planning_policy=exact_main_visual_balanced`,
`reservation_conflict_mode` omitted, no client `task_id`/`session_id`.

Result: HTTP 202, server-owned `task_id`, planner `requested_count=2`,
`accepted_count=2`, `termination_reason=REQUEST_SATISFIED`, two distinct
FP-001 fingerprints, two child executions, two rendered outputs, UI
completed.

Durable context: tenant `video_tasks` contains completed
`exact_main_visual_balanced` batch-2 rows with `DEFAULT_OFF` / `OFF`
before any ENFORCE admit (ordinary omitted UI before rollout config).
This report does not invent which of those UUIDs is the operator’s Gate 1
card.

Manual classification:
`VAR001_PHASE3D2IA2_MANUAL_GATE1_L1_UI_SMOKE_PASS`

## 6. Gate 2 — Explicit ENFORCE

Test-only lease: `RESERVATION_LEASE_TTL_SECONDS=30`,
`RESERVATION_HEARTBEAT_INTERVAL_SECONDS=5`.

Same public body as the successful UI payload, plus
`reservation_conflict_mode=ENFORCE`. HTTP 202, real planner/worker/render.

Diagnostics after Gate 2 (manifest): enforce=1, planning observed=1,
completed=1, failed=0, reservationConflictCount=0, authorityLoss=0,
terminalPersistFailure=0, workerLeaseConfigFailure=0, cleanupWarning=0.

Durable: `88e0e3af-33c8-47e2-8b61-ef56be4749d0` is
`EXPLICIT_ENFORCE` / `ENFORCE` / completed / batch 2, with a matching
diagnostic row (no conflict flags).

Manual classification:
`VAR001_PHASE3D2IA2_MANUAL_GATE2_EXPLICIT_ENFORCE_BASIC_SUCCESS_PASS`

## 7. Gate 3 — Concurrent Same-FP Contention

Forced one-candidate space (Hook/Context/Build each one locked asset),
`candidate_space_size=1`, `batch_size=1`, explicit `ENFORCE`, two
concurrent public admissions. Both HTTP 202 with distinct server IDs.

Winner: `accepted_count=1`, `REQUEST_SATISFIED`.
Loser: `accepted_count=0`, `RESERVATION_CONFLICT_EXHAUSTED`.
Loser did not launch duplicate authoritative production for that FP.

Durable pair:

- `b9c2b4be-473c-4161-83c0-8387e4d4a197` — `EXPLICIT_ENFORCE`, completed,
  batch 1, diagnostic conflict flags 0
- `bef6da1b-fd7e-4f04-ae83-5fbd1ae42a8a` — `EXPLICIT_ENFORCE`, failed,
  batch 1, `had_reservation_conflict=1`, `reservation_conflict_count=1`,
  `zero_plan_conflict=1`, `terminal_status=failed`

Post-Gate 3 diagnostics (manifest) match this ENFORCE trio: enforce=3,
completed=2, failed=1, planningObserved=3, reservationConflictCount=1,
conflictTaskCount=1, zeroPlanConflictCount=1, partial=0, authorityLoss=0.

Manual classification:
`VAR001_PHASE3D2IA2_MANUAL_GATE3_L2_CONCURRENT_DUPLICATE_PROTECTION_PASS`

## 8. Gate 4A — Readiness Fail-Safe

Before readiness env: `GET /api/v1/diagnostics/reservation/readiness?planning_policy=exact_main_visual_balanced`
returned HTTP 200, `state=NOT_CONFIGURED`,
`recommendation=KEEP_EXPLICIT_ONLY`, `gates=[]`, uncomputed metrics null.

Source: `load_reservation_rollout_readiness_configuration()` is `None` →
`_not_configured_result`.

Manual classification:
`VAR001_PHASE3D2IA2_MANUAL_GATE4_READINESS_NOT_CONFIGURED_FAILSAFE_PASS`

## 9. Gate 4B — Configured Readiness

Test-only readiness required enforce≥3, planning observed≥3, conflict≥1,
coverage rates 1.0, max zero-plan 0.34, other max rates 0.

Observed (manifest): 13 gates PASS, `leaseConfigurationReady=true`,
authoritativeEnforce=3, planningObserved=3, conflictTaskCount=1,
`zeroPlanConflictRate=0.3333333333333333`,
`state=READY_FOR_CONTROLLED_CANARY`,
`recommendation=ELIGIBLE_FOR_CONTROLLED_DEFAULT_ON_CANARY`.

That rate is 1/3 from the Gate 3 loser among three ENFORCE planning
observations — consistent with durable diagnostics.

Manual classification:
`VAR001_PHASE3D2IA2_MANUAL_GATE4B_CONFIGURED_READINESS_PASS`

## 10. Gate 5 — Controlled Canary Promotion

Test-only rollout: enabled, generation `v15-gate5-local-001`, allowlist
`v15_acceptance`, exact bps 0, balanced bps **10000**, kill switch false,
`minimum_canary_task_count=1`, rollback window `1h`. Assignment secret
existed and is **not** recorded.

Preflight: readiness `READY_FOR_CONTROLLED_CANARY`; rollout
`WARMING_UP`, `canaryTaskCount=0`, bps 10000, breaker false.

Ordinary Vue payload: `batch_size=2`, `tenant_id=v15_acceptance`,
`variant_planning_policy=exact_main_visual_balanced`. **Absent:**
`reservation_conflict_mode`, `reservation_mode_source`,
`rollout_generation`, `rollout_bucket`, `rollout_canary_basis_points`,
assignment secret, `task_id`, `session_id`.

HTTP 202, task `a24a3922-8e0e-4c7e-b4cb-9bccc3a71211`, completed with
two rendered outputs.

Read-only SQLite for that row (this phase):

| Field | Durable value |
|---|---|
| status | `completed` |
| reservation_conflict_mode | `ENFORCE` |
| planning_policy | `exact_main_visual_balanced` |
| reservation_mode_source | `ROLLOUT_CANARY` |
| rollout_generation | `v15-gate5-local-001` |
| rollout_bucket | `6425` |
| rollout_canary_basis_points | `10000` |
| batch_size | `2` |

`6425 < 10000` matches the source canary assignment rule
(`bucket >= basis_points` → OFF). Diagnostic row exists
(`planning_observed=1`, no conflict/safety flags, `terminal_status=completed`).

Post-task (manifest): enforce cohort 4; canary status `CANARY_ACTIVE`,
`canaryTaskCount=1`, generation `v15-gate5-local-001`, breaker false,
readiness still `READY_FOR_CONTROLLED_CANARY`.

SQLite now: ENFORCE tasks=4, `ROLLOUT_CANARY` rows=1, breakers empty.

Manual classification:
`VAR001_PHASE3D2IA2_MANUAL_GATE5_CONTROLLED_CANARY_RUNTIME_PASS`

## 11. Gate 6 — Kill Switch Fail-Safe OFF

Only test-only `RESERVATION_ROLLOUT_KILL_SWITCH` set true. Preflight
rollout `KILL_SWITCHED`, `canaryTaskCount=1`, breaker false, same
generation.

Ordinary Vue omitted request again. HTTP 202, task
`28a9522a-68a7-4a9b-b768-f178bdb2fa3b`, completed with two outputs.

Read-only SQLite:

| Field | Durable value |
|---|---|
| status | `completed` |
| reservation_conflict_mode | `OFF` |
| planning_policy | `exact_main_visual_balanced` |
| reservation_mode_source | `DEFAULT_OFF` |
| rollout_generation | NULL |
| rollout_bucket | NULL |
| rollout_canary_basis_points | NULL |
| batch_size | `2` |

No `reservation_run_diagnostics` row for this task. ENFORCE diagnostic
aggregates remain 4 / planning 4 / conflict 1 / zero-plan 1 / safety 0.

Post-task rollout (manifest) stayed `KILL_SWITCHED`, `canaryTaskCount=1`.
Gate 5 row was **not** rewritten.

Manual classification:
`VAR001_PHASE3D2IA2_MANUAL_GATE6_KILL_SWITCH_FAILSAFE_OFF_PASS`

## 12. Gate 5 vs Gate 6 Durable Metadata Contrast

| Dimension | Gate 5 | Gate 6 |
|---|---|---|
| Client reservation mode | omitted | omitted |
| Planning policy | `exact_main_visual_balanced` | `exact_main_visual_balanced` |
| Kill switch | false | true |
| Server effective mode | `ENFORCE` | `OFF` |
| reservation_mode_source | `ROLLOUT_CANARY` | `DEFAULT_OFF` |
| rollout_generation | `v15-gate5-local-001` | NULL |
| rollout_bucket | `6425` | NULL |
| rollout_canary_basis_points | `10000` | NULL |
| ENFORCE diagnostic cohort | yes (row present) | no (no diagnostic row; enforce count unchanged) |
| Canary cohort | yes (`ROLLOUT_CANARY`, later `CANARY_ACTIVE` count 1) | no (canary count stayed 1 = Gate 5 only) |
| Render result | completed, two outputs | completed, two outputs |

This table is the key durable acceptance contrast.

## 13. Reservation Diagnostics Evidence

Source: `GET /api/v1/diagnostics/reservation/summary` reads ENFORCE
runs only.

Durable `reservation_run_diagnostics` (4 rows = 4 ENFORCE tasks):

| task_id prefix | source | terminal | conflict | zero-plan |
|---|---|---|---|---|
| `88e0e3af` | EXPLICIT_ENFORCE | completed | 0 | 0 |
| `bef6da1b` | EXPLICIT_ENFORCE | failed | 1 | 1 |
| `b9c2b4be` | EXPLICIT_ENFORCE | completed | 0 | 0 |
| `a24a3922` | ROLLOUT_CANARY | completed | 0 | 0 |

Aggregates: planning_observed=4, reservation_conflict_count=1,
zero_plan=1, partial=0, authority_loss=0, terminal_persist=0,
worker_cfg=0, cleanup=0. Matches post-Gate 5/6 manifest
(`enforceTaskCount=4`, Gate 6 not added).

## 14. Readiness Evidence

Gate 4A: not configured → fail-safe keep explicit only.

Gate 4B: configured against the three ENFORCE tasks then present;
READY because evidence gates passed including the one conflict.

After Gate 5 the ENFORCE evidence set grew to 4; readiness remained
READY (manifest). Readiness does not write Reservation authority.

## 15. Rollout Status Evidence

Source `reservation_rollout_status` is read-only (no breaker trip).

Manual sequence:

- Gate 5 pre: `WARMING_UP`, canaryTaskCount=0, bps=10000
- Gate 5 post: `CANARY_ACTIVE`, canaryTaskCount=1
- Gate 6: `KILL_SWITCHED` (kill switch short-circuits before readiness
  in source), canaryTaskCount remains 1

`minimum_canary_task_count=1` explains warmup → active after the first
`ROLLOUT_CANARY` admit.

## 16. UI / API Contract

Current source still supports:

**A.** `WorkspaceView.blindFission` payload has no
`reservation_conflict_mode` key. AI 起草 sets
`exact_main_visual_balanced`.

**B.** `_admit_dsl_public_task_admission` uses
`"reservation_conflict_mode" in payload.model_fields_set`. Omitted ≠
explicit OFF.

**C.** `_ALLOWED_POLICIES` includes `exact_main_visual_balanced`.

**D.** `ROLLOUT_CANARY` decision sets effective `ENFORCE` plus generation,
bucket, basis. Admission `_validate_rollout_metadata` requires
CANARY ⇒ ENFORCE and complete metadata.

**E.** `DEFAULT_OFF` ⇒ OFF and all rollout fields null (validator +
CHECK on `video_tasks`).

**F.** `resolve_omitted_reservation_mode` returns `_default_off_decision()`
when `kill_switch` is true. Explicit path never installs the resolver.

**G.** Kill switch is evaluated at **new omitted admit** time. Source does
not rewrite existing `VideoTask` rows. SQLite: Gate 5 still CANARY after
Gate 6.

**H.** Explicit ENFORCE uses `model_fields_set` and
`admit_public_task(..., reservation_conflict_mode=payload...)` with no
rollout resolver.

**I.** Rollout-status route docstring: without mutation.

**J.** Rollout control calls readiness; planner receives only effective
mode (`reservation_rollout_control.py` module contract).

**K.** Wiring audit: no Vue canary controls required for ordinary
operator flow.

## 17. Restart and Persistence Observation

Backend was restarted between some manual gates to load process-local
test configuration. Accumulated tenant ENFORCE diagnostics survived and
were later consumed by Readiness (Gate 4B used enforce=3 after Gate 3).

This supports: **tenant-local operational evidence is durable**;
**process-local TEST configuration is ephemeral**.

This is **not** a formal crash-recovery test.

## 18. Safety Results

Across the ENFORCE diagnostic cohort used for this acceptance:

- authorityLossCount = 0
- terminalPersistFailureCount = 0
- workerLeaseConfigFailureCount = 0
- cleanupWarningCount = 0
- partialPlanCount = 0
- one expected zero-plan conflict on the Gate 3 loser only

No breaker row is persisted.

## 19. L1 vs L2 Functional Conclusion

**L1 same-batch uniqueness** is one public task with multiple planned
children. Accepted planning fingerprints **inside that batch** must be
unique. Gate 1 exercised that on the real UI (batch 2, two FPs, two
outputs).

**L2 Reservation Authority** is about **different concurrently running
public tasks**. The hard question: may two independent active owners
authoritatively produce the **same** planning fingerprint **at the same
time**? Gate 3’s forced single-FP contention proved **NO**.

Reservation Authority is **not** historical deduplication. It does
**not** mean a video generated yesterday or last week can never be
generated again. That belongs to future **L3 Historical Creative Memory**.

## 20. Controlled Canary Product Conclusion

Absence of Vue rollout controls is **intentional** for V1.5 ordinary
operation.

Normal operator flow remains:

AI Draft → Tactical Board → Render

Server-side governance decides whether an omitted eligible request
stays `DEFAULT_OFF` or is promoted to `ROLLOUT_CANARY` / `ENFORCE`.

Gate 5 proves promotion ON. Gate 6 proves kill-switch OFF fallback.

This is server-side operational governance, not an unfinished
customer-facing UI control.

## 21. What This Manual Acceptance Does Not Prove

Manual 2I-A2 does **not** replace automated Reservation suites for:

- lease renewal
- expiry takeover
- stale-owner fencing
- terminal fencing
- whole-task authority loss
- SQLite writer contention
- HMAC assignment across mixed basis-point values
- Philippine production thresholds

It proves the **user-realistic integration surface**:

Vue/UI → HTTP → public admission → planner → Reservation mode →
real render → SQLite truth → diagnostics → rollout control.

## 22. Test-Only Configuration Boundary

All manual values for lease TTL/heartbeat, readiness thresholds,
rollout generation `v15-gate5-local-001`, 10000 balanced basis points,
assignment secret, and kill switch were **process-local TEST-ONLY**.

They were **not** written as production defaults. The assignment secret
must never appear in this artifact. These thresholds are **not**
Philippine seed production policy.

## 23. Findings

No `VAR3D2IA2-RF-11` … `RF-18` with evidence.

- RF-11: ordinary UI omitted; Gate 5 still CANARY. Not client ENFORCE.
- RF-12: Gate 6 durable metadata is DEFAULT_OFF with null rollout fields.
- RF-13: Gate 6 has zero diagnostic rows; enforce count stayed 4.
- RF-14: Gate 5 durably `ROLLOUT_CANARY`.
- RF-15: warmup → `CANARY_ACTIVE` after the first canary task.
- RF-16: Gate 3 loser zero-plan failed; winner completed; one conflict.
- RF-17: readiness used post-restart durable ENFORCE evidence (Gate 4B).
- RF-18: UI/API payloads omitted internal rollout fields; client
  authority keys remain schema-rejected.

## 24. Release Classification

**LOCAL V1.5 RC FULL-STACK MANUAL ACCEPTANCE**

Not:

- Philippine production seed acceptance
- V1.5 GA authorization
- 100% global rollout approval

## 25. Next Phase Boundary

Next: **Phase 3D-2I-B Philippine Seed Acceptance**.

2I-B must choose actual seed configuration, execute
backup-before-canary, follow the operator runbook, and record production
evidence thresholds. This report does not invent those values.

Diagnostic URLs for operators are the **source** paths
`/api/v1/diagnostics/reservation/{summary,readiness,rollout-status}`
(the seed runbook’s `/api/v1/reservation-diagnostics/...` prefix is not
the mounted router).

## 26. Final Git Status

```text
git branch --show-current
feature/var-001-variation-policy

git rev-parse HEAD
a518aa1f24bf94893821c0c465c05d5bb2e7aaf4
```

Pre-existing untracked wiring audit was not altered.

```text
git status --short
?? doc/investigations/VAR001_PHASE3D2IA2_MANUAL_FULLSTACK_ACCEPTANCE.md
?? doc/investigations/VAR001_PHASE3D2IA2_UI_API_WIRING_AUDIT.md
```

Proof markers:

- L1_REAL_UI_SAME_BATCH_UNIQUENESS_PROVEN
- EXPLICIT_ENFORCE_REAL_RUNTIME_PROVEN
- CONCURRENT_SAME_FP_DUPLICATE_AUTHORITY_PREVENTED
- READINESS_NOT_CONFIGURED_FAILSAFE_PROVEN
- CONFIGURED_READINESS_REAL_EVIDENCE_PROVEN
- ORDINARY_UI_RESERVATION_FIELD_OMISSION_PROVEN
- SERVER_SIDE_CANARY_PROMOTION_PROVEN
- ROLLOUT_CANARY_DURABLE_METADATA_PROVEN
- CANARY_WARMUP_TO_ACTIVE_PROVEN
- KILL_SWITCH_OMITTED_TO_DEFAULT_OFF_PROVEN
- KILL_SWITCH_TASK_EXCLUDED_FROM_ENFORCE_COHORT_PROVEN
- KILL_SWITCH_TASK_EXCLUDED_FROM_CANARY_COHORT_PROVEN
- MANUAL_E2E_SAFETY_METRICS_CLEAN
- LOCAL_FULLSTACK_MANUAL_ACCEPTANCE_PROVEN

VAR001_PHASE3D2IA2_LOCAL_FULLSTACK_MANUAL_ACCEPTANCE_FINAL_PASS
