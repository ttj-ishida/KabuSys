# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ ETL、ニュース収集・NLP（OpenAI を利用したセンチメント分析）、リサーチ（ファクター計算）、市場レジーム判定、監査ログ（トレース用テーブル）など、アルゴリズム取引基盤で必要となる機能群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の抽出とバリデーション

- Data（ETL / データ品質）
  - J-Quants API クライアント（株価・財務・マーケットカレンダー取得）
  - 差分 ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損、重複、スパイク、日付整合性）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news に保存、SSRF 対策・サイズ制限・トラッキング除去）

- Research（特徴量・ファクター）
  - モメンタム / ボラティリティ / バリュー のファクター計算
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
  - Z スコア正規化ユーティリティ

- AI（OpenAI を用いる分析）
  - ニュースの銘柄ごとセンチメントスコア化（gpt-4o-mini, JSON mode）
  - マクロニュース + ETF（1321）200日移動平均乖離を組み合わせた市場レジーム判定
  - API 呼び出しはリトライ・バックオフ・フェイルセーフ設計

- 監査（Audit / トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化
  - 監査 DB 初期化ユーティリティ（DuckDB）

- その他
  - DuckDB を前提に設計（ローカル分析・ETL 用）
  - OpenAI・J-Quants API 呼び出しでの堅牢なエラーハンドリングとレート制御

---

## セットアップ手順

前提: Python 3.10+（型注釈の Union 表現等を使用しています）を想定しています。

1. リポジトリをクローン / ソースを配置

2. 仮想環境作成・有効化（例）
   - macOS / Linux:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - プロジェクトに requirements ファイルが無い場合、主に以下を入れてください（環境に応じてバージョン管理してください）:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - その他、標準ライブラリ以外の依存があれば追加してください（例: requests 等）。  
     ※ テスト時は unittest.mock を利用する設計です。

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注等で使用）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API を使う処理を実行する場合に必要
   - 任意 / デフォルト値:
     - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"
     - KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト "development"）
     - LOG_LEVEL: "INFO"（デフォルト）

   - 自動 .env ロードを無効化したい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データベース初期化（監査ログ等）
   - 監査用 DuckDB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - その他テーブルスキーマは用途に応じて用意してください（本リポジトリ内のスキーマ初期化関数を利用して作成できます）。

---

## 使い方（簡単な例）

以下は代表的なユースケースの使用例です。実際は適切なエラーハンドリング・ロギングを付けてください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアを生成（OpenAI API 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n} codes")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査データベース初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS を取得して記事リストを得る（news_collector）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  for a in articles:
      print(a["id"], a["title"])
  ```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必要)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development/paper_trading/live、デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env の自動ロードを無効化)

---

## セキュリティ／運用上の注意

- news_collector は SSRF 対策（リダイレクト検査、プライベート IP 拒否）や受信サイズ上限を実装していますが、実運用では追加のネットワーク制御（プロキシ、FW）を推奨します。
- OpenAI / J-Quants 呼び出しはリトライ・バックオフ・ステータスハンドリングを備えています。API キーやトークンは安全に管理してください。
- DuckDB ファイルはローカルに機密データを保存するため、適切なファイルパーミッションで保護してください。
- run_daily_etl 等は外部 API を多数呼びます。レート制御・API 利用上限に注意してください（J-Quants のレートはモジュール内に設定あり）。

---

## ディレクトリ構成（主なファイルと説明）

（プロジェクトのルートが src/ を含む構成を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定の読み込み / バリデーションロジック
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄別ニュースセンチメント算出（OpenAI）
    - regime_detector.py
      - ETF とマクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py
      - ETL 実行（run_daily_etl 等）
    - etl.py
      - ETL の公開インターフェース（ETLResult の再エクスポート）
    - news_collector.py
      - RSS 収集・前処理・保存ロジック（SSRF・圧縮・トラッキング除去対応）
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・calendar_update_job
    - stats.py
      - 汎用統計ユーティリティ（zscore_normalize 等）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
    - audit.py
      - 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value のファクター計算
    - feature_exploration.py
      - 将来リターン・IC・統計サマリー等

---

## 開発・テストに関するメモ

- モジュールは外部 API 呼び出し部分を容易にモックできる設計（内部で関数を分離）になっています。ユニットテストでは OpenAI/J-Quants の呼び出しを patch してテスト可能です。
- 自動 .env ロードはプロジェクトルート（.git か pyproject.toml がある親ディレクトリ）を基に行われます。CI や一時的なテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。

---

必要に応じて README にサンプル .env.example、requirements.txt、起動スクリプト（CLI）を追加できます。詳細や追加のユースケース（発注・モニタリング・Slack 通知など）を盛り込みたい場合は教えてください。