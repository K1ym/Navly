# Migration Skeleton

本目录预留给 legacy -> new data-platform 的迁移脚本与校验逻辑。

当前已落地：

- `sql/001_nightly_sync_cursor_ledger.sql`
  - nightly sync cursor ledger 的本地/数据库建表入口
  - 当前服务于 worker persistence slice
