# TODO: Sector Cap Price Fallback Handling

> **ステータス: 完了（2026-05-10）**
> GitHub Issue #287 · PR #290 にて対応済み。

## 対応内容

- `price_map.get(code, 0.0)` による無言フォールバックを廃止
- `code not in price_map` だけでなく、`0.0`/`None`/`NaN`/`inf`/負値も不正値として保守的にブロック
- 不正値検出時に `logger.warning` で銘柄・不正値・セクターを記録
- 不正値セクターは `price_missing_sectors` set に追加し、最後に `blocked_sectors |= price_missing_sectors` でマージ
- テスト追加: キー欠損・`0.0`/`-100`/`NaN`/`inf`/`None` の6ケースでセクターブロックを確認

## Background

`apply_sector_cap()` は既存ポジションのセクター別エクスポージャーを集計し、上限超過セクターの新規候補を除外する。

現状は `price_map.get(code, 0.0)` を使っており、価格が欠損した既存保有は `0 円` として扱われていた。

対象実装:

- `src/kabusys/portfolio/risk_adjustment.py`

## Problem

価格欠損時に既存保有のエクスポージャーが過少見積りされる。

その結果、

- 本来は上限超過のセクターが `blocked_sectors` に入らない
- 新規 BUY 候補が誤って通過する
- セクター集中リスクを見逃す

## Done Criteria

- [x] 価格欠損時に sector exposure が過少見積りされない
- [x] 新規 BUY ブロック漏れが起きない
- [x] 欠損時の挙動がドキュメントとテストで説明できる
