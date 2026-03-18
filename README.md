# KabuSys — 日本株自動売買システム

簡潔な日本語 README。ここではプロジェクトの概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を説明します。

※本 README はリポジトリ内のソースコードを元に作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・データ基盤を目的とした Python パッケージです。  
J-Quants API などの外部データソースから市場データ（株価・財務・市場カレンダー）やニュースを収集し、DuckDB に保存、ETL（差分取得・バックフィル・品質チェック）を行います。  
さらに、監査ログ（シグナル→発注→約定のトレース）やマーケットカレンダー管理、ニュースの銘柄紐付け等の機能を備え、戦略レイヤー／発注エンジンと連携できる設計になっています。

主な設計方針：
- データ収集は冪等性（ON CONFLICT）を意識して実装
- API レート制限と再試行（指数バックオフ）に対応
- Look-ahead bias を防ぐため取得時刻（fetched_at）を記録
- ニュース収集は SSRF / XML Bomb 等の安全対策を実施
- DuckDB を用いた軽量・高速な分析ストア

---

## 機能一覧

- 環境変数／.env の自動読込と設定ラッパー（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロード
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務四半期データ、JPX マーケットカレンダー取得
  - 120 req/min のレート制御、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得、記事正規化（URL トラッキングパラメータ除去、SHA-256 ベースの ID）
  - defusedxml を用いた安全な XML パース、SSRF 対策、最大受信サイズ制限
  - DuckDB への冪等保存（raw_news、news_symbols）と銘柄コード抽出

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層を含む DuckDB スキーマ定義と初期化
  - テーブル作成とインデックス作成を自動化する init_schema, get_connection

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日に基づく差分算出）・バックフィル・品質チェック統合
  - 日次 ETL エントリ（run_daily_etl）でカレンダー → 株価 → 財務 → 品質チェックを順次実行

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
  - 夜間バッチによるカレンダー更新ジョブ（calendar_update_job）

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比閾値）および日付不整合チェック
  - QualityIssue オブジェクトで問題を集約

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化
  - 発注から約定までのトレースをUUIDチェーンで保証

---

## 必要要件

- Python 3.10 以上（型注釈の union 演算子 `|` を使用）
- 主要ライブラリ（例）
  - duckdb
  - defusedxml

（インストール済みライブラリはプロジェクト配布時の requirements.txt / pyproject.toml に合わせてください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係をインストール
   - 例: pip install duckdb defusedxml
   - 実際は requirements.txt / pyproject.toml があればそれに従ってください。

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意変数（デフォルトがあるもの）:
     - KABUS_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live; default: development)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL; default: INFO)

   - 簡単な .env 例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

4. データベース初期化（DuckDB）
   - 例: Python REPL またはスクリプト内で以下を実行
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

5. 監査ログスキーマ初期化（任意）
   - from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（基本例）

以下は主要な操作のサンプルです。実行は Python スクリプト／REPL 上で行います。

- DuckDB の初期化と接続取得
  - from kabusys.data.schema import init_schema, get_connection
    conn = init_schema("data/kabusys.duckdb")
    # 既存 DB に接続する場合
    conn = get_connection("data/kabusys.duckdb")

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())  # ETLResult の要約

- ニュース収集ジョブの実行
  - from kabusys.data.news_collector import run_news_collection
    # known_codes は銘柄コードセット（抽出に使用）
    results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
    print(results)  # {source_name: saved_count, ...}

- カレンダーの夜間更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print("saved:", saved)

- J-Quants の単発 API 呼び出し（例：日足取得）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
    saved = save_daily_quotes(conn, records)

- 品質チェックを直接実行
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=None)
    for i in issues:
        print(i)

- 環境設定の参照
  - from kabusys.config import settings
    token = settings.jquants_refresh_token
    db_path = settings.duckdb_path

ログレベルは環境変数 LOG_LEVEL で制御できます（例: LOG_LEVEL=DEBUG）。

---

## 注意点 / 運用上のポイント

- J-Quants API のレート制限（120 req/min）を厳守しています。大量リクエストを行う場合は実装済みの RateLimiter の挙動に注意してください。
- ネットワーク障害や HTTP 5xx 等に対してはリトライ（指数バックオフ）を行いますが、長時間の API 停止や認証情報の期限切れには対処が必要です。
- ニュース収集では外部から供給される XML を扱うため、defusedxml および受信サイズ上限、SSRF ブロック等の安全対策を組み込んでいます。
- DuckDB のファイルパスは settings.duckdb_path で指定できます（デフォルト: data/kabusys.duckdb）。バックアップやファイルロックに注意してください（複数プロセスからの同時書き込みは設計に注意が必要）。
- audit スキーマはトレーサビリティ確保のため削除しない想定です。運用ポリシーに合わせて DB 管理を行ってください。
- 自動で .env を読み込む機能はテスト時や CI で無効化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## ディレクトリ構成

以下は主要なファイル・モジュールの配置（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py                    -- DuckDB スキーマ定義と init_schema
      - jquants_client.py            -- J-Quants API クライアント (取得・保存)
      - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
      - news_collector.py            -- RSS ニュース収集・保存
      - calendar_management.py       -- マーケットカレンダー管理
      - quality.py                   -- データ品質チェック
      - audit.py                     -- 監査ログスキーマ
      - pipeline.py
    - strategy/
      - __init__.py                   -- 戦略レイヤ（拡張点）
    - execution/
      - __init__.py                   -- 発注エンジン（拡張点）
    - monitoring/
      - __init__.py                   -- 監視・アラート（拡張点）

このリポジトリはデータ収集・品質管理・監査ログの基盤を提供するコアを持ち、戦略や実際の発注システムは strategy / execution 層を実装して繋げる構成です。

---

## 今後の拡張案（参考）

- Slack 等への通知連携（settings に Slack 設定があるので通知モジュールの追加が容易）
- 発注実行モジュール（kabu ステーション / ブローカー API 連携）
- ストラテジー実装例とリスク管理パイプライン
- CI / テスト向けのモックや固定レスポンスを用いた統合テストスイート

---

ご不明点や README に追加したい具体的な使用例（例: systemd での定期実行 / Airflow 連携など）があればお知らせください。必要に応じて README に追記します。