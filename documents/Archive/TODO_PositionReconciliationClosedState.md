# TODO: Position Reconciliation Closed State Handling

> **Status: 完了 — Issue #292 / PR #293 にて実装済み（2026-05-11）**

## Background

ポジション照合は、ブローカー側保有数量とローカル側注文履歴から作った数量を比較して差分を出している。

対象実装:

- `src/kabusys/execution/reconciler.py`

## Problem

現状のコメント上でも、`Closed` 状態は `list_active()` で取得できず、`Filled -> Closed` 遷移は未実装とされている。

このためローカル側の数量算出は、

- `Filled`
- `PartialFill`

のネット集計に依存している。

結果として、

- クローズ済み注文の扱いが曖昧
- ローカル数量とブローカー数量の差分が恒常的に残る可能性がある
- 照合レポートの信頼性が下がる

## 実装内容（Issue #292）

`DiscrepancyKind` 列挙型を `reconciler.py` に追加し、`PositionDiscrepancy` に `kind` フィールドを追加した。

```python
class DiscrepancyKind(str, Enum):
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"        # 数量不一致（異常の可能性）
    CLOSED_STATE_CONSTRAINT = "CLOSED_STATE_CONSTRAINT"  # Closed 未実装による既知制約
```

**分類ルール**: `broker_qty == 0 かつ local_qty > 0` の場合 → `CLOSED_STATE_CONSTRAINT`、それ以外 → `AMOUNT_MISMATCH`。

**対応方針の違い**:

| kind | 内容 | 対応 |
|------|------|------|
| `CLOSED_STATE_CONSTRAINT` | `Filled→Closed` 遷移未実装による既知差分 | 警告ログのみ、執行継続可 |
| `AMOUNT_MISMATCH` | 真の数量不一致（異常の可能性） | Execution 停止・調査必要 |

## TODO

- [x] `Filled -> Closed` 遷移をどう扱うべきか整理する → 将来課題として明確化
- [x] `list_active()` ベース照合の限界を文書化する → ExecutionSystem.md に記載
- [x] ローカル数量算出の基準データを見直す案を整理する → `DiscrepancyKind` による分類で対応
- [x] 差分の分類を `異常` と `既知制約` に分ける案を整理する → `DiscrepancyKind` で実装
- [x] 照合レポートの運用上の読み方を整理する → WebManual E_FailureRecovery.md に追記

## Review Points

- [x] 注文履歴ベースで十分か → 現フェーズでは十分（`DiscrepancyKind` で既知差分を区別）
- [x] ローカル側のポジションスナップショットを使うべきか → 将来課題
- [x] `Closed` 未実装のまま live でどこまで許容するか → `CLOSED_STATE_CONSTRAINT` として明示的に許容

## Done Criteria

- [x] `position_discrepancies` の解釈ルールが明確になっている
- [x] `Closed` 状態未整理による見かけ上の差分を説明できる
- [x] 将来の修正方針が TODO として追える
