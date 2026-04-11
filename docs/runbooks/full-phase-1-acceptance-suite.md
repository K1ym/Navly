# Full Phase-1 Acceptance Suite

日期：2026-04-11  
状态：active-acceptance-runbook  
适用范围：Navly_v1 full phase-1 completion board 与 authoritative go/no-go closure

## 1. 单一入口

```bash
bash scripts/validate-full-phase1-acceptance-suite.sh
```

这就是 current authoritative acceptance suite。

## 2. 套件内容

该 suite 顺序执行：

1. `bash scripts/validate-first-usable-alpha-smoke.sh`
2. `bash scripts/validate-remaining-phase1-live-transport.sh`
3. `python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'`

## 3. 怎么判读结果

### 3.1 `alpha`

- 如果第 1 步通过，则 `alpha` 在当前 completion board 中为 `reached`

### 3.2 `full phase-1`

- 如果 1 / 2 / 3 步都通过，则 `full phase-1` 为 `reached`

### 3.3 `go/no-go`

- 当前 authoritative go/no-go answer 是：
  - `GO`
- 触发条件就是：
  - `bash scripts/validate-full-phase1-acceptance-suite.sh` 全绿

## 4. 和历史 alpha 文档的关系

- `docs/specs/navly-v1/verification/2026-04-09-navly-v1-first-usable-alpha-smoke-and-status-board.md`
  - 现在只作为 historical alpha gate snapshot 阅读
- 当前 current-state answer 以：
  - `docs/specs/navly-v1/verification/2026-04-11-navly-v1-full-phase-1-acceptance-suite-and-completion-board.md`
  - `bash scripts/validate-full-phase1-acceptance-suite.sh`
  为准

## 5. 不在这张 completion board 里的内容

不要把以下内容重新塞回 full phase-1 acceptance suite：

- real upstream credential replays
- tenant-specific secrets handling
- post-phase-1 orchestration / UI / multi-channel expansion
