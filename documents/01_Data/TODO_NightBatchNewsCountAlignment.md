# TODO: Night Batch News Count Alignment

## Background

Yahoo News 収集は `raw_news` に保存する実装になっている。

対象実装:

- `src/kabusys/data/news_collector.py`
- `src/kabusys/data/schema.py`

一方、Night Batch レポートの update counts は `news_articles` を見ている。

対象実装:

- `scripts/run_night_batch_report.py`
- `src/kabusys/operations/night_batch_report.py`

## Problem

ニュース収集が成功しても、Night Batch レポート上の `news_articles` 件数が `0` のままになる可能性がある。

これにより、

- レポートの update counts が実態とずれる
- 運用者が「ニュース更新されていない」と誤解する
- `raw_news` と `news_articles` の責務が文書上も実装上も分かりにくい

## Open Questions

- `raw_news` を Night Batch の更新件数として採用するか
- `news_articles` は AI 前処理後の派生テーブルとして扱うか
- Night Batch では「収集成功件数」と「AI 処理済み件数」を分けて出すべきか

## TODO

- [ ] `raw_news` と `news_articles` の役割を明文化する
- [ ] Night Batch のニュース件数として何を表示するか決める
- [ ] `collect_update_counts()` の参照先見直し方針を決める
- [ ] CLI summary と Markdown report の表示名を見直す
- [ ] DataSchema / 運用文書との用語整合を確認する

## Expected Direction

候補は次のいずれか。

- `news_articles` ではなく `raw_news` を数える
- `raw_news` と `news_articles` を両方表示する
- ニュース収集成功件数を JobRunResult 側で持ち、update counts とは別に表示する

## Done Criteria

- [ ] Night Batch レポートのニュース件数が実態と一致する
- [ ] `raw_news` と `news_articles` の違いが運用者に伝わる
- [ ] レポートを見て誤判定しない
