# OpenClaw Local Source In Navly

状态：reference  
用途：说明 Navly 仓内 `upstreams/openclaw/` 源码的定位与使用边界

## 本地位置

- `upstreams/openclaw/`

## 在 Navly 中的定位

OpenClaw 在 Navly 中不是普通第三方依赖，而是：

- 已纳入仓库的上游源码
- 可直接参考、复用、裁剪和受控集成的基础内核

## 当前建议保留能力

- WeCom 接入
- Gateway
- Session / Workspace
- AGENTS / Skills / bootstrap 机制
- 身份 / 角色 / scope / conversation 绑定语义
- Gate 0 / 治理 / 审计相关能力

## 当前不建议直接继承的部分

- 历史业务编排逻辑
- 旧业务问答路径
- 与 Navly 数据中台目标冲突的局部实现

## 原则

- OpenClaw 是 Navly 的上游能力来源，不是 Navly 业务逻辑的最终边界
- 复用时必须服从 Navly 的新分层与新目录结构
- 不把 OpenClaw 当黑盒，也不把 Navly 业务代码塞回 OpenClaw 目录
