# Tool Publication Backbone

本目录承载 capability -> host tool publication。

当前 phase-1 已实现：

- capability-oriented `tool_publication_manifest`
- publication refresh / warmup local backbones
- host-visible tool names 只围绕 `capability_id` / `service_object_id`

当前仍**不**实现：

- live OpenClaw tool registration side effects
- source endpoint / SQL / internal table 暴露
- bridge 内部业务路由
