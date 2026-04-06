# AGENTS.md - Navly Workspace

## Session Startup

1. Read this file first.
2. Treat this workspace as **Navly**, not as a continuation of `claw2qinqin`.
3. Treat `upstreams/openclaw/` as upstream source code that is available for reference, reuse, and controlled integration — not as the place to casually implement Navly product logic.
4. Treat Navly's current long-term assets as:
   - the **data platform / data middle platform**
   - the **permission and session-binding kernel** built on OpenClaw / WeCom concepts
5. Treat older business orchestration, prompt glue, ad-hoc routing, and temporary query logic as replaceable layers unless explicitly promoted into the new architecture.

## Project Direction

Navly is being rebuilt around a **data middle platform**.

The goal is not to preserve old implementation shape. The goal is to produce a system that is:

- globally coherent
- structurally correct
- complete enough to be reused by future upper layers
- easy to audit, backfill, and reason about

When making decisions, optimize for the future Navly architecture, not for preserving local legacy code paths.

## Decision Bias

Default to the **best overall solution**, not the smallest patch.

Prioritize, in order:

1. correctness of system boundaries
2. correctness of source-of-truth semantics
3. end-to-end completeness of the target change
4. maintainability of the resulting structure
5. local diff size

A smaller diff is **not** better if it leaves the architecture more confusing, more brittle, or more internally inconsistent.

## Change Strategy

When working on a task:

- prefer **global, coherent fixes** over local band-aids
- prefer **root-cause fixes** over symptom suppression
- prefer **structural cleanup** over compatibility hacks when the hack would become future debt
- prefer **complete working slices** over partially-fixed chains

If a change touches one part of a chain, check the connected layers too.

Examples:

- If you change ingestion semantics, also check sync state, completeness, projections, and docs.
- If you change API field handling, also check contracts, mapping, storage, audits, and field governance docs.
- If you change permission behavior, also check binding data, session routing, governance logs, and operator-facing docs.

## Do Not Default To Minimal Patches

Do **not** automatically choose:

- the smallest diff
- the least invasive patch
- the fastest local workaround
- the narrowest possible interpretation of the task

unless that option is also the most correct system-level choice.

If the right fix is broader but clearly justified, do the broader fix.

## Handle Problems Encountered During Execution

If you encounter adjacent problems that directly block, invalidate, or weaken the requested outcome:

- fix them in the same pass when reasonably bounded
- do not stop at the first superficial success condition
- do not leave behind obviously broken linked state if it is within the same architectural slice

Examples of problems to fix directly when encountered:

- inconsistent source-of-truth tables
- broken links between sync state and historical runs
- missing completeness resolver branches
- projection states that no longer match data-layer truth
- docs that would immediately mislead future implementation
- config/secrets/docs mismatch that blocks practical use

## When To Ask The User

Do **not** ask the user for every uncertainty.

Default behavior:

- make a reasonable, explicit assumption
- proceed
- record the assumption in the response or docs if relevant

Ask the user only when one of these is true:

1. the choice changes product direction in a major way
2. multiple options are equally plausible and produce materially different architectures
3. the action is destructive or irreversible
4. required credentials, external approvals, or unavailable facts cannot be inferred safely
5. the user has explicitly requested approval before proceeding

If the issue is implementation-local and the likely best option is clear, proceed without asking.

## No Hardcoding

Do **not** solve Navly tasks by hardcoding values into product logic.

Prefer:

- config over inline environment-specific values
- schema / metadata / registry driven behavior over scattered special-case branches
- shared constants or typed definitions over duplicated literals
- explicit source-of-truth tables over hidden fallback mappings in code
- documented defaults with clear ownership over magic values

Avoid hardcoding:

- tenant, corp, app, user, role, or conversation identifiers
- secrets, tokens, cookies, keys, or private endpoints
- environment-specific hosts, ports, paths, or routing targets
- API field lists, permission decisions, status mappings, or business rules that belong in governed data or config
- one-off prompt text, query routing logic, or answer selection behavior that should live in reusable architecture

If a temporary compatibility mapping is unavoidable, isolate it in one place, label it clearly, document why it exists, and state what should replace it.

## Architecture Priorities For Navly

### 1. Data Middle Platform First

Navly's data platform should become the stable truth source for:

- full target-store coverage
- full historical backfill
- API-document field governance
- ingestion runs and endpoint runs
- latest usable sync state
- completeness / answer-readiness
- projections / serving objects
- audits and replayability

### 2. Permission Kernel Second

Preserve and refine the permission/session-binding kernel around:

- actor identity
- role binding
- scope binding
- conversation binding
- Gate 0 / access control
- WeCom routing semantics
- governance and audit trails

### 3. Upper Layers Are Replaceable

Do not treat old orchestration, answer routing, deep-query glue, or prompt-driven workflows as immutable foundations.

## Data-Platform Working Rules

When touching the data platform:

- API document fields are all in scope for governance
- "captured in payload_json" is not enough to declare the requirement complete
- distinguish clearly between:
  - raw source preservation
  - canonical facts
  - state / quality
  - projection / serving
- each table must express one kind of truth only
- historical execution truth and latest-usable-state truth must not be conflated

## Documentation Rules

When the architecture changes, update docs in the same pass.

Navly docs are organized by **document purpose first**, then **domain**.

Use:

- `docs/specs/` for formal design
- `docs/architecture/` for structure and boundaries
- `docs/api/` for input truth sources
- `docs/audits/` for historical and gap analysis
- `docs/runbooks/` for operations
- `docs/reference/` for dictionaries, enums, secrets/config rules

If a doc is outdated enough to mislead future work, update it as part of the change.

## Secrets Handling

Public or reviewable docs must not contain live secrets.

Real secrets may exist only in explicitly private local materials or runtime config.

Never spread secrets from a private location into:

- specs
- audits
- public API docs
- readmes
- commit messages

## Validation Rules

Before declaring a task done, check the relevant chain end to end.

Depending on the task, this may include:

- contracts
- config
- ingestion
- state tables
- completeness
- projections
- docs
- scripts
- migration implications

Do not stop at "code compiles" if the data, state, or documentation outcome is still inconsistent.

## Red Lines

- Do not preserve a broken legacy behavior just because it already exists.
- Do not prefer minimal change over correct architecture.
- Do not ask the user questions that can be resolved by informed engineering judgment.
- Do not leave a directly-blocking adjacent defect unfixed if it is in the same bounded slice.
- Do not mix raw truth, latest state, completeness truth, and projection truth without making the boundaries explicit.
- Do not treat historical docs or audits as current truth without labeling them.
- Do not hardcode identifiers, secrets, environment values, routing decisions, or business rules that should come from config, metadata, or governed data.
- Do not put real secrets into publicly reviewable docs.

## Preferred Working Style

- Be decisive.
- Be explicit about assumptions.
- Be willing to restructure when restructuring is the right answer.
- Aim for the clean, reviewable, future-proof version of the change.
- Optimize for what Navly is becoming, not what the legacy code happened to be.
