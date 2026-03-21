# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants API などから市場データを収集・保存し、ファクター計算・特徴量生成・シグナル生成・発注管理までの一連の処理をサポートします。設計上は「ルックアヘッドバイアスの排除」「冪等性」「運用上の安全対策（SSRF対策・サイズ制限など）」を重視しています。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、JPX カレンダーを取得
  - レートリミット従守、リトライ、トークン自動リフレッシュ
- ETL パイプライン
  - 差分取得 / バックフィル機能、品質チェックフレームワーク
- DuckDB を用いた永続化スキーマ
  - Raw / Processed / Feature / Execution 層のテーブル設計
  - 冪等な INSERT（ON CONFLICT）やトランザクションの利用
- 研究（research）用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 戦略（strategy）層
  - 特徴量構築（Z スコア正規化、ユニバースフィルタ）
  - シグナル生成（最終スコア計算、BUY / SELL 生成、Bear レジーム考慮）
- ニュース収集（RSS）
  - トラッキングパラメータ除去、SSRF 対策、gzip/サイズ上限チェック
- 監査ログ/発注監査設計（audit）
  - signal → order → execution のトレースを想定したスキーマ設計

---

## 必要な環境変数

このライブラリは .env ファイルまたは環境変数から設定を読み込みます（自動読み込みあり、無効化可）。主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション等の API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: `http://localhost:18080/kabusapi`）
- SLACK_BOT_TOKEN (必須) — 通知用 Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知対象の Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite（監視用等）のパス（デフォルト: `data/monitoring.db`）
- KABUSYS_ENV — 環境（`development`, `paper_trading`, `live`）
- LOG_LEVEL — ログレベル（`DEBUG`,`INFO`,`WARNING`,`ERROR`,`CRITICAL`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まなくなります（テスト時に便利）。

（.env.example をプロジェクトルートに置く運用を想定しています）

---

## セットアップ

1. Python 環境の準備（推奨: venv）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージのインストール（最小セット）

   - duckdb
   - defusedxml

   例:

   ```bash
   pip install duckdb defusedxml
   ```

   （実運用ではロギング・HTTP・Slack クライアント等の追加パッケージが必要になる場合があります）

3. パッケージのインストール（開発中なら editable）

   プロジェクトルートに pyproject.toml / setup.py がある想定で:

   ```bash
   pip install -e .
   ```

   ※ 配布形態に応じて変更してください。

4. 環境変数の設定

   プロジェクトルートに `.env` を作成するか、OS 環境変数として設定してください。最低限以下を設定してください:

   - JQUANTS_REFRESH_TOKEN=
   - KABU_API_PASSWORD=
   - SLACK_BOT_TOKEN=
   - SLACK_CHANNEL_ID=

5. データベーススキーマ初期化

   DuckDB データベースを初期化します（デフォルトパスは `data/kabusys.duckdb`）:

   ```bash
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

   メモリ上で試す場合:

   ```bash
   python -c "from kabusys.data.schema import init_schema; init_schema(':memory:')"
   ```

---

## 使い方（基本的なワークフロー）

以下は代表的な操作例です。実際はスケジューラ（cron / Airflow 等）や運用スクリプトから呼び出します。

1. DuckDB に接続して日次 ETL を実行（データ収集）

   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.pipeline import run_daily_etl

   # DB 初期化済みなら get_connection で接続
   conn = get_connection('data/kabusys.duckdb')

   # 今日の ETL を実行
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 特徴量を作成（feature engineering）

   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection('data/kabusys.duckdb')
   count = build_features(conn, target_date=date.today())
   print(f'features created: {count}')
   ```

3. シグナル生成

   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection('data/kabusys.duckdb')
   total_signals = generate_signals(conn, target_date=date.today())
   print(f'signals generated: {total_signals}')
   ```

4. ニュース収集（RSS）

   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection('data/kabusys.duckdb')
   # known_codes: 既知の銘柄コードセット（抽出用）
   results = run_news_collection(conn, known_codes={'7203','6758'})
   print(results)  # {source_name: saved_count, ...}
   ```

5. カレンダー更新ジョブ

   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection('data/kabusys.duckdb')
   saved = calendar_update_job(conn)
   print(f'saved calendar rows: {saved}')
   ```

---

## よく使うモジュールと公開 API

- kabusys.config
  - settings: 環境変数から設定を取得する (Settings クラス)
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

---

## ディレクトリ構成（抜粋）

以下は主要なソースツリーの一例です（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - calendar_management.py
      - features.py
      - audit.py
      - (その他: quality.py 等想定)
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
      - (発注 / ブローカー連携ロジック)
    - monitoring/
      - (監視・Slack 通知等)

プロジェクトには各レイヤー（Raw / Processed / Feature / Execution）を表す DuckDB テーブル定義が含まれており、init_schema() により自動作成されます。

---

## 運用上の注意点

- シークレット類（トークン・パスワード）は .env / 環境変数で管理し、ソース管理に含めないでください。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してテスト時に自動 .env 読み込みを抑制できます。
- J-Quants の API レート制限（120 req/min）に従う設計ですが、運用時のリクエストパターンに応じてさらに調整してください。
- ニュース収集は外部フィードを扱うため、SSRF・XML パース攻撃・巨大レスポンス等に対して防御ロジックを実装していますが、運用環境での追加評価を推奨します。
- 本パッケージは戦略ロジックと発注ロジックを分離しています。generate_signals は signals テーブルへの書き込みまで行いますが、発注（実際の送信）は execution 層 / ブローカー固有の実装が必要です。
- production (live) 環境では KABUSYS_ENV を `live` に設定し、追加の安全チェック・監査・ロギング設定を行ってください。

---

この README はコードベースに含まれる主要モジュールの設計意図と利用方法をまとめたものです。実行時の詳細な挙動や拡張方法については各モジュール内のドキュメンテーション文字列（docstring）を参照してください。必要であればサンプルスクリプトや運用手順（cron / systemd / Airflow 例）を別途作成します。