# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
J-Quants API からの市場データ取得、DuckDB を使ったデータレイク（スキーマ定義・初期化）、ETL パイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ用スキーマなど、取引システムの基盤機能を提供します。

主な設計方針:
- データ取得は冪等（INSERT ... ON CONFLICT）で保存
- API 呼び出しはレート制御・リトライ・トークン自動更新を実装
- SSRF / XML BOM / Gzip bomb 等への安全対策を実装
- DuckDB をデータストアとして想定し、スキーマは DataPlatform.md に準拠

---

## 機能一覧
- 環境変数/設定管理（kabusys.config）
  - .env/.env.local の自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須設定の取得と検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期BS/PL）、市場カレンダー取得
  - レートリミット（120 req/min）、再試行（指数バックオフ）、401 時のトークン自動リフレッシュ対応
  - DuckDB への保存関数（冪等）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・XML パース（defusedxml 使用）、記事正規化、トラッキングパラメータ除去
  - SSRF 対策、受信サイズ制限、記事ID の SHA-256 ベース生成、DuckDB へのバルク保存
  - テキスト中から銘柄コード抽出、news_symbols への紐付け
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（DuckDB）
  - インデックス定義
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック、backfill、カレンダー先読み
  - ETL の結果を ETLResult で返す
  - 品質チェック呼び出し連携
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日検索、カレンダー更新ジョブ
- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）
- 監査ログスキーマ（kabusys.data.audit）
  - シグナル→発注→約定のトレース用テーブル群の初期化（UUID による追跡）
- ほか、strategy / execution / monitoring 用のパッケージプレースホルダ

---

## セットアップ手順

前提
- Python 3.10 以上推奨（コードは型ヒントに Python 3.10 の union 型等を利用）
- pip / 仮想環境ツール（venv、poetry 等）

1. リポジトリをクローンして、開発環境を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. 必要パッケージをインストール
   - 最小必須: duckdb, defusedxml
   - 実運用では Slack SDK や kabu API ラッパー、J-Quants クライアント（本プロジェクトの get_id_token を使うため外部依存は不要）などを追加する可能性あり。

   例（requirements が無い場合の最小インストール）:
   ```
   pip install duckdb defusedxml
   ```

3. パッケージをインストール（編集可能に）
   ```
   pip install -e .
   ```

4. 環境変数を用意
   プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（既定: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（既定: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

   例（.env の一部）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

注: パッケージ内の config モジュールは実行時にプロジェクトルート（.git または pyproject.toml を検出）を基準として .env/.env.local を自動的に読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

---

## 使い方（主な操作例）

以下はライブラリ API を使った基本的な例です。実運用では各操作をジョブスケジューラ（cron、systemd timer、Airflow 等）やワーカーでラップしてください。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリが自動作成されます
   ```

2. 監査ログ用 DB 初期化（別 DB を使う場合）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

3. 日次 ETL 実行（市場カレンダー／株価／財務／品質チェック）
   ```python
   from datetime import date
   from kabusys.data.schema import get_connection
   from kabusys.data.pipeline import run_daily_etl

   conn = get_connection("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

   - run_daily_etl は ETLResult を返します。品質チェックの結果（QualityIssue のリスト）やエラーは ETLResult に含まれます。

4. ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # sources を省略すると組み込みの DEFAULT_RSS_SOURCES を使用
   results = run_news_collection(conn, known_codes={"7203", "6758"})
   print(results)  # {source_name: 新規保存件数, ...}
   ```

5. J-Quants から個別データ取得（テスト／直接取得）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
   # id_token を明示的に渡すことも、モジュールキャッシュを使うことも可能
   quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,2,1))
   ```

6. カレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print("saved:", saved)
   ```

7. 品質チェックを単独で実行
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=None)
   for i in issues:
       print(i)
   ```

注意点:
- jquants_client は内部でレート制御・リトライ・トークンキャッシュを行います。大量の同時リクエストを行う場合は注意してください。
- news_collector は RSS の取得時に SSRF や大きなレスポンスを検出して安全にスキップします。

---

## よく使う環境変数（一覧）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

---

## ディレクトリ構成

リポジトリの主なファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py           -- J-Quants API クライアント（取得・保存）
      - news_collector.py           -- RSS ニュース収集・保存ロジック
      - schema.py                   -- DuckDB スキーマ定義・初期化
      - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py      -- マーケットカレンダー管理
      - audit.py                    -- 監査ログ（audit）スキーマ初期化
      - quality.py                  -- データ品質チェック
    - strategy/
      - __init__.py                 -- 戦略関連パッケージ（拡張用）
    - execution/
      - __init__.py                 -- 発注/実行関連のパッケージ（拡張用）
    - monitoring/
      - __init__.py                 -- 監視関連のパッケージ（拡張用）

ドキュメント等（リポジトリルート）:
- .env.example (想定)              -- 必要な環境変数の例（存在するなら）
- pyproject.toml / setup.cfg 等    -- ビルド/パッケージ設定（存在する場合）

---

## 運用上の注意・ベストプラクティス
- secrets（API トークン等）は .env/.env.local に保存する場合でも適切に管理し、バージョン管理に含めないでください。
- 本ライブラリはデータ取得・ETL・監査ログなどを提供しますが、実際の「板寄せ・約定ロジック」や「資金管理・リスク管理」は strategy / execution 層で独自実装してください。
- ETL やニュース収集はジョブスケジューラで定期実行することを想定しています（ex. cron、Airflow、systemd timer）。
- 本コードは DuckDB を前提としています。複数プロセスから同一ファイルへ同時書き込みする運用には注意が必要です（ロック・接続戦略を検討してください）。

---

もし README に含めたい追加情報（例: requirements.txt、.env.example の具体例、cron サンプル、API 利用制限の詳細など）があれば教えてください。必要に応じて README を拡張します。