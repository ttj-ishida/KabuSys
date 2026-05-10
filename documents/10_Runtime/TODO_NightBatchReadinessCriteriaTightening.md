# TODO: Night Batch Readiness Criteria Tightening

## Background

Night Batch の最終判定は `READY / READY_WITH_WARNINGS / BLOCKED` で返している。

対象実装:

- `src/kabusys/operations/night_batch_report.py`
- `scripts/run_night_batch_report.py`

## Problem

現状の BLOCKED 条件は主に次に依存している。

- 必須ジョブの欠落
- 必須ジョブの `failed` / `skipped`
- `signal_queue == 0`

一方で、次は warning 止まりになっている。

- `signals == 0`
- `prices_daily == 0`
- `features == 0`

このため、夜間更新が実質不完全でも `READY` または `READY_WITH_WARNINGS` で流れる余地がある。

## Concern

運用者が `night_batch_report` を「翌営業日運用可否の最終判定」として使う場合、判定が甘いと誤解を生む。

特に次は整理が必要。

- `prices_daily == 0` を BLOCKED に上げるべきか
- `features == 0` を BLOCKED に上げるべきか
- `signals == 0` は戦略上ありうる正常系か、それとも異常系か

## TODO

- [ ] `READY / READY_WITH_WARNINGS / BLOCKED` の業務定義を明文化する
- [ ] `prices_daily == 0` の扱いを決める
- [ ] `features == 0` の扱いを決める
- [ ] `signals == 0` の扱いを決める
- [ ] 必須ジョブ以外の `warning` をどこまで昇格させるか決める
- [ ] CLI / Markdown 表示文言も判定基準と整合させる

## Review Points

- [ ] `signal_queue > 0` だけで翌営業日準備完了と見なしてよいか
- [ ] データ更新 0 件を正常系として許容する日があるか
- [ ] `READY_WITH_WARNINGS` を誰がどう扱うか運用手順に落とせるか

## Done Criteria

- [ ] 判定基準が運用手順と一致している
- [ ] `READY` の意味が誤解なく説明できる
- [ ] データ欠損時に過度に楽観的な判定を返さない
