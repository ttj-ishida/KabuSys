# KabuSys

日本株向け自動売買基盤ライブラリ。J-Quants / kabuステーション 等の外部データ/ブローカーと連携して、データ収集（ETL）、品質チェック、ニュース収集、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたコンポーネント群を含む Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた多層（Raw / Processed / Feature / Execution）データスキーマ定義と初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF対策、XML攻撃対策、受信サイズ制限）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数管理（.env 自動ロード、必須パラメータ検証）

設計のポイント: 冪等性（ON CONFLICT / RETURNING を活用）・セキュリティ（SSRF、XML Bomb の対策）・運用性（ログ／監査／品質チェック）を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから取得）
  - レート制限（120 req/min 固定間隔）、リトライ（指数バックオフ）、401 でトークン自動更新
  - DuckDB への冪等保存（save_daily_quotes 等）

- data.schema
  - DuckDB スキーマ（raw_prices, raw_financials, raw_news, market_calendar, features, signals, orders, trades, positions, audit テーブル 等）
  - init_schema(db_path) / get_connection(db_path)

- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分更新、自動バックフィル、品質チェック呼び出し（data.quality）

- data.news_collector
  - RSS 取得（defusedxml, gzip 解凍, SSRF リダイレクト検査）
  - 記事正規化・ID 生成（URL 正規化 + SHA-256）
  - raw_news 保存（チャンク INSERT / RETURNING）、news_symbols 紐付け

- data.quality
  - 欠損・スパイク（前日比）・重複・日付不整合チェック
  - QualityIssue を返却し呼び出し元が重度に応じて対応可能

- data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）とインデックス定義
  - init_audit_schema / init_audit_db

- config
  - .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml）
  - 必須環境変数チェック（Settings クラス）

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

（実プロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / checkout

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb defusedxml

   ※プロジェクトに pyproject.toml がある場合は poetry / pip-tools 等を使用してください。

4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を配置します。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意/デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（default: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（default: INFO）
     - KABUS_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: データベースファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

5. データベース初期化（DuckDB スキーマ作成）
   - Python REPL やスクリプトで下記を実行:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")  # パスは環境に合わせる

---

## 使い方（例）

以下は主要なユースケースの使用例です。実行は Python スクリプトやバッチジョブから行います。

- Settings（環境変数読み取り）
  - from kabusys.config import settings
  - settings.jquants_refresh_token / settings.kabu_api_password / settings.duckdb_path などを参照

- J-Quants のトークン取得
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使って ID トークンを取得

- DuckDB スキーマ初期化
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)  # ファイルを自動作成してテーブル作成

- 日次 ETL 実行（市場カレンダ・株価・財務・品質チェックを含む）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
    conn = init_schema(settings.duckdb_path)
    # known_codes を与えると記事と銘柄を紐付ける
    known_codes = {"7203", "6758", "6861"}
    stats = run_news_collection(conn, known_codes=known_codes)
    print(stats)  # {source_name: 新規保存数}

- 生データ保存（手動フェッチ→保存）
  - from kabusys.data import jquants_client as jq
    conn = init_schema(settings.duckdb_path)
    token = jq.get_id_token()
    records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
    saved = jq.save_daily_quotes(conn, records)

- 品質チェック単体実行
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date.today())
    for i in issues: print(i)

- 監査ログ初期化
  - from kabusys.data.audit import init_audit_schema
    conn = init_schema(settings.duckdb_path)
    init_audit_schema(conn)

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知トークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（検証あり）
- LOG_LEVEL: ログレベル（検証あり）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env 自動読み込みを無効化

設定はプロジェクトルートの `.env` / `.env.local` で指定可能（自動ロード時の優先順: OS env > .env.local > .env）。

---

## 開発時のヒント

- 自動 .env ロードは config モジュールがプロジェクトルート（.git または pyproject.toml）を基に行います。テストで自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制御は内部で固定間隔スロットリング（120 req/min）を行います。大量データを取得する際はページネーションと速さに注意してください。
- news_collector は SSRF、gzip bomb、XML Bomb を考慮した実装です。テストでは _urlopen をモックして外部呼び出しを避けてください。
- DuckDB の操作はトランザクションを適切に使用（begin/commit/rollback）しています。スキーマを変更する場合は既存データとの互換性に注意してください。
- 型と Python の構文（PEP 604 のユニオン演算子など）を使用しているため、Python 3.10 以上を推奨します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（取得・保存）
    - news_collector.py            -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                    -- DuckDB スキーマ定義と初期化
    - pipeline.py                  -- ETL パイプライン（差分更新 / 日次実行）
    - audit.py                     -- 監査ログ（signal/order/execution）初期化
    - quality.py                   -- データ品質チェック
  - strategy/
    - __init__.py                  -- 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                  -- 発注/ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py                  -- 監視用モジュール（拡張ポイント）

---

## 免責・今後の作業

- このリポジトリはプラットフォーム実装の基礎を示すもので、実際の本番運用にはさらなるテスト、エラーハンドリング、運用監視、セキュリティチェックが必要です。
- strategy / execution / monitoring は拡張ポイントとして用意されています。実運用用の戦略実装やブローカーインターフェースは別途実装してください。

---

必要ならば README に追記する例：CI 用コマンド、ログ設定例、より詳細な .env.example（サンプル）や、よくあるトラブルシューティング（DB ファイル権限、ネットワーク問題など）。必要な内容があれば指示してください。