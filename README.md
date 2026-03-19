# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB を用いたデータレイク構成で、J-Quants API からのデータ取得、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログの土台を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを備えたモジュール群を提供します。

- Data (data/): J-Quants からのデータ取得クライアント、DuckDB スキーマ定義、ETL パイプライン、ニュース収集、カレンダー管理、統計ユーティリティなど。
- Research (research/): ファクター計算・特徴量探索ツール（モメンタム、ボラティリティ、バリュー等）。
- Strategy (strategy/): 特徴量を統合して戦略用の features を作成する処理と、最終スコアから売買シグナルを生成するロジック。
- Execution (execution/): 発注・約定管理レイヤ（骨格）。
- Monitoring: 監視・監査用テーブル / ログ（audit 等）。

設計上のポイント:
- DuckDB を中心に「Raw / Processed / Feature / Execution」の多層スキーマを採用。
- J-Quants API のレート制御・リトライ・トークン自動更新に対応。
- ETL/保存処理は冪等性（ON CONFLICT / INSERT … DO UPDATE / DO NOTHING）を重視。
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ参照）。


---

## 主な機能一覧

- J-Quants API クライアント（data/jquants_client.py）
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レートリミット、リトライ、401時のトークンリフレッシュ
  - DuckDB への冪等保存ヘルパー（save_*）

- DuckDB スキーマ管理（data/schema.py）
  - raw_prices, raw_financials, prices_daily, features, ai_scores, signals, orders, executions, positions などの定義
  - init_schema(db_path) による初期化

- ETL パイプライン（data/pipeline.py）
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得 / バックフィル対応

- 特徴量計算（research/factor_research.py, strategy/feature_engineering.py）
  - モメンタム、ボラティリティ、バリュー等の計算
  - Zスコア正規化、ユニバースフィルタ（株価・出来高基準）

- シグナル生成（strategy/signal_generator.py）
  - ファクター + AI スコアの統合 → final_score 計算
  - Bear レジーム判定、BUY/SELL シグナル生成、エグジット判定（ストップロス等）
  - signals テーブルへの冪等書き込み

- ニュース収集（data/news_collector.py）
  - RSS フィード取得、XML セキュリティ（defusedxml）、SSRF 対策、トラッキングパラメータ除去、記事ID生成
  - raw_news / news_symbols の冪等保存

- マーケットカレンダー管理（data/calendar_management.py）
  - market_calendar の差分取得と営業日判定ユーティリティ（next/prev/get_trading_days/is_sq_day など）

- 統計ユーティリティ（data/stats.py）
  - クロスセクションの Z スコア正規化など

---

## セットアップ手順（開発用）

前提: Python 3.10 以上を推奨（型アノテーションの union 演算子 `|` を使用）。

1. リポジトリをクローン / 配布コードを入手
   - 例: git clone <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストール（最低限）
   - pip install duckdb defusedxml
   - その他、プロジェクトで要求されるパッケージがあれば追加でインストールしてください（例: slack-sdk 等、発注や通知を行う場合）。

   （パッケージ管理は requirements.txt / pyproject.toml を用意している場合はそちらを使用してください。）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動でロードされます（ただしテスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN (J-Quants のリフレッシュトークン)
     - KABU_API_PASSWORD (kabuステーション API を使う場合)
     - SLACK_BOT_TOKEN (Slack 通知を行う場合)
     - SLACK_CHANNEL_ID (Slack 通知先)
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH (例: data/kabusys.duckdb) — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH (監視 DB 等) — デフォルト: data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプト内で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 使い方（主要な操作例）

以下はライブラリを直接インポートして実行する例です。プロダクションでは CLI やスケジューラ（cron / Airflow / GitHub Actions 等）から呼び出してください。

- スキーマ初期化
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルの作成）
  ```
  from datetime import date
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date(2024, 1, 31))
  print(f"upserted features: {count}")
  ```

- シグナル生成
  ```
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date(2024,1,31))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ実行
  ```
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
  print(results)  # {source: saved_count}
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants からデータを個別に取得して保存
  ```
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)
  ```

注意:
- これらの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。
- 実運用では KABUSYS_ENV を `paper_trading` / `live` に応じて扱いを分けてください（発注部分など）。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定管理（Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント / fetch_* / save_* / 認証・レート制御
    - news_collector.py
      - RSS 取得、前処理、raw_news / news_symbols 保存
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize などの統計ユーティリティ
    - pipeline.py
      - ETL ジョブ（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - calendar_management.py
      - market_calendar の更新ジョブと営業日ユーティリティ
    - audit.py
      - 監査ログ用テーブル定義（signal_events, order_requests, executions 等）
    - features.py
      - データ側の特徴量ユーティリティ（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリューの計算（prices_daily, raw_financials を参照）
    - feature_exploration.py
      - 将来リターン計算、IC（スピアマン）計算、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - research のファクターを統合し features テーブルへ保存
    - signal_generator.py
      - features と ai_scores を統合し final_score を計算、signals に書き込み
  - execution/
    - __init__.py
      - 発注層の雛形（実装は拡張前提）

（README に記載した以外にも補助モジュール・ユーティリティ関数が存在します。上記は主要なエントリポイントの一覧です。）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 認証用リフレッシュトークン
- KABU_API_PASSWORD (必須 for kabuAPI) — kabuステーション API パスワード
- KABUSYS_ENV (development | paper_trading | live) — 動作モード
- LOG_LEVEL (DEBUG | INFO | …)
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知に利用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にする（テスト用）

config.Settings 経由でコード内から参照可能です（kabusys.config.settings）。

---

## 注意事項 / 運用上のヒント

- ETL・API 通信はネットワーク・レート制限・API エラーの影響を受けます。ジョブは監視下で定期的に実行し、失敗時のアラート運用を推奨します。
- シグナル生成 → 発注 → 約定のワークフローは、実際の発注部分（broker 接続・注文送信）の実装が別途必要です。本リポジトリは戦略・データ基盤と監査ログの土台を提供します。
- DuckDB ファイルは定期的にバックアップしてください。大容量になる場合はパーティショニング・アーカイブ戦略を検討してください。
- ニュース収集は外部 RSS に依存するため、SSRF / XML インジェクション / 大容量レスポンス等の防御（この実装で一部対策済み）を適切に評価してください。

---

ご要望があれば、README に含めるサンプルスクリプト（起動用 CLI、systemd タイマー例、Airflow DAG 例）や、追加のセットアップ手順（Slack 通知設定、kabuAPI 接続例）を追記します。