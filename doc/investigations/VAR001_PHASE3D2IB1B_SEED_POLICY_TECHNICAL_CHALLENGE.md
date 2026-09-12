# VAR-001 Phase 3D-2I-B-1B
# Philippine Seed Policy Technical Challenge Review

## 1. Executive Verdict

Profile B is fail-safe but is **not technically balanced as written** and must not be frozen unchanged.

The Reservation authority protocol is not the blocker. The policy defects are small-sample and cohort effects:

1. `minimum_canary_task_count = 2` does not defer rollback. One canary is enough for every defined rollback rate to be evaluated.
2. At one to three canaries, a single zero-plan, partial-plan, or cleanup event exceeds Profile B's respective maximum. The generation can latch before it reaches the advertised two-task `CANARY_ACTIVE` status.
3. At 250--500 bps, a 24-hour rollback cohort is usually empty or contains one task when eligible volume is low. The result alternates between no evaluation and a one-event 100% rate.
4. Readiness includes every matching-policy ENFORCE `VideoTask`, including explicit and canary tasks and tasks that have not yet produced planning diagnostics. With 1.0 diagnostic/planning coverage, an in-flight task can make readiness temporarily non-READY. Once a generation has any canary history, the next omitted-mode resolution can latch `READINESS_LOST`.
5. `cleanup_warning` can be emitted after authoritative terminal truth committed successfully. Treating one cleanup warning like authority loss is too coarse for a small seed cohort.

A revised Seed candidate is technically coherent without changing source, but exposure, windows, coverage tolerances, lease selection, and review timing require operator facts.

**Technical verdict on Profile B:** `CHANGE`, then freeze only after the operator facts in section 17 are supplied.

## 2. Inputs and Evidence Precedence

The following were read completely before source analysis:

- `VAR001_PHASE3D2IB1A_PHILIPPINE_SEED_POLICY_FACT_PACK.md`
- `DOPAMATRIX_V15_PHILIPPINE_SEED_CANARY_RUNBOOK.md`
- `VAR001_PHASE3D2IB_PRE_PHILIPPINE_SEED_RUNBOOK_CORRECTION.md`
- `VAR001_PHASE3D2IA2_MANUAL_FULLSTACK_ACCEPTANCE.md`

Evidence was applied in the required order: current source, current tests, accepted final artifacts, then Fact Pack interpretation. No service, render, test, SQLite, or environment mutation was performed.

## 3. Source Revalidation

Current source independently proves:

- Readiness configuration allows nonnegative count minima. `minimum_conflict_tasks = 0` is valid.
- `_rate(n, d)` returns `None` only when `d == 0`; with planning observations and zero conflicts, `conflictTaskRate` and `zeroPlanConflictRate` are `0.0`.
- `conflictTaskRate` is returned as information and has no readiness or rollback gate.
- Readiness selects all matching-policy `VideoTask` rows with effective mode `ENFORCE`; it does not filter `reservation_mode_source`. Explicit and canary ENFORCE share the cohort.
- Readiness `QUALITY` or `SAFETY` failure yields `BLOCKED`; incomplete `EVIDENCE` or any `UNKNOWN` yields `INSUFFICIENT_EVIDENCE` unless a blocking failure also exists.
- Rollback selects only current-policy/current-generation `ROLLOUT_CANARY` tasks inside its configured window.
- `_rollback_reason()` skips only when `canaryTaskCount == 0`. `minimum_canary_task_count` is consulted later and only selects `WARMING_UP` versus `CANARY_ACTIVE`.
- Omitted assignment evaluates readiness and rollback before calculating the new task's HMAC bucket. A request that would ultimately be OFF can therefore trigger an existing generation breaker.
- When readiness is not READY and the generation has ever admitted a canary, omitted resolution writes a `READINESS_LOST` breaker before returning OFF.
- Rollout-status GET is read-only; breaker mutation occurs during omitted-mode resolution, not during status inspection.
- Lease configuration requires finite positive values with `heartbeat <= TTL / 3`; the heartbeat renews leases and TTL is not a render deadline.
- HMAC input includes tenant, policy, server task ID, and generation, but not basis points. Changing generation re-buckets; changing basis points within a generation does not.

The current tests explicitly cover that coverage rollback can trip while `minimum_canary_task_count` is still unmet, and that a breaker does not cancel or rewrite an already admitted canary.

## 4. Conflict-Minimum Challenge

`minimum_conflict_tasks = 0` is technically correct.

For any `planningObservedTaskCount > 0` with no conflict tasks:

- `conflictTaskCount = 0`;
- `conflictTaskRate = 0.0`, not `UNKNOWN`;
- `MINIMUM_CONFLICT_TASKS` passes because `0 >= 0`;
- no other gate indirectly consumes `conflictTaskRate`;
- rollback does not contain a conflict-task-rate reason.

Organic contention can still produce zero-plan or partial-plan quality evidence. That evidence is evaluated normally, but it is not required to unlock readiness. Production Seed must not manufacture same-FP contention.

`VAR3D2IB1B-RF-01` is not present.

## 5. Readiness Integer-Denominator Analysis

The table assumes all N tasks are matching-policy ENFORCE tasks, all have diagnostics, planning observations, and terminal observations, and the lease configuration is valid. Quality denominators are planning-observed tasks; safety and cleanup denominators are all authoritative ENFORCE tasks.

| N | All-normal state | Zero-plan max .30: allowed / first block | Partial max .20: allowed / first block | Cleanup max .10: allowed / first block | Safety max 0: allowed / first block | One missing required observation |
|---:|---|---:|---:|---:|---:|---|
| 1 | `INSUFFICIENT_EVIDENCE` (min 5 unmet) | 0 / 1 | 0 / 1 | 0 / 1 | 0 / 1 | `INSUFFICIENT_EVIDENCE` |
| 3 | `INSUFFICIENT_EVIDENCE` (min 5 unmet) | 0 / 1 | 0 / 1 | 0 / 1 | 0 / 1 | `INSUFFICIENT_EVIDENCE` |
| 5 | `READY_FOR_CONTROLLED_CANARY` | 1 / 2 | 1 / 2 | 0 / 1 | 0 / 1 | `INSUFFICIENT_EVIDENCE` |
| 10 | `READY_FOR_CONTROLLED_CANARY` | 3 / 4 | 2 / 3 | 1 / 2 | 0 / 1 | `INSUFFICIENT_EVIDENCE` |
| 20 | `READY_FOR_CONTROLLED_CANARY` | 6 / 7 | 4 / 5 | 2 / 3 | 0 / 1 | `INSUFFICIENT_EVIDENCE` |

Blocking failures take precedence over insufficient counts. Thus at N=1 or N=3, one zero-plan, partial-plan, cleanup, or safety event produces `BLOCKED`, not merely `INSUFFICIENT_EVIDENCE`.

Coverage minima of 1.0 permit no missing observation. Diagnostic and planning coverage divide by all ENFORCE tasks, including queued/processing tasks. Terminal coverage divides only by terminal ENFORCE tasks; if there are no terminal tasks its rate is `UNKNOWN`.

At N=5, one cleanup warning is 0.20 and therefore already exceeds 0.10. Profile B's cleanup setting behaves as zero tolerance until N reaches 10.

## 6. Rollback Small-Sample Analysis

This table assumes each canary has a diagnostic and planning observation and is terminal where terminal coverage is relevant.

| Canary N | Normal status with minimum=2 | Zero-plan .30: allowed / first trip | Partial .20: allowed / first trip | Cleanup .10: allowed / first trip | Safety max 0 | Coverage 1.0 |
|---:|---|---:|---:|---:|---|---|
| 0 | `WARMING_UP`; rollback skipped | n/a | n/a | n/a | n/a | rates `None`; skipped |
| 1 | `WARMING_UP` | 0 / 1 | 0 / 1 | 0 / 1 | first event trips | first missing diagnostic/planning observation trips |
| 2 | `CANARY_ACTIVE` | 0 / 1 | 0 / 1 | 0 / 1 | first event trips | first missing observation trips |
| 3 | `CANARY_ACTIVE` | 0 / 1 | 0 / 1 | 0 / 1 | first event trips | first missing observation trips |
| 5 | `CANARY_ACTIVE` | 1 / 2 | 1 / 2 | 0 / 1 | first event trips | first missing observation trips |
| 10 | `CANARY_ACTIVE` | 3 / 4 | 2 / 3 | 1 / 2 | first event trips | first missing observation trips |

`minimum_canary_task_count = 2` is only a display/status threshold. It is not a rollback warmup gate, admission gate, or evaluation delay. Profile B is therefore `ROLLBACK_TOO_SENSITIVE` at N=1--3 and can also be `ROLLBACK_TOO_SPARSE` when the 24-hour window contains no canary.

Terminal coverage is skipped when no canary is terminal because its denominator is zero. Diagnostic coverage is 0.0 when an admitted canary row exists without a diagnostic, and can trip immediately.

`VAR3D2IB1B-RF-02` is confirmed.

`VAR3D2IB1B-RF-04` is confirmed.

## 7. Shared Readiness Cohort Hazard

The readiness query filters by effective `ENFORCE`, planning policy, and time only. It combines `EXPLICIT_ENFORCE` and `ROLLOUT_CANARY`.

Consequences after P3 begins:

- A later explicit authority loss, terminal-persistence failure, or worker-config failure makes the zero-tolerance readiness gate fail.
- A sufficient number of explicit zero-plan, partial-plan, or cleanup events can also block readiness.
- The next omitted-mode resolution sees non-READY readiness and, because the generation has canary history, latches `READINESS_LOST` even if current-generation canary-only metrics are healthy.
- Explicit ENFORCE bypasses kill switch and breaker, so continuing routine explicit traffic after P3 can both contaminate readiness and bypass the containment intended for omitted traffic.

This is a `POLICY_HAZARD`, not an architecture blocker, provided Seed adopts a strict rule: after P3 starts, routine explicit ENFORCE stops. It is restricted to a central technical/operator role for a documented diagnostic or incident purpose; ordinary Philippine creative operators continue omitted/default Vue submissions only. Explicit work after a kill switch or breaker requires separate approval because source controls do not stop it.

There is a second shared-cohort hazard not emphasized by the candidate: with five fully observed bootstrap tasks, one newly admitted task that has not reached planning observation changes planning coverage from 5/5 to 5/6 = 0.833. A configured minimum of 1.0 makes readiness non-READY. If another omitted request resolves during that interval, it can latch `READINESS_LOST`. This is source-derived and must be addressed by serialized early Seed operation or a concurrency-aware coverage threshold.

`VAR3D2IB1B-RF-05` is confirmed as a policy hazard.

## 8. Cleanup Warning Analysis

The only production setter is `PlannerReservationController._warn_cleanup()`. It is reached when:

- heartbeat stop raises or does not quiesce within the bounded join;
- owner-safe Reservation release raises or otherwise fails;
- post-acquire/planner/worker cleanup uses the same `abort()` path and cleanup cannot finish.

The normal reservation-enabled terminal path commits the fenced terminal occurrence, TaskHistory, and fatigue transaction, then calls `abort()`. A cleanup warning can therefore occur **after a safely completed authoritative render**.

A cleanup warning means cleanup uncertainty, not proof that authority was granted incorrectly or that terminal truth is corrupt. A Reservation may remain until expiry. If stop timed out, the already requested heartbeat stop eventually quiesces; if release failed, the committed lease naturally expires. A later acquire can take over only after expiry. This may retain capacity and cause later conflicts, but it is not itself stale-result authority.

Discrete challenge:

| Max | First denominator at which one warning passes | Seed effect |
|---:|---:|---|
| 0 | never | one warning always blocks/trips; treats cleanup as authority loss |
| .05 | 20 | effectively zero tolerance for N < 20 |
| .10 | 10 | effectively zero tolerance for N < 10 |
| .20 | 5 | permits one warning at N=5; two of 10 also pass exactly |

Recommendation: readiness cleanup max 0.20 during the small Seed cohort, with manual investigation of every event; tighten to 0.10 only after N >= 10 and operational review. Because source has no rollback count warmup, set rollback cleanup tolerance permissively during the first-canary warmup or explicitly accept that one warning will latch the generation. Do not describe 0.10 as tolerant at N < 10.

`VAR3D2IB1B-RF-06` is confirmed.

## 9. Quality Threshold Analysis

Zero-plan and partial-plan are planning-quality/capacity signals, not direct authority-safety signals.

- A healthy L2 loser can be zero-plan when two operators target the only authoritative FP candidate.
- A small catalog or batch size near distinct candidate capacity can cause partial plans without any Reservation defect.
- Two concurrent operators can raise conflict/zero-plan rates precisely because duplicate authority is being prevented correctly.
- Poor catalog diversity can produce the same metrics without concurrency.

Readiness values 0.30/0.20 are coherent **after** the minimum five planning observations: one zero-plan (0.20) and one partial plan (0.20) pass; two of either block. They intentionally distinguish one legitimate shortfall from repeated inability to plan.

They are not coherent as immediate rollback maxima at N=1--3 because one event becomes 1.0, 0.5, or 0.333. The minimum-canary status does not protect this interval. Preserve 0.30/0.20 as post-warmup targets, but do not activate them as automatic rollback thresholds until at least five fully observed canaries have been manually reviewed, unless operators explicitly prefer first-event rollback.

## 10. Lease Policy Challenge

All candidate pairs satisfy `0 < heartbeat <= TTL/3`.

| Pair | Verdict | Technical interpretation |
|---|---|---|
| 180 / 45 | `BALANCED` with conditions | Three useful renew opportunities before original expiry and 135 seconds from first scheduled renewal to expiry. Good middle ground on an awake host. |
| 300 / 60 | Conservative | More tolerance for short pauses/SQLite contention; crash takeover can be delayed up to five minutes. Prefer when the Seed host is a laptop or scheduling is uncertain. |
| 120 / 30 | Aggressive but viable on a stable server | Less pause margin and faster crash recovery. Do not select without host and contention evidence. |
| 90 / 25 | Too short for initial real Seed | A 65-second delay after the first scheduled renewal can exhaust the known lease; laptop sleep and writer stalls make false loss more likely. |

Several-minute renders do not require a several-minute static lease because heartbeat renews. Process crash correctly stops renewal and waits for expiry. CPU saturation, SQLite writer contention, and Python scheduling delay consume renewal margin. Windows sleep longer than TTL loses the lease; on resume, terminal fencing prevents stale result authority, but computation may be wasted. No finite TTL makes arbitrary sleep safe.

Recommendation: retain 180/45 only if the Seed host is kept awake during active work and SQLite contention is low. Use 300/60 if laptop sleep/pause cannot be operationally prevented. Do not adopt 120/30 or 90/25 for the first real Seed.

`VAR3D2IB1B-RF-07` is not proven; 180/45 is conditionally safe.

## 11. Exposure and Sample Accumulation

Expected canary count uses `eligible/day * bps / 10000`. Days-to-count is an expectation, not a guarantee. Empty-window probability is a Poisson approximation for illustration.

| Eligible/day | Canary/day @250 | Canary/day @500 | Days to 2/5/10 @250 | Days to 2/5/10 @500 | Approx. 24h P(0), 250 / 500 |
|---:|---:|---:|---:|---:|---:|
| 10 | .25 | .50 | 8 / 20 / 40 | 4 / 10 / 20 | .779 / .607 |
| 25 | .625 | 1.25 | 3.2 / 8 / 16 | 1.6 / 4 / 8 | .535 / .287 |
| 50 | 1.25 | 2.50 | 1.6 / 4 / 8 | .8 / 2 / 4 | .287 / .082 |
| 100 | 2.50 | 5.00 | .8 / 2 / 4 | .4 / 1 / 2 | .082 / .007 |
| 250 | 6.25 | 12.50 | .32 / .8 / 1.6 | .16 / .4 / .8 | .002 / <.001 |

For the specifically requested 24-hour rollback cases:

| Eligible balanced tasks/day | Expected canaries at 250 bps | Expected canaries at 500 bps | 24h verdict |
|---:|---:|---:|---|
| 10 | .25 | .50 | overwhelmingly 0/1; evidence-starved |
| 25 | .625 | 1.25 | commonly 0/1; one-event trip dominates |
| 50 | 1.25 | 2.50 | still small; 500 bps reaches five only over about two days |
| 100 | 2.50 | 5.00 | 500 bps is the first listed combination with about five per 24h |

At 10 eligible/day, 250--500 bps is operationally cosmetic for a one-week decision: five canaries take roughly 10--20 days. At 25/day, 250 bps still takes about eight days to five. A 24-hour rate policy becomes reasonably interpretable only near five canaries/window; for a one-day window that requires approximately:

`bps >= 10000 * 5 / eligible_tasks_per_day`.

The exact basis points cannot be frozen without eligible-volume and review-horizon facts.

`VAR3D2IB1B-RF-03` is confirmed conditionally for low-volume Seed traffic.

## 12. Window Coupling

| Readiness / rollback | Low volume | Medium volume | High volume |
|---|---|---|---|
| 7d / 24h | readiness stable, rollback sparse/noisy | usable only after warmup or near >=5 canaries/day | coherent and responsive |
| 7d / 7d | coherent; slower quality rollback, use manual immediate safety kill | coherent initial Seed choice | unnecessarily slow for quality detection |
| 24h / 24h | both cohorts starve/oscillate | fragile unless explicit and canary volume are reliably daily | coherent when both cohorts are large |

Profile B's 7d/24h mismatch is acceptable only when expected canary count is high enough. At low volume choose 7d/7d for rate stability and rely on zero-tolerance safety alerts plus manual kill switch for immediate containment. At high volume retain 7d/24h. Do not use 24h readiness until at least five fully observed matching-policy ENFORCE tasks per day is source-operationally routine.

## 13. Safety Zero-Tolerance Review

| Signal | Automatic breaker | Manual action | Why |
|---|---|---|---|
| Authority loss | Keep max 0 | Immediate kill switch and stop explicit ENFORCE | Stale computation was fenced, but authority continuity failed. Breaker is evaluated only on the next omitted resolution, so manual containment must not wait. |
| Terminal persistence failure | Keep max 0 | Immediate kill switch and durability investigation | Authoritative terminal transaction failed; creative outputs must not be trusted as committed truth. |
| Worker lease-config failure | Keep max 0 | Immediate kill switch/config repair; stop explicit ENFORCE | Resolver preflight should make this rare; occurrence indicates configuration drift between admission and worker or an integration failure. |

All three should both block readiness and automatically latch on the next omitted resolution; serious incident response should also set the kill switch immediately. They are not identical operational incidents, but zero tolerance is correct for each during Seed. A read-only status query does not create the breaker, and explicit ENFORCE bypasses both breaker and kill switch, so the operator procedure must explicitly stop it.

## 14. Bootstrap Ownership

P0--P3 is technically safe with these ownership constraints:

- P0: central technical operator verifies backup, configures lease/readiness, and holds omitted traffic OFF.
- P1: only a central technical/operator role submits a small number of normal, diverse explicit ENFORCE tasks through the API. Philippine creative operators do not receive an ENFORCE switch and do not manufacture contention.
- P2: the technical operator reviews every gate and confirms READY.
- P3: ordinary creative operators continue AI Draft -> Tactical Board -> Render with the mode omitted; server governance assigns canary.

Once P3 begins, routine explicit ENFORCE must stop. It is `RESTRICTED`, not a normal creative path, because it bypasses kill/breaker controls and shares readiness evidence. If it is used for diagnosis, record its purpose and wait for its terminal diagnostic before interpreting readiness.

Early P3 requests should be serialized until planning observation is recorded, or readiness diagnostic/planning coverage must be lowered according to known peak in-flight tasks. Profile B's unconditional 1.0 values do not tolerate that transient.

## 15. Generation Rules

Generation is an assignment and breaker epoch, not a convenient evidence-clear button.

| Change | Generation rule |
|---|---|
| Ordinary planned basis-point ramp | Same generation; HMAC buckets remain stable and only the cut changes. |
| Threshold change | Same generation; preserve evidence and document the policy change. |
| Kill-switch toggle | Same generation. |
| Allowlist change | Same campaign generation by default; each tenant still needs its own backup/readiness. Do not re-bucket existing tenants merely to add one. |
| Lease pair change | Same generation; kill switch during risky reconfiguration, then revalidate readiness. |
| Breaker latch / `READINESS_LOST` recovery | New generation is required, after root cause, evidence review, and explicit approval. |
| Safety incident without an existing breaker | New generation after remediation when the operator deliberately starts a new authority epoch. |
| Code release | New generation only when rollout/authority behavior materially changes; unrelated patch releases do not justify resetting canary evidence. |
| Major catalog/diversity change | New generation may start a reviewed canary cohort after backup; readiness history still remains shared and must be interpreted explicitly. |

Rotating generation changes HMAC buckets, excludes old canaries from rollback metrics, and bypasses the old generation's breaker. Routine rotation for ramp, threshold tuning, or cosmetic naming can mask evidence. Every rotation therefore needs a reason, approver, verified backup, and explicit statement that prior evidence was reviewed rather than discarded.

`VAR3D2IB1B-RF-09` is confirmed as an operator-policy risk.

## 16. Drill Boundaries

| Drill | Technical classification | Challenge result |
|---|---|---|
| Backup + verify | `SAFE_ON_REAL_SEED` | Accept; mandatory before canary. |
| Kill switch | `SAFE_ON_REAL_SEED` | Accept; it affects future omitted requests and does not cancel active work. Do not use an active task as a cancellation test. |
| Restart | `CONTROLLED_REAL_SEED_ONLY_AFTER_DRAIN` | Tighten classification: drain active tasks, verify backup, schedule off-peak. If drain cannot be proven, use staging. |
| Breaker fault injection | `STAGING_OR_SYNTHETIC_ONLY` | No manufactured bad rates on real creative work. A naturally occurring real breaker may be observed, not induced. |
| Forced same-FP contention | `STAGING_OR_SYNTHETIC_ONLY` | Accept; it deliberately causes a losing task. |
| Lease expiry/takeover fault | `STAGING_OR_SYNTHETIC_ONLY` | Accept; it can waste or fence real output. |
| SQLite lock/outage injection | `STAGING_OR_SYNTHETIC_ONLY` | Accept; it threatens persistence and task lifecycle. |

The runbook's phrase allowing breaker threshold crossing in a "safe controlled seed window" must not be interpreted as permission to inject failure into real Philippine creative tasks. No evidence supports `VAR3D2IB1B-RF-10` if this stricter boundary is followed.

## 17. Operator Fact Dependencies

### CAN_FREEZE_WITHOUT_OPERATOR_FACT

- Primary policy `exact_main_visual_balanced`.
- Exact policy at 0 bps initially.
- `minimum_conflict_tasks = 0`.
- Coverage/quality/cleanup must be interpreted with integer counts, not percentages alone.
- Safety maxima 0 for authority loss, terminal persistence failure, and worker config failure.
- Backup before nonzero omitted canary, P0--P3, no automatic ramp, no customer-facing rollout UI.
- Routine explicit ENFORCE stops/restricts after P3.
- Generation is not rotated for ordinary ramp or threshold change.

### MUST_WAIT_FOR_OPERATOR_FACT

| Missing fact | Policy value blocked |
|---|---|
| Eligible balanced tasks/day | Exact bps; 24h versus 7d rollback; expected review duration |
| Peak concurrent ENFORCE/canary tasks | Readiness diagnostic/planning coverage minima; early P3 serialization rule; SQLite contention margin |
| Number of operators and overlap | Expected organic conflict rate; zero-plan threshold interpretation |
| Working hours / unattended periods | Rollback window and monitoring cadence |
| Seed tenant count | Allowlist rollout sequence and generation approval workflow |
| Machine sleep/restart behavior | 180/45 versus 300/60; restart drill classification |
| Acceptable kill-switch response time | Manual safety containment procedure and alert ownership |
| Acceptable calendar days to review | Bps, canary status minimum, and observation window |
| Typical batch size and catalog diversity | Zero-plan/partial-plan maxima and whether 0.30/0.20 is permissive or strict |
| Assignment-secret custodian and generation approver | Exact generation value and re-arm authority |

## 18. Profile B Decision Table

| Policy Item | Profile B Candidate | Technical Verdict | Reason | Operator Fact Needed? | Recommended Change |
|---|---|---|---|---|---|
| Primary policy | balanced | ACCEPT | Product direction and source supported | No | None |
| Exact canary | 0 bps | ACCEPT | Prevents simultaneous policy expansion | No | None |
| Balanced exposure | 250--500 bps | WAIT_FOR_OPERATOR_FACT | Can be cosmetic at low volume | Yes: eligible/day, review horizon | Choose bps to reach reviewed count; target about >=5/window |
| Lease | 180/45 | ACCEPT_WITH_CONDITION | Valid 4:1 pair; awake host required | Yes: sleep/contention | Keep if awake; otherwise 300/60 |
| Readiness window | 7d | ACCEPT_WITH_CONDITION | Stable initial history | Yes: task/day | Keep unless volume is demonstrably high |
| Min ENFORCE/planning | 5/5 | ACCEPT_WITH_CONDITION | Gives first useful discrete quality denominator | Yes: P1 duration | Keep as initial floor; increase later if inexpensive |
| Min conflict | 0 | ACCEPT | No hidden conflict requirement | No | None |
| Readiness diagnostic/planning coverage | 1.0/1.0 | CHANGE | Active tasks can transiently break READY and latch generation | Yes: peak unobserved concurrency | Serialize early P3 or set threshold <= observed/(observed+peak-unobserved) |
| Readiness terminal coverage | 1.0 | ACCEPT | Denominator contains terminal tasks only | No | Keep |
| Readiness zero-plan | .30 | ACCEPT_WITH_CONDITION | One of five passes; two block | Yes: diversity/concurrency | Keep after >=5 observed |
| Readiness partial | .20 | ACCEPT_WITH_CONDITION | One of five passes exactly | Yes: batch/catalog | Keep after >=5 observed |
| Readiness safety | 0/0/0 | ACCEPT | Correct Seed fail-closed posture | No | Keep |
| Readiness cleanup | .10 | CHANGE | One warning blocks until N=10 | Yes: cleanup incidence | Start .20 with mandatory review; tighten at N>=10 |
| Rollback window | 24h | WAIT_FOR_OPERATOR_FACT | Empty/one-task windows at low bps | Yes: canary/day | Use 7d until about >=5 canaries/day |
| Minimum canary tasks | 2 | CHANGE | Status only; does not protect rates | Yes: review target | Use 5 as an honest review/status milestone; never call it a rollback gate |
| Rollback coverage | 1.0 | ACCEPT_WITH_CONDITION | Correct completeness target but first in-flight row can trip | Yes: concurrency | Keep only with serialized warmup; otherwise stage/tune |
| Rollback zero/partial | .30/.20 | CHANGE | One event trips for N<=3 | Yes: willingness for first-event latch | Warmup permissively; tighten to .30/.20 after >=5 complete canaries |
| Rollback safety | 0/0/0 | ACCEPT | Any event warrants containment | No | Keep from first canary |
| Rollback cleanup | .10 | CHANGE | One warning trips until N=10 although it is not authority loss | Yes: response policy | Warmup/manual handling; .20 at N>=5, .10 at N>=10 |
| Explicit ENFORCE after P3 | unrestricted by source | REJECT | Bypasses controls and contaminates readiness | No | Central-role exception only; routine use stops |
| Automatic ramp | none | ACCEPT | Source and product contract | No | None |

## 19. Failure Scenario Table

Assumptions: S1--S5 are five fully observed readiness tasks before canary unless stated. S6--S12 add canaries to a clean five-task explicit baseline. Breaker mutation occurs on the next omitted-mode resolution, not at diagnostic-write time or during GET status.

| Scenario | Readiness effect | Rollback effect | Breaker effect | Operational interpretation |
|---|---|---|---|---|
| S1: 5 normal readiness tasks | READY | n/a | none | P2 can complete if lease is ready |
| S2: 5 tasks, 1 zero-plan | 1/5=.20 <=.30; READY | n/a | none | One legitimate L2/capacity loser tolerated |
| S3: 5 tasks, 2 zero-plan | 2/5=.40; BLOCKED | n/a | none before P3; `READINESS_LOST` if generation already has canary | Repeated capacity shortfall blocks |
| S4: 5 tasks, 1 partial | 1/5=.20; READY | n/a | none | Passes exactly at threshold |
| S5: 5 tasks, 1 cleanup | 1/5=.20>.10; BLOCKED | n/a | none before P3; otherwise `READINESS_LOST` | Candidate cleanup max is effectively zero tolerance |
| S6: 1 normal canary | Shared readiness remains READY if fully observed | rollback passes; status WARMING_UP | none | Min=2 did not delay evaluation |
| S7: 1 zero-plan canary | Combined 1/6=.167; readiness still READY | 1/1=1>.30 | `ZERO_PLAN_CONFLICT_RATE_EXCEEDED` | One legitimate loser latches generation under as-written rollback |
| S8: 1 cleanup canary | Combined 1/6=.167>.10; BLOCKED | Canary-only 1.0>.10 | `READINESS_LOST` wins because readiness is checked first | Cleanup is promoted to generation loss |
| S9: 1 authority-lost canary | Combined rate >0; BLOCKED | Canary-only rate 1.0>0 | `READINESS_LOST` wins on next omitted resolve; manual kill immediately | Serious safety incident; exact reason ordering matters |
| S10: 5 canaries, 1 zero-plan | Combined 1/10=.10; READY | 1/5=.20<=.30 | none | Post-warmup threshold behaves reasonably |
| S11: 5 canaries, 1 partial | Combined 1/10=.10; READY | 1/5=.20<=.20 | none | Passes exactly |
| S12: 5 canaries, 1 cleanup | Combined 1/10=.10; READY | 1/5=.20>.10 | `CLEANUP_WARNING_RATE_EXCEEDED` | One non-authority cleanup issue still latches |
| S13: healthy P3 canary + later bad explicit ENFORCE | Canary-only rollback remains healthy; shared readiness may BLOCK (always for a safety event, conditionally for quality/cleanup) | unchanged canary metrics | `READINESS_LOST` once shared readiness crosses threshold | Restrict explicit ENFORCE after P3 |

## 20. Revised Candidate Direction

Use **Profile B-R**, not Profile B as-is:

1. Keep balanced as primary, exact 0 bps, conflict minimum 0, safety maxima 0, backup-before-canary, P0--P3, and no auto-ramp.
2. Keep 180/45 only on an awake, stable host; otherwise use 300/60.
3. Keep 7d readiness and 5/5 count minima as the initial baseline.
4. Keep terminal coverage 1.0. For diagnostic/planning coverage, either serialize early P3 until each task reaches planning observation or choose a threshold from `observed / (observed + peak_unobserved)` after peak concurrency is known.
5. Use readiness quality 0.30/0.20 after at least five planning observations. Use readiness cleanup 0.20 initially, tightening to 0.10 after at least ten reviewed tasks.
6. Treat `minimum_canary_task_count` as a display/review milestone; use 5 rather than 2 if five is the first interpretable rollback denominator.
7. Because source has no rollback warmup gate, use a manually reviewed warmup stage: safety maxima remain 0 from the first task, while quality and cleanup automatic rollback thresholds stay permissive until five fully observed canaries exist. Then tighten in the **same generation** to zero-plan 0.30, partial 0.20, and cleanup 0.20; tighten cleanup to 0.10 only at N>=10 if evidence supports it.
8. Choose 250--500 bps only if it reaches the desired canary count within the operator's review horizon. If expected canaries are below five per 24h, use a 7d rollback window or change exposure; do not pretend min=2 supplies a warmup gate.
9. Stop routine explicit ENFORCE at P3. Central technical use only, with explicit approval and cohort interpretation.

This direction is technically coherent but deliberately does not freeze the traffic-dependent numbers.

## 21. Open Decisions for Final Freeze

- Eligible balanced tasks/day and desired calendar days to five and ten canaries.
- Peak concurrent tasks that may be admitted but not yet planning-observed.
- Whether the machine can sleep and whether active-task sleep is operationally disabled.
- Final 180/45 versus 300/60 lease pair.
- Exact balanced bps and 24h versus 7d rollback window.
- Whether operators accept first-event quality/cleanup rollback, or will use the staged warmup thresholds.
- Final readiness diagnostic/planning coverage minima.
- Final cleanup thresholds and mandatory manual response.
- Typical batch size/catalog diversity and expected organic L2 contention.
- Named central role for explicit ENFORCE, kill switch, secret custody, generation rotation, and re-arm approval.
- Whether a real-seed restart drill can prove all active tasks drained.

## 22. Findings

Confirmed:

- `VAR3D2IB1B-RF-02 MINIMUM_CANARY_TASKS_MISUSED_AS_ROLLBACK_WARMUP_GATE`
- `VAR3D2IB1B-RF-03 LOW_BPS_24H_ROLLBACK_WINDOW_EVIDENCE_STARVATION` (conditional on low/medium volume; operator volume is not yet known)
- `VAR3D2IB1B-RF-04 SMALL_DENOMINATOR_SINGLE_EVENT_TRIP_HAZARD`
- `VAR3D2IB1B-RF-05 EXPLICIT_ENFORCE_CONTAMINATES_ACTIVE_CANARY_READINESS` (policy hazard, not architecture blocker)
- `VAR3D2IB1B-RF-06 CLEANUP_WARNING_POLICY_OVERCLASSIFIED`
- `VAR3D2IB1B-RF-09 GENERATION_ROTATION_POLICY_CAN_MASK_OR_RESET_EVIDENCE`

Additional source-derived condition: 1.0 readiness diagnostic/planning coverage includes active ENFORCE tasks and can transiently latch `READINESS_LOST` after canary start. Profile B must serialize early Seed traffic or use a concurrency-aware coverage threshold.

Not confirmed:

- RF-01: conflict minimum zero has no indirect conflict requirement.
- RF-07: 180/45 is conditionally balanced, not source-proven unsafe.
- RF-08: Profile B can reach/stay READY under serialized, fully observed traffic; the unconditional 1.0 coverage candidate is the hazard.
- RF-10: real creative work is not damaged if fault injection remains staging/synthetic and restart occurs only after drain.

No code/architecture issue prevents selection of a safe Seed policy. The remaining blockers are policy correction and operator facts.

## 23. Git Status

Baseline before this artifact:

```text
git branch --show-current
feature/var-001-variation-policy

git rev-parse HEAD
6ef49a114352cd198ea0d5c0c6fa6e509ba8d57c

git status --short
?? doc/investigations/VAR001_PHASE3D2IB1A_PHILIPPINE_SEED_POLICY_FACT_PACK.md

git diff --check
(empty; exit 0)
```

This review adds only `doc/investigations/VAR001_PHASE3D2IB1B_SEED_POLICY_TECHNICAL_CHALLENGE.md`. No source, tests, frontend, SQLite, environment, or existing artifact was modified. No commit or push was performed.

Final status after creating this artifact:

```text
git status --short
?? doc/investigations/VAR001_PHASE3D2IB1A_PHILIPPINE_SEED_POLICY_FACT_PACK.md
?? doc/investigations/VAR001_PHASE3D2IB1B_SEED_POLICY_TECHNICAL_CHALLENGE.md

git diff --check
(empty; exit 0)
```

VAR001_PHASE3D2IB1B_TECHNICAL_CHALLENGE_PASS_PENDING_OPERATOR_FACTS
