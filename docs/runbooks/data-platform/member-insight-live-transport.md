# Member Insight Live Transport

日期：2026-04-09  
状态：active-minimal-slice-diagnostics  
适用范围：`platforms/data-platform/` 的 `member_insight` 最小 live transport vertical slice

## 1. 目的

本手册说明当前 member insight 最小 slice 如何：

- 用 `fixture` / `live` transport 跑同一条 ingestion chain
- 写出 raw replay / endpoint run / ingestion run
- 在失败时给出明确 error taxonomy
- 在不暴露真实 secrets 的前提下完成最小 live 调试

重要说明：

- 本手册描述的是 live transport / replay diagnostics path
- 自 2026-04-12 closeout lane 起，artifact 输出不再是 intended production primary truth path
- 生产主语义应指向 PostgreSQL substrate + Temporal nightly plane

## 2. 当前范围

当前 live scope 只覆盖：

- `qinqin.member.get_customers_list.v1_1`
- `qinqin.member.get_consume_bill_list.v1_2`

当前**不**包含：

- 其余 6 个 Qinqin 端点
- 8 端点全量 canonical landing
- runtime / bridge / auth-kernel 改造

## 3. 运行方式

### 3.1 Fixture

```bash
python3 platforms/data-platform/scripts/run_member_insight_vertical_slice.py \
  --request-id req-member-insight-slice-001 \
  --trace-ref navly:trace:req-member-insight-slice-001 \
  --transport fixture \
  --org-id demo-org-001 \
  --start-time '2026-03-20 09:00:00' \
  --end-time '2026-03-24 09:00:00' \
  --requested-business-date 2026-03-23 \
  --app-secret '<redacted-app-secret>' \
  --output-dir /tmp/member-insight-fixture
```

### 3.2 Live

可通过 CLI 参数或环境变量提供 live 配置。

```bash
QINQIN_API_BASE_URL='http://<redacted-host>' \
QINQIN_API_REQUEST_TIMEOUT_MS='15000' \
QINQIN_API_AUTHORIZATION='Bearer <redacted-access-token>' \
QINQIN_API_TOKEN='<redacted-token>' \
python3 platforms/data-platform/scripts/run_member_insight_vertical_slice.py \
  --request-id req-member-insight-live-001 \
  --trace-ref navly:trace:req-member-insight-live-001 \
  --transport live \
  --org-id demo-org-001 \
  --start-time '2026-03-20 09:00:00' \
  --end-time '2026-03-24 09:00:00' \
  --requested-business-date 2026-03-23 \
  --app-secret '<redacted-app-secret>' \
  --output-dir /tmp/member-insight-live
```

### 3.3 Fail-Closed 规则

- `--transport live` 且缺少 `base_url` 时，脚本直接报错退出
- live mode 不自动回退到 fixture
- transport 级异常会写入 endpoint run 和 replay artifact，而不是静默吞掉

## 4. 输出产物

### 4.1 Historical Run Truth

- `historical-run-truth/ingestion-runs.json`
- `historical-run-truth/endpoint-runs.json`
- `vertical-slice-summary.json`
  - 当前 diagnostic runner 的顶层摘要输出
  - 会保留 CLI 提供的 `request_id` / `trace_ref`

### 4.2 Raw Replay

- `raw-replay/raw-response-pages.json`
  - source page truth
- `raw-replay/transport-replay-artifacts.json`
  - transport replay truth

### 4.3 Canonical / Latest State

- `canonical/customer.json`
- `canonical/customer_card.json`
- `canonical/consume_bill.json`
- `canonical/consume_bill_payment.json`
- `canonical/consume_bill_info.json`
- `latest-state/latest-usable-endpoint-state.json`
- `latest-state/vertical-slice-backbone-state.json`

这些文件的定位：

- diagnostics / replay / smoke artifacts
- 不等于 production authoritative persistence

## 5. Error Taxonomy

当前最小 slice 显式使用以下 taxonomy：

- `transport_config_error`
  - live transport 配置缺失或非法
- `transport_timeout_error`
  - 请求超时
- `transport_network_error`
  - DNS / 连接等网络层错误
- `transport_http_status_error`
  - HTTP 非 2xx
- `transport_invalid_json_error`
  - HTTP 成功但响应不是合法 JSON
- `transport_invalid_payload_error`
  - JSON 合法但顶层不是 object
- `transport_unexpected_exception`
  - 未分类 transport 异常
- `source_business_error`
  - source 返回 JSON，但 `Code != 200`

## 6. 判读规则

- `endpoint_status=completed`
  - source 成功，且分页完成
- `endpoint_status=source_empty`
  - source 成功，但窗口内无数据
- `endpoint_status=failed`
  - transport error 或 source business error

只有 `completed` / `source_empty` 端点会进入 canonical landing。  
失败端点不会把 partial page truth 当成 canonical truth 落下去。

## 7. Secrets 约束

- replay artifact 会保留 request headers 的 key，但会对敏感值做 `<redacted>` 处理
- 不要把真实 `Authorization`、`Token`、`AppSecret` 写进 runbook、README、spec 或审计文档
