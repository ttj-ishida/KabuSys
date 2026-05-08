# Core Extension Points

- 目的: `Core` が `Addon` に公開する接続点を定義する
- スコープ: 2026-05-06 時点の現行コードをもとにした `Phase 1 / Issue 2`
- 前提: `Core` から `Addon` を直接 import しない

---

## 1. 設計原則

拡張点の原則:

- `Core` は抽象化された接続点だけを知る
- `Addon` は接続点を実装する
- `Addon` 未導入時は `Core` がフォールバックで動く
- `Core` の実行・監視・基本レポートは単独で成立する

禁止事項:

- `Core` から `Addon` の具体モジュールを直接 import する
- `Addon` が `Core` の private 関数や内部テーブル都合に依存する
- `Addon` が失敗しただけで `Core` の注文フローを止める

---

## 2. 接続点一覧

`Core` が公開対象として扱う接続点は次の 7 つ。

1. `Notifier`
2. `NewsProvider`
3. `DisclosureProvider`
4. `DashboardPageProvider`
5. `StrategyEnhancer`
6. `ReportAugmenter`
7. `RegimeProvider` ✅ 実装済み（Issue #271）

---

## 3. Notifier

### 3.1 目的

`Core` の execution / monitoring / batch が通知を送りたいときに使う。

### 3.2 現行実装

- `src/kabusys/operations/notifier.py`
- `build_notifier(settings)`
- `NullNotifier`
- `LineNotifier`

現状評価:

- すでにもっとも完成度の高い extension point
- `NullNotifier` フォールバックがあり、`Core` 非停止要件を満たしている

### 3.3 Core が知るべき責務

- `.send(message: str) -> bool`

`Core` は「送れるかどうか」だけ見ればよい。送信先や API 種別は知る必要がない。

### 3.4 Addon 側の責務

- LINE / Slack / Discord / Email など個別通知実装
- 認証情報検証
- 送信失敗時の自己完結したエラーハンドリング

### 3.5 フォールバック

- `NullNotifier`

### 3.6 判定

- `Notifier` は `Core` 公開 IF として確定

---

## 4. NewsProvider

### 4.1 目的

ニュース原文の収集・保存、および将来的なニュースソース差し替えを扱う。

### 4.2 現行実装

- Yahoo News 収集: `src/kabusys/data/news_collector.py`
- AI 解釈: `src/kabusys/ai/news_nlp.py`

現状評価:

- 収集と解釈が近接しているが、`Core` / `Addon` 分離の観点ではまだ接続点化されていない
- `Yahoo News` は `Addon` 側に寄せる方針

### 4.3 Core が知るべき責務

最低限:

- `collect(target_date) -> int`
- `source_name() -> str`

将来的には:

- `save_raw_news(conn, items) -> int`
- `healthcheck() -> bool`

### 4.4 Addon 側の責務

- RSS / HTML / API ごとの取得
- レート制限・SSRF 対策・失敗時のログ
- 原文を `raw_news` へ保存

### 4.5 フォールバック

- News Addon 未導入時はニュース収集なし
- `Core` はニュース非依存で稼働

### 4.6 判定

- `NewsProvider` は新設すべき公開 IF

---

## 5. DisclosureProvider

### 5.1 目的

TDnet / EDINET などの開示ソースを `Core` から疎結合に扱う。

### 5.2 現行実装

- TDnet: `src/kabusys/data/tdnet_collector.py`, `scripts/run_tdnet_collection.py`
- EDINET: `src/kabusys/data/edinet_collector.py`, `scripts/run_edinet_collection.py`
- 分類: `scripts/run_disclosure_classification.py`

現状評価:

- ソースごとの collector はある
- ただし `Core` 公開 IF としてはまだ未整理

### 5.3 Core が知るべき責務

最低限:

- `collect(target_date) -> int`
- `source_name() -> str`

分類系まで含めるなら:

- `classify(target_date) -> int`

### 5.4 Addon 側の責務

- TDnet / EDINET ごとの取得
- 認証や利用制約の処理
- `raw_disclosures` への保存
- 必要なら `disclosure_events` への分類

### 5.5 フォールバック

- `ENABLE_TDNET=false`
- `ENABLE_EDINET=false`

未導入時はスキップで終了し、`Core` 売買フローには影響させない。

### 5.6 判定

- `DisclosureProvider` は新設すべき公開 IF

---

## 6. DashboardPageProvider

### 6.1 目的

Streamlit ページ群を `Core` と `Addon` で分離し、後からページを追加できるようにする。

### 6.2 現行実装

- `src/kabusys/monitoring/streamlit_dashboard.py`
- `src/kabusys/monitoring/pages/1_WebManual.py`
- `src/kabusys/monitoring/pages/2_Signal_Queue.py`
- `src/kabusys/monitoring/pages/3_Performance.py`
- `src/kabusys/monitoring/pages/4_Strategy_Lab.py`

現状評価:

- Streamlit の multi-page 機構に直接載せている
- `Strategy Lab` を Addon へ出すには、ページ登録方法の抽象化が必要

### 6.3 Core が知るべき責務

最低限:

- `page_id() -> str`
- `page_title() -> str`
- `render(**context) -> None`
- `is_enabled(settings) -> bool`

### 6.4 Addon 側の責務

- 追加ページの定義
- 追加ページ用のデータ取得
- 有効 / 無効判定

### 6.5 フォールバック

- `Core` だけでも `Home / WebManual / Signal Queue / Performance` が表示される
- `Addon` ページがなくてもダッシュボードは成立する

### 6.6 判定

- `DashboardPageProvider` は新設すべき公開 IF

---

## 7. StrategyEnhancer

### 7.1 目的

`Core` のシグナル生成ロジックを壊さずに、追加スコアや追加フィルタを差し込めるようにする。

### 7.2 現行実装

- `src/kabusys/strategy/signal_generator.py`
- AI score, breadth, earnings avoidance などが内部統合されている

現状評価:

- regime 判定は `RegimeProvider` プロトコルとして分離済み（Issue #271）
- AI score 差し込み・premium factor / event filter の拡張点はまだ未抽象化
- 将来の AI tuning / premium factor / event filter を Addon 化するには追加の抽象化が必要

### 7.3 Core が知るべき責務

候補:

- `augment_features(df, target_date) -> df`
- `adjust_scores(df, target_date) -> df`
- `extra_buy_filters(df, target_date) -> mask`
- `extra_sell_filters(df, target_date) -> mask`

### 7.4 Addon 側の責務

- quality / flow / event 系の追加スコア
- 高度な売買フィルタ
- premium factor の追加

### 7.5 フォールバック

- enhancer 未導入時は no-op
- `Core` の元スコアだけで売買判断する

### 7.6 判定

- `StrategyEnhancer` は新設すべき公開 IF

---

## 8. ReportAugmenter

### 8.1 目的

基本レポートは `Core` に残しつつ、追加セクションや高機能分析を `Addon` から差し込めるようにする。

### 8.2 現行実装

- `src/kabusys/run_pre_market_report.py`
- `src/kabusys/run_market_close_report.py`
- `src/kabusys/run_performance_report.py`
- `src/kabusys/backtest/report.py`

現状評価:

- 各レポートは独立して完結している
- 拡張前提の IF は未整備

### 8.3 Core が知るべき責務

候補:

- `augment_summary(report) -> report`
- `extra_sections(report) -> list[str | dict]`
- `extra_warnings(report) -> list[str]`

### 8.4 Addon 側の責務

- premium analytics
- 比較分析
- 追加 KPI
- AI commentary

### 8.5 フォールバック

- augmenter 未導入時は基本レポートのみ出力

### 8.6 判定

- `ReportAugmenter` は新設すべき公開 IF

---

## 9. 現時点の成熟度

| 接続点 | 現状 | 評価 |
|---|---|---|
| `Notifier` | 実装済み | すでに公開 IF に近い |
| `RegimeProvider` | ✅ 実装済み（Issue #271） | `src/kabusys/core/interfaces/regime.py` |
| `NewsProvider` | 未抽象化 | Addon 分離のため新設必要 |
| `DisclosureProvider` | 未抽象化 | Addon 分離のため新設必要 |
| `DashboardPageProvider` | 未抽象化 | Streamlit 分離のため新設必要 |
| `StrategyEnhancer` | 部分的（regime のみ分離済み） | AI score / premium factor は未抽象化 |
| `ReportAugmenter` | 未抽象化 | premium report 分離のため新設必要 |

---

## 10. RegimeProvider ✅ 実装済み（Issue #271）

### 10.1 目的

`Core` のシグナル生成・バックテストエンジンが市場レジームラベル（`'bull'` / `'neutral'` / `'bear'`）を取得するための接続点。
AI Addon 未導入時は `NullRegimeProvider`（常に `'bull'`）を使用し、Core が単独で動作できるようにする。

### 10.2 実装

- `src/kabusys/core/interfaces/regime.py`
  - `RegimeProvider` — `@runtime_checkable` Protocol
  - `NullRegimeProvider` — Core-only モード（常に `'bull'`）
  - `DatabaseRegimeProvider` — `market_regime` テーブルからラベルを取得
- `src/kabusys/core/interfaces/__init__.py`
  - `build_regime_provider(conn, enabled)` — `ENABLE_AI_SENTIMENT` フラグに基づいて実装を切り替えるファクトリ

### 10.3 Core が知るべき責務

- `get_regime(target_date: date) -> str`

Core は文字列ラベルだけを受け取り、AI がどのように判定したかを知る必要はない。

### 10.4 Addon 側の責務

- `market_regime` テーブルへのレジームスコア書き込み（`src/kabusys/ai/regime_detector.py`）

### 10.5 フォールバック

- `ENABLE_AI_SENTIMENT=false` → `NullRegimeProvider`（Bear フィルタは発動しない）
- `market_regime` にデータがない日 → `'bull'` を返す（安全側フォールバック）

---

## 11. Core から見た依存方向

理想形:

```text
Core
  -> Extension Point Interface
      -> Addon Implementation
```

避ける形:

```text
Core
  -> Addon Concrete Module
```

---

## 12. 次にやること

この文書を前提に、次の監査へ進む。

1. `TODO_CoreAddonImportBoundaryAudit.md`
2. `CoreAddonConfigBoundary.md`

---

## 12. 関連

- [TODO_CoreAddonRepoSplit.md](./TODO_CoreAddonRepoSplit.md)
- [TODO_CoreAddonResponsibilityMatrix.md](./TODO_CoreAddonResponsibilityMatrix.md)
