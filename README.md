# KabuSys

日本株向け自動売買 / データ基盤ライブラリ（KabuSys）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびそのためのデータ基盤を提供する Python パッケージです。  
主に以下を目的としたモジュール群を含みます。

- J-Quants API からの市場データ取得（株価日足・四半期財務・JPX カレンダー）
- DuckDB ベースのデータスキーマ定義・初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と記事→銘柄紐付け
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 市場カレンダー管理、モニタリング、戦略／実行プレースホルダ

設計上のポイント:
- API レート制御、リトライ、トークン自動リフレッシュを備えた堅牢なクライアント
- DuckDB による冪等な保存（ON CONFLICT ... DO UPDATE / DO NOTHING）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- SSRF や XML Bomb 等を考慮した安全な RSS パーサ

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）取得・ページネーション対応
  - 四半期財務データ取得
  - JPX マーケットカレンダー取得
  - 自動トークンリフレッシュ（401 時にリフレッシュし 1 回リトライ）
  - レート制御（120 req/min）と指数バックオフリトライ
- DuckDB スキーマ（raw / processed / feature / execution 層）と初期化 API
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- ニュース収集（RSS）：
  - URL 正規化、トラッキングパラメータ削除、ID（SHA-256 の先頭 32 文字）
  - SSRF 対策、gzip サイズチェック、XML 安全パーサ
  - raw_news への冪等保存、news_symbols への銘柄紐付け
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- マーケットカレンダー管理（営業日判定、前後営業日取得、夜間アップデートジョブ）
- 監査ログ / トレーサビリティ（signal_events / order_requests / executions 等）

---

## 要件

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
  - defusedxml
  - （その他標準ライブラリに依存）

実際のパッケージ化・install 要件は pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）:

   ```bash
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .
   ```

2. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を読み込みます（自動ロード機能あり）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
   - 任意・デフォルト:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

   `.env.example` を参考に `.env` を作成してください。

   自動 env 読み込みを無効化する場合:

   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（簡単な例）

以降の例は Python インタプリタやスクリプト内で実行します。

1. DuckDB スキーマ初期化

   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

2. 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # デフォルトは本日を対象
   print(result.to_dict())
   ```

   run_daily_etl は ETLResult を返します。エラーや品質問題は result.errors / result.quality_issues に格納されます。

3. ニュース収集ジョブ

   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.news_collector import run_news_collection

   conn = init_schema("data/kabusys.duckdb")
   # sources を省略するとデフォルトの RSS ソース群を使用
   # known_codes は銘柄抽出用に有効な銘柄コード集合を渡す（例: {"7203","6758",...}）
   stats = run_news_collection(conn, sources=None, known_codes=None)
   print(stats)  # {source_name: saved_count, ...}
   ```

4. カレンダー更新ジョブ（夜間バッチ想定）

   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.calendar_management import calendar_update_job

   conn = init_schema("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print("saved:", saved)
   ```

5. 監査ログスキーマ初期化（監査専用 DB を別に作る場合）

   ```python
   from kabusys.data.audit import init_audit_db

   conn_audit = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動読み込みを無効化

---

## 開発・テスト時のヒント

- テスト・CI で .env の自動読み込みが邪魔な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector._urlopen や jquants_client のネットワーク呼び出しはモック可能な設計になっています（テスト容易性を考慮）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（自動 .env 読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（レート制御、リトライ、token refresh）
    - news_collector.py — RSS 取得・前処理・DB 保存（SSRF 対策、size 制限）
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py — ETL パイプライン（差分更新・backfill・品質チェック）
    - calendar_management.py — 市場カレンダー管理（営業日判定など）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - audit.py — 監査ログ用スキーマ（signal / order / execution）
  - strategy/
    - __init__.py (戦略関連プレースホルダ)
  - execution/
    - __init__.py (発注・実行関連プレースホルダ)
  - monitoring/
    - __init__.py (監視関連プレースホルダ)

---

## 設計ノート（要点）

- J-Quants クライアントは 120 req/min のレート制限を固定間隔で守る実装です（RateLimiter）。
- HTTP エラー（408/429/5xx）は指数バックオフで最大 3 回リトライ。429 の場合は Retry-After を優先。
- 401 を受けた場合はリフレッシュトークンで id_token を再取得して 1 回リトライします（無限再帰を避ける設計）。
- DuckDB への保存は主に冪等（ON CONFLICT DO UPDATE / DO NOTHING）。
- ニュース収集では URL 正規化→SHA-256 ハッシュ（先頭 32 文字）を記事 ID として使用し冪等性を担保。
- RSS 収集は SSRF（リダイレクト含む）や XML に対する堅牢な対策を実装。

---

この README はコードベースの主要部分を元に作成しています。より詳細な仕様・設計ドキュメント（DataPlatform.md 等）がある場合は併せて参照してください。質問や追加の使い方サンプルが必要であれば知らせてください。