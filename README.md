# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETLパイプライン、DuckDB スキーマ、ニュース収集、品質チェック、監査ログなど、取引戦略・発注実装のための基盤機能を提供します。

## 概要

KabuSys は以下を主目的とした内部ライブラリです。

- J-Quants API から株価（日足）・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS を用いたニュース収集と記事の銘柄紐付け
- ETL（差分更新・バックフィル）パイプラインとデータ品質チェック
- 監査ログ（シグナル→発注→約定フロー）のための監査テーブル定義
- 設定管理（.env / 環境変数）と簡易なクライアントユーティリティ

設計上の特徴（抜粋）:

- J-Quants API のレート制御（120 req/min）、リトライ・トークン自動リフレッシュ
- DuckDB への冪等保存（ON CONFLICT を利用）
- ニュース収集での SSRF 防止、XML Bomb 対策、トラッキングパラメータ除去
- ETL は差分更新とバックフィル対応、品質チェックは Fail-Fast ではなく問題を収集

## 主な機能一覧

- 環境設定管理: kabusys.config.settings（.env の自動ロード機能あり）
- J-Quants クライアント: kabusys.data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB に冪等保存
- ニュース収集: kabusys.data.news_collector
  - RSS フィード取得、テキスト前処理、raw_news 保存、銘柄抽出と紐付け
- スキーマ管理: kabusys.data.schema
  - init_schema / get_connection（DuckDB の全テーブル定義）
- ETL パイプライン: kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- 監査ログ: kabusys.data.audit
  - 監査用テーブルの初期化（signal_events, order_requests, executions）
- 品質チェック: kabusys.data.quality
  - 欠損、重複、スパイク、日付不整合などの検出
- プレースホルダモジュール: kabusys.strategy, kabusys.execution, kabusys.monitoring（上位実装向け拡張ポイント）

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリへコピー

2. Python 仮想環境の作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

3. 必要パッケージのインストール
   - 本コードで使用されている主な依存（例）:
     - duckdb
     - defusedxml
   - 実プロジェクトでは requirements.txt や pyproject.toml を用意している想定です。開発環境では以下のようにインストールします:
     ```bash
     pip install duckdb defusedxml
     # 任意: ローカル開発パッケージとしてインストール
     pip install -e .
     ```

4. 環境変数の設定
   - リポジトリルートに `.env` または `.env.local` を配置すると自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（Settings クラスで参照されるもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD      : kabuステーション API 用パスワード（必須）
     - SLACK_BOT_TOKEN        : Slack 通知に使用（必須）
     - SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
   - 任意 / デフォルト値あり:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
     - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（DuckDB）
   - Python REPL もしくはスクリプトから:
     ```python
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)
     # 監査ログテーブルを追加で初期化する場合:
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     ```

## 使い方（代表的な例）

- 日次 ETL の実行
  ```python
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)  # または init_schema() で初期化済みの接続
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  # known_codes: 銘柄抽出に使う有効な銘柄コードの集合（例: {'7203', '6758', ...}）
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
  print(res)  # {source_name: 新規保存数}
  ```

- J-Quants から直接データ取得（テスト等）
  ```python
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings にある refresh token を利用
  prices = jq.fetch_daily_quotes(id_token=token, code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

## 注意点 / 実装上の設計メモ

- J-Quants クライアントはレート制御（120 req/min）を内部に持ち、指数バックオフでリトライします。401 はリフレッシュして1回リトライします。
- DuckDB への保存は冪等（ON CONFLICT による更新またはスキップ）になっています。
- news_collector は SSRF/ZIP Bomb 等の攻撃対策を考慮して実装されています（スキーム検証、プライベートIP検査、受信サイズ上限、defusedxml の使用）。
- ETL は差分更新（DB の最終日を基準に未取得分のみ取得）と、後出し修正吸収のための backfill をサポートします。
- 品質チェックは Fail-Fast ではなく問題を収集する方針です。呼び出し元で severity に応じた対処を行ってください。

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得・保存）
      - news_collector.py      — RSS ニュース収集 + DB 保存
      - schema.py              — DuckDB スキーマ定義 & 初期化
      - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
      - audit.py               — 監査ログ（signal / order_request / executions）
      - quality.py             — データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py            — 戦略実装の拡張ポイント
    - execution/
      - __init__.py            — 発注実装の拡張ポイント
    - monitoring/
      - __init__.py            — 監視・メトリクス実装の拡張ポイント

## 追加・運用メモ

- テスト時や外部副作用を抑えたい場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動ロードを無効にできます。
- DuckDB ファイルのパスは settings.duckdb_path で管理します。デフォルトは data/kabusys.duckdb。
- 監査ログを別 DB に分けたい場合は data.audit.init_audit_db() を使って専用 DB を作成して運用できます。
- 実運用では KABUSYS_ENV を paper_trading / live に設定して挙動を切り替える想定です（Settings.is_live / is_paper / is_dev が利用可能）。

---

必要であれば README に動作例のスクリーンショット、CI/デプロイ手順、依存関係の pin 例（requirements.txt / pyproject.toml）や各テーブルの詳細仕様（カラム説明）を追加できます。どの情報を優先的に追加しますか？