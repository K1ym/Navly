# Projections

本目录负责 theme / service truth 的内部构建。

当前已具备：

- `finance_summary_service_projection.py`
  - 从 finance canonical + prerequisite state 收敛 owner-facing summary object
- `staff_board_service_projection.py`
  - 从 staff canonical + backbone state 收敛 owner-facing summary object
- `daily_overview_service_projection.py`
  - 聚合 member / staff / finance 三个已发布 service object
- `capability_explanation_service_projection.py`
  - 把 readiness / service 结果收敛成 companion explanation service object
