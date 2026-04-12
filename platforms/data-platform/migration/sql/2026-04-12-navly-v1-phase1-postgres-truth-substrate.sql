-- Navly_v1 phase-1 closeout truth substrate
-- Authoritative production intent: PostgreSQL-first persisted truth, with
-- runtime artifacts retained only as diagnostics / replay helpers.

create schema if not exists navly_data_platform;

create table if not exists navly_data_platform.scheduler_run (
  scheduler_run_id text primary key,
  scheduler_trace_ref text not null unique,
  workflow_id text not null,
  workflow_kind text not null,
  org_id text not null,
  target_business_date date not null,
  planner_mode text not null,
  task_queue text not null,
  scheduler_status text not null,
  plan_task_count integer not null,
  dispatched_task_count integer not null default 0,
  failure_budget integer not null default 0,
  execution_trace_refs jsonb not null default '[]'::jsonb,
  started_at timestamptz not null,
  completed_at timestamptz
);

create table if not exists navly_data_platform.ingestion_run (
  ingestion_run_id text primary key,
  run_trace_ref text not null unique,
  scheduler_trace_ref text,
  workflow_id text,
  task_kind text not null,
  capability_id text not null,
  service_object_id text not null,
  source_system_id text not null,
  org_id text not null,
  requested_business_date date not null,
  window_start_at timestamptz not null,
  window_end_at timestamptz not null,
  run_status text not null,
  transport_kind text not null,
  started_at timestamptz not null,
  completed_at timestamptz,
  foreign key (scheduler_trace_ref) references navly_data_platform.scheduler_run(scheduler_trace_ref)
);

create index if not exists idx_ingestion_run_org_date
  on navly_data_platform.ingestion_run(org_id, requested_business_date desc);

create table if not exists navly_data_platform.ingestion_endpoint_run (
  endpoint_run_id text primary key,
  endpoint_run_trace_ref text not null unique,
  ingestion_run_id text not null references navly_data_platform.ingestion_run(ingestion_run_id),
  endpoint_contract_id text not null,
  org_id text not null,
  requested_business_date date not null,
  endpoint_status text not null,
  page_count integer not null,
  record_count integer not null,
  transport_kind text not null,
  error_taxonomy text,
  error_code text,
  error_message text,
  retryable boolean,
  started_at timestamptz not null,
  completed_at timestamptz
);

create index if not exists idx_endpoint_run_org_endpoint_date
  on navly_data_platform.ingestion_endpoint_run(org_id, endpoint_contract_id, requested_business_date desc);

create table if not exists navly_data_platform.ingestion_page_run (
  page_run_id text primary key,
  page_run_trace_ref text not null unique,
  endpoint_run_id text not null references navly_data_platform.ingestion_endpoint_run(endpoint_run_id),
  endpoint_contract_id text not null,
  page_index integer not null,
  replay_artifact_id text not null,
  response_record_count integer not null,
  page_status text not null,
  captured_at timestamptz not null
);

create table if not exists navly_data_platform.raw_replay_artifact (
  replay_artifact_id text primary key,
  replay_trace_ref text not null unique,
  endpoint_run_id text not null references navly_data_platform.ingestion_endpoint_run(endpoint_run_id),
  endpoint_contract_id text not null,
  requested_business_date date not null,
  page_index integer not null,
  transport_kind text not null,
  transport_outcome text not null,
  request_method text,
  request_url text,
  request_headers_redacted jsonb not null default '{}'::jsonb,
  request_payload jsonb not null default '{}'::jsonb,
  response_http_status integer,
  response_headers jsonb not null default '{}'::jsonb,
  response_body text,
  source_response_code text,
  source_response_message text,
  error_taxonomy text,
  error_code text,
  error_message text,
  retryable boolean,
  captured_at timestamptz not null
);

create table if not exists navly_data_platform.member_insight_customer_fact (
  fact_id text primary key,
  fact_trace_ref text not null unique,
  org_id text not null,
  requested_business_date date not null,
  customer_id text not null,
  payload_json jsonb not null
);

create table if not exists navly_data_platform.member_insight_customer_card_fact (
  fact_id text primary key,
  fact_trace_ref text not null unique,
  org_id text not null,
  requested_business_date date not null,
  customer_card_id text not null,
  payload_json jsonb not null
);

create table if not exists navly_data_platform.member_insight_consume_bill_fact (
  fact_id text primary key,
  fact_trace_ref text not null unique,
  org_id text not null,
  requested_business_date date not null,
  settle_id text not null,
  payload_json jsonb not null
);

create table if not exists navly_data_platform.member_insight_consume_bill_payment_fact (
  fact_id text primary key,
  fact_trace_ref text not null unique,
  org_id text not null,
  requested_business_date date not null,
  settle_id text not null,
  payment_index integer not null,
  payload_json jsonb not null
);

create table if not exists navly_data_platform.member_insight_consume_bill_info_fact (
  fact_id text primary key,
  fact_trace_ref text not null unique,
  org_id text not null,
  requested_business_date date not null,
  settle_id text not null,
  info_index integer not null,
  payload_json jsonb not null
);

create table if not exists navly_data_platform.latest_sync_state (
  state_id text primary key,
  state_trace_ref text not null unique,
  capability_id text not null,
  source_system_id text not null,
  endpoint_contract_id text not null,
  org_id text not null,
  latest_usable_business_date date,
  availability_status text not null,
  latest_run_trace_ref text,
  latest_endpoint_run_id text,
  latest_endpoint_status text,
  last_attempted_business_date date not null,
  last_attempted_status text not null,
  last_attempted_run_trace_ref text not null,
  updated_at timestamptz not null,
  unique (endpoint_contract_id, org_id)
);

create table if not exists navly_data_platform.backfill_progress_state (
  state_id text primary key,
  state_trace_ref text not null unique,
  capability_id text not null,
  endpoint_contract_id text not null,
  org_id text not null,
  target_business_date date not null,
  planner_mode text not null,
  cursor_business_date date,
  newest_missing_business_date date,
  oldest_missing_business_date date,
  remaining_gap_count integer not null,
  last_planned_business_dates jsonb not null default '[]'::jsonb,
  scheduler_trace_ref text,
  progress_status text not null,
  updated_at timestamptz not null,
  unique (endpoint_contract_id, org_id)
);

create table if not exists navly_data_platform.field_coverage_snapshot (
  snapshot_id text primary key,
  snapshot_trace_ref text not null unique,
  endpoint_contract_id text not null,
  org_id text not null,
  requested_business_date date not null,
  documented_field_count integer not null,
  observed_field_count integer not null,
  missing_field_paths jsonb not null default '[]'::jsonb,
  coverage_status text not null,
  endpoint_run_id text not null,
  run_trace_ref text not null,
  updated_at timestamptz not null
);

create table if not exists navly_data_platform.schema_alignment_snapshot (
  snapshot_id text primary key,
  snapshot_trace_ref text not null unique,
  endpoint_contract_id text not null,
  org_id text not null,
  requested_business_date date not null,
  alignment_status text not null,
  mismatch_count integer not null,
  mismatch_details jsonb not null default '[]'::jsonb,
  endpoint_run_id text not null,
  run_trace_ref text not null,
  updated_at timestamptz not null
);

create table if not exists navly_data_platform.quality_issue (
  quality_issue_id text primary key,
  issue_trace_ref text not null unique,
  endpoint_contract_id text not null,
  org_id text not null,
  requested_business_date date not null,
  quality_code text not null,
  severity text not null,
  message text not null,
  run_trace_ref text not null,
  state_trace_ref text,
  opened_at timestamptz not null
);

create table if not exists navly_data_platform.capability_readiness_snapshot (
  snapshot_id text primary key,
  state_trace_ref text not null unique,
  capability_id text not null,
  org_id text not null,
  requested_business_date date not null,
  latest_usable_business_date date not null,
  readiness_status text not null,
  reason_codes jsonb not null default '[]'::jsonb,
  blocking_dependencies jsonb not null default '[]'::jsonb,
  run_trace_refs jsonb not null default '[]'::jsonb,
  state_trace_refs jsonb not null default '[]'::jsonb,
  evaluated_at timestamptz not null,
  unique (capability_id, org_id, requested_business_date)
);

create table if not exists navly_data_platform.service_projection (
  projection_id text primary key,
  projection_trace_ref text not null unique,
  capability_id text not null,
  service_object_id text not null,
  org_id text not null,
  requested_business_date date not null,
  latest_usable_business_date date not null,
  service_status text not null,
  service_object jsonb not null default '{}'::jsonb,
  explanation_object jsonb not null default '{}'::jsonb,
  run_trace_refs jsonb not null default '[]'::jsonb,
  state_trace_refs jsonb not null default '[]'::jsonb,
  served_at timestamptz not null,
  unique (service_object_id, org_id, requested_business_date)
);
