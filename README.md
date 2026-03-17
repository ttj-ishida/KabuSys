# KabuSys

日本株向け自動売買システムのコアライブラリ（README）

---

## プロジェクト概要

KabuSys は日本株向けのデータ取得・ETL・監査・ニュース収集・発注管理を想定したライブラリ群です。主に以下を目的とします。

- J-Quants API を用いた株価・財務・マーケットカレンダーの取得と DuckDB への冪等保存
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策やトラッキングパラメータ除去を実装）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 監査ログ（シグナル → 発注 → 約定のトレース用テーブル群）
- マーケットカレンダー管理（営業日判定、前後営業日取得など）

設計上のポイント：
- API レート制限（J-Quants: 120 req/min）遵守
- リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
- DuckDB への挿入は ON CONFLICT を使った冪等処理
- セキュリティ対策（XML 対策、SSRF対策、レスポンスサイズ制限 等）
- テスト容易性（id_token 注入や _urlopen のモックが可能）

---

## 機能一覧

- data/jquants_client.py
  - J-Quants からの日足（OHLCV）、四半期財務、マーケットカレンダーの取得
  - レートリミット、リトライ、トークン自動更新
  - DuckDB への save_*（冪等）関数

- data/pipeline.py
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新、バックフィル機能

- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema() による初期化

- data/news_collector.py
  - RSS 取得・解析・前処理・ID生成（SHA-256）・DuckDB への保存
  - SSRF/圧縮爆弾対策、トラッキングパラメータ除去、銘柄コード抽出

- data/calendar_management.py
  - market_calendar の更新ジョブ、営業日判定・前後営業日・営業日リスト取得

- data/quality.py
  - 欠損・スパイク・重複・日付不整合のチェック
  - run_all_checks() による一括実行

- data/audit.py
  - シグナル / 発注要求 / 約定 の監査用テーブル定義・初期化
  - init_audit_db() による監査DBの初期化

- config.py
  - 環境変数読み込み（.env / .env.local の自動読み込み、必要変数チェック）
  - settings オブジェクト経由で設定取得

その他:
- strategy, execution, monitoring パッケージ用の枠組み（空の __init__.py）

---

## セットアップ手順

前提
- Python 3.10+ を推奨（typing の新記法を使用）
- ネットワークアクセスが必要（J-Quants, RSS 等）

1. レポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   必要な主な依存は duckdb と defusedxml などです。プロジェクトに requirements.txt がある場合はそれを利用してください。サンプル:
   ```
   pip install duckdb defusedxml
   ```

   （実運用では HTTP クライアントや Slack SDK 等を追加する可能性があります）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（config.Settings が要求）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト付き:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DB スキーマ初期化
   Python REPL やスクリプトで DuckDB スキーマを作成します。
   例:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを自動作成
   ```

   監査用 DB を別で用意する場合:
   ```python
   from kabusys.data import audit
   aconn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（サンプル）

以下は典型的な利用例（Python スクリプト / REPL）です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 個別ジョブ実行
  - 市場カレンダー更新
    ```python
    from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print("saved:", saved)
    ```

  - 株価差分 ETL
    ```python
    from datetime import date
    from kabusys.data.pipeline import run_prices_etl
    fetched, saved = run_prices_etl(conn, target_date=date.today())
    ```

- ニュース収集と銘柄紐付け
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes: 銘柄コードのセット（例: システム内で管理しているコード群）
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants API を直接使う（テストやページネーション制御）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って ID トークン取得
  rows = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
  ```

注意点:
- run_daily_etl などは例外を捕捉してエラー情報を ETLResult に格納しますが、呼び出し側でログやアラートを適切に処理してください。
- ネットワーク呼び出しはリトライ / レート制御されていますが、API 利用上の制限や課金に注意してください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須)：kabuステーション API のパスワード
- KABU_API_BASE_URL：kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)：Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID (必須)：通知先 Slack チャンネル ID
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：監視用途の SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV：実行環境（development / paper_trading / live）
- LOG_LEVEL：ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1：.env 自動読み込みを無効化（テスト用）

---

## ディレクトリ構成

リポジトリ内の主要ファイル／モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得・保存）
    - news_collector.py        # RSS ニュース収集・保存・銘柄抽出
    - schema.py                # DuckDB スキーマ定義・初期化
    - pipeline.py              # 日次 ETL、差分更新ロジック
    - calendar_management.py   # マーケットカレンダー管理（営業日判定等）
    - audit.py                 # 監査ログ（signal/order/execution）
    - quality.py               # データ品質チェック
  - strategy/
    - __init__.py
    (戦略関連モジュールを配置する想定)
  - execution/
    - __init__.py
    (発注・ブローカー連携の実装を置く想定)
  - monitoring/
    - __init__.py
    (監視・メトリクス収集用の実装を置く想定)

ドキュメントに基づく設計（DataPlatform.md / DataSchema.md 等）に準拠して層別スキーマ・監査テーブルなどを実装しています。

---

## 運用上の注意点

- J-Quants の API レートと利用規約に従ってください（本コードは 120 req/min を想定したレートリミッタを実装しています）。
- DuckDB ファイルはローカルファイルロックやバックアップに注意してください（同一ファイルへの多重プロセス書き込みは注意が必要）。
- ニュース取得では外部 URL をダウンロードするため、SSRF 対策・Content-Length チェック・デコード後サイズチェックを行っていますが、運用環境で更なる制約が必要なら設定を追加してください。
- 本ライブラリはフレームワークの核であり、実際の発注（証券会社連携）、リスク管理、通知ロジック等は別途実装が必要です。

---

必要であれば、README に CI / テスト実行方法やより詳しい API ドキュメント用のサンプル（関数説明・入出力例）を追記します。どの部分を詳しく書くか指定してください。