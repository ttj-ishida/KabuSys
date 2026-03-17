# KabuSys

日本株向けの自動売買データ基盤およびETL/収集ライブラリです。  
J-Quants API から市場データ（株価・財務・マーケットカレンダー）や RSS ニュースを収集し、DuckDB に整形して保存します。品質チェック・監査ログ・カレンダー管理など、量産運用を想定した設計を備えています。

- Python パッケージ名: kabusys
- バージョン: 0.1.0

---

## 機能一覧

- J-Quants API クライアント（認証 / レート制御 / ページネーション / リトライ）
  - 株価日足（OHLCV）取得・保存
  - 財務データ（四半期 BS/PL）取得・保存
  - JPX マーケットカレンダー取得・保存
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層を含むテーブル定義
  - インデックス定義、冪等な初期化（CREATE TABLE IF NOT EXISTS 等）
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得 / バックフィル）
  - 日次 ETL の統合実行（calendar → prices → financials → 品質チェック）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）
  - RSS フィード取得、XML の安全パース（defusedxml）
  - URL 正規化、トラッキングパラメータ除去、記事ID（SHA-256先頭32文字）
  - SSRF 対策（スキームチェック、プライベートアドレス拒否、リダイレクト検査）
  - DuckDB への冪等保存（INSERT ... ON CONFLICT / RETURNING）
  - 記事と銘柄コードの紐付け
- マーケットカレンダー管理
  - 営業日判定 / 前後営業日取得 / 期間の営業日リスト取得
  - カレンダーの夜間差分更新ジョブ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル
  - 発注フローのトレース（UUID を利用した冪等性と追跡）
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数経由の必須設定取得、検証（KABUSYS_ENV, LOG_LEVEL 等）

---

## 動作環境・依存

- Python 3.10 以上（型ヒントに | タイプを使用しているため）
- 主な Python パッケージ
  - duckdb
  - defusedxml

（プロジェクトでは urllib / json / logging 等の標準ライブラリを多用しています。必要に応じて slack や kabu API のクライアントを追加してください。）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストールします（例）:

   ```bash
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください。）

3. 環境変数を設定します。プロジェクトルート（.git または pyproject.toml がある親階層）に `.env` として配置すると自動で読み込まれます。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨の .env（例）:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（省略時: data/kabusys.duckdb）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境設定
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマを初期化します（例: Python REPL またはスクリプトで）:

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   監査ログ用スキーマを追加する場合:

   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   # または audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な例）

以下は主要な操作のサンプルです。

- J-Quants の ID トークン取得（自動リフレッシュを行うヘルパあり）:

  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を参照してトークン取得
  ```

- 日次 ETL 実行（株価・財務・カレンダ・品質チェック）:

  ```python
  from datetime import date
  from kabusys.data import pipeline, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダーの夜間バッチ更新ジョブ:

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved:", saved)
  ```

- RSS ニュース収集と記事の DB への保存（既知銘柄セットで紐付けまで）:

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- DuckDB 接続の取得（既存 DB）:

  ```python
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  ```

- 品質チェックのみ実行:

  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（必要に応じて）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

注意: .env.local は OS 環境変数より優先して上書きされます（ただし OS 環境変数は保護されます）。自動ロードはプロジェクトルート（.git または pyproject.toml）を基に行われます。

---

## ディレクトリ構成

主要なファイル配置（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得・保存）
      - news_collector.py            — RSS ニュース収集・保存
      - schema.py                    — DuckDB スキーマ定義・初期化
      - pipeline.py                  — ETL パイプライン（差分更新・日次ETL）
      - calendar_management.py       — カレンダー判定・更新ジョブ
      - audit.py                     — 監査ログ（signal/order/execution）
      - quality.py                   — データ品質チェック
    - strategy/                       — 戦略関連（未実装のエントリ）
      - __init__.py
    - execution/                      — 発注/ブローカー連携（未実装のエントリ）
      - __init__.py
    - monitoring/                     — 監視・メトリクス（未実装のエントリ）

README や設計資料（DataPlatform.md 等）がプロジェクトにある場合は、それらを参照してください。

---

## 運用上の注意・設計方針（抜粋）

- API レート制限を守るため固定間隔スロットリングを採用（J-Quants: 120 req/min）。
- リトライは指数バックオフ（指定ステータス：408/429/5xx、最大 3 回）。401 ならトークン自動リフレッシュを試行。
- DuckDB への書き込みは冪等性を考慮（ON CONFLICT DO UPDATE / DO NOTHING）。
- RSS 収集は SSRF や XML Bomb を防ぐ対策を実装。
- カレンダーが未取得のときは曜日ベースのフォールバック（主に土日判定）を行い、DB データがある場合は DB を優先。
- 品質チェックは Fail-Fast にせず、可能な限り問題を収集して呼び出し側で判断可能にする。

---

## 開発・拡張

- strategy/ や execution/ モジュールは拡張ポイントです。戦略ロジック・発注ロジックを実装して、signal_queue や audit との橋渡しを行ってください。
- テストでは環境変数自動読み込みを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用できます。
- news_collector._urlopen 等のネットワーク呼び出しはテストでモックしやすいよう設計されています。

---

必要な追加情報（運用スケジュール・スクリプト化・外部サービス連携など）があれば教えてください。README に追記して整理します。