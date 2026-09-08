# DopaMatrix V1.5 Philippine Seed Canary Runbook

## Status

This document prepares Phase 3D-2I-B. It has not been executed against a real
Philippine production tenant and is not evidence of Philippine production
acceptance.

Product release status and a tenant's Reservation canary percentage are
separate decisions. DopaMatrix V1.5 can be released while an individual
tenant deliberately remains at 10%, 25%, or 50%; universal 100% Default-ON is
not a V1.5 GA requirement.

## Preconditions

1. Select one Philippine seed tenant using a safe operator label. Do not put
   tenant business content or task IDs in the acceptance summary.
2. Select one supported planning policy:
   `exact_main_visual` or `exact_main_visual_balanced`.
3. Record the reviewed application commit/tag and a new rollout generation.
4. Create and independently verify a complete tenant backup using
   `DOPAMATRIX_V15_BACKUP_RESTORE_RUNBOOK.md`.
5. Confirm the tenant's authoritative asset references are complete.
6. Confirm Reservation lease TTL and heartbeat configuration are valid.
7. Query `/api/v1/reservation-diagnostics/readiness` for the selected policy
   and record every gate.
8. Query `/api/v1/reservation-diagnostics/rollout-status` and record the kill
   switch, breaker, generation, readiness, and configured basis points.
9. Confirm the tenant and policy are present in the backend rollout
   allowlists. Do not expose the assignment secret.

Do not proceed when readiness is unavailable, the kill switch is active, a
breaker is latched for the generation, backup verification failed, or lease
configuration is invalid.

## Configuration authority

Use the existing backend-only controls, including:

- `RESERVATION_ROLLOUT_CONTROL_ENABLED`
- `RESERVATION_ROLLOUT_GENERATION`
- `RESERVATION_ROLLOUT_TENANT_ALLOWLIST`
- `RESERVATION_ROLLOUT_EXACT_CANARY_BASIS_POINTS`
- `RESERVATION_ROLLOUT_BALANCED_CANARY_BASIS_POINTS`
- `RESERVATION_ROLLOUT_ASSIGNMENT_SECRET`
- `RESERVATION_ROLLOUT_KILL_SWITCH`
- `RESERVATION_ROLLOUT_ROLLBACK_WINDOW`
- existing readiness and rollback evidence thresholds

Do not put these controls in an end-user request or frontend toggle. Explicit
ENFORCE requests retain their existing B2 semantics; the canary governs
omitted/default mode assignment.

## Initial stage and observation

Choose the initial basis points explicitly. A conservative conceptual sequence
is 5% -> 10% -> 25%, but these are not production defaults and no stage is
automatic. Before every increase, an operator must review and sign the current
evidence.

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

1. record the current rollout status;
2. enable `RESERVATION_ROLLOUT_KILL_SWITCH` through normal operator config;
3. submit the next omitted-mode request and prove its effective mode is OFF;
4. prove an explicit ENFORCE request still follows B2 semantics;
5. confirm already-running work was not cancelled or rewritten;
6. record diagnostics and lifecycle outcomes;
7. disable the switch only through normal operator configuration;
8. re-query readiness and rollout status before further canary work.

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
5. Re-run readiness and rollout-status queries.
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

