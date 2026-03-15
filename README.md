# KabuSys

日本株向け自動売買システムの骨格ライブラリです（データ取得、DBスキーマ、監査ログ等）。  
このリポジトリはミニマルなコア機能を提供し、戦略・発注ロジックやモニタリング機能は拡張して利用することを想定しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は主に以下を目的とした内部ライブラリです。

- J-Quants API からのマーケットデータ（OHLCV、財務データ、マーケットカレンダー）取得
- 取得データを DuckDB に保存するためのスキーマ定義と初期化機能
- 取引フローの監査ログ（トレーサビリティ）を記録する監査テーブルの定義・初期化
- 環境変数管理（.env 自動読み込み、Settings オブジェクト）
- レート制限・リトライ・トークン自動リフレッシュ等の実装

戦略層（strategy）、実行層（execution）、モニタリング（monitoring）はパッケージの名前空間として用意されていますが、具体的な戦略やブローカ接続の実装は含まれていません。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須変数をラップした Settings クラス
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - API レート制限（120 req/min）を守る RateLimiter
  - 指数バックオフによるリトライ（最大 3 回）、HTTP 429 の Retry-After 対応
  - 401 受信時はリフレッシュトークンで自動的に id_token を再取得して再試行
  - ページネーション対応
  - 取得時刻（fetched_at）を UTC で保存し look-ahead bias を防止

- DuckDB スキーマ（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義
  - init_schema(db_path) で DB 初期化（親ディレクトリ自動作成）
  - get_connection(db_path) による既存 DB への接続

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions テーブルの定義
  - 監査データの永続化（全て UTC）
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化

---

## 必要条件

- Python 3.10+
  - （コード内で PEP 604 の union 型表記（|）を使用しているため 3.10 以上が必要）
- pip パッケージ:
  - duckdb
  - （必要に応じて urllib 関連は標準ライブラリを使用）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストールします（最低限 duckdb）。

   ```bash
   pip install duckdb
   ```

   ※ 本プロジェクトをパッケージ化している場合は `pip install -e .` 等で開発インストールできます。

3. 環境変数を用意します。プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます（読み込みは .git または pyproject.toml を基準にプロジェクトルートを検出します）。

   例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
   KABU_API_PASSWORD=あなたの_kabu_api_password
   SLACK_BOT_TOKEN=あなたの_slack_bot_token
   SLACK_CHANNEL_ID=あなたの_slack_channel_id

   # 任意: データベースパス（デフォルトは data/kabusys.duckdb）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（簡易サンプル）

以下は基本的な利用例です。J-Quants からデータを取得し、DuckDB に保存する流れを示します。

1. DuckDB スキーマ初期化（ファイル DB を使用する例）:

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

2. J-Quants から日足を取得して保存:

   ```python
   from kabusys.data import jquants_client
   # 銘柄コードと期間を指定して取得（None で全件）
   records = jquants_client.fetch_daily_quotes(code="7203", date_from=None, date_to=None)
   count = jquants_client.save_daily_quotes(conn, records)
   print(f"保存件数: {count}")
   ```

3. 財務データやマーケットカレンダーも同様:

   ```python
   fin = jquants_client.fetch_financial_statements(code="7203")
   jquants_client.save_financial_statements(conn, fin)

   cal = jquants_client.fetch_market_calendar()
   jquants_client.save_market_calendar(conn, cal)
   ```

4. 監査ログの初期化（既存 conn に対して追加）:

   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   ```

   または監査専用 DB を新規作成する場合:

   ```python
   audit_conn = audit.init_audit_db("data/audit.duckdb")
   ```

5. ID トークンを手動で取得する場合:

   ```python
   from kabusys.data.jquants_client import get_id_token
   token = get_id_token()  # settings.jquants_refresh_token を用いて POST
   ```

注意点:
- jquants_client._request は自動でレート制御・リトライ・401 リフレッシュを行います。複数ページを横断する処理では id_token を引数に渡すことによりページ間で共有できます（モジュール内キャッシュも利用されます）。
- DuckDB への INSERT は ON CONFLICT DO UPDATE により冪等になっています。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用途等）（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境区分（development, paper_trading, live）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化するフラグ（存在すれば無効）

---

## ディレクトリ構成

リポジトリ内の主なファイル・ディレクトリ構成は以下の通りです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数読み込みと Settings
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（取得・保存ロジック）
      - schema.py              -- DuckDB スキーマ定義・初期化
      - audit.py               -- 監査ログ（signal/order/execution）
      - audit.py
      - (その他データ関連モジュール)
    - strategy/
      - __init__.py            -- 戦略モジュールのエントリ（拡張ポイント）
    - execution/
      - __init__.py            -- 発注 / ブローカ接続の拡張ポイント
    - monitoring/
      - __init__.py            -- モニタリング関連（拡張ポイント）

上記以外にプロジェクトルートに .env/.env.local/.git や pyproject.toml があることを想定しています（config の自動読み込みでプロジェクトルート検出に使用）。

---

## 開発・拡張のヒント

- 戦略（strategy）層は features / ai_scores テーブル等を利用してシグナルを生成し、signal_queue / signals テーブルへ書き出す形を想定しています。
- 発注（execution）層は signal_queue を監視して order_requests テーブルを作成・更新し、証券会社 API へ送信します。監査ログは audit モジュールで管理してください。
- すべての TIMESTAMP は UTC を前提に扱う設計です。監査ログ初期化時に SET TimeZone='UTC' を実行します。

---

## ライセンス / 貢献

本 README はコードベースに基づくドキュメントです。実際に運用する場合は API キー管理・シークレット管理・テスト・エラーハンドリング・権限管理等を十分に行ってください。貢献方法やライセンス情報はプロジェクトのルートにある LICENSE や CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば README に「API 使用例（より詳細）」「運用チェックリスト」「よくある質問」などを追加できます。どのセクションを拡張するか教えてください。