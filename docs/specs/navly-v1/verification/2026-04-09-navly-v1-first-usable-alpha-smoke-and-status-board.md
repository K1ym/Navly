# 2026-04-09 Navly_v1 First Usable Alpha Smoke And Status Board

日期：2026-04-09  
状态：alpha-candidate-gate  
用途：定义 Navly_v1 “第一个可用版本”的 smoke baseline、状态板与 full phase-1 边界

---

## 1. 文档目的

本文档回答：

1. 什么叫 Navly_v1 的 **first usable alpha**
2. 哪些检查通过后，才可以把当前版本称为“第一个可用版”
3. 它与 **full phase-1** 的边界差在哪里
4. 当前实现栈距离这条线还有什么

---

## 2. first usable alpha 的定义

first usable alpha 不是 “某条 demo 路径能跑一次”。

它的正式定义是：

> 在 `WeCom + OpenClaw` 第一入口域中，`member_insight` 这条最小 capability slice 已具备
> **受控权限入口 + 真实数据接入形态 + formal owner surface + runtime 默认消费 + smoke 可复验**
> 的第一条可实际试用链路。

最小主语固定为：

- `capability_id = navly.store.member_insight`
- `service_object_id = navly.service.store.member_insight`

---

## 3. Alpha 通过标准

### 3.1 数据中台

必须同时成立：

1. `Qinqin v1.1` 的 8 个正式端点已进入 formal governance registry
2. `member_insight` vertical slice 已支持 fixture / live transport 形态
3. `member_insight` 已发布 formal owner-side `capability_readiness_response`
4. `member_insight` 已发布 formal owner-side `theme_service_response`
5. runtime 不再依赖 data-platform 内部 summary/backbone shape

### 3.2 权限与入口

必须同时成立：

1. bridge 入口继续先过 `auth-kernel` Gate 0
2. runtime 继续显式做 capability access decision
3. `decision_ref` / `state_trace_ref` / `run_trace_ref` 仍可回链

### 3.3 验证

必须通过以下 smoke baseline 脚本：

```bash
bash scripts/validate-first-usable-alpha-smoke.sh
```

说明：

- `scripts/validate-first-usable-alpha-smoke.sh` 是当前 alpha smoke baseline 的单一命令源
- 它验证的是最小可用链路，不代表 full phase-1 全面完成

---

## 4. 当前状态板

### 4.1 main 分支

截至 2026-04-09，`main` 还**不应**被描述为 first usable alpha。

原因：

- `ASP-27` / `ASP-28` / `ASP-29` / `ASP-30` 形成的 data-platform + runtime 闭环仍在 stacked PR 中推进
- 因此 `main` 还不能作为当前 alpha authoritative answer

### 4.2 当前 stacked implementation train

以下 PR 栈共同构成当前 alpha candidate：

- `#24`：ASP-28 `member_insight` live transport backbone
- `#26`：ASP-27 Qinqin contract governance registry freeze
- `#27`：ASP-29 formal owner-side readiness / theme service surface
- `#28`：ASP-30 runtime consumes formal owner surface

结论：

> 当以上 PR 栈合入并且 3.3 中的 smoke baseline 继续通过时，可把 Navly_v1 标记为 **first usable alpha reached**。

---

## 5. Alpha 与 Full Phase-1 的边界

### 5.1 alpha 已覆盖

- 最小 capability：`member_insight`
- 第一条真实数据接入形态：Qinqin member 两个主端点
- formal readiness / theme service surface
- runtime 默认消费 formal owner surface
- 受控权限入口与最小 trace closure

### 5.2 full phase-1 仍未覆盖

以下仍属于 full phase-1，而不是 alpha：

- member finance 面：`recharge_bill` / `account_trade`
- staff / workforce 面：`person` / `clock` / `market`
- commission setting / quality / coverage / backfill state
- `daily_overview` / `staff_board` / `finance_summary` / `capability_explanation` 全量 service set
- auth-kernel governance / outcome surface 完整闭环
- bridge capability-oriented tool publication、dispatch / resume / trace linkage 全闭环
- full phase-1 acceptance / regression baseline

---

## 6. 总控答案

如果用户问：

> “Navly_v1 现在是否已经到第一个可用版本？”

authoritative answer 应为：

- 对 `main`：**还没有**
- 对当前 `ASP-27/28/29/30` stacked implementation train：**达到 alpha candidate，待合入并复跑 smoke 后可正式宣布 reached**

如果用户问：

> “Navly_v1 是否已经完成 full phase-1？”

authoritative answer 应为：

- **没有**
- full phase-1 仍需继续完成 `ASP-21`、`ASP-32` 至 `ASP-40` 这一后半程实现链
