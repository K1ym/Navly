# 2026-04-11 Navly_v1 Full Phase-1 Acceptance Suite And Completion Board

日期：2026-04-11  
状态：phase-1-acceptance-suite-governed  
用途：冻结 current authoritative acceptance suite、completion board 与 full phase-1 的 go/no-go answer

---

## 1. 目标

`ASP-40` 的目标不是再写一份 informal status note。

它的目标是：

> 把 full phase-1 的 acceptance suite、completion board、alpha vs full phase-1 status、以及最终的 authoritative go/no-go answer 都落成同一份可机械运行、可 review、可被后续窗口直接消费的正式验证资产。

---

## 2. Authoritative Acceptance Suite

当前 single authoritative command 是：

```bash
bash scripts/validate-full-phase1-acceptance-suite.sh
```

该 acceptance suite 当前冻结 3 步：

| Step | Label | Command | Covers | Status |
| --- | --- | --- | --- | --- |
| `alpha_smoke` | `First usable alpha smoke baseline` | `bash scripts/validate-first-usable-alpha-smoke.sh` | `D e2e acceptance` | `green` |
| `remaining_live_transport` | `Remaining Qinqin live transport validation matrix` | `bash scripts/validate-remaining-phase1-live-transport.sh` | `D e2e acceptance` + `E regression baseline` | `green` |
| `full_data_platform_regression` | `Full data-platform contract and owner-surface regression` | `python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'` | `A boundary verification` + `B contract consistency` + `C docs consistency` + `E regression baseline` | `green` |

结论：

- 这套 command sequence 就是 current authoritative acceptance suite
- 后续如果 full phase-1 gate 变化，应先改这套 suite，再改 completion board

---

## 3. Completion Board

### 3.1 Verification Completion Board

| Board group | Board item | Status | Evidence |
| --- | --- | --- | --- |
| `verification` | `A boundary verification` | `green` | `python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'` |
| `verification` | `B contract consistency` | `green` | `python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'` |
| `verification` | `C docs consistency` | `green` | `python3 -m unittest discover -s platforms/data-platform/tests -p 'test_*.py'` |
| `verification` | `D e2e acceptance` | `green` | `bash scripts/validate-full-phase1-acceptance-suite.sh` |
| `verification` | `E regression baseline` | `green` | `bash scripts/validate-full-phase1-acceptance-suite.sh` |

### 3.2 Milestone Completion Board

| Board group | Board item | Status | Evidence |
| --- | --- | --- | --- |
| `milestone` | `alpha` | `reached` | `bash scripts/validate-first-usable-alpha-smoke.sh` |
| `milestone` | `full phase-1` | `reached` | `bash scripts/validate-full-phase1-acceptance-suite.sh` |
| `decision` | `go/no-go` | `go` | `authoritative answer: GO` |

---

## 4. Authoritative Go/No-Go Answer

当前 authoritative go/no-go answer 为：

> **GO**: `bash scripts/validate-full-phase1-acceptance-suite.sh` 通过后，可把当前 repo state 回答为 `full phase-1 reached`。

这句话意味着：

- `alpha` 已不再只是 candidate，而是 accepted baseline 的前置层
- `full phase-1` 的答案不再停留在“还在 stacked PR 中”
- 当前 repo 可以通过 authoritative acceptance suite 给出结构化 completion board

---

## 5. Historical Boundary

`2026-04-09-navly-v1-first-usable-alpha-smoke-and-status-board.md` 仍然保留，因为它记录了 alpha gate 的历史快照。

但从 `ASP-40` 开始：

- `2026-04-09` 文档是 **historical alpha gate snapshot**
- 当前 authoritative current-state answer 以本文和 `scripts/validate-full-phase1-acceptance-suite.sh` 为准

---

## 6. Post-Phase-1 Out Of Scope

以下仍属于 post-phase-1，不应被重新塞回 completion board：

- real upstream credential replays 与 tenant-specific secrets handling
- richer orchestration / UI / multi-channel expansion
- 非 WeCom + OpenClaw 的渠道扩展

这一步是为了保持：

- alpha
- full phase-1
- post-phase-1 expansion

三者边界清楚，不再混成同一张模糊状态板。
