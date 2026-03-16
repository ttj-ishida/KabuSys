# KabuSys

日本株自動売買プラットフォームのコアライブラリ（内部用ライブラリ）。
J-Quants から市場データを取得して DuckDB に保存し、品質チェックや戦略/発注レイヤへデータを提供することを目的としたモジュール群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ収集・保存・品質管理・監査追跡を行うための基盤モジュールです。主な役割は次の通りです。

- J-Quants API からの株価（日足）・財務データ・JPX カレンダーの取得
- DuckDB に対するスキーマ定義と冪等な保存（ON CONFLICT DO UPDATE）
- ETL（差分取得、バックフィル、品質チェック）パイプライン
- 監査ログ（シグナル → 発注 → 約定）用テーブル群の初期化
- 環境変数による設定管理（.env 自動ロード機能）

設計上のポイント:
- API レート制限（120 req/min）に従うレートリミッター
- リトライ（指数バックオフ）、401 の自動トークンリフレッシュ、ページネーション対応
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログによりトレーサビリティを保証

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須環境変数の取得（未設定時は ValueError）

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークン → IDトークン）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制限・リトライ・401自動リフレッシュ・ページネーション対応
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）※冪等

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を含むテーブル定義
  - init_schema(db_path) でテーブルとインデックスを作成
  - get_connection(db_path) で接続取得（初期化は行わない）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日に基づく）、バックフィル機能
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック統合（kabusys.data.quality）
  - run_daily_etl: 日次 ETL の高水準エントリポイント（個別ジョブも呼べる）

- 品質チェック（kabusys.data.quality）
  - 欠損（OHLC）検出
  - 主キー重複検出
  - スパイク（前日比）検出
  - 日付不整合（未来日付、非営業日のデータ）検出
  - 全チェックを run_all_checks で実行可能

- 監査ログ初期化（kabusys.data.audit）
  - シグナル・発注要求・約定の監査テーブルとインデックスを作成
  - init_audit_schema, init_audit_db を提供

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 のタイプ表記（X|Y）などを使用）
- 基本的な標準ライブラリのみで動作しますが、DuckDB を使用するため `duckdb` パッケージが必要です。

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存のインストール
   - pip install duckdb

   （パッケージ配布がある場合は pip install -e . や requirements.txt を使ってください）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` と `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（kabusys.config.Settings に基づく）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN        : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID       : 通知先 Slack チャンネル ID（必須）

任意 / デフォルト付き
- KABU_API_BASE_URL : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH       : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH       : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV       : 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL         : ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)（デフォルト: INFO）

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
KABU_API_PASSWORD=あなたの_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

以下は最小限の利用例です。実行前に必須環境変数を設定してください。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー取得 → 株価・財務 ETL → 品質チェック）
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")  # すでに init_schema が呼ばれている前提
result = pipeline.run_daily_etl(conn, target_date=date.today())

# ETL 結果確認
print(result.to_dict())
```

- J-Quants から個別データ取得（テストやデバッグ）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使ってトークン取得
quotes = fetch_daily_quotes(id_token=id_token, code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
print(len(quotes))
```

- 監査ログの初期化（既存 DuckDB 接続に追加）
```python
from kabusys.data import audit, schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

注意点
- run_daily_etl は個々のステップで例外を捕捉し、可能な範囲で残りのステップを継続します。結果は ETLResult オブジェクトで返り、品質問題やエラーの概要が含まれます。
- J-Quants API はレート制限（120 req/min）を守るため、fetch 系関数は内部で待機します。大規模なバルク取得時は時間がかかる点に注意してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイルと説明:

- src/kabusys/
  - __init__.py             - パッケージ定義（__version__=0.1.0, __all__）
  - config.py               - 環境変数・設定管理（.env 自動ロード、Settings）
  - execution/              - 発注・実行関連モジュール（プレースホルダ）
    - __init__.py
  - strategy/               - 戦略関連（プレースホルダ）
    - __init__.py
  - monitoring/             - 監視・メトリクス関連（プレースホルダ）
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py     - J-Quants API クライアント（取得・保存・認証・リトライ）
    - schema.py             - DuckDB スキーマ定義と初期化関数
    - pipeline.py           - ETL パイプライン（差分取得・バックフィル・品質チェック）
    - quality.py            - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py              - 監査ログ（シグナル/発注/約定）スキーマ初期化

（将来的に strategy や execution モジュール内に具体的なアルゴリズム・ブローカー連携が追加される想定です）

---

## 運用上の注意・補足

- 環境自動ロード
  - パッケージは起動時にプロジェクトルートを .git または pyproject.toml で検出し、`.env` と `.env.local` を順に読み込みます（OS 環境変数が優先）。
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト目的など）。

- 環境（KABUSYS_ENV）
  - 有効値: development, paper_trading, live
  - is_dev / is_paper / is_live プロパティで判定可能

- ログレベル検証
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかである必要があります。設定ミスは ValueError になります。

- テストについて
  - jquants_client の get_id_token は allow_refresh=False の内部呼び出しを考慮して設計されており、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD や id_token を注入して外部通信をモックしてください。

---

必要であれば README に以下の内容も追加できます：
- CI/CD のセットアップ例
- Docker / コンテナ化手順
- 詳細な ETL スケジュール（Cron / Airflow 例）
- 監視・アラート設計（Slack 通知のサンプル）
- SQL スキーマの ER 図・DataPlatform.md への参照

追加したい項目があれば指示してください。