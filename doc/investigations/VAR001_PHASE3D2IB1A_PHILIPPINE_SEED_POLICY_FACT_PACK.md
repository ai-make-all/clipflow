# VAR-001 Phase 3D-2I-B-1A
# Philippine Seed Policy Fact Pack

Role: read-only source fact pack. No production values are frozen.
No code, tests, SQLite, environment, or git writes besides this file.

Statement labels used below:

- **SOURCE FACT** — current code contract
- **EXISTING ACCEPTANCE EVIDENCE** — 2I-A2 / 2I-B PRE
- **POLICY INFERENCE** — operational reading of those facts
- **POLICY RECOMMENDATION** — candidate, not a freeze

## 1. Executive Result

Current source is sufficient for technical challenge of a Philippine
Seed policy. The highest-leverage facts:

1. **SOURCE FACT:** `RESERVATION_ROLLOUT_MINIMUM_CONFLICT_TASKS = 0` is
   valid (`int >= 0`). Seed **need not** manufacture same-FP collisions
   to become READY.
2. **SOURCE FACT:** `conflictTaskRate` is **informational**. It is not a
   readiness or rollback gate.
3. **SOURCE FACT:** A legitimate L2 loser is `zero_plan_conflict` (quality),
   not `authority_lost` (safety). Zero-tolerance on zero-plan can trip
   rollback after one real contention.
4. **SOURCE FACT:** Rollback metrics use only `ROLLOUT_CANARY` rows in
   the rollback window. `canaryTaskCount == 0` skips rollback. One canary
   with a 1.0 rate can exceed a 0 maximum.
5. **SOURCE FACT:** Successful canary does **not** change basis points.
   Ramp is manual only.
6. **SOURCE FACT:** P0–P3 (explicit-only bootstrap → READY → small
   omitted balanced canary) is supported without code or Vue changes
   (`enabled=false` / `bps=0` / kill switch / not READY all yield
   omitted `DEFAULT_OFF`; explicit `ENFORCE` bypasses the resolver).

**Recommended candidate for 2I-B-1B challenge: PROFILE B — RECOMMENDED SEED.**
Not frozen.

**VAR001_PHASE3D2IB1A_SEED_POLICY_FACT_PACK_READY**

## 2. Scope

Inputs: current source; 2I-A2 local full-stack acceptance (FINAL PASS);
2I-B PRE runbook correction (PASS); Philippine seed and backup runbooks;
2E/2F/2G contracts as implemented today.

Does **not** reopen Reservation authority, L3 historical memory, or
2I-A2 runtime evidence.

## 3. Frozen Product Direction

Treat as decided unless source forbids (it does not):

| Item | Direction | Label |
|---|---|---|
| A | Primary policy `exact_main_visual_balanced` | POLICY RECOMMENDATION (product) |
| B | `exact_main_visual` canary 0 bps initially | POLICY RECOMMENDATION (product) |
| C | UI: AI Draft → Tactical Board → Render; no canary UI | EXISTING ACCEPTANCE EVIDENCE |
| D | New/insufficient tenant: omitted `DEFAULT_OFF` + explicit ENFORCE bootstrap until READY | POLICY RECOMMENDATION + SOURCE FACT (supported) |
| E | Verified backup before any omitted canary bps > 0 | EXISTING ACCEPTANCE EVIDENCE |
| F | Exposure changes are manual; no auto-ramp | SOURCE FACT + product |
| G | L2 = concurrent Reservation Authority, not L3 history | EXISTING ACCEPTANCE EVIDENCE |

## 4. Source Configuration Domains

### Lease — SOURCE FACT

| Key | Domain | Absent | Fail-safe |
|---|---|---|---|
| `RESERVATION_LEASE_TTL_SECONDS` | finite float `> 0` | both absent → unconfigured | ENFORCE route/worker reject; omitted canary falls OFF |
| `RESERVATION_HEARTBEAT_INTERVAL_SECONDS` | finite float `> 0` and `<= TTL/3` | one-of-two → incomplete/invalid | same |

TTL is a stale-owner horizon, **not** render duration. Heartbeat loop
renews bindings every interval (`reservation_lease.py`).

May be zero? **No** (`<= 0` invalid).

### Readiness — SOURCE FACT

All-or-none key set. Window: `24h` \| `7d` \| `30d`.
Count minima: `int >= 0` (zero allowed).
Rates: `0.0 .. 1.0`.

Absent config → `NOT_CONFIGURED` / `KEEP_EXPLICIT_ONLY` / empty gates.
Incomplete set → HTTP 503 `RESERVATION_ROLLOUT_READINESS_CONFIGURATION_INVALID`.

Cohort: `VideoTask.reservation_conflict_mode == ENFORCE` **and** matching
`planning_policy` in the window (explicit + canary ENFORCE).

### Rollout control — SOURCE FACT

All-or-none key set. Generation: `[A-Za-z0-9._-]{1,64}`.
Allowlist: already-canonical tenant labels.
Basis points: `int` `0..10000` inclusive.
`minimum_canary_task_count`: `int >= 1` (**cannot be 0**).
Rollback window: `1h` \| `24h` \| `7d`.
Rates: `0.0 .. 1.0`.
Secret: nonempty string (never logged here).

Absent entire set → omitted resolver `DEFAULT_OFF`; status `DISABLED`.
`enabled=false` or `bps=0` or kill switch or tenant not allowlisted →
omitted OFF. Breaker for (policy, generation) → omitted OFF.
Not READY → omitted OFF; if that generation already had a canary,
trips `READINESS_LOST`.

HMAC bucket `0..9999`; promote iff `bucket < basis_points`.
10000 bps ⇒ all omitted eligible promote; 0 ⇒ none.

**SOURCE FACT:** nothing in source increments basis points after success.

## 5. Readiness Semantics

**SOURCE FACT** state machine:

- QUALITY or SAFETY gate `FAIL` → `BLOCKED`
- any gate not `PASS` (including EVIDENCE `FAIL` or any `UNKNOWN`) →
  `INSUFFICIENT_EVIDENCE` (unless already BLOCKED)
- all 13 gates `PASS` → `READY_FOR_CONTROLLED_CANARY`

Lease ready is a SAFETY gate (`CURRENT_LEASE_CONFIGURATION_READY`).

`_rate(n, d)` is `None` when `d == 0` → rate gates `UNKNOWN` → cannot be
READY.

**SOURCE FACT:** EVIDENCE `FAIL` (count/coverage minima) does **not**
set `BLOCKED`. It keeps `INSUFFICIENT_EVIDENCE` / `KEEP_EXPLICIT_ONLY`.
Only QUALITY/SAFETY `FAIL` blocks.

**SOURCE FACT:** readiness cohort is every `VideoTask` with
`reservation_conflict_mode == ENFORCE` and matching `planning_policy`
in the window. Explicit ENFORCE and canary ENFORCE **share** this
cohort.

**POLICY INFERENCE:** a brand-new tenant with zero ENFORCE rows cannot
be READY even if all count minima are 0, because coverage/quality/safety
rates are UNKNOWN until denominators exist.

Per-field map. Recommended ranges are **POLICY RECOMMENDATION**, not a
freeze. Other columns are **SOURCE FACT** unless marked.

| Field / env | Source domain | Denominator | PASS | FAIL / UNKNOWN | Seed risk | Recommended range |
|---|---|---|---|---|---|---|
| `RESERVATION_ROLLOUT_READINESS_WINDOW` | `24h` \| `7d` \| `30d` | time gate | n/a | invalid window → config error | too short: rates noisy; too long: stale evidence | `7d` first, `24h` only if volume is high |
| `MINIMUM_AUTHORITATIVE_ENFORCE_TASKS` | `int >= 0` | count of ENFORCE rows in window | `count >= min` | FAIL if below; 0 tasks + min 0 still PASS this gate | too high: READY delayed; too low / 0: READY can rest on thin samples once rates exist | 5–8 (Profile B: 5) |
| `MINIMUM_PLANNING_OBSERVED_TASKS` | `int >= 0` | `planning_observed` diagnostic rows | `count >= min` | FAIL if below | same as ENFORCE min; quality rates need this denom | 5–8 (match ENFORCE min) |
| `MINIMUM_CONFLICT_TASKS` | `int >= 0` (0 legal) | tasks with `had_reservation_conflict` | `count >= min` | EVIDENCE FAIL only (not BLOCKED) | min > 0 **requires manufactured or organic same-FP collisions** to leave INSUFFICIENT_EVIDENCE | **0** |
| `MINIMUM_DIAGNOSTIC_RUN_COVERAGE_RATE` | `0.0..1.0` | diagnostic rows / ENFORCE count | `rate >= min` | UNKNOWN if ENFORCE count=0 | <1.0 hides missing observability | 1.0 |
| `MINIMUM_PLANNING_OBSERVATION_COVERAGE_RATE` | `0.0..1.0` | planning-observed / ENFORCE count | `rate >= min` | UNKNOWN if ENFORCE count=0 | same | 1.0 |
| `MINIMUM_TERMINAL_OBSERVATION_COVERAGE_RATE` | `0.0..1.0` | terminal diagnostic / **terminal** ENFORCE count | `rate >= min` | UNKNOWN if no terminal ENFORCE yet | in-flight-only window → UNKNOWN | 1.0 |
| `MAXIMUM_ZERO_PLAN_CONFLICT_RATE` | QUALITY `0.0..1.0` | zero-plan / **planning_count** | `rate <= max` | UNKNOWN if planning_count=0; FAIL → BLOCKED | max=0: one legitimate L2 loser blocks READY | 0.20–0.35 |
| `MAXIMUM_PARTIAL_PLAN_RATE` | QUALITY `0.0..1.0` | partial-plan / planning_count | `rate <= max` | same UNKNOWN/BLOCKED | max=0 punishes partial fills | 0.10–0.25 |
| `MAXIMUM_AUTHORITY_LOSS_RATE` | SAFETY `0.0..1.0` | authority_lost / ENFORCE count | `rate <= max` | UNKNOWN if no ENFORCE; FAIL → BLOCKED | max>0 tolerates authority defects | **0** |
| `MAXIMUM_TERMINAL_PERSIST_FAILURE_RATE` | SAFETY | persist-fail / ENFORCE count | `rate <= max` | same | same | **0** |
| `MAXIMUM_WORKER_LEASE_CONFIG_FAILURE_RATE` | SAFETY | worker-config-fail / ENFORCE count | `rate <= max` | same | same | **0** |
| `MAXIMUM_CLEANUP_WARNING_RATE` | **source category SAFETY** (FAIL → BLOCKED); **operational class CLEANUP** | cleanup_warning / ENFORCE count | `rate <= max` | same | max=0 treats operability as authority-class | 0.05–0.10 (not 0 unless ops prove cleanup is silent) |
| `CURRENT_LEASE_CONFIGURATION_READY` | live lease env, not a rate | n/a | lease configured | FAIL → BLOCKED | unconfigured lease blocks READY even with good history | must be configured before P2 |

Traffic-volume dependent? Count minima and windows are. Rate maxima are
not volume-dependent in code, but small denominators make them brittle
(**POLICY INFERENCE**).

May be zero?

- Count minima: **yes**, source-valid (`>= 0`).
- Rate maxima: **yes**, `0.0` is valid; operationally harsh for quality
  and cleanup.
- Coverage minima: **0** is source-valid but then coverage never gates.

## 6. Conflict Evidence Question

**SOURCE FACT — `conflictTaskCount`:** count of ENFORCE rows in the
readiness window whose diagnostic has `had_reservation_conflict`
(`reservation_conflict_count > 0`).

**SOURCE FACT — `conflictTaskRate`:**
`conflictTaskCount / planningObservedCount`, or `None` if no planning
observations. **Not a readiness gate. Not a rollback metric.**

**SOURCE FACT — `zeroPlanConflictRate`:**
`zero_plan_count / planning_count` (same planning denominator).
`zero_plan_conflict` is `planned_count == 0` **and**
`termination_reason == RESERVATION_CONFLICT_EXHAUSTED`.

**SOURCE FACT:** zero real conflicts + `planning_count > 0` ⇒
`zeroPlanConflictRate = 0.0` (valid, not UNKNOWN).
Zero planning observations ⇒ rate `None` / UNKNOWN.

**SOURCE FACT:** `minimum_conflict_tasks = 0` is legal
(`_parse_nonnegative_integer` / `int >= 0`). Then
`conflictTaskCount >= 0` always PASSES. Operators need **not**
manufacture same-FP collisions to unlock READY.

**SOURCE FACT:** if `minimum_conflict_tasks > 0` and observed conflicts
are 0, `MINIMUM_CONFLICT_TASKS` is EVIDENCE `FAIL` →
`INSUFFICIENT_EVIDENCE`, **not** `BLOCKED`. Omitted traffic still stays
OFF until the count is met. The source therefore *can* require
manufactured collisions, but only if operators choose min > 0.

**EXISTING ACCEPTANCE EVIDENCE:** Gate 3 manufactured contention for
L2 proof, not because readiness required it. Local Gate 4B used
`minimum conflict = 1` as TEST-ONLY.

**POLICY RECOMMENDATION:** Seed `minimum_conflict_tasks = 0`. Keep
`conflictTaskRate` as an efficiency signal (healthy L2 vs poor
candidate diversity), not an unlock requirement.

High conflict rate may mean L2 is working (two operators hit one FP)
**or** the catalog is too small. Neither is automatically `authority_lost`.

## 7. Quality Metrics

| Metric | Numerator | Denominator | Category |
|---|---|---|---|
| `zeroPlanConflictRate` | tasks with exhausted reservation and planned=0 | planning-observed ENFORCE (readiness) / planning-observed **canary** (rollback) | QUALITY |
| `partialPlanRate` | `0 < planned < requested` | same planning denominators | QUALITY |

**SOURCE FACT:** a real Reservation conflict that exhausts the only
candidate is a **quality** zero-plan, not authority loss. Gate 3 loser
was exactly that.

Threshold 0:

- Readiness: one legitimate loser among N planning observations fails
  READY (`1/N > 0`) → BLOCKED.
- Rollback: after first canary, if that one task is a loser and
  `canaryTaskCount >= 1`, rate 1.0 trips breaker.

Permissive threshold: hides chronic inability to plan; still does not
disable L2.

**POLICY RECOMMENDATION (range, not freeze):** Seed zero-plan max
**0.20–0.35**; partial max **0.10–0.25**. Do not use 0 unless the seed
catalog is proven never to contend.

## 8. Safety Metrics

| Signal | Class | Meaning (source/ops) | max=0 appropriate? |
|---|---|---|---|
| `authority_lost` | AUTHORITY SAFETY | Reservation authority lost mid-run | **Yes** for Seed |
| `terminal_persist_failed` | DATA DURABILITY | public terminal persist failed | **Yes** for Seed |
| `worker_lease_config_failed` | CONFIGURATION | ENFORCE worker lacked valid lease config | **Yes** for Seed (should be impossible if P0 checked) |
| `cleanup_warning` | CLEANUP / OPERABILITY | controller cleanup warning; **not** authority grant/loss | **Not equivalent** to authority loss |

**SOURCE FACT:** readiness still classifies
`MAXIMUM_CLEANUP_WARNING_RATE` as category `SAFETY`. A cleanup FAIL
therefore **BLOCKED** readiness the same way authority-loss FAIL does.
That is a **gating category**, not an operational-severity equivalence.

**POLICY RECOMMENDATION:** Seed rollback/readiness maxima **0** for
authority loss, terminal persist failure, and worker lease-config
failure. Cleanup: prefer a small **>0** (0.05–0.10). Do **not** treat
cleanup as the same operational severity as authority loss, even though
the source gate category is SAFETY.

**SOURCE FACT:** SAFETY `FAIL` → readiness `BLOCKED` (omitted stays OFF;
if generation already had canary, `READINESS_LOST` breaker).

## 9. Rollback / Breaker Semantics

**SOURCE FACT:** `_canary_metrics` filters
`reservation_mode_source == ROLLOUT_CANARY` **and** current
`rollout_generation` **and** `planning_policy` in the rollback window.

`minimum_canary_task_count` (`>= 1`) is **not** a rollback skip and
**not** an admission gate. It only chooses status
`WARMING_UP` vs `CANARY_ACTIVE` when otherwise eligible.

**WARMING_UP (SOURCE FACT):** eligible, READY, no breaker, no kill
switch, bps>0, allowlisted, `window canaryTaskCount < minimum`.
**Omitted promotion still occurs.**

Rollback becomes active when `canaryTaskCount > 0` in the window
(`_rollback_reason` returns immediately if count is 0). UNKNOWN rates
(`None`) are **skipped** (not tripped).

A single bad canary: count=1, rate=1.0. Any maximum `< 1` (including 0)
trips. Coverage minima of 1.0 fail if that one row lacks a diagnostic.

Latch: insert `reservation_rollout_breakers` for (policy, generation);
`on_conflict_do_nothing`. Future omitted → OFF. **No auto-rearm.**
Healthy metrics do not clear the row. **New generation** required to
re-enter assignment (`READINESS_LOST` and quality/safety reasons alike).

**SOURCE FACT:** explicit ENFORCE never consults the breaker.

Rollback field map (**SOURCE FACT** unless marked recommendation):

| Field / env | Domain | Cohort / denom | When it trips | Seed note |
|---|---|---|---|---|
| `RESERVATION_ROLLOUT_ROLLBACK_WINDOW` | `1h` \| `24h` \| `7d` | time filter on canary rows | n/a | 1h + low volume often `canaryTaskCount==0` (skip) |
| `RESERVATION_ROLLOUT_MINIMUM_CANARY_TASKS` | `int >= 1` (**cannot be 0**) | window `canaryTaskCount` vs this min | **does not trip**; only `WARMING_UP` vs `CANARY_ACTIVE` | WARMING_UP still admits |
| rollback diagnostic coverage | `0.0..1.0` | diagnostic / **canary count** | below min → `DIAGNOSTIC_RUN_COVERAGE_BELOW_MINIMUM` | one undiagnosed canary at n=1 trips if min=1.0 |
| rollback planning coverage | `0.0..1.0` | planning-observed / canary count | `PLANNING_OBSERVATION_COVERAGE_BELOW_MINIMUM` | same |
| rollback terminal coverage | `0.0..1.0` | terminal diagnostic / **canary terminal** count | `TERMINAL_OBSERVATION_COVERAGE_BELOW_MINIMUM`; UNKNOWN/skip if no terminals | in-flight-only window skips this reason |
| rollback zero-plan max | `0.0..1.0` | zero-plan / **canary planning_count** | `ZERO_PLAN_CONFLICT_RATE_EXCEEDED`; skip if no planning obs | max=0 + one L2 loser trips |
| rollback partial max | `0.0..1.0` | partial / canary planning_count | `PARTIAL_PLAN_RATE_EXCEEDED` | same |
| rollback authority-loss max | `0.0..1.0` | authority_lost / **canary count** | `AUTHORITY_LOSS_RATE_EXCEEDED` | max=0 appropriate |
| rollback terminal-persist max | `0.0..1.0` | persist-fail / canary count | `TERMINAL_PERSIST_FAILURE_RATE_EXCEEDED` | max=0 appropriate |
| rollback worker-config max | `0.0..1.0` | worker-config-fail / canary count | `WORKER_LEASE_CONFIG_FAILURE_RATE_EXCEEDED` | env key is `...WORKER_CONFIG_FAILURE_RATE` (not `WORKER_LEASE_...`) |
| rollback cleanup max | `0.0..1.0` | cleanup / canary count | `CLEANUP_WARNING_RATE_EXCEEDED` | not authority-equivalent |
| `READINESS_LOST` | n/a | **generation** canary count (window-independent) | readiness not READY **and** this generation ever had ≥1 canary | latch; new generation to re-arm |

`conflictTaskRate` does **not** appear in `_ROLLBACK_REASONS`.

## 10. Lease Policy Analysis

**SOURCE FACT:** both env vars required; `heartbeat <= TTL/3`; no
defaults; TTL is not a render deadline; heartbeat thread renews
`expires_at = now + TTL`. Failed renew → `LEASE_LOST`.

Tradeoffs:

| Risk | Short TTL | Long TTL |
|---|---|---|
| Crash / hung owner takeover | faster | slower (stale owner can hold FP) |
| Laptop sleep / pause | false lease loss | more tolerant |
| SQLite writer blip | more renew failures | fewer false losses |

Candidate profiles (**POLICY RECOMMENDATION**, not freeze):

| Profile | TTL | Heartbeat | Tradeoff |
|---|---|---|---|
| CONSERVATIVE | 300 s | 60 s | slower takeover; fewer false losses |
| BALANCED | 180 s | 45 s | 4 renews per TTL; middle |
| AGGRESSIVE | 90 s | 25 s | faster fencing; higher sleep/contention risk |

Local Gate 2 used 30/5 TEST-ONLY — **do not** reuse for Seed.

Volume-dependent? Indirectly (more concurrent ENFORCE ⇒ more renew
writers). May be zero? **No.**

## 11. Exposure / Basis-Point Analysis

**SOURCE FACT:** HMAC-SHA256 over UTF-8 message
`"\x1f".join(("reservation-rollout-v1", tenant, policy, task_id, generation))`.
Bucket = digest `% 10000` → `0..9999`. Promote iff `bucket < basis_points`.
HMAC **does not** include basis points. Deterministic per those inputs.
Operator changes bps manually; source never ramps.

Bands (**POLICY RECOMMENDATION** analysis only; not a freeze):

| Band | bps | Fraction |
|---|---|---|
| VERY LOW | 100 | 0.01 |
| LOW | 250–500 | 0.025–0.05 |
| MODERATE | 1000 | 0.10 |

Do **not** reuse Gate 5’s 10000.

Expected canary tasks/day ≈ `eligible_balanced_tasks_day * bps / 10000`
(independence approximation; **POLICY INFERENCE**):

| Eligible/day | 100 bps | 250 | 500 | 1000 |
|---|---|---|---|---|
| 10 | 0.10 | 0.25 | 0.50 | 1.0 |
| 25 | 0.25 | 0.63 | 1.25 | 2.5 |
| 50 | 0.50 | 1.25 | 2.5 | 5.0 |
| 100 | 1.0 | 2.5 | 5.0 | 10 |
| 250 | 2.5 | 6.3 | 12.5 | 25 |

At 10 eligible/day and VERY LOW, expect ~1 canary / 10 days. Rollback
and status evidence stay thin even if “percentage is safe.”

Exact policy at 0 bps: **SOURCE FACT** omitted exact never promotes.

## 12. Sample Size and Window Coupling

| Gate type | Examples |
|---|---|
| Time | readiness window 24h/7d/30d; rollback 1h/24h/7d |
| Sample-count | min ENFORCE, min planning, min canary (**status only**) |
| Rate | coverage, quality, safety |

**POLICY INFERENCE:** `expected_days_to_N_canaries ≈ N / (tasks_day * bps/10000)`.

Example: 25 eligible/day, 250 bps, want 5 canaries ≈ 8 days. Same N at
100 bps ≈ 20 days. A 1h rollback window with 0.25 canary/day is usually
empty → rollback skipped (`canaryTaskCount==0`) even if a bad task
exists outside the hour — **or** a 1h window that happens to contain
exactly one bad task trips at rate 1.0.

**POLICY RECOMMENDATION:** couple rollback window to expected canary
volume (prefer `24h` or `7d` until traffic is known). Do not treat
percentage as a safety substitute for sample size.

Readiness ENFORCE sample can be grown in **P1 via explicit ENFORCE**
without waiting for canary.

## 13. Explicit-Only Bootstrap Analysis

Proposed P0–P3 is **SOURCE FACT supported** with no code/UI change:

| Phase | Mechanism |
|---|---|
| P0 | Verified backup; omitted OFF via `enabled=false` or balanced bps `0` or kill switch; lease configured |
| P1 | `POST /api/v1/tasks/submit-dsl` with `reservation_conflict_mode=ENFORCE` (same body as UI, plus that field). No Vue control |
| P2 | Readiness READY on explicit ENFORCE cohort (`minimum_conflict_tasks=0`) |
| P3 | Set balanced bps > 0, kill switch false, allowlist, enabled; ordinary omitted UI may promote |

**EXISTING ACCEPTANCE EVIDENCE:** Gate 2 did exactly this API ENFORCE
reuse; Gate 5 omitted UI promotion after READY.

Safest bootstrap: operator/API explicit ENFORCE on **normal** diverse
catalogs (not forced single-FP) unless a **staging** L2 drill is
scheduled separately.

## 14. Generation Policy

**SOURCE FACT:** `[A-Za-z0-9._-]{1,64}`; required when rollout configured;
breaker and canary metrics are per (policy, generation).

**POLICY RECOMMENDATION** naming (non-secret, auditable, re-arm friendly):

`ph-seed-bal-YYYYMMDD-rN`

Example structure only — **not** `v15-gate5-local-001`.

**Same generation:** change allowlist, kill switch, basis points,
rollback thresholds. HMAC message does **not** include bps, so changing
bps only changes the cut, not the hash function.

**New generation required:** after breaker latch; after `READINESS_LOST`;
when operators want a clean canary cohort / re-arm. Changing generation
changes HMAC inputs (new buckets).

## 15. Kill Switch vs Breaker

| | Kill switch | Breaker |
|---|---|---|
| Trigger | Manual env `RESERVATION_ROLLOUT_KILL_SWITCH` | Automatic on omitted resolve |
| Status | `KILL_SWITCHED` | `AUTO_ROLLED_BACK` |
| Affects | omitted promotion only | omitted promotion only |
| Explicit ENFORCE | unaffected | unaffected |
| Already admitted | not rewritten | not rewritten |
| Rearm | set false | **new generation** |

**POLICY RECOMMENDATION** — consider **immediate manual kill switch**
(do not wait for windowed rates):

- any `authority_lost`
- any `terminal_persist_failed`
- lease configuration invalid / worker config failures
- diagnostics/readiness/rollout-status unavailable (503)
- SQLite integrity / lock residue / stuck processing cluster
- repeated unexplained failed ENFORCE

**Cleanup warnings only:** investigate; not automatic equivalent to
authority loss. May still kill-switch if volume spikes.

Not frozen incident policy.

## 16. Drill Environment Classification

| Drill | Class | Why |
|---|---|---|
| Kill switch (omitted OFF + explicit ENFORCE still works) | **SAFE_ON_REAL_SEED** | Gate 6 class; no manufactured failure |
| Restart + re-query + breaker persistence | **CONTROLLED_REAL_SEED_ONLY** | Schedule off-peak; no creative damage |
| Backup verify | **SAFE_ON_REAL_SEED** | Required checkpoint |
| Breaker threshold-crossing (inject bad rates) | **STAGING_OR_SYNTHETIC_ONLY** | Do not damage real work |
| Forced same-FP contention | **STAGING_OR_SYNTHETIC_ONLY** | Gate 3 class; one task fails by design |
| Lease expiry / takeover fault | **STAGING_OR_SYNTHETIC_ONLY** | False loss / stolen render risk |
| SQLite lock/outage injection | **STAGING_OR_SYNTHETIC_ONLY** | Durability risk |

Policy must **not** require damaging a real Philippine catalog to prove
guards. Automated suites already cover lease/fencing/contention.

## 17. Operator Facts Required Before Final Freeze

**OPERATOR_FACTS_REQUIRED_BEFORE_FINAL_FREEZE**

Source cannot answer (do not fabricate):

- expected eligible **balanced** public tasks/day
- peak concurrent ENFORCE/canary tasks
- number of Philippine operators and whether they overlap
- operating hours / overnight unattended
- one seed tenant vs several (allowlist width)
- whether the seed machine sleeps or restarts mid-render
- acceptable time-to-kill-switch response
- acceptable calendar days before a canary-stage review
- typical batch_size and catalog diversity (affects real conflict rate)
- who holds assignment secret and generation-change approval

These dominate whether VERY LOW bps is evidence-useful vs cosmetic.

## 18. Candidate Profile A

**PROFILE A — ULTRA CONSERVATIVE**

Assumption: low traffic (≲25 eligible/day) or first week of a new tenant;
operators accept slow canary evidence.

| Field | Candidate |
|---|---|
| planning policy | `exact_main_visual_balanced` |
| exact bps | 0 |
| balanced bps | 100 (VERY LOW) |
| lease TTL / heartbeat | 300 / 60 |
| readiness window | 7d |
| min ENFORCE / planning / conflict | 8 / 8 / **0** |
| coverage minima | 1.0 / 1.0 / 1.0 |
| zero-plan / partial max | 0.25 / 0.15 |
| safety maxima (auth, persist, worker) | 0 / 0 / 0 |
| cleanup max | 0.05 |
| rollback window | 7d |
| min canary tasks (status only) | 3 |
| rollback coverage minima | 1.0 |
| rollback quality maxima | 0.25 / 0.15 |
| rollback safety maxima | 0 / 0 / 0 / cleanup 0.05 |

**POLICY RECOMMENDATION** only.

## 19. Candidate Profile B

**PROFILE B — RECOMMENDED SEED**

Assumption: roughly 25–100 eligible balanced tasks/day once P1 is
running; one tenant; operators available same day.

| Field | Candidate |
|---|---|
| planning policy | `exact_main_visual_balanced` |
| exact bps | 0 |
| balanced bps | 250–500 (LOW) |
| lease TTL / heartbeat | 180 / 45 |
| readiness window | 7d |
| min ENFORCE / planning / conflict | 5 / 5 / **0** |
| coverage minima | 1.0 / 1.0 / 1.0 |
| zero-plan / partial max | 0.30 / 0.20 |
| safety maxima | 0 / 0 / 0 |
| cleanup max | 0.10 |
| rollback window | 24h |
| min canary tasks | 2 |
| rollback coverage | 1.0 |
| rollback quality | 0.30 / 0.20 |
| rollback safety | 0 / 0 / 0 / cleanup 0.10 |

P0–P3 as in §13. No auto-ramp. 100% Default-ON not required.

## 20. Candidate Profile C

**PROFILE C — FASTER LEARNING**

Assumption: ≥100 eligible/day **or** operators accept more canary
share to learn faster; stronger on-call.

| Field | Candidate |
|---|---|
| planning policy | `exact_main_visual_balanced` |
| exact bps | 0 |
| balanced bps | 1000 (MODERATE) |
| lease TTL / heartbeat | 120 / 30 |
| readiness window | 24h |
| min ENFORCE / planning / conflict | 3 / 3 / **0** |
| coverage minima | 1.0 |
| zero-plan / partial max | 0.35 / 0.25 |
| safety maxima | 0 / 0 / 0 |
| cleanup max | 0.10 |
| rollback window | 24h |
| min canary tasks | 1 |
| rollback coverage | 1.0 |
| rollback quality | 0.35 / 0.25 |
| rollback safety | 0 / 0 / 0 / cleanup 0.10 |

Faster evidence; higher chance a single unlucky contention or cleanup
warning latches the generation (especially min canary status 1 + 24h).

## 21. Recommended Direction

**POLICY RECOMMENDATION:** take **PROFILE B** into 2I-B-1B challenge,
with these non-negotiables from source/product:

- `minimum_conflict_tasks = 0` (do not require manufactured L2)
- exact bps = 0 at start
- backup verified before balanced bps > 0
- omitted OFF until READY
- explicit ENFORCE API for P1
- safety maxima 0 for authority / terminal persist / worker config
- cleanup **not** treated as authority loss
- quality maxima **> 0** so one Gate-3-like loser does not freeze seed
- no automatic ramp; 100% Default-ON not a V1.5 requirement

Choose LOW bps using the §11 table once `eligible_tasks/day` is known.

## 22. Open Decisions for 2I-B-1B

Still `TO_BE_DECIDED_BY_2I_B_SEED_POLICY` after operator facts (§17):

- exact balanced bps inside 250–500 (or another band)
- final lease pair
- readiness/rollback windows
- ENFORCE sample minima (3 vs 5 vs 8)
- cleanup maximum 0 vs 0.05–0.10
- quality maxima inside recommended ranges
- `minimum_canary_task_count` (status only; ≥1)
- generation string
- kill-switch incident list
- whether any **controlled** real-seed restart drill is scheduled

## 23. Git Status

```text
git branch --show-current
feature/var-001-variation-policy

git rev-parse HEAD
6ef49a114352cd198ea0d5c0c6fa6e509ba8d57c

git status --short
?? doc/investigations/VAR001_PHASE3D2IB1A_PHILIPPINE_SEED_POLICY_FACT_PACK.md

git diff --check
(empty)
```

Only this artifact is new. No commit. No push.

Proof:

- Conflict-min 0 is source-valid
- conflictTaskRate is informational
- Rollback is canary-generation-windowed
- No auto-ramp
- P0–P3 needs no code change

VAR001_PHASE3D2IB1A_SEED_POLICY_FACT_PACK_READY
