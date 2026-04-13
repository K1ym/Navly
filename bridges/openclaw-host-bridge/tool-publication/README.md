# First-Party Host Publication

本目录承载 Navly first-party `skill -> tool -> capability` 宿主发布面。

当前 closeout 已落地：

- `host-skill-surface.seed.json`
- `host-tool-surface.seed.json`
- `first-party-host-surface.mjs`
- `first-party-tool-publication.manifest.json`
- capability/service/auth vocabulary 对齐后的 real discovery join

当前发布面规则：

- host-visible tools 只暴露 capability/service 主语
- tool invocation 必须挂带 `request_id`、`trace_ref`、`access_context_envelope`、`decision_ref`
- `host_agent_id` 只表达宿主隔离容器，不表达权限真相
- capability/service truth 仍由 `platforms/data-platform/**` 与 `platforms/auth-kernel/**` 持有

当前 first-party surfaces：

- 7 个 host skills
- 10 个 host tools
- manager-facing `daily_overview` / `member_insight` / `finance_summary` / `staff_board` / `capability_explanation`
- operator-facing `sync_status` / `backfill_status` / `rerun_sync` / `trigger_backfill` / `quality_report`

当前语义：

- manager-facing 5 能力默认走 persisted owner surface / aggregate / fallback surface
- operator-facing 5 能力默认走 formal operator surface
- `sync_status` / `backfill_status` / `quality_report` 读取 persisted PostgreSQL truth snapshot
- `rerun_sync` / `trigger_backfill` 执行 repo-authoritative Temporal workflow semantics，并回写 persisted truth snapshot

当前不做：

- upstream OpenClaw patch
- plugin skill 作为 Navly 最终产品面
- source endpoint / SQL / internal table 暴露为 host tools
