# Qinqin API Docs

本目录存放 Navly 数据中台所依赖的 **Qinqin API 输入文档真相源**。

## 当前内容

- `auth-and-signing.md`
  - 共享认证、签名、访问时间窗、门店白名单
- `endpoint-manifest.md`
  - Navly 当前冻结支持的 8 个正式接口清单
- `member/`
  - 会员相关接口分页文档（1.1 ~ 1.4）
- `staff/`
  - 技师/员工相关接口分页文档（1.5 ~ 1.8）

## 配套审计文档

Qinqin 的差距审计、live 对齐结果、网页恢复材料不放在本目录，而统一放在：

- `docs/audits/qinqin/`

## 在 Navly 中的定位

本目录用于：

1. 作为数据中台字段治理的输入真相源
2. 作为 endpoint、request schema、response field 的人工审查依据
3. 作为事实层字段建模、主题层字段选择的文档依据

## 维护规则

- 这里放的是 API 输入文档，不放系统方案文档
- 如果 live 行为与文档不一致，差异记录写入 `docs/audits/qinqin/`，不要直接混写在接口说明里
- 新增接口时，必须同步更新：
  - `endpoint-manifest.md`
  - 对应分页文档
  - 审计文档（如有 live 差异）
