# VAR-001 Phase 3D-2I-A2
# V1.5 UI / API Wiring Audit

Role: read-only full-stack wiring audit. No servers started. No tasks
submitted. No production, frontend, test, or database modifications.

Primary architecture answer (proven below):

**A. EXPECTED ARCHITECTURE**

Ordinary Vue submissions omit `reservation_conflict_mode`. That omission
is the Controlled Canary admission input. L2 Reservation Authority and
2G canary therefore required no Vue control surface.

## 1. Baseline

```text
git branch --show-current
feature/var-001-variation-policy

git rev-parse HEAD
a518aa1f24bf94893821c0c465c05d5bb2e7aaf4

git status --short
(empty)

git log -12 --oneline --decorate
a518aa1 (HEAD -> feature/var-001-variation-policy, origin/feature/var-001-variation-policy) feat(var-001): prepare v1.5 rc backup and restore safety
7712d54 docs(var-001): audit v1.5 forward compatibility
76d5cd5 (tag: var-001-controlled-canary-v1) feat(var-001): add controlled reservation canary rollout
ca1a4af (tag: var-001-rollout-readiness-v1) feat(var-001): add reservation rollout readiness guardrails
5f73335 (tag: var-001-reservation-observability-v1) feat(var-001): add reservation operational diagnostics
697577a (tag: var-001-public-reservation-enforce-v1) feat(var-001): activate public reservation enforce mode
76a070a refactor(var-001): establish server-owned task identity
ee1b8c3 refactor(var-001): separate reservation owner attempt identity
f179e15 (tag: var-001-reservation-authority-v1) fix(var-001): harden reservation transactions and runtime acceptance
2427038 feat(var-001): add reservation confirmation and terminal fencing
dfb2cb9 feat(var-001): enforce planner reservation conflicts
d4338c7 feat(var-001): add renewable reservation lease foundation

git diff --check
(empty, exit 0)
```

Working tree is clean after the completed 2I-A commit. Baseline is
acceptable.

Architecture artifacts consulted (source remains authority):

- `doc/investigations/VAR001_PHASE3D2G_CONTROLLED_CANARY_REPORT.md`
- `doc/investigations/VAR001_PHASE3D2IA_V15_RC_BACKUP_ACCEPTANCE_REPORT.md`

## 2. Frontend Architecture

- Framework: Vue 3 + Vite + Pinia + Vue Router (hash history)
- Entry: `web_ui/src/main.js` → `App.vue`
- Router: `web_ui/src/router/index.js`
- API helper: `web_ui/src/api/index.js` (approval only)
- Task HTTP: direct `axios` / `fetch` from views and stores
- Backend base: `web_ui/src/stores/appStore.js` `API_BASE = 'http://127.0.0.1:8000'`
- Auth: Login stores username in `localStorage` key `dopamatrix_user`
  and sets axios `X-Local-User`

Task-related pages:

| Route | File | Submits render tasks? |
|---|---|---|
| `/workspace` | `views/WorkspaceView.vue` | **Yes — primary** |
| `/dashboard` | `views/DashboardView.vue` | No (CTA to workspace) |
| `/approval` | `views/ApprovalView.vue` | No (post-render review) |
| `/assets` | `views/AssetsView.vue` | No |
| `/settings` | `views/SettingsView.vue` | No |
| `/video/:id` | `views/VideoDetailView.vue` | No |
| (embedded) | `views/QueueView.vue` | No (status/history) |
| (drawer) | `views/DslOrchestratorDrawer.vue` | Yes — manual / confirm |

Stores/composables:

- `stores/appStore.js` — auth, toast, optional REST poll of
  `GET /api/v1/tasks/{taskId}`
- `stores/useQueueStore.ts` — queue + WebSocket bridge
- `workers/queueWorker.ts` — per-`taskId` queue map

## 3. Primary V1.5 UI Entry

Philippine / V1.5 operator workflow uses **Workspace**
(`/workspace`, `WorkspaceView.vue`).

Dashboard CTA label: “去新建矩阵任务” → `/workspace`.

Two submit buttons on that page:

1. **AI 起草** (`draftBlueprint`) → opens tactical board with
   `variant_planning_policy = exact_main_visual_balanced` and
   `directRender = true`. Confirm calls `blindFission({ variantPlanningPolicy })`
   which, with populated beats, POSTs **non-blind** `submit-dsl`.
   This is the V1.5 exact/balanced matrix path.

2. **极速裂变** (`blindFission()` with no options) →
   `variant_planning_policy = legacy`. Canary-ineligible by backend
   policy. Still admits through public L2 admission as omitted + OFF.

Manual board (`openManualOrchestrator`) POSTs `submit-manual` without
a planning-policy field (Pydantic default `legacy`). Exact/balanced
are rejected on that endpoint (`_guard_pre_planner_policy`).

## 4. Task Submission Route

Primary V1.5 HTTP:

- Method: `POST`
- URL: `http://127.0.0.1:8000/api/v1/tasks/submit-dsl`
- Body: JSON `RenderDSLRequest`
- Handler: `src/api/routes_dsl.py` `submit_dsl`
- Router prefix: `/tasks` included at `/api/v1`

Trace:

```text
WorkspaceView.blindFission
  → axios.post(.../submit-dsl)
  → submit_dsl
  → _guard_pre_planner_policy
  → _preflight_public_reservation_policy
  → _admit_dsl_public_task_admission
  → admit_public_task  (server task_id)
  → _dispatch_claimed_public_task / render_worker
  → resolve_omitted_reservation_mode (if omitted + exact/balanced)
  → PlannerReservationController when effective ENFORCE
```

`POST /api/v1/tasks/submit` (`routes.py` `submit_task`) is **not** used
by the Vue app. It always admits `legacy` + `DEFAULT_OFF`.

UI_PRIMARY_TASK_FLOW_REACHES_PUBLIC_L2_ADMISSION_PROVEN: **PASS**

`VAR3D2IA2-RF-01` is not reported.

## 5. Request Payload

`WorkspaceView.vue` `blindFission` object (keys actually assigned):

- `engine_type`, `timeline`, `aspect_ratio`, `target_duration`,
  `batch_size`, `test_language`, `tenant_id`, `mode`,
  `variant_planning_policy`, `user_hard_tags`, `meta`,
  `enable_tts`, `enable_subtitles`, optional `prompt`

Not present: `reservation_conflict_mode`, `historical_novelty_mode`,
`task_id`, `session_id`, rollout/lease/breaker fields.

`DslOrchestratorDrawer.submitRenderTask` (non-direct) POSTs
`submit-manual` without `variant_planning_policy` and without
`reservation_conflict_mode`.

Axios default transform is `JSON.stringify` of that object. Missing
keys are omitted. No axios interceptor adds reservation fields.

## 6. Reservation Field Semantics

Frontend outcome: **A — field entirely absent**

- No TypeScript interface on the submit payload includes it
- No reactive default, store field, or spread injects it
- `JSON.stringify` / axios therefore cannot send `OFF`, `ENFORCE`, or
  `null`

Client authority fields (`owner_attempt_id`, `rollout_generation`,
`assignment_secret`, …) are rejected by
`RenderDSLRequest.reject_client_reservation_authority` if a client
ever sent them. The UI does not send them.

UI_ORDINARY_REQUEST_RESERVATION_FIELD_OMISSION_PROVEN: **PASS**

`VAR3D2IA2-RF-02` / `RF-03` / `RF-10` are not reported.

## 7. Omitted vs Explicit OFF

Backend (`_admit_dsl_public_task_admission`):

```text
explicit_mode = "reservation_conflict_mode" in payload.model_fields_set
```

Pydantic v2: JSON body without the key → attribute default `"OFF"`
but **not** in `model_fields_set` → omitted path.

JSON `"reservation_conflict_mode": "OFF"` → in `model_fields_set` →
`EXPLICIT_OFF` → no canary resolver.

No FastAPI middleware copies a default into the raw body. Worker
kwargs initially copy the Pydantic attribute, then **overwrite** with
`admission.reservation_conflict_mode` before dispatch.

Omitted + `exact_main_visual` / `exact_main_visual_balanced` installs
`resolve_omitted_reservation_mode`. Omitted + `legacy` never constructs
the resolver (stays `DEFAULT_OFF`).

END_TO_END_OMITTED_VS_EXPLICIT_OFF_SEMANTICS_PROVEN: **PASS**

## 8. Controlled Canary UI Contract

Current UI contains **none** of: Reservation mode dropdown, canary
toggle, basis-points, generation, kill switch, readiness, breaker.

That is intentional. 2G report: frontend unchanged; controls are
backend environment + diagnostics APIs.

**Does Controlled Canary REQUIRE a Vue modification for normal
business task submission? NO.**

Ordinary AI-draft `submit-dsl` omits the mode field and sends
`exact_main_visual_balanced`, which is canary-eligible.

CONTROLLED_CANARY_NORMAL_UI_REQUIRES_NO_SPECIAL_CONTROL_PROVEN: **PASS**

## 9. Planning Policy

UI values match backend `Literal`:

- `legacy`
- `exact_main_visual` (constant exists; **no visible control assigns it**)
- `exact_main_visual_balanced` (AI 起草)

极速裂变 default: `legacy` (backend default if omitted is also
`legacy`).

Canary eligibility: exact and balanced only.

Operator reaches canary-eligible policy by **AI 起草 → tactical
confirm**, not by 极速裂变.

Exact is API-selectable; not a current Workspace control. Not RF-05
(values that are sent match the contract). Not RF-04 (UI *can* reach
balanced).

UI_CAN_REACH_CANARY_ELIGIBLE_PLANNING_POLICY_PROVEN: **PASS**

## 10. Exact / Balanced User Flow

- **balanced:** user-selectable via AI 起草 (hard-assigned in
  `draftBlueprint`). No dropdown.
- **exact:** not user-selectable in Vue. Use explicit API
  `variant_planning_policy: "exact_main_visual"` for local E2E if
  needed. Do not invent a UI requirement; backend selection is
  sufficient.

Blind fission cannot carry exact/balanced (`EXACT_UNSUPPORTED_FOR_BLIND`).
AI 起草 populates beats first, so confirm is non-blind.

## 11. L1 Wiring

Same UI `submit-dsl` with `batch_size` (toolbar, default 1) and
balanced/exact planning reaches the DSL planner same-batch fingerprint
uniqueness path (`routes_dsl` authoritative main-visual worker kwargs).

L1 manual acceptance historically used Workspace + variant planning
(commits `648ce47` / `4a2d6d6`, before L2). That page is still the
submit surface.

Set batch size ≥ 2 on the same page for Scenario A.

L1_UI_FLOW_STILL_REACHES_SAME_BATCH_UNIQUENESS_PROVEN: **PASS**

## 12. L2 Wiring

Ordinary omitted UI request → server `task_id` → (if exact/balanced)
rollout resolver → effective `OFF` or `ENFORCE` persisted on admit →
worker uses admitted mode → `PlannerReservationController` only when
`ENFORCE` (`routes_dsl` render worker ~4084+) → conflict / terminal
diagnostics.

Lease TTL/heartbeat must already be configured for ENFORCE or the
route preflight/worker fail closed (`RESERVATION_LEASE_CONFIGURATION_REQUIRED`).
That is backend config, not a UI gap.

L2_UI_FLOW_CAN_REACH_RESERVATION_AUTHORITY_PROVEN: **PASS**

## 13. Explicit OFF / ENFORCE Testability

Vue cannot submit explicit OFF or ENFORCE. **Not a UI defect.**

Safest local E2E: `POST /api/v1/tasks/submit-dsl` with the same body
the UI would send, plus `"reservation_conflict_mode": "ENFORCE"` or
`"OFF"`. Use curl/httpie/devtools Replay. Header `X-Local-User` must
match login / allowlist.

Do not add production UI controls in 2I-A2.

## 14. Concurrency Capability

`isSubmitting` disables 极速裂变 only until the **202 ACK**, not until
render completion. After ACK the operator can submit Task B while
Task A is queued/processing.

Classification: **SAME_PAGE_CONCURRENCY_SUPPORTED**

Two independent tabs also work. Not RF-06.

LOCAL_CONCURRENT_L2_TEST_PATH_IDENTIFIED: **PASS**

## 15. Two-Tab Behavior

- Queue / Pinia / Worker: **per-tab memory**
- Shared: `localStorage` `dopamatrix_user`, `dopamatrix_output_dir`
- Not used for task slots: IndexedDB
- WebSocket: per tab, `POST /api/v1/auth/ws-ticket` then
  `WS /ws/events?ticket=`
- One tab cannot cancel the other's **server** task
- Each tab's queue list is independent until `/tasks/today` hydrate

Recommended: same-page sequential submits after ACK, or two tabs with
the same login for visual isolation. Server is authority.

## 16. Server-Owned Task ID

UI does not send `task_id` / `session_id`. Backend
`_ServerOwnedTaskRequest` rejects client `task_id`.

UI reads `resp.data.task_id` and `queueStore.pushTaskUpdate({ taskId })`.

UI_SERVER_OWNED_TASK_ID_CONTRACT_PROVEN: **PASS**

`VAR3D2IA2-RF-07` is not reported.

## 17. Task Status Flow

- Immediate: 202 + `task_id`
- Live: WebSocket `WS_UPDATE` keyed by `payload.taskId`
- Hydrate: `GET /api/v1/tasks/today`
- Optional: `GET /api/v1/tasks/{taskId}` in `appStore.startGlobalPolling`
  (feed cards keyed by `task.taskId`)

Worker: `_tasks.find(t => t.id === payload.taskId)` then unshift or
update. Concurrent IDs do not share one global slot.

Statuses shown: pending / running / completed / failed (WS). Backend
queued/processing map onto those WS labels.

`VAR3D2IA2-RF-08` is not reported.

## 18. Reservation Conflict UX

Successful recovery with a completed plan appears as a normal
completed queue card. Coverage diagnostics panel may show partial /
balanced notes when the worker attached `coverageDiagnostics`.

Failure: failed badge “✕ 错误”; submit HTTP errors as toast with
status + `detail`. No owner-attempt, HMAC, or lease internals.

Sufficient for V1.5 seed operation. Internal conflict taxonomy stays
on diagnostics APIs.

`VAR3D2IA2-RF-09` is not reported.

## 19. Diagnostics / Readiness / Rollout APIs

No customer dashboard. Operator HTTP (source prefix
`/diagnostics/reservation`, mounted at `/api/v1`):

- `GET /api/v1/diagnostics/reservation/summary?window=24h`
- `GET /api/v1/diagnostics/reservation/readiness?planning_policy=exact_main_visual_balanced`
- `GET /api/v1/diagnostics/reservation/rollout-status?planning_policy=exact_main_visual_balanced`

Header: `X-Local-User`.

(The 2I-B runbook’s `/api/v1/reservation-diagnostics/...` path does
not match this router. Use the source paths above.)

## 20. Kill Switch / Breaker UI

None. Expected: environment variables + rollout-status API + 2G
runbook. Sufficient for V1.5 seed. Do not add controls.

## 21. Frontend Git History

`web_ui/src` diff `dfb2cb9..76d5cd5`: **empty**

`web_ui/src` diff `697577a..76d5cd5`: **empty**

`76d5cd5..HEAD` (`web_ui/`): `package.json`, `package-lock.json`,
`tauri.conf.json` version `1.5.0-rc1` only.

L2 Reservation Authority, B2 public ENFORCE, 2E observability, 2F
readiness, 2G canary: **no Vue logic changes**.

Earlier L1 UI (not L2): `648ce47` explicit planning policy,
`4a2d6d6` balanced AI draft, `163177b` coverage explainability.

Answer: L2 / Controlled Canary did **not** require frontend
implementation. Version metadata in 2I-A is packaging only.

## 22. Frontend Need Matrix

| Capability | Backend present? | Frontend aware? | V1.5 frontend change | Reason |
|---|---|---|---|---|
| L1 same-batch uniqueness | Yes | Via balanced/exact submit | NOT_REQUIRED | Planner; UI already sends policy + batch_size |
| L2 explicit ENFORCE | Yes | No control | NOT_REQUIRED | API E2E; canary uses omit |
| L2 ordinary omitted request | Yes | Field absent | NOT_REQUIRED | Intended |
| Controlled Canary | Yes | No | NOT_REQUIRED | Omitted + backend config |
| Readiness | Yes | No | NOT_REQUIRED | Operator API |
| Diagnostics | Yes | No | NOT_REQUIRED | Operator API |
| Breaker | Yes | No | NOT_REQUIRED | Backend |
| Kill switch | Yes | No | NOT_REQUIRED | Env |
| Reservation failure display | Terminal failed/completed | Generic failed / completed | OPTIONAL_LATER | Seed-sufficient |
| Concurrent task display | Yes | Per-taskId queue | NOT_REQUIRED | Worker keyed by id |

## 23. Local Startup Commands

Recommend for 2I-A2 manual acceptance (browser Network tab):

**Backend** (repo root `e:\dopaworkspace\dopamatrix-desktop`):

```text
python main.py
```

Host: `127.0.0.1:8000` (`main.py` uvicorn). Equivalent:
`uvicorn main:app --reload --port 8000`.

**Frontend** (`web_ui/`):

```text
npm run dev
```

Vite default: `http://localhost:5173` (`tauri.conf.json` `devUrl`).
`vite.config.js` sets no custom port.

**Tauri (optional, not required for this audit):**

```text
cd web_ui
npm run tauri
```

Login with a tenant label that will match the canary allowlist.
Do not start these in this phase.

LOCAL_FULLSTACK_STARTUP_COMMANDS_IDENTIFIED: **PASS**

## 24. Local Canary Configuration

Do not change production defaults in this audit. Completely absent
rollout env ⇒ omitted stays OFF.

Rollout control requires the **full** key set or load fails closed.
Keys (`src/api/reservation_rollout_control.py`):

- `RESERVATION_ROLLOUT_CONTROL_ENABLED`
- `RESERVATION_ROLLOUT_GENERATION`
- `RESERVATION_ROLLOUT_TENANT_ALLOWLIST`
- `RESERVATION_ROLLOUT_EXACT_CANARY_BASIS_POINTS` (0–10000)
- `RESERVATION_ROLLOUT_BALANCED_CANARY_BASIS_POINTS` (0–10000)
- `RESERVATION_ROLLOUT_ASSIGNMENT_SECRET` (do not log/screenshot)
- `RESERVATION_ROLLOUT_KILL_SWITCH`
- `RESERVATION_ROLLOUT_ROLLBACK_WINDOW`
- plus the rollback min/max rate and `RESERVATION_ROLLOUT_MINIMUM_CANARY_TASKS`
  keys in `_ENVIRONMENT_KEYS`

Lease (required before ENFORCE, including canary ENFORCE):

- `RESERVATION_LEASE_TTL_SECONDS`
- `RESERVATION_HEARTBEAT_INTERVAL_SECONDS`

Readiness (also full-set-or-invalid). Omitted canary requires
`readiness.state == READY_FOR_CONTROLLED_CANARY`. Empty local DB
yields `UNKNOWN` rate gates → `INSUFFICIENT_EVIDENCE` → omitted OFF
even at 10000 bps. Proposed **temporary local test** approach (not
applied here): accumulate explicit ENFORCE evidence first (Scenario B),
or set count minima to `0` **and** still satisfy rate gates (rates are
`None`/`UNKNOWN` until ENFORCE rows exist). Deterministic first-shot
100% omitted canary on a blank DB is therefore a **readiness evidence**
constraint, not a UI wiring hole.

100% bucket: basis points `10000` (HMAC bucket `digest % 10000`).

Kill switch local test: `RESERVATION_ROLLOUT_KILL_SWITCH=true` (all
keys still required).

## 25. Manual E2E Scenario Plan

Do not execute in this phase.

**A — L1 same-batch uniqueness**

- Page: `/workspace`
- Do: AI 起草, batch size ≥ 2, confirm tactical board
- Network: `POST /submit-dsl` with `variant_planning_policy=exact_main_visual_balanced`,
  no `reservation_conflict_mode`, `batch_size>=2`
- Backend: planner uniqueness / coverage diagnostics
- UI: one task_id, completed variants

**B — L2 explicit ENFORCE success**

- Page: none required; replay `submit-dsl` with `"reservation_conflict_mode":"ENFORCE"`
- Network: field present; 202
- Backend: admitted ENFORCE, lease configured, reservation controller
- UI: if same session, queue card for returned `task_id`

**C — two concurrent ENFORCE, same FP**

- Same-page: submit B after A’s 202, or two tabs, or second via API
- Inspect two `task_id`s, statuses, diagnostics summary conflict counts
- UI: both IDs visible in one tab if both submitted there

**D — ordinary UI omitted + local 100% canary**

- Page: `/workspace` AI 起草 (balanced, omit mode)
- Pre: rollout enabled, tenant on allowlist, balanced bps 10000, kill
  switch false, lease valid, readiness READY
- Network: omit `reservation_conflict_mode`
- Backend: `rollout-status`; task metadata ENFORCE / `ROLLOUT_CANARY`
- UI: normal completed task if promoted

**E — kill switch**

- Set `RESERVATION_ROLLOUT_KILL_SWITCH=true`, same omitted UI
- Backend: omitted OFF; rollout-status shows kill switch
- UI: still renders (OFF), no special banner

**F — restart persistence**

- Submit, restart frontend, open workspace
- `GET /api/v1/tasks/today` hydrate; task_id unchanged

## 26. Evidence Capture Plan

Capture: UI before submit; Network request JSON (no secrets);
Task A/B `task_id`; statuses; output/history; rollout-status;
readiness; diagnostics summary; server log excerpts without
owner-attempt IDs or HMAC/assignment secret.

## 27. Findings

No source-proven `VAR3D2IA2-RF-01` … `RF-10`.

Notes (not defects): 极速裂变 is legacy; exact has no Vue control;
Philippine runbook diagnostics URL prefix differs from source;
blank-DB omitted canary is gated by readiness evidence.

## 28. Required Markers

- UI_PRIMARY_TASK_FLOW_REACHES_PUBLIC_L2_ADMISSION_PROVEN: **PASS**
- UI_ORDINARY_REQUEST_RESERVATION_FIELD_OMISSION_PROVEN: **PASS**
- END_TO_END_OMITTED_VS_EXPLICIT_OFF_SEMANTICS_PROVEN: **PASS**
- UI_CAN_REACH_CANARY_ELIGIBLE_PLANNING_POLICY_PROVEN: **PASS**
- L1_UI_FLOW_STILL_REACHES_SAME_BATCH_UNIQUENESS_PROVEN: **PASS**
- L2_UI_FLOW_CAN_REACH_RESERVATION_AUTHORITY_PROVEN: **PASS**
- UI_SERVER_OWNED_TASK_ID_CONTRACT_PROVEN: **PASS**
- LOCAL_CONCURRENT_L2_TEST_PATH_IDENTIFIED: **PASS**
- CONTROLLED_CANARY_NORMAL_UI_REQUIRES_NO_SPECIAL_CONTROL_PROVEN: **PASS**
- LOCAL_FULLSTACK_STARTUP_COMMANDS_IDENTIFIED: **PASS**

## 29. Final Recommendation

Proceed to manual E2E without a Vue change.

Use `/workspace` + **AI 起草** for canary-eligible omitted requests.
Use API replay for explicit OFF/ENFORCE. Use same-page submit-after-ACK
for concurrency. Configure backend rollout/lease/readiness before
Scenario D.

## 30. Final Git Status

Recorded after this artifact was added:

```text
git rev-parse HEAD
a518aa1f24bf94893821c0c465c05d5bb2e7aaf4

git status --short
?? doc/investigations/VAR001_PHASE3D2IA2_UI_API_WIRING_AUDIT.md
```

Production/frontend source unmodified by this audit.

VAR001_PHASE3D2IA2_UI_WIRING_READY_FOR_MANUAL_E2E
