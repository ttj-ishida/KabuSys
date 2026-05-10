# TODO: Sector Cap Price Fallback Handling

## Background

`apply_sector_cap()` は既存ポジションのセクター別エクスポージャーを集計し、上限超過セクターの新規候補を除外する。

現状は `price_map.get(code, 0.0)` を使っており、価格が欠損した既存保有は `0 円` として扱われる。

対象実装:

- `src/kabusys/portfolio/risk_adjustment.py`

## Problem

価格欠損時に既存保有のエクスポージャーが過少見積りされる。

その結果、

- 本来は上限超過のセクターが `blocked_sectors` に入らない
- 新規 BUY 候補が誤って通過する
- セクター集中リスクを見逃す

これは live 運用時のリスク制御として見逃せない。

## Expected Direction

価格欠損を `0.0` にフォールバックしない。

少なくとも次のどれかが必要。

- 直近終値などの代替価格を使う
- 価格欠損銘柄を warning 扱いで保守的にブロックする
- 価格欠損時は sector cap 判定自体を `READY_WITH_WARNINGS` 相当で止める

## TODO

- [ ] `price_map` 欠損時の扱い方針を決める
- [ ] 代替価格の取得元候補を整理する
- [ ] `0.0` フォールバックが live で許容不可であることを明文化する
- [ ] 欠損時のログ / warning 出力方針を決める
- [ ] テスト観点を整理する

## Test Cases

- [ ] 既存保有に価格欠損がない通常ケース
- [ ] 既存保有の一部だけ価格欠損するケース
- [ ] 上限超過セクターで価格欠損が起きるケース
- [ ] `sell_codes` 除外と価格欠損が同時にあるケース

## Done Criteria

- [ ] 価格欠損時に sector exposure が過少見積りされない
- [ ] 新規 BUY ブロック漏れが起きない
- [ ] 欠損時の挙動がドキュメントとテストで説明できる
