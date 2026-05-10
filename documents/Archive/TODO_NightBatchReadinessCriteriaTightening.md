# TODO: Night Batch Readiness Criteria Tightening

> **ステータス: 完了（2026-05-10）**
> GitHub Issue #288 · PR #290 にて対応済み。

## 対応内容

- `prices_daily == 0` を `READY_WITH_WARNINGS` から `BLOCKED` に昇格
- `features == 0` を `READY_WITH_WARNINGS` から `BLOCKED` に昇格
- `_generate_warnings()` からこれら2条件の警告行を削除（BLOCKED ステータス自体が問題を伝達するため）
- テスト追加: `prices_daily=0` / `features=0` いずれも `BatchStatus.BLOCKED` を返すことを確認
- `signals == 0` は戦略上ありうる正常系（市場レジームが Bear の日など）のため BLOCKED 昇格は見送り

## Background

Night Batch の最終判定は `READY / READY_WITH_WARNINGS / BLOCKED` で返している。

対象実装:

- `src/kabusys/operations/night_batch_report.py`
- `scripts/run_night_batch_report.py`

## Problem

`prices_daily == 0` / `features == 0` が warning 止まりのため、夜間更新が実質不完全でも `READY` または `READY_WITH_WARNINGS` で流れる余地があった。

## Done Criteria

- [x] 判定基準が運用手順と一致している
- [x] `READY` の意味が誤解なく説明できる
- [x] データ欠損時に過度に楽観的な判定を返さない
