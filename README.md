# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants API や RSS を利用したデータ収集、DuckDB を利用したスキーマ管理・ETL、品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）など、運用に必要な機能群を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダーの取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS フィードからのニュース収集と銘柄紐付け（SSRF対策・XML攻撃対策・トラッキング除去）
- DuckDB を用いた層別スキーマ（Raw / Processed / Feature / Execution / Audit）の定義・初期化
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、次/前営業日計算）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

設計上、冪等性（ON CONFLICT を活用）、Look-ahead バイアス防止（fetched_at の記録）、安全性（SSRF防止・defusedxml など）に配慮しています。

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local の自動読み込み（必要に応じて無効化可）
  - 必須環境変数チェック（settings オブジェクト）
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token（refresh token → id token）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レート制御（120 req/min）、再試行（指数バックオフ、401 時の自動リフレッシュ含む）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理（URL除去・空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF・XML攻撃対策・受信サイズ上限
  - raw_news / news_symbols への保存（チャンク挿入・RETURNING使用）
  - 銘柄コード抽出（4桁数字）
- スキーマ管理（kabusys.data.schema）
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution）
  - init_schema, get_connection
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl（カレンダー、株価、財務の差分取得＋品質チェック）
  - 差分取得、バックフィル、品質チェック（kabusys.data.quality）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチでの差分更新）
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL
  - init_audit_schema / init_audit_db（UTC タイムゾーン固定）
- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合の検出
  - run_all_checks（問題のリストを返す）

---

## 要件

- Python 3.10+
- 依存パッケージ（主なもの）
  - duckdb
  - defusedxml

開発環境や CI では上記ライブラリをインストールしてください。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン／作業ディレクトリへ移動
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - またはプロジェクトに pyproject.toml / requirements.txt があればそれに従ってください
4. パッケージを editable インストール（任意）
   - pip install -e .

環境変数は .env ファイルまたは OS 環境変数で設定します（自動ロードあり）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主なもの）

以下は本プロジェクトが参照する主な環境変数です（.env に定義してください）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot Token（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（省略時: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（省略時: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時: INFO）

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## 基本的な使い方

以下は最もよく使う API の例です。実行は Python スクリプト内から行います。

- DuckDB スキーマ初期化

  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイルを作成してスキーマを作る

- 監査 DB 初期化（監査専用 DB を別に作る場合）

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

- 日次 ETL 実行（株価・財務・カレンダーの差分 ETL + 品質チェック）

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 引数で target_date, id_token, run_quality_checks 等を指定可能
  print(result.to_dict())

- J-Quants から直接データ取得（テストや個別取得）

  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings のリフレッシュトークンを使用
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- ニュース収集ジョブ実行

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は銘柄コードセット（抽出に使用）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})

- 品質チェック単体実行

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None, reference_date=None)
  for i in issues:
      print(i)

- カレンダー関連ユーティリティ

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_trade = is_trading_day(conn, date(2024,1,4))
  nxt = next_trading_day(conn, date(2024,1,4))

---

## 注意点・運用上のポイント

- J-Quants API はレート制限（120 req/min）に従う必要があります。本クライアントは固定スロットリングで制御します。
- get_id_token は内部でトークンキャッシュを持ち、401 時に自動リフレッシュしてリトライします。
- ETL は差分更新を行います。初回はデータ開始日（デフォルト 2017-01-01 など）から取得します。
- DuckDB への保存は可能な限り冪等に設計（ON CONFLICT DO UPDATE / DO NOTHING）されています。
- RSS ニュース取得は SSRF・XML 攻撃対策を施しています。外部 URL の検証や受信サイズ上限を設定しています。
- 監査ログ（audit）は UTC タイムゾーンを前提にしています。init_audit_schema は接続の TimeZone を UTC に設定します。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると .env ファイルの自動ロードを抑制できます（テスト等で便利）。

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ構成（抜粋）:

src/
  kabusys/
    __init__.py
    config.py                     # 環境変数・設定管理（.env 自動読み込みなど）
    data/
      __init__.py
      jquants_client.py           # J-Quants API クライアント（取得・保存）
      news_collector.py           # RSS ニュース収集・保存・銘柄抽出
      schema.py                   # DuckDB スキーマ定義・初期化
      pipeline.py                 # ETL パイプライン（run_daily_etl 等）
      calendar_management.py      # マーケットカレンダー管理
      audit.py                    # 監査ログ（signal/order/execution）DDL と初期化
      quality.py                  # データ品質チェック
    strategy/
      __init__.py                 # 戦略関連（今後拡張想定）
    execution/
      __init__.py                 # 発注 / ブローカー関連（今後拡張想定）
    monitoring/
      __init__.py                 # 監視モジュール（今後拡張想定）

ドキュメントや設計メモ（DataPlatform.md 等）がある場合はプロジェクトルートに配置される想定です。

---

## 追加情報 / 貢献

- ログレベルは環境変数 LOG_LEVEL で制御できます（デフォルト INFO）。
- 開発・テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効化できます。
- 新しい機能追加やバグ修正は PR ベースでお願いします。テスト・型チェック・ドキュメント整備を重視してください。

---

この README はコードベースからの要点をまとめたものです。各モジュールの詳細はソースコード内の docstring を参照してください。必要であればサンプルスクリプトや運用手順のテンプレートも作成しますので、ご希望を教えてください。