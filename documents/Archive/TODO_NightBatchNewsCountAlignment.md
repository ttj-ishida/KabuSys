# TODO: Night Batch News Count Alignment

> **ステータス: 完了（2026-05-10）**
> GitHub Issue #286 · PR #290 にて対応済み。

## 対応内容

- `UpdateCounts.news_articles` フィールドを `raw_news` にリネーム
- `src/kabusys/operations/night_batch_report.py` の CLI/Markdown 出力を `raw_news` に統一
- `scripts/run_night_batch_report.py` の `collect_update_counts()` 参照先を `raw_news` テーブルに修正
- `tests/test_night_batch_report.py` / `tests/test_night_batch_runner.py` の参照を更新

## Background

Yahoo News 収集は `raw_news` に保存する実装になっている。

対象実装:

- `src/kabusys/data/news_collector.py`
- `src/kabusys/data/schema.py`

一方、Night Batch レポートの update counts は `news_articles` を見ていた。

対象実装:

- `scripts/run_night_batch_report.py`
- `src/kabusys/operations/night_batch_report.py`

## Problem

ニュース収集が成功しても、Night Batch レポート上の `news_articles` 件数が `0` のままになる可能性があった。

これにより、

- レポートの update counts が実態とずれる
- 運用者が「ニュース更新されていない」と誤解する
- `raw_news` と `news_articles` の責務が文書上も実装上も分かりにくい

## Done Criteria

- [x] Night Batch レポートのニュース件数が実態と一致する
- [x] `raw_news` と `news_articles` の違いが運用者に伝わる
- [x] レポートを見て誤判定しない
