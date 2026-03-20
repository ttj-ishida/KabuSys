KabuSys — 日本株自動売買基盤 (README)
=================================

概要
----
KabuSys は日本株向けのデータプラットフォームと戦略レイヤーを備えた自動売買基盤です。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に保存し、研究用ファクター計算、特徴量正規化、シグナル生成、ニュース収集などを行います。発注・監視用のテーブル定義や監査ログ設計も含まれ、実運用に耐える設計思想（冪等性、レート制御、トレーサビリティ、Look‑ahead バイアス対策）を重視しています。

主な機能
--------
- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーをページネーション・レート制御・リトライ含め取得
  - 差分更新、バックフィル、品質チェック
- データ格納
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - 冪等保存（ON CONFLICT / upsert）
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - クロスセクション Z スコア正規化ユーティリティ
- 特徴量構築とシグナル生成
  - features テーブル構築（ユニバースフィルタ、Z スコアクリップ）
  - ai_scores と統合して final_score を計算、BUY / SELL シグナルを signals テーブルへ出力
  - Bear レジーム抑制、ストップロス等のエグジット判定
- ニュース収集
  - RSS フィード取得、前処理、raw_news 保存、記事→銘柄の紐付け
  - SSRF 対策、XML 脆弱性対策、受信サイズ制限
- カレンダー管理
  - market_calendar の更新と営業日判定ユーティリティ（next/prev/get_trading_days など）
- 監査ログ
  - signal_events / order_requests / executions 等によるトレーサビリティ設計

必須条件 / 推奨
----------------
- Python 3.10 以上（typing の構文で Python 3.10+ を想定）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース）
- 環境変数に API トークン等を設定すること

セットアップ手順
----------------

1. リポジトリをクローン・作業環境を用意
   - 任意の仮想環境を作成（venv / pyenv / conda 等を推奨）
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 依存パッケージをインストール
   - 必須: duckdb, defusedxml など
     ```
     pip install duckdb defusedxml
     ```
   - 開発用やパッケージ化されている場合は pyproject / requirements に従ってください。

3. 環境変数（または .env）を準備
   - 以下の環境変数はアプリケーション起動時に必要／推奨されます。

     必須（本番的に動かす場合）
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_station_api_password>
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>

     任意（デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   - 開発時はプロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   例 .env:
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトでスキーマを作成します:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成して全テーブルを生成
     conn.close()
     ```
   - テストや一時実行では ":memory:" を指定してインメモリ DB を使えます:
     init_schema(":memory:")

使い方（主要 API の例）
-----------------------

- 日次 ETL（市場カレンダー、株価、財務、品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量構築（features テーブルへの upsert）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 10))
  print(f"built features for {n} codes")
  conn.close()
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 10))
  print(f"generated {total} signals")
  conn.close()
  ```

- ニュース収集ジョブ（RSS 取得・保存・銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes: 銘柄コードの集合（例: {"7203", "6758", ...}）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
  print(results)
  conn.close()
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  conn.close()
  ```

設計時の注意点（運用・開発）
------------------------
- 自動環境変数ロードはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込みます。テスト中に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API に対するレート制御・再試行・トークン自動更新が組み込まれていますが、API 利用時は自身の利用規約・レートを確認してください。
- DuckDB のトランザクションを用いたバルク挿入で原子性を確保しています。運用中はバックアップや VACUUM 等の管理を検討してください。
- シグナル→発注→約定の監査ログ設計が含まれており、order_request_id などの冪等キーを活用してください。

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクトの主なソース構成（src/kabusys を基準）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存ロジック）
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL（run_daily_etl 等）
    - news_collector.py         — RSS 取得・前処理・保存・銘柄抽出
    - calendar_management.py    — カレンダー更新・営業日ユーティリティ
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - features.py               — features の公開インターフェース
    - audit.py                  — 監査ログテーブル DDL（signal_events 等）
    - (その他 data/*.py)
  - research/
    - __init__.py
    - factor_research.py        — Momentum / Volatility / Value の計算
    - feature_exploration.py    — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py    — features テーブル構築の高レベル処理
    - signal_generator.py       — final_score 計算と signals テーブル生成
  - execution/
    - __init__.py
    - (発注 / 実行層は別モジュールで実装)
  - monitoring/
    - (監視・アラート関連モジュール)

補足
----
- テスト: モジュールは DB を注入（get_connection / init_schema）する設計なので、インメモリ DuckDB を使ったユニットテストが容易です。
- セキュリティ: RSS のパースに defusedxml、SSRF 対策、受信バイト数制限などを導入しています。
- 設計文書参照: ソース内のコメント（StrategyModel.md, DataPlatform.md 等を参照する旨）に沿って実装方針が書かれています。プロジェクトに該当する設計ドキュメントがあれば合わせて参照してください。

問題報告・貢献
--------------
バグ報告・機能提案は Issue を立ててください。プルリクエストを歓迎します。コードスタイルやテストを追加した上で送ってください。

以上。必要であればセットアップや実行例（cron / systemd / Container 化など）の具体的な手順を追加で作成します。