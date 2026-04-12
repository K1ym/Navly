# 2026-04-12 Navly First-Party Host Live Validation

日期：2026-04-12  
状态：active  
适用范围：ASP-50 / ASP-52 / ASP-53 closeout 验收

## 1. 目的

本手册用于验证：

- Navly first-party host skill/tool surface 是否已被宿主识别
- WeCom/OpenClaw 消息是否能进入 Navly first-party capability path
- 店长在 WeCom 中是否能直接使用 manager-facing surface
- `agent_id` 是否只影响 host isolation，而不影响最终授权真相

## 1.1 Live Cutover

先把 Navly first-party host plugin 安装到 OpenClaw profile：

```bash
node bridges/openclaw-host-bridge/scripts/install-navly-first-party-host-plugin.mjs \
  --repoRoot /opt/navly \
  --profileDir /root/.openclaw-prod \
  --dataPlatformEnvPath /etc/navly/data-platform.env \
  --defaultChannel wecom \
  --channelAccountRef openclaw-host-bridge:channel-account:wecom-main

systemctl restart openclaw-gateway.service
```

安装后应检查：

- `~/.openclaw-prod/extensions/navly-first-party-host` 已存在
- `~/.openclaw-prod/openclaw.json` 中 `plugins.allow` 包含 `navly-first-party-host`
- `plugins.entries.navly-first-party-host.enabled = true`

## 2. First-Party Skill List

- `navly-store-daily-overview`
- `navly-store-member-insight`
- `navly-store-finance-summary`
- `navly-store-staff-board`
- `navly-capability-explain`
- `navly-sync-ops`
- `navly-data-quality`

## 3. First-Party Tool List

- `navly_daily_overview`
- `navly_member_insight`
- `navly_finance_summary`
- `navly_staff_board`
- `navly_explain_unavailable`
- `navly_sync_status`
- `navly_backfill_status`
- `navly_rerun_sync`
- `navly_trigger_backfill`
- `navly_quality_report`

## 4. Store-Manager Validation Questions

问题 1：
`今天门店概览怎么样？`

预期：

- 命中 `navly-store-daily-overview`
- 调用 `navly_daily_overview`
- `capability_id = navly.store.daily_overview`
- runtime 返回 `result_status=answered`
- reply 中包含 overview summary / key metrics / risk flags

问题 2：
`帮我看下会员洞察`

预期：

- 命中 `navly-store-member-insight`
- 调用 `navly_member_insight`
- `capability_id = navly.store.member_insight`
- runtime 返回 `result_status=answered`
- reply 中包含 formal service object，不暴露 source endpoint 名

问题 3：
`看下今天充值和流水`

预期：

- 命中 `navly-store-finance-summary`
- 调用 `navly_finance_summary`
- `capability_id = navly.store.finance_summary`
- 在 phase-1-ready data path 上，runtime 返回 `result_status=answered`
- reply 中包含 `navly.service.store.finance_summary` formal service object
- 若 live data 真实缺数，仍必须 fail-close 为结构化 fallback，不暴露 source endpoint / SQL

问题 4：
`看看员工看板`

预期：

- 命中 `navly-store-staff-board`
- 调用 `navly_staff_board`
- `capability_id = navly.store.staff_board`
- 在 phase-1-ready data path 上，runtime 返回 `result_status=answered`
- reply 中包含 `navly.service.store.staff_board` formal service object
- 若 live data 真实缺数，仍必须返回结构化 not-ready explanation

问题 5：
`为什么我现在拿不到财务汇总？`

预期：

- 命中 `navly-capability-explain` 或来自前一能力的 explanation path
- reply 中包含 capability-oriented explanation object
- 必须能回链 `decision_ref` / `trace_ref`

## 5. Operator Boundary Validation

验证：

- 让 `store_staff` 通过 `admin` agent 容器请求 `navly_finance_summary`

预期：

- `agent_id=admin` 只体现在 host carrier metadata
- auth-kernel 仍返回 `capability_not_granted`
- 不产生 runtime capability handoff
- 证明 agent selection 不是 authorization truth

## 6. Regression Command

```bash
node --test bridges/openclaw-host-bridge/tests/navly-first-party-host-plugin.test.mjs \
  bridges/openclaw-host-bridge/tests/first-party-host-surface.test.mjs \
  bridges/openclaw-host-bridge/tests/first-party-live-handoff.test.mjs \
  bridges/openclaw-host-bridge/tests/milestone-b-auth-linkage.test.mjs \
  runtimes/navly-runtime/tests/milestone-b-guarded-execution.test.mjs \
  runtimes/navly-runtime/tests/milestone-b-owner-adapter-closure.test.mjs \
  platforms/auth-kernel/tests/milestone-b-backbone.test.mjs
```
