# 2026-04-11 Data Platform Nightly Sync Currentness And Backfill Planner

日期：2026-04-11  
状态：phase-1-productionization-followup  
用途：把 nightly sync 的 currentness-first / backlog-carry-forward 策略冻结成 governed policy 与 planner slice

---

## 1. 目标

这轮不是把 `Temporal` 或 production scheduler 一次做完。

这轮先把下面这件长期正确的事落成正式对象：

> 当 nightly access window 只有 `03:00-04:00`，而历史 backlog 很大时，数据中台必须先保护最新业务日 currentness，再继续历史 backfill，而且下一晚必须从上次断点继续，而不是每晚重新从头算。

---

## 2. 当前要解决的具体问题

如果没有正式 planner，系统很容易退化成以下坏状态：

1. 今天先补历史，结果最新业务日没保住
2. 每晚都重新扫一遍缺口，但没有 carry-forward cursor
3. profile / transaction / daily-full-replace 三种端点被同一条粗糙 cron 混着跑
4. latest usable state 能回答“现在是不是最新”，却不能回答“下一步应该拉哪一天”

---

## 3. Governed Policy Object

当前 authoritative objects：

- `platforms/data-platform/contracts/nightly-sync-policy-entry.contract.seed.json`
- `platforms/data-platform/directory/nightly-sync-policy.seed.json`

当前冻结的 Qinqin nightly policy：

- timezone：`Asia/Shanghai`
- activation：`03:10`
- formal access window：`03:00-04:00`
- currentness priority：`target_business_date_first`
- backfill fill direction：`latest_to_oldest`
- carry-forward cursor：`true`
- default page size：`200`

增量策略差异：

- `business_window_incremental`
  - 最新目标日优先
  - 允许历史 backfill
- `daily_full_replace`
  - 最新目标日优先
  - 允许历史 backfill
- `profile_refresh_windowed`
  - 只做近窗口刷新
  - 不默认排入深历史 backfill

---

## 4. Planner Slice

authoritative planner module：

- `platforms/data-platform/ingestion/nightly_sync_planner.py`
- `platforms/data-platform/sync-state/nightly_sync_cursor_state.py`

planner 的输入：

- source system
- org
- target business date
- expected business dates
- latest usable endpoint states
- endpoint increment strategies
- governed nightly sync policy

planner 的输出：

- `currentness_tasks`
- `backfill_tasks`
- endpoint-scoped progress view
- endpoint-scoped nightly sync cursor state

关键规则：

1. first launch：
   - 先排 target business date
   - 再把 older missing business dates 按 newest -> oldest 排队
2. follow-up launch：
   - 若 target 已 current，则不再重复排 currentness task
   - 历史 backlog 从上次 newest missing date 继续往前
3. profile endpoints：
   - 当前只做近窗口刷新，不默认进入深历史补数

cursor state 回答：

- target business date 现在是不是还欠 currentness
- 历史 backlog 现在是不是还欠补数
- 下一步应该先跑哪一个 business date
- 当前 cursor 属于 `currentness_pending`、`backfill_pending` 还是 `current_and_complete`

---

## 5. 当前边界

本轮明确不做：

1. production worker / Temporal 调度器
2. 自动限流 / 动态配额 / 失败重试 budget
3. tenant 级真实执行排程
4. PostgreSQL persisted cursor ledger

所以这轮的定位是：

- **先把 planning semantics 做对**
- 再把具体 scheduler runtime 接上

---

## 6. 为什么这轮值得先做

当前 phase-1 已经有：

- endpoint increment strategy
- latest usable state
- commission-setting backfill semantics

但还缺：

- generic nightly planner
- generic carry-forward backlog rule
- profile / transaction / full-replace 的统一 planning contract

如果不先补这层，后续即使接上 production scheduler，也会把错误策略固化进去。
