# KabuSys

日本株向けの自動売買／データ基盤ライブラリ集です。  
市場データの取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査ログ管理などをモジュール単位で提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を持つ Python パッケージです。

- J-Quants API からの市場データ・財務データ・市場カレンダー取得（差分取得、ページネーション、レート制御、リトライ）
- DuckDB を用いたデータスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・保存・品質チェック）
- ファクター計算（Momentum / Volatility / Value 等）および特徴量正規化
- 戦略用シグナル生成（複数コンポーネントのスコア統合、Bear レジーム抑制、エグジット判定）
- RSS フィードからのニュース収集と銘柄紐付け（SSRF/サイズ/トラッキング除去対策）
- 監査ログ（シグナル→発注→約定のトレース）テーブル定義
- 環境変数ベースの設定管理（.env 自動ロード機能）

設計方針は「ルックアヘッドバイアスの排除」「冪等性」「外部依存（発注 API 等）への直接依存を排し層分離」を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（トークンリフレッシュ、ページネーション、レートリミット、保存ユーティリティ）
  - データ保存: raw_prices / raw_financials / market_calendar などへの冪等保存関数
- data/schema.py
  - DuckDB 用のスキーマ定義と初期化（init_schema, get_connection）
- data/pipeline.py
  - 日次 ETL（run_daily_etl）、個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- data/news_collector.py
  - RSS フィード収集 + 前処理 + raw_news 保存 + news_symbols 紐付け
- data/calendar_management.py
  - 営業日判定、next/prev_trading_day、calendar_update_job
- data/audit.py
  - 監査ログ（signal_events / order_requests / executions 等）
- data/stats.py / data/features.py
  - Z スコア正規化などの統計ユーティリティ
- research/*
  - ファクター計算（calc_momentum / calc_volatility / calc_value）および特徴量探索ユーティリティ（IC, forward returns, summary）
- strategy/*
  - 特徴量を用いた features テーブルへの構築（build_features）
  - features と AI スコアを統合して signals テーブルへシグナル書き込み（generate_signals）
- config.py
  - 環境変数読み込み・検証（自動 .env 読み込み、必須キーチェック、環境モード判定）

---

## 必要な環境変数（主なもの）

以下はコード内で参照される主な環境変数です。`.env` ファイルをプロジェクトルートに置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注モジュール利用時）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB 等）のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

設定が不足していると Settings プロパティが ValueError を投げますので .env.example を参考に .env を作成してください（プロジェクトルートに .env または .env.local を置くと自動ロードされます）。

---

## セットアップ手順

1. Python 環境
   - Python 3.9+ を推奨（typing の新しい機能を使用）
2. 必要パッケージをインストール
   - 最低限の依存（必須）:
     - duckdb
     - defusedxml
   - インストール例:
     ```
     pip install duckdb defusedxml
     ```
   - パッケージとしてインストールする場合（プロジェクトルートで）:
     ```
     pip install -e .
     ```
     （setup.py/pyproject.toml が用意されていることを前提）
3. 環境変数の準備
   - プロジェクトルートに `.env` を作成し、上記の必須変数を設定します。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから初期化します:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - ":memory:" を渡すとインメモリ DB が使えます（テスト用）。

---

## 使い方（主要ワークフロー例）

以下は典型的な日次処理の流れ（ETL → 特徴量構築 → シグナル生成 → ニュース収集）のサンプルです。

1. DuckDB 接続 / スキーマ初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL の実行（J-Quants からデータ取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を指定しないと今日が対象
   print(result.to_dict())
   ```

3. 特徴量（features）構築
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   n = build_features(conn, date.today())
   print(f"features upserted: {n}")
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals

   total_signals = generate_signals(conn, date.today(), threshold=0.6)
   print(f"total signals: {total_signals}")
   ```

5. ニュース収集と銘柄紐付け
   ```python
   from kabusys.data.news_collector import run_news_collection

   # known_codes: 銘柄コードの集合（抽出に用いる）
   known_codes = {"7203", "6758", "9984"}  # 例
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

6. J-Quants トークンを手動で取得する（必要に応じて）
   ```python
   from kabusys.data.jquants_client import get_id_token

   id_token = get_id_token()  # settings.jquants_refresh_token を使用
   ```

注意事項:
- 各処理は「target_date 時点で利用可能なデータのみ」を使うよう設計されており、ルックアヘッドバイアスを避ける実装になっています。
- ETL や保存処理は冪等（ON CONFLICT 等）で実装されているため、リトライや部分実行が比較的安全です。
- 実稼働での発注機能（kabuステーション連携等）を有効化する場合は追加の設定・テストが必要です（KABU_API_PASSWORD 等）。

---

## API / モジュール一覧（簡易説明・参照先）

- kabusys.config
  - Settings: 環境変数から設定値を取得するラッパー
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可能）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
  - DuckDB のテーブル定義をすべて作成
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult 型で結果を返す
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit
  - 監査ログ用 DDL と初期化（signal_events, order_requests, executions 等）
- kabusys.data.stats
  - zscore_normalize
- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

---

## ディレクトリ構成

（プロジェクトの主要ファイル・ディレクトリ一覧）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - stats.py
    - (その他 ETL/品質チェック関連モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/
    - (監視関連モジュール: ここには監視/アラート用機能が入る想定)

---

## 開発・運用上の注意点

- 環境変数を使った機密情報管理を採用しています。`.env` を誤って公開しないでください。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に保存されます。バックアップ・マイグレーション方法を運用ルールで定めてください。
- J-Quants API のレート制限(120 req/min)に対応するよう内部でスロットリングを実装していますが、運用での大量取得時は追加の配慮が必要です。
- 実ポジションに資金を投じる前に paper_trading 環境で十分な検証を行ってください（KABUSYS_ENV を paper_trading に設定）。
- ログレベルや監視（Slack 通知等）を適切に設定して異常検知を容易にしてください。

---

この README はコードベースに基づく概要・導入ガイドです。より詳細な設計仕様（StrategyModel.md, DataPlatform.md 等）や運用手順書は別途参照してください。必要であれば README にサンプル .env.example やよくあるトラブルシュート項目を追加します。