# Nightly Sync Currentness And Backfill Planner

日期：2026-04-11  
状态：active-planning-runbook  
适用范围：Qinqin nightly sync 的 currentness-first / backlog-carry-forward planning path

## 1. 这份 runbook 回答什么

回答三个操作问题：

1. 今天晚上的 target business date 应该先拉什么
2. 历史 backlog 该从哪一天继续
3. 哪些 endpoint 不该被默认塞进深历史 backfill

## 2. Governed Source Of Truth

- `platforms/data-platform/directory/nightly-sync-policy.seed.json`
- `platforms/data-platform/ingestion/nightly_sync_planner.py`
- `platforms/data-platform/sync-state/nightly_sync_cursor_state.py`

## 3. 当前 planner 规则

### 3.1 交易类 / 日级全量类

- 先保 target business date
- 再补 older missing business dates
- backfill 顺序固定为 `latest_to_oldest`
- 下一晚继续沿用同一缺口方向，不重新从最老处开始

### 3.2 档案类

- 默认只做近窗口刷新
- 不默认排进深历史补数

## 4. 你应该怎么读 planner 输出

### `currentness_tasks`

表示今晚必须先做的任务。

如果目标业务日还没 current，这部分永远优先于 backlog。

### `backfill_tasks`

表示在 currentness 做完以后，剩余 access window 可以继续吃掉的历史缺口。

如果这里给出的 next business date 是 `2026-04-10`，就表示：

- `2026-04-11` 已经在 currentness path 里处理
- 历史补数应该先从 `2026-04-10` 开始
- 再向更旧日期推进

### nightly sync cursor state

如果要给后续 scheduler / Temporal worker 一个稳定读取面，应优先读取 cursor state，而不是重新从日志临时推断。

它至少给出：

- `next_currentness_business_date`
- `next_backfill_business_date`
- `cursor_status`

生产 runtime 还必须满足两个条件，history 才会真的继续往前补：

- 调度入口要把 `history_start_business_date -> target_business_date` 的完整业务日窗口传给 planner，而不是只传 target day
- dispatch budget 不能只够 currentness；要额外给 backfill 独立预算，否则会出现“每天都只保最新、历史永远不推进”的饥饿状态

## 5. 当前非目标

这份 planner 目前只是 governed planning slice。

它不是：

- production cron
- Temporal workflow
- 真正的多租户执行器

所以如果你现在问“它会不会每天夜里自己跑”，答案仍然是否定的。
