# TODO: Yahoo News 取得機能の配線確認と統合

> **ステータス（2026-05-06時点）**: **実装済み（Issue #254）**  
> - `src/kabusys/data/news_collector.py` は実装済み（RSS 取得・`raw_news` 保存）  
> - `scripts/run_yahoonews_collection.py` を新設。`ENABLE_YAHOONEWS=true` でオプション機能として動作  
> - `raw_news` を正として統一。`news_articles` は不使用  

## 背景

コードベースを確認した結果、Yahoo News の RSS 取得機能そのものは実装されているが、夜間バッチや日次データ更新フローには未接続だった。

そのため、現状は `raw_news` を前提に `score_news()` / `score_regime()` を実行する設計が存在する一方で、ニュースを継続的に投入する実行経路が不足している。

---

## 確認結果

### 実装済み

- `src/kabusys/data/news_collector.py`
  - `DEFAULT_RSS_SOURCES` に Yahoo News RSS が定義済み
  - `fetch_rss()` で RSS 取得・解析を実装済み
  - `run_news_collection()` で `raw_news` 保存を実装済み
- `config/data_config.yaml`
  - `news_data.provider: yahoo_news` が設定済み
- `tests/test_news_collector.py`
  - RSS 解析、デフォルトソース利用、銘柄コード抽出のテストあり

### 未接続

- `scripts/run_data_update.py`
  - `run_daily_etl()` と breadth 計算のみで、ニュース収集を呼んでいない
- `src/kabusys/data/pipeline.py`
  - `run_daily_etl()` は価格・財務・配当・決算カレンダーのみ対象
  - `run_news_collection()` を呼んでいない
- `scripts/run_ai_analysis.py`
  - `score_news()` / `score_regime()` は `raw_news` 前提だが、前段のニュース収集ジョブが存在しない

### 不整合

- 設定では `news_articles` を参照している
- 収集実装は `raw_news` に保存している
- AI 分析系も `raw_news` を参照している

---

## TODO

- [ ] Yahoo News 収集の正式な実行ポイントを決める
- [ ] `run_data_update.py` もしくは `run_daily_etl()` から `run_news_collection()` を呼ぶ
- [ ] 収集失敗時の扱いを決める
- [ ] `known_codes` の供給元を決める
- [ ] `news_data.table` が `news_articles` でよいか再確認する
- [ ] `raw_news` と `news_articles` の役割を整理する
- [ ] 必要なら `raw_news -> news_articles` の整形ステップを追加する
- [ ] 夜間バッチ完了レポートにニュース収集件数を反映する
- [ ] Yahoo News 収集が実行される統合テストまたはスモークテストを追加する

---

## 優先判断

まず着手すべきなのは次の 3 点。

1. `run_data_update.py` または `run_daily_etl()` に `run_news_collection()` を組み込む
2. `known_codes` の供給方法を決める
3. `raw_news` と `news_articles` のどちらを正とするか統一する

---

## 参照箇所

- `src/kabusys/data/news_collector.py`
- `src/kabusys/data/pipeline.py`
- `scripts/run_data_update.py`
- `scripts/run_ai_analysis.py`
- `config/data_config.yaml`
- `tests/test_news_collector.py`
