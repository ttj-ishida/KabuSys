# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。データ取得（J-Quants）、ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログなど、取引システムの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API から株価（日足）・財務データ・マーケットカレンダーを安全に取得する
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution）スキーマを管理・初期化する
- ETL（差分取得・バックフィル・品質チェック）を行うパイプラインを提供する
- RSS ベースのニュース収集と銘柄抽出機能を提供する（SSRF/Gzip Bomb 等の安全対策済み）
- 監査ログ（シグナル→発注→約定のトレース）用スキーマを提供する
- 市場カレンダー（JPX）に基づく営業日判定・更新ジョブを提供する

設計上のポイント：
- API レート制御（J-Quants: 120 req/min）
- 冪等（idempotent）保存（DuckDB 側で ON CONFLICT を利用）
- リトライ・トークン自動リフレッシュ（401 時）
- データ品質チェックを分離して実行（Fail-Fast ではなく全件収集）
- セキュリティ対策（RSS の SSRF 检査、defusedxml、受信サイズ制限 等）

---

## 主な機能一覧

- 環境変数管理・自動ロード（`.env` / `.env.local` のサポート、起点はプロジェクトルート）
- J-Quants API クライアント
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - レートリミット、リトライ、トークンキャッシュを内蔵
- DuckDB スキーマ管理（data.schema）
  - init_schema(), get_connection()
  - Raw / Processed / Feature / Execution 層の多数テーブル定義
- ETL パイプライン（data.pipeline）
  - run_daily_etl(), run_prices_etl(), run_financials_etl(), run_calendar_etl()
  - 差分更新、バックフィル、品質チェック呼び出し
- ニュース収集（data.news_collector）
  - fetch_rss(), save_raw_news(), save_news_symbols(), extract_stock_codes()
  - URL 正規化、トラッキングパラメータ除去、SSRF/サイズ制限対策
- カレンダー管理（data.calendar_management）
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()
- 品質チェック（data.quality）
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency(), run_all_checks()
- 監査ログ（data.audit）
  - init_audit_schema(), init_audit_db()（シグナル・発注要求・約定の監査テーブル）

---

## セットアップ手順

前提
- Python 3.9+（型アノテーション等を利用）
- Git リポジトリのルートにプロジェクトが存在する想定（.env 自動ロード機能で使用）

1. リポジトリをクローン
   - git clone ...（省略）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - （開発時はローカルパッケージとしてインストールする場合）
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` として必要な環境変数を配置するか、OS 環境変数で設定します。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN (J-Quants リフレッシュトークン)
     - KABU_API_PASSWORD (kabuステーション API パスワード)
     - SLACK_BOT_TOKEN (Slack 通知用ボットトークン)
     - SLACK_CHANNEL_ID (通知先 Slack チャンネル ID)
   - 任意 / デフォルトを持つ変数:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
   - 自動 .env ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 初期化（DuckDB スキーマ作成）
   - Python REPL やスクリプトから:
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)

---

## 使い方（簡易チュートリアル）

以下は主要機能の簡単な利用例です。実際はログ設定や例外処理を追加してご利用ください。

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - from kabusys.config import settings
  - conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（推奨エントリポイント）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定することで任意日にも実行可能
  - print(result.to_dict())

  run_daily_etl は以下を順に実行します：
  1. 市場カレンダー更新（先読み）
  2. 株価（日足）差分取得 + 保存
  3. 財務データ差分取得 + 保存
  4. 品質チェック（オプション）

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
  - new_counts = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  - print(new_counts)

  デフォルト RSS ソースは `DEFAULT_RSS_SOURCES`（例: Yahoo Finance のビジネスカテゴリ）。

- マーケットカレンダー夜間更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- 監査ログ用スキーマ初期化
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

- J-Quants API を直接使う例
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を利用
  - rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,2,1))

注意点：
- jquants_client は内部でレート制限とリトライを行います。大量のリクエストは避け、バックオフの設計を尊重してください。
- news_collector は RSS の安全性（SSRF、gzip 圧縮サイズ等）に配慮しています。外部ネットワークアクセスが必要です。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — development / paper_trading / live
- LOG_LEVEL (任意) — DEBUG/INFO/...
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

.env のパース挙動:
- export KEY=val 形式に対応
- シングル/ダブルクォート内はエスケープ対応
- コメントは # の前にスペースがある場合のみ扱う（簡易仕様）
- プロジェクトルートは __file__ を起点に .git または pyproject.toml を探して決定

---

## ディレクトリ構成

リポジトリは src パッケージ構成となっており、主要ファイルは以下の通りです。

- src/kabusys/
  - __init__.py  (パッケージ初期化、__version__ = "0.1.0")
  - config.py    (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py       (J-Quants API クライアント、保存ユーティリティ)
    - news_collector.py      (RSS ニュース収集、SSRF 対策、DB 保存)
    - schema.py              (DuckDB スキーマ定義・初期化)
    - pipeline.py            (ETL パイプライン、差分更新・品質チェック)
    - calendar_management.py (マーケットカレンダー管理・営業日ヘルパー)
    - audit.py               (監査ログテーブル定義と初期化)
    - quality.py             (データ品質チェック)
  - strategy/
    - __init__.py  (戦略層用パッケージプレースホルダ)
  - execution/
    - __init__.py  (注文実行層用パッケージプレースホルダ)
  - monitoring/
    - __init__.py  (監視モジュールプレースホルダ)

各モジュールの役割は上記「主な機能一覧」参照。

---

## 注意事項 / ベストプラクティス

- DuckDB ファイルは適切にバックアップしてください。init_schema は冪等（既存テーブルはスキップ）ですが、スキーマ設計は慎重に扱ってください。
- 本ライブラリは実運用の取引ロジックそのものを提供するものではなく、データ基盤・監査基盤を提供します。実際の発注ロジックや資金管理は上位で実装してください。
- API トークン等の機密情報は .env / シークレット管理ツールで安全に管理してください。`.env` をリポジトリにコミットしないでください。
- テスト実行時に .env 自動ロードを妨げたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。

---

## さらに詳しく

コード内には各モジュールの docstring と設計メモが含まれています。実装や動作の詳細、SQL 定義、品質チェックのアルゴリズムは該当ソース（src/kabusys/data/*.py）を参照してください。

ご不明な点やドキュメント化してほしい追加項目があれば教えてください。