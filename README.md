# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants API からマーケットデータ・財務データ・マーケットカレンダーを取得し、DuckDB に格納・品質チェックを行う ETL、RSS ベースのニュース収集、安全なリダイレクト検査付きのニュース取得、監査ログ（トレーサビリティ）用スキーマなどを提供します。

主な設計方針:
- API レート制限・リトライ・トークン自動リフレッシュ対応（J-Quants）
- DuckDB を用いた冪等なデータ保存（ON CONFLICT を利用）
- ニュース収集は SSRF / XML Bomb / Gzip bomb 等への対策を実装
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）

---

## 機能一覧

- データ取得（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レートリミット（120 req/min）、指数バックオフを伴うリトライ、401 時のトークン自動更新、取得時刻（fetched_at）記録

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新（DB の最終取得日に基づく差分取得、デフォルトで backfill）
  - 市場カレンダー先読み
  - 品質チェックの実行（quality モジュール）

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS 取得・前処理・ID 生成（URL 正規化後の SHA-256 先頭 32 文字）
  - SSRF 対策（リダイレクト先検証）、受信サイズ上限、gzip 解凍検査
  - DuckDB への冪等保存（INSERT ... ON CONFLICT DO NOTHING、RETURNING で挿入件数取得）
  - 銘柄コード抽出（4桁数字、known_codes によるフィルタ）

- スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義および初期化（init_schema）
  - インデックス作成

- カレンダー管理（src/kabusys/data/calendar_management.py）
  - 営業日判定、next/prev_trading_day、期間内営業日列挙、夜間カレンダー更新ジョブ

- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合検出
  - QualityIssue 型で結果を返す

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions を含む監査用スキーマの初期化（init_audit_schema / init_audit_db）
  - UTC 強制、冪等性・トレーサビリティ重視

- 設定管理（src/kabusys/config.py）
  - .env 自動ロード（プロジェクトルート基準）
  - 必須環境変数取得、環境モード（development / paper_trading / live）やログレベル検証

---

## 動作環境（推奨）

- Python 3.10+
- 主要依存パッケージ:
  - duckdb
  - defusedxml

（その他は標準ライブラリで実装されています）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   # .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

2. 必要パッケージをインストールします（例）:

   ```bash
   pip install duckdb defusedxml
   # 開発時はパッケージをローカルインストールして利用する場合:
   pip install -e .
   ```

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

3. 環境変数を設定します。
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化可）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - DUCKDB_PATH: データベースファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

   例 `.env`:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易ガイド）

以下は Python インタプリタやスクリプトから各機能を使うサンプルです。

1. DuckDB スキーマの初期化

   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作成
   ```

2. 日次 ETL（株価 / 財務 / カレンダー の差分取得 + 品質チェック）

   ```python
   from kabusys.data import pipeline
   from kabusys.data import schema
   from kabusys.config import settings
   from datetime import date

   conn = schema.init_schema(settings.duckdb_path)
   result = pipeline.run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

   - run_daily_etl はカレンダー更新 → 株価 ETL → 財務 ETL → 品質チェックの順に実行し、ETLResult を返します。

3. ニュース収集ジョブ（RSS）

   ```python
   from kabusys.data import news_collector
   from kabusys.data import schema

   conn = schema.init_schema("data/kabusys.duckdb")

   # 既知の銘柄コードセット（抽出に使用）
   known_codes = {"7203", "6758", "9984"}

   results = news_collector.run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: saved_count, ...}
   ```

   - fetch_rss は RSS の安全な取得（リダイレクト検査、gzip 上限、XML の安全パース）を行います。
   - save_raw_news は ON CONFLICT DO NOTHING と INSERT ... RETURNING を用いて新規記事の ID を返します。

4. 監査スキーマの初期化

   - 既存の DuckDB 接続に監査テーブルを追加する:

     ```python
     from kabusys.data import audit
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)
     audit.init_audit_schema(conn, transactional=True)
     ```

   - 監査専用 DB を新たに作る場合:

     ```python
     conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

5. 設定管理に関して

   - settings は src/kabusys/config.py で提供されます。必須のキーが未設定の場合は ValueError が発生します。
   - 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時などに便利です）。

---

## 実装上の注意点 / セキュリティ設計

- J-Quants クライアント
  - 120 req/min のレート制限を固定間隔スロットリングで守ります。
  - リトライは指数バックオフ、最大 3 回。408/429/5xx をリトライ対象。
  - 401 受信時はリフレッシュトークンを使って自動で id_token を再取得し、1 回だけ再試行します。
  - 取得したデータの fetched_at を UTC で記録し、look-ahead bias を防止します。

- NewsCollector
  - defusedxml を使った安全な XML パース。
  - リダイレクト先のスキーム検査（http/https のみ許可）とホストがプライベート IP でないか検査（SSRF 防止）。
  - 受信バイト数上限（デフォルト 10 MB）を設け、Gzip 解凍後も上限チェックを実施（Gzip bomb 対策）。
  - URL 正規化によるトラッキングパラメータ除去と SHA-256 ベースの記事 ID 設計で冪等性を確保。

- DuckDB スキーマ
  - 原則すべての INSERT が冪等または重複回避されるように設計されています（ON CONFLICT DO UPDATE / DO NOTHING）。
  - 監査用スキーマは UTC タイムゾーンで運用することを前提に初期化されます。

---

## ディレクトリ構成

以下はコードベースの主要ファイルとディレクトリ構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/                # 発注・実行関連（現状空のパッケージ）
      - __init__.py
    - strategy/                 # 戦略関連（現状空のパッケージ）
      - __init__.py
    - monitoring/               # 監視関連（現状空のパッケージ）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント・保存処理
      - news_collector.py       # RSS ニュース収集・DB 保存ロジック
      - pipeline.py             # ETL パイプライン（差分取得・品質チェック）
      - schema.py               # DuckDB スキーマ定義・初期化
      - calendar_management.py  # 市場カレンダー管理（営業日判定など）
      - audit.py                # 監査ログ用スキーマ
      - quality.py              # データ品質チェック

---

## 開発時のヒント

- types の書き方（`Path | None`、`dict[str, Any]` 等）は Python 3.10 以上を想定しています。
- テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env 自動読み込みを無効化できます。
- news_collector._urlopen など一部関数はテストでモックしやすいように分離されています。
- DuckDB はインメモリ（":memory:"）接続もサポートしています。テストではこのモードを使うと便利です。

---

もし README に含めたい実行スクリプト（CLI）や docker-compose、CI 設定のサンプルが必要であれば、提供できます。どの操作を優先してドキュメント化しましょうか？