# 2026-04-10 Commission Setting Quality And State Semantics

日期：2026-04-10  
状态：phase-1-governed  
用途：冻结 `GetTechCommissionSetList` 的 quality / latest-state / backfill / completeness 语义

---

## 1. 目标

`GetTechCommissionSetList` 是 `Qinqin v1.1` 中最容易污染 Phase-1 状态语义的端点：

- 它是 `daily_full_replace`
- 它要求额外 runtime auth headers
- 它可能返回 `404 / 暂无数据`

本规格的目标不是补一条局部特判，而是把该端点的 L2 语义正式拆成受治理对象。

---

## 2. 必须分开的对象

本端点至少要分成以下对象：

1. historical run truth
   - endpoint run 的成功 / 失败 / `source_empty`
2. latest usable endpoint state
   - 当前哪一天可用
3. `backfill_progress_state`
   - 当前日是否 current
   - 历史窗口是否补齐
4. `field_coverage_snapshot`
   - 当前 snapshot 实际观测到了哪些 governed fields
5. `schema_alignment_snapshot`
   - 当前 payload 是否仍和 field catalog / response shape 对齐
6. `commission_setting_completeness_state`
   - 结合 latest state / backfill / quality 后，当前该 slice 是否 complete

禁止：

- 用一条 `partial` 混写 auth failure、source-empty、schema drift、currentness gap
- 让 runtime / bridge / auth 解释 `1.8` 的 state semantics

---

## 3. Source-Empty 语义

`1.8` 的空返回语义通过以下 governed object 冻结：

- `platforms/data-platform/directory/source-variance.seed.json`
- `variance_id = qinqin.response.tech-commission-set-source-empty-governed`

冻结规则：

- `404 / 暂无数据`
- 或 `RetData = []`

都按：

- `source_empty`
- 零行 `commission_setting`
- 零行 `commission_setting_detail`
- 目标业务日的 current zero-row full-replace snapshot

这意味着：

- 它不是 auth failure
- 它不是 schema drift
- 它不应该把 latest-state 强行打成 unknown / partial

---

## 4. Auth / Header 语义

`Authorization` / `Token` 的要求已经在：

- `qinqin.auth.tech-commission-set-runtime-headers-required`

中冻结。

当端点因 auth 失败而不可用时：

- historical run truth 记录 `source_auth_error`
- latest usable state 标记 `unavailable`
- completeness / quality issue 必须带出该 variance ref

禁止把这类问题伪装成“暂时没数据”。

---

## 5. Business-Day Policy

`backfill_progress_state` 必须消费：

- `platforms/data-platform/directory/business-day-boundary-policy.seed.json`

至少保留：

- `business_day_boundary_policy_id`
- `business_day_boundary_local_time`
- `timezone`

原因：

- `currentness` 不是 runtime 临时口径
- `业务日` 切换边界属于 data-platform governed object

---

## 6. Currentness 与 Backfill 的区别

`currentness` 回答：

> 目标业务日现在是不是可用？

`backfill_progress` 回答：

> 要求覆盖的业务日窗口是不是补齐了？

因此允许出现：

- `currentness = current`
- `backfill_progress_status = incomplete`

即：

- 当天已经 current
- 但历史窗口仍存在 backfill gap

这两个语义不能混成一个布尔值。
