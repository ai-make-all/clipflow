# DopaMatrix V1.5 Philippine Seed Canary Runbook

## Status

This document prepares Phase 3D-2I-B. It has not been executed against a real
Philippine production tenant and is not evidence of Philippine production
acceptance.

Product release status and a tenant's Reservation canary exposure are
separate decisions. A tenant may deliberately remain at a controlled
partial canary exposure; universal 100% Default-ON is not a V1.5 GA
requirement. Any actual exposure percentage remains
`TO_BE_DECIDED_BY_2I_B_SEED_POLICY`.

Ordinary seed-operator creative work stays:

AI Draft → Tactical Board → Render

Controlled Canary is server-side operational governance. Do not require a
customer-facing Reservation, canary, basis-point, generation, readiness,
breaker, or kill-switch UI control.

Reservation Authority (L2) coordinates concurrently active public tasks. It
is not same-batch uniqueness (L1) and is not historical duplicate prevention
(future L3). L2 does not mean a video generated yesterday cannot be generated
again.

Numeric seed policy (exposure %, sample size, rate thresholds, observation
windows, lease TTL/heartbeat) is `TO_BE_DECIDED_BY_2I_B_SEED_POLICY`. Do not
copy Phase 3D-2I-A2 local manual-acceptance test values into Philippine
defaults.

## Operator identity and diagnostic routes

Tenant routing for these operator APIs is the request header `X-Local-User`.
The server canonicalizes it with the same `canonical_tenant_id` used for
tenant SQLite. Do not send tenant identity as a query parameter or JSON body
field on these endpoints.

Current mounted routes (`main.py` prefix `/api/v1` + router
`/diagnostics/reservation`):

```text
GET /api/v1/diagnostics/reservation/summary?window=24h
GET /api/v1/diagnostics/reservation/readiness?planning_policy=<policy>
GET /api/v1/diagnostics/reservation/rollout-status?planning_policy=<policy>
```

`<policy>` must be exactly `exact_main_visual` or
`exact_main_visual_balanced`. `window` is optional on summary and must be one
of `1h`, `24h`, `7d`, `30d` (default `24h`).

All three GETs are read-only. They do not admit tasks, trip breakers, or
change Reservation authority.

Example (replace origin and tenant; never log secrets):

```text
curl -H "X-Local-User: <canonical-tenant>" ^
  "http://127.0.0.1:8000/api/v1/diagnostics/reservation/readiness?planning_policy=exact_main_visual_balanced"

curl -H "X-Local-User: <canonical-tenant>" ^
  "http://127.0.0.1:8000/api/v1/diagnostics/reservation/rollout-status?planning_policy=exact_main_visual_balanced"

curl -H "X-Local-User: <canonical-tenant>" ^
  "http://127.0.0.1:8000/api/v1/diagnostics/reservation/summary?window=24h"
```

Readiness `state` values: `NOT_CONFIGURED`, `INSUFFICIENT_EVIDENCE`,
`BLOCKED`, `READY_FOR_CONTROLLED_CANARY`.
Recommendations: `KEEP_EXPLICIT_ONLY` or
`ELIGIBLE_FOR_CONTROLLED_DEFAULT_ON_CANARY`.
`NOT_CONFIGURED` means readiness env is absent; keep omitted requests
explicit-only until 2I-B policy configures it.

Rollout-status `state` values: `DISABLED`, `NOT_ELIGIBLE`, `WARMING_UP`,
`CANARY_ACTIVE`, `KILL_SWITCHED`, `AUTO_ROLLED_BACK`.

Minimum seed-decision fields:

- summary: `enforceTaskCount`, `planningObservedTaskCount`,
  `completedTaskCount`, `failedTaskCount`, `conflictTaskCount`,
  `reservationConflictCount`, `zeroPlanConflictCount`,
  `zeroPlanConflictRate`, `partialPlanCount`, `authorityLossCount`,
  `terminalPersistFailureCount`, `workerLeaseConfigFailureCount`,
  `cleanupWarningCount`
- readiness: `state`, `recommendation`, `gates`,
  `leaseConfigurationReady`, `authoritativeEnforceTaskCount`
- rollout-status: `state`, `rolloutGeneration`, `canaryBasisPoints`,
  `readinessState`, `breakerTripped`, `breakerReason`, `canaryTaskCount`

## Preconditions

1. Select one Philippine seed tenant using a safe operator label. Do not put
   tenant business content or task IDs in the acceptance summary.
2. Select one supported planning policy:
   `exact_main_visual` or `exact_main_visual_balanced`.
3. Record the reviewed application commit/tag and a new rollout generation.
4. Create and independently verify a complete tenant backup using
   `DOPAMATRIX_V15_BACKUP_RESTORE_RUNBOOK.md` **before** enabling seed canary
   (allowlist / enabled / non-zero basis points / kill switch inactive).
5. Confirm the tenant's authoritative asset references are complete.
6. Confirm Reservation lease TTL and heartbeat environment keys are set to
   the 2I-B seed policy values (`TO_BE_DECIDED_BY_2I_B_SEED_POLICY`). Valid
   configuration requires both keys; heartbeat must not exceed one third of
   TTL.
7. Query `GET /api/v1/diagnostics/reservation/readiness?planning_policy=...`
   with header `X-Local-User: <canonical-tenant>` and record every gate.
8. Query `GET /api/v1/diagnostics/reservation/rollout-status?planning_policy=...`
   with the same header and record `state`, kill-switch implication
   (`KILL_SWITCHED`), `breakerTripped`, `rolloutGeneration`,
   `readinessState`, and `canaryBasisPoints`.
9. Query `GET /api/v1/diagnostics/reservation/summary?window=...` with the
   same header and record the minimum seed-decision fields above.
10. Confirm the tenant appears on `RESERVATION_ROLLOUT_TENANT_ALLOWLIST` and
    the selected policy has the intended basis points **only after** backup
    verification succeeded. Do not print, screenshot, commit, or paste the
    assignment secret into any artifact.

Do not proceed when readiness is unavailable or not
`READY_FOR_CONTROLLED_CANARY` (unless 2I-B policy explicitly stays
explicit-only), the kill switch is active, a breaker is latched for the
generation, backup verification failed, or lease configuration is invalid.

## Configuration authority

All of the following are backend environment keys. Values are
`TO_BE_DECIDED_BY_2I_B_SEED_POLICY`. Rollout control and readiness each
require their **complete** key set; a partial set is invalid.

Lease:

- `RESERVATION_LEASE_TTL_SECONDS`
- `RESERVATION_HEARTBEAT_INTERVAL_SECONDS`

Rollout control:

- `RESERVATION_ROLLOUT_CONTROL_ENABLED`
- `RESERVATION_ROLLOUT_GENERATION`
- `RESERVATION_ROLLOUT_TENANT_ALLOWLIST`
- `RESERVATION_ROLLOUT_EXACT_CANARY_BASIS_POINTS`
- `RESERVATION_ROLLOUT_BALANCED_CANARY_BASIS_POINTS`
- `RESERVATION_ROLLOUT_ASSIGNMENT_SECRET`
- `RESERVATION_ROLLOUT_KILL_SWITCH`
- `RESERVATION_ROLLOUT_ROLLBACK_WINDOW`
- `RESERVATION_ROLLOUT_MINIMUM_CANARY_TASKS`
- `RESERVATION_ROLLOUT_ROLLBACK_MINIMUM_DIAGNOSTIC_COVERAGE_RATE`
- `RESERVATION_ROLLOUT_ROLLBACK_MINIMUM_PLANNING_COVERAGE_RATE`
- `RESERVATION_ROLLOUT_ROLLBACK_MINIMUM_TERMINAL_COVERAGE_RATE`
- `RESERVATION_ROLLOUT_ROLLBACK_MAXIMUM_ZERO_PLAN_CONFLICT_RATE`
- `RESERVATION_ROLLOUT_ROLLBACK_MAXIMUM_PARTIAL_PLAN_RATE`
- `RESERVATION_ROLLOUT_ROLLBACK_MAXIMUM_AUTHORITY_LOSS_RATE`
- `RESERVATION_ROLLOUT_ROLLBACK_MAXIMUM_TERMINAL_PERSIST_FAILURE_RATE`
- `RESERVATION_ROLLOUT_ROLLBACK_MAXIMUM_WORKER_CONFIG_FAILURE_RATE`
- `RESERVATION_ROLLOUT_ROLLBACK_MAXIMUM_CLEANUP_WARNING_RATE`

Readiness (distinct keys; do not reuse the rollback-prefixed names):

- `RESERVATION_ROLLOUT_READINESS_WINDOW`
- `RESERVATION_ROLLOUT_MINIMUM_AUTHORITATIVE_ENFORCE_TASKS`
- `RESERVATION_ROLLOUT_MINIMUM_PLANNING_OBSERVED_TASKS`
- `RESERVATION_ROLLOUT_MINIMUM_CONFLICT_TASKS`
- `RESERVATION_ROLLOUT_MINIMUM_DIAGNOSTIC_RUN_COVERAGE_RATE`
- `RESERVATION_ROLLOUT_MINIMUM_PLANNING_OBSERVATION_COVERAGE_RATE`
- `RESERVATION_ROLLOUT_MINIMUM_TERMINAL_OBSERVATION_COVERAGE_RATE`
- `RESERVATION_ROLLOUT_MAXIMUM_ZERO_PLAN_CONFLICT_RATE`
- `RESERVATION_ROLLOUT_MAXIMUM_PARTIAL_PLAN_RATE`
- `RESERVATION_ROLLOUT_MAXIMUM_AUTHORITY_LOSS_RATE`
- `RESERVATION_ROLLOUT_MAXIMUM_TERMINAL_PERSIST_FAILURE_RATE`
- `RESERVATION_ROLLOUT_MAXIMUM_WORKER_LEASE_CONFIG_FAILURE_RATE`
- `RESERVATION_ROLLOUT_MAXIMUM_CLEANUP_WARNING_RATE`

`RESERVATION_ROLLOUT_ASSIGNMENT_SECRET` is required when rollout control is
configured. Never print it, never screenshot it, never include it in
acceptance artifacts, and never commit it. Do not place an example secret in
this runbook.

Do not put these controls in an end-user request or frontend toggle. Explicit
ENFORCE requests retain their existing B2 semantics; the canary governs
omitted/default mode assignment.

Do not reuse Phase 3D-2I-A2 local test numbers (including TTL 30, heartbeat 5,
minimum ENFORCE 3, minimum conflict 1, max zero-plan 0.34, balanced 10000
basis points, or generation `v15-gate5-local-001`) as Philippine defaults.

## Seed activation sequence

Follow this order. Do not enable omitted-request canary before a verified
backup exists.

1. Select tenant and planning policy; record application commit/tag.
2. Complete backup + independent verify
   (`DOPAMATRIX_V15_BACKUP_RESTORE_RUNBOOK.md`).
3. Keep omitted traffic `DEFAULT_OFF` / explicit-only until checks pass
   (rollout disabled, kill switch true, or basis points 0, per 2I-B policy).
4. Confirm lease configuration is valid.
5. Query summary, readiness, and rollout-status with `X-Local-User`.
6. Only then apply 2I-B seed rollout keys (generation, allowlist, basis
   points, kill switch false) so omitted eligible UI requests may promote.
7. Observe `WARMING_UP` then `CANARY_ACTIVE` when `canaryTaskCount` meets
   `RESERVATION_ROLLOUT_MINIMUM_CANARY_TASKS`.
8. Monitor summary + readiness quality/safety fields for the observation
   window.
9. If required, set `RESERVATION_ROLLOUT_KILL_SWITCH` and prove
   `rollout-status.state=KILL_SWITCHED` and the next omitted request is
   `DEFAULT_OFF`.
10. Preserve diagnostics evidence. Restore only under the accepted backup
    contract; do not treat restore-to-staging as live-tenant overwrite.

## Initial stage and observation

Choose the initial basis points explicitly
(`TO_BE_DECIDED_BY_2I_B_SEED_POLICY`). Any later increase follows a
policy-neutral reviewed sequence: initial reviewed exposure → higher
reviewed exposure → later reviewed exposure. No stage is automatic, and
no percentage is implied. Before every increase, an operator must review
and sign the current evidence.

For each observation period, record at least:

- total admitted and authoritative ENFORCE task counts;
- diagnostic, planning, and terminal observation coverage;
- Reservation conflict attempts and conflict-task rate;
- zero-plan conflict rate;
- partial-plan rate;
- authority-loss rate;
- terminal-persistence-failure rate;
- worker lease-configuration-failure rate;
- cleanup-warning rate;
- readiness state and every failed/unknown gate;
- breaker state and reason;
- task lifecycle anomalies, SQLite lock errors, and heartbeat/thread leaks.

Use the configured readiness/rollback windows. Do not cherry-pick only healthy
minutes or infer safety from a small denominator.

## Ramp decision

An operator may increase the stage only when:

1. the full observation period is complete;
2. required evidence counts and coverage pass;
3. all safety rates remain within configured thresholds;
4. no unexplained authority loss, terminal persistence failure, lock residue,
   or stuck task exists;
5. the breaker is not latched and the kill switch is inactive;
6. the prior backup remains verified or a newer verified backup exists.

Record the decision and approver. A healthy stage does not schedule or imply
the next stage.

## Rollback conditions

Stop ramping and place omitted requests in OFF when any configured breaker
condition is met, readiness is lost, lease configuration becomes invalid,
authority loss or terminal persistence failure is unexplained, task lifecycle
truth becomes inconsistent, or operators cannot verify diagnostics.

Already-running tasks are not cancelled by the rollout control. Explicit
ENFORCE remains the existing public B2 contract. Incident response must not
rewrite Reservation authority, Ledger occurrences, or TaskHistory.

## Kill-switch drill

In staging or controlled seed conditions while readiness is healthy and an
omitted request would otherwise be selected for ENFORCE:

1. record current `GET /api/v1/diagnostics/reservation/rollout-status`;
2. enable `RESERVATION_ROLLOUT_KILL_SWITCH` through normal operator config;
3. re-query rollout-status and prove `state=KILL_SWITCHED`;
4. submit the next omitted-mode request (ordinary AI Draft → Render) and prove
   durable effective mode is `OFF` / `DEFAULT_OFF` with null rollout metadata;
5. prove an explicit ENFORCE request still follows B2 semantics (kill switch
   does not apply to explicit ENFORCE);
6. confirm already-running work was not cancelled or rewritten;
7. record diagnostics and lifecycle outcomes (the omitted OFF task must not
   enter the ENFORCE summary cohort);
8. disable the switch only through normal operator configuration;
9. re-query readiness and rollout-status before further canary work.

## Breaker / rollback drill

Use staging or a safe controlled seed window; do not damage real creative work
to manufacture failures.

1. Configure controlled evidence that crosses one existing rollback threshold.
2. Prove the breaker latches for the current policy and generation.
3. Prove future omitted requests resolve to OFF.
4. Restore healthy metrics and prove that recovery does not auto-rearm.
5. Introduce a new reviewed rollout generation and prove only that new
   generation can re-enter the readiness/assignment process.
6. Record reason code, timestamps, observations, and operator decision without
   recording assignment secrets or raw HMAC material.

## Restart drill

1. Record rollout generation, breaker status, and current diagnostic counts.
2. Restart the application normally.
3. Confirm the tenant DB and TaskHistory remain readable.
4. Confirm a latched breaker remains latched and rollout does not silently
   reset or auto-rearm.
5. Re-run `GET /api/v1/diagnostics/reservation/readiness` and
   `GET /api/v1/diagnostics/reservation/rollout-status` with `X-Local-User`.
6. Verify a backup bundle and confirm authoritative asset paths still resolve.
7. Confirm no old Reservation heartbeat or owner-attempt identity is resumed.

## Incident notes

For every anomaly record UTC time, safe tenant label, application commit/tag,
planning policy, rollout generation, stage, aggregate metrics, breaker/kill
switch state, bounded error codes, containment action, and operator decision.
Do not include prompt text, raw creative content, assignment secrets, HMAC
values, owner-attempt IDs, or tenant database paths.

## Exit criteria for Phase 3D-2I-B

- backup-before-canary and independent verification succeeded;
- readiness and configured evidence gates remained satisfied;
- the selected manual stage completed its observation period;
- kill-switch, restart, and rollback drills produced the expected source-truth
  behavior;
- no unresolved authority, terminal persistence, task lifecycle, SQLite lock,
  heartbeat, or cleanup defect remains;
- evidence is recorded in the seed acceptance template and independently
  reviewed.

Local automated tests and this runbook do not satisfy these production exit
criteria.

