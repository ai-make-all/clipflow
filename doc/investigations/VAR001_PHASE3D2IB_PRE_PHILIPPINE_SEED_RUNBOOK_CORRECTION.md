# VAR-001 Phase 3D-2I-B PRE
# Philippine Seed Runbook Operational Correction Report

This phase is documentation correctness only. Production Python, Vue,
tests, SQLite, environment, and git history were not modified. 2I-A2
local full-stack acceptance was not reopened.

## 1. Executive Result

The Philippine seed canary runbook is now aligned with current source
diagnostic routes, tenant header routing, operator contracts, and
backend environment-key names. Premature seed-exposure percentage
examples were removed (**RF-09**). Seed **numeric** policy remains
undecided (`TO_BE_DECIDED_BY_2I_B_SEED_POLICY`).

**VAR001_PHASE3D2IB_PRE_RUNBOOK_OPERATIONAL_CORRECTION_PASS**

## 2. Scope

Correct `doc/operations/DOPAMATRIX_V15_PHILIPPINE_SEED_CANARY_RUNBOOK.md`
only where current source or accepted 2I-A / 2I-A2 artifacts prove a
mismatch. Do not decide Philippine exposure %, sample size, or
production thresholds.

Read first:

- `doc/investigations/VAR001_PHASE3D2IA2_MANUAL_FULLSTACK_ACCEPTANCE.md`
- `doc/investigations/VAR001_PHASE3D2IA2_UI_API_WIRING_AUDIT.md`
- `doc/operations/DOPAMATRIX_V15_PHILIPPINE_SEED_CANARY_RUNBOOK.md` (before)
- 2F / 2G operational contracts via current source

## 3. Source Authority

Inspected:

- `src/api/routes_reservation_diagnostics.py`
- `main.py` (`include_router(..., prefix="/api/v1")`)
- `src/api/database.py` (`request_tenant_id` / `get_db`)
- `src/api/reservation_rollout_control.py` (`_ENVIRONMENT_KEYS`, status
  states)
- `src/api/reservation_rollout_readiness.py` (`_ENVIRONMENT_KEYS`,
  `_not_configured_result`)
- `src/api/reservation_lease.py` (TTL / heartbeat env names)
- `doc/operations/DOPAMATRIX_V15_BACKUP_RESTORE_RUNBOOK.md` (checkpoint
  contract, not redesigned)

HEAD at start: `648a617cd27fefae3568e9c258fb11a676740766`
Branch: `feature/var-001-variation-policy`
Working tree was clean.

## 4. Confirmed Diagnostic Routes

Router prefix: `/diagnostics/reservation`
App mount: `/api/v1`

| Operator query | Method | Path |
|---|---|---|
| Summary | GET | `/api/v1/diagnostics/reservation/summary` |
| Readiness | GET | `/api/v1/diagnostics/reservation/readiness` |
| Rollout status | GET | `/api/v1/diagnostics/reservation/rollout-status` |

Stale prefix `/api/v1/reservation-diagnostics/...` is **not** mounted.

## 5. Tenant Routing Contract

`X-Local-User` → `canonical_tenant_id` → tenant engine (`get_db`) and
rollout-status `canonical_tenant=request_tenant_id(request)`.

No tenant query parameter and no JSON tenant body on these GETs.

## 6. Readiness Operator Contract

- Query: required `planning_policy` =
  `exact_main_visual` | `exact_main_visual_balanced`
- GET-only; no client thresholds or window in the request
- Window comes from `RESERVATION_ROLLOUT_READINESS_WINDOW` when configured
- Unconfigured: HTTP 200, `state=NOT_CONFIGURED`,
  `recommendation=KEEP_EXPLICIT_ONLY`, empty/uncomputed metrics
- Ready: `READY_FOR_CONTROLLED_CANARY` +
  `ELIGIBLE_FOR_CONTROLLED_DEFAULT_ON_CANARY`
- Also: `INSUFFICIENT_EVIDENCE`, `BLOCKED`

## 7. Rollout Status Operator Contract

GET `/rollout-status?planning_policy=...` is read-only
(“without mutation”).

States in current response model: `DISABLED`, `NOT_ELIGIBLE`,
`WARMING_UP`, `CANARY_ACTIVE`, `KILL_SWITCHED`, `AUTO_ROLLED_BACK`.

Kill switch maps to `KILL_SWITCHED`. `canaryTaskCount` vs
`RESERVATION_ROLLOUT_MINIMUM_CANARY_TASKS` selects `WARMING_UP` vs
`CANARY_ACTIVE` when otherwise eligible.

## 8. Summary Operator Contract

GET `/summary?window=` default `24h`; allowed `1h|24h|7d|30d`.
Cohort is tenant-local ENFORCE runs.

Minimum seed fields documented in the runbook match current response
names (`enforceTaskCount`, `zeroPlanConflictRate`,
`authorityLossCount`, …). Obsolete names were not present in the old
runbook body beyond the stale URL prefix.

## 9. Environment-Key Cross-Check

No obsolete aliases were found in the previous runbook. The listed
rollout keys were current but **incomplete**. Readiness and lease keys
were not named. Worker-config rollback vs readiness keys differ:

- rollout: `RESERVATION_ROLLOUT_ROLLBACK_MAXIMUM_WORKER_CONFIG_FAILURE_RATE`
- readiness: `RESERVATION_ROLLOUT_MAXIMUM_WORKER_LEASE_CONFIG_FAILURE_RATE`

The runbook now lists source `_ENVIRONMENT_KEYS` / lease names without
values.

## 10. Assignment Secret Safety

Previous text said “Do not expose the assignment secret.” No example
secret existed (`RF-03` not reported).

The runbook now states: required when rollout control is configured;
never print, screenshot, commit, or include in acceptance artifacts; no
example secret.

## 11. Backup-Before-Canary Boundary

Backup/restore implementation was not changed. The runbook already
pointed at `DOPAMATRIX_V15_BACKUP_RESTORE_RUNBOOK.md`.

Gap: preconditions mixed backup with “confirm allowlist” without stating
that canary enablement must wait for a verified checkpoint. An ordered
**Seed activation sequence** now places backup + verify before applying
allowlist / enabled / non-zero bps / kill switch inactive.

## 12. Test-Only vs Philippine Seed Boundary

The previous runbook did not copy 2I-A2 numbers as defaults (`RF-04` not
reported). It now forbids those local test values explicitly and marks
all numeric policy `TO_BE_DECIDED_BY_2I_B_SEED_POLICY`. Specific ramp
percentages such as 5%→10%→25% were later removed under **RF-09**.

## 13. UI Operational Boundary

Ordinary workflow remains AI Draft → Tactical Board → Render. No
customer-facing canary UI was required before; the runbook now states
that prohibition explicitly (`RF-05` not reported as a prior defect).

## 14. L1 / L2 / L3 Boundary

The previous runbook did not call L2 historical deduplication
(`RF-06` not reported). A short L1 / L2 / L3 paragraph was added so
operators cannot misread Reservation as “never generate yesterday’s
video again.”

## 15. Runbook Changes

| Area | Before | Source-proven contract | After | Reason |
|---|---|---|---|---|
| Diagnostic prefix | `/api/v1/reservation-diagnostics/readiness` and `.../rollout-status` | `/api/v1/diagnostics/reservation/{summary,readiness,rollout-status}` | Current paths + curl + `X-Local-User` | **RF-01 / RF-08** |
| Tenant routing | Unspecified | `X-Local-User` only | Header required; no query/body tenant | Operator would otherwise miss the tenant DB |
| Summary | Not listed | GET `/summary?window=` | Added | Seed decisions need ENFORCE cohort metrics |
| Readiness/status states | Implicit | Literal models in `routes_reservation_diagnostics.py` | Enumerated | **RF-08** completeness |
| Env keys | Partial rollout list | Full lease + rollout + readiness names | Complete names, no values | Avoid mixing readiness vs rollback keys |
| Assignment secret | “Do not expose” | Never print/screenshot/commit | Explicit prohibitions | Safety |
| Backup vs canary | Backup was a precondition; allowlist later | 2I-A2: backup-before-canary | Ordered activation; no enable until verify | **RF-07** sequence |
| Test numbers | Not used as defaults | 2I-A2 TEST-ONLY | Explicit do-not-copy list | Prevent promotion |
| Seed ramp % examples | `10%/25%/50%` and `5% -> 10% -> 25%` | Exposure % is `TO_BE_DECIDED_BY_2I_B_SEED_POLICY` | Generic partial-canary + reviewed-exposure sequence; no seed % ladder | **RF-09** |
| UI / L1–L3 | Not stated | 2I-A2 product contract | Short preserved boundaries | Operator clarity |

## 16. Findings

**VAR3D2IB-PRE-RF-01**
`PHILIPPINE_SEED_RUNBOOK_DIAGNOSTIC_ROUTE_PREFIX_STALE` — **confirmed,
corrected.**

**VAR3D2IB-PRE-RF-07**
`RUNBOOK_CANARY_SEQUENCE_CAN_BYPASS_BACKUP_CHECKPOINT` — **sequence gap,
corrected.** Backup existed as a checklist item; allowlist confirmation
could be read as canary already on. Ordered activation now forbids
enablement before verified backup.

**VAR3D2IB-PRE-RF-08**
`RUNBOOK_ROLLOUT_STATUS_STATE_OR_ROUTE_STALE` — **stale route,
corrected** (same prefix as RF-01). States were missing, not wrong;
they are now listed from source.

**VAR3D2IB-PRE-RF-09**
`RUNBOOK_PREMATURELY_INTRODUCES_NUMERIC_CANARY_RAMP_EXAMPLES` —
**CONFIRMED_AND_CORRECTED.** Status text listed 10%/25%/50% and the
ramp section listed 5%→10%→25% as a conceptual ladder. Those numbers
are removed. Architecture retains only that universal 100% Default-ON
is not a V1.5 GA requirement. Actual seed exposure remains
`TO_BE_DECIDED_BY_2I_B_SEED_POLICY`.

Not reported: RF-02 (no stale env alias), RF-03 (no secret exposure),
RF-04 (test numbers were not promoted), RF-05 (no fake UI control),
RF-06 (no L2/historical conflation in the old text).

## 17. Remaining 2I-B Policy Decisions

Still `TO_BE_DECIDED_BY_2I_B_SEED_POLICY` (this PRE phase must not
invent them):

- Philippine exposure % / exact vs balanced basis points
- minimum production sample size / ENFORCE and conflict counts
- production zero-plan, partial-plan, conflict, coverage, and safety
  rate thresholds
- readiness and rollback observation windows
- lease TTL and heartbeat
- `RESERVATION_ROLLOUT_MINIMUM_CANARY_TASKS`
- rollout generation string for the seed
- whether seed starts explicit-only until READY

## 18. Git Diff

```text
git diff --check
(exit 0; LF→CRLF warning only)

git diff --stat
 ...OPAMATRIX_V15_PHILIPPINE_SEED_CANARY_RUNBOOK.md | 209 ++++++++++++++++++---
 1 file changed, 185 insertions(+), 24 deletions(-)
```

No production code, tests, or other files changed.

## 19. Final Git Status

```text
git branch --show-current
feature/var-001-variation-policy

git rev-parse HEAD
648a617cd27fefae3568e9c258fb11a676740766

git status --short
 M doc/operations/DOPAMATRIX_V15_PHILIPPINE_SEED_CANARY_RUNBOOK.md
?? doc/investigations/VAR001_PHASE3D2IB_PRE_PHILIPPINE_SEED_RUNBOOK_CORRECTION.md
```

Proof markers:

- PHILIPPINE_SEED_DIAGNOSTIC_ROUTES_SOURCE_ALIGNED
- PHILIPPINE_SEED_READINESS_COMMAND_SOURCE_ALIGNED
- PHILIPPINE_SEED_ROLLOUT_STATUS_COMMAND_SOURCE_ALIGNED
- PHILIPPINE_SEED_SUMMARY_COMMAND_SOURCE_ALIGNED
- PHILIPPINE_SEED_ENV_KEYS_SOURCE_ALIGNED
- PHILIPPINE_SEED_ASSIGNMENT_SECRET_NOT_EXPOSED
- PHILIPPINE_SEED_BACKUP_CHECKPOINT_PRESERVED
- LOCAL_TEST_THRESHOLDS_NOT_PROMOTED_TO_SEED_DEFAULTS
- V15_SERVER_SIDE_CANARY_UI_BOUNDARY_PRESERVED
- L1_L2_L3_OPERATIONAL_BOUNDARY_PRESERVED
- PHILIPPINE_SEED_RUNBOOK_READY_FOR_POLICY_DECISION

VAR001_PHASE3D2IB_PRE_RUNBOOK_OPERATIONAL_CORRECTION_PASS
