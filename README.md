# KabuSys

日本株向けの自動売買システム用ライブラリ群（データ取得・ETL・ファクター計算・シグナル生成・監査用DBスキーマ等）

このリポジトリは、J‑Quants 等の外部 API から市場データを取得し、DuckDB に保存／前処理を行い、研究用ファクター・戦略用特徴量を作成して売買シグナルを生成するための共通モジュール群を提供します。発注（ブローカー連携）やモニタリングは分離された層として設計されています。

主な設計方針
- ルックアヘッドバイアス防止（集計は target_date 時点の情報のみ使用）
- 冪等性（DB への保存は ON CONFLICT やトランザクションで安全化）
- API レート制御・リトライ・トークン自動更新などの堅牢性考慮
- DuckDB を中心としたローカル DB ベースのパイプライン

## 機能一覧
- 環境設定管理（.env 自動読み込み、必須環境変数の検査） — kabusys.config
- J‑Quants API クライアント（トークン管理、ページネーション、リトライ、レート制限） — kabusys.data.jquants_client
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層） — kabusys.data.schema
- ETL パイプライン（差分取得、バックフィル、品質チェック呼び出し） — kabusys.data.pipeline
- RSS ニュース収集・正規化・DB 保存（SSRF対策、URL正規化、記事ID生成、銘柄抽出） — kabusys.data.news_collector
- マーケットカレンダー管理（営業日判定、前後の営業日探索、夜間更新ジョブ） — kabusys.data.calendar_management
- 統計ユーティリティ（クロスセクション Z スコア正規化 等） — kabusys.data.stats
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等） — kabusys.research.factor_research
- 特徴量作成（研究出力の正規化・ユニバースフィルタ・features テーブル更新） — kabusys.strategy.feature_engineering
- シグナル生成（features と AI スコア統合、BUY/SELL 判定、signals テーブル更新） — kabusys.strategy.signal_generator
- 監査ログ（signal → order_request → execution の追跡を想定したスキーマ） — kabusys.data.audit

## 必要条件
- Python 3.10 以上（Union 型表記 `X | Y` を使用しているため）
- 必要パッケージ（例）:
  - duckdb
  - defusedxml

実行環境により追加で必要となるライブラリ（Slack 通知・ブローカー SDK 等）は各機能で別途依存設定してください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（用途に応じて setuptools / wheel / その他 CI ツールを導入してください）

## 環境変数（主なもの）
config.Settings から参照される主要な環境変数です。実行前に .env を作成して設定して下さい（自動で .env / .env.local をプロジェクトルートから読み込みます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボット用トークン（通知等で使用する場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション（デフォルトあり）:
- KABUS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

注意: Settings は必須項目が未設定だと ValueError を投げます。

## セットアップ手順（簡易）
1. リポジトリをチェックアウト
2. Python 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```
3. プロジェクトルートに .env を配置（.env.example をコピーして必要値を埋めることを想定）
   ```
   cp .env.example .env
   # .env を編集して JQUANTS_REFRESH_TOKEN 等を設定
   ```
4. DuckDB スキーマ初期化
   Python REPL またはワンライナーで初期化できます:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   またはコマンドライン:
   ```
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

## 使い方（代表的な操作例）

- 日次 ETL を実行（J‑Quants から差分取得して保存・品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 存在しない場合は作成して接続を返す
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）を作成
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  import duckdb
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 31))
  print(f"features upserted: {n}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 31), threshold=0.6)
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 事前に有効銘柄リストを用意
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

これらの関数は DuckDB 接続を受け取り、内部でトランザクションや冪等操作（ON CONFLICT）を行います。実運用ではログ出力・監視・エラーハンドリングをラッパー側で実装してください。

## 主要モジュールと API（抜粋）
- kabusys.config.settings — 環境設定アクセス
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

各関数の詳細な挙動・引数や戻り値はモジュール内の docstring を参照してください。

## ディレクトリ構成
（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数管理
  - data/
    - __init__.py
    - jquants_client.py  — J‑Quants API クライアント + 保存ユーティリティ
    - schema.py          — DuckDB スキーマ定義 / init_schema
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - news_collector.py  — RSS 取得・前処理・DB 保存
    - calendar_management.py — マーケットカレンダー関連ユーティリティ
    - stats.py           — zscore_normalize 等の統計ユーティリティ
    - features.py        — データ層からの feature ユーティリティ再エクスポート
    - audit.py           — 監査ログ用スキーマ定義
    - (その他: execution / monitoring などのサブパッケージ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/ (空の __init__ が存在、発注層を想定)
  - monitoring/ (監視用コードを配置する想定)

※ 実際のリポジトリでは README と .env.example をプロジェクトルートに置くことを推奨します。

## 開発・テストのヒント
- 自動環境変数ロードはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を読み込みます。ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にすることができます。
- network や API を叩く部分（jquants_client._request、news_collector._urlopen 等）はテストでモックしやすいようにモジュール内部で分離されています。
- DuckDB はインメモリ ":memory:" をサポートするため、単体テストでは永続ファイル不要でスキーマ初期化 → テスト用データ挿入が可能です。
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```

## ライセンス / 貢献
- 本 README はこのコードベースの概要と使い方を説明するためのものです。実際のライセンス・貢献ルールはリポジトリのルートに LICENSE / CONTRIBUTING ドキュメントがあればそちらを参照してください。

---

必要であれば、.env.example のテンプレートや CI 用の実行手順（cron / Airflow / GitHub Actions での ETL スケジュール例）、より具体的な監視・アラート設計の README セクションも作成できます。どの情報を優先して追加しますか？