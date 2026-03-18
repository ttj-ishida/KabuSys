# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants や kabuステーション、RSS 等からデータを収集・保存し、ETL、品質チェック、監査ログ、ニュース収集などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダーの取得と DuckDB への冪等保存
- RSS フィードからのニュース収集と銘柄紐付け
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、次/前営業日取得）
- 監査ログ（シグナル→発注→約定 のトレーサビリティ）用スキーマ初期化
- 設定値・環境変数の管理（自動 .env ロードをサポート）

設計上の特徴：
- API レート制御・リトライ・トークン自動リフレッシュ（J-Quants クライアント）
- Look-ahead bias 防止のため取得時刻 (fetched_at) を UTC で記録
- DuckDB に対して冪等的な INSERT/ON CONFLICT ロジックを使用
- ニュース収集モジュールは SSRF / XML Bomb 等を考慮した安全設計

---

## 主な機能一覧

- 環境設定管理: kabusys.config.Settings（.env の自動読み込み、必須項目チェック）
- J-Quants クライアント: デイリープライス、財務、マーケットカレンダー取得、トークン取得（自動リフレッシュ）  
  - レート制限 (120 req/min)、指数バックオフ、401 時のトークンリフレッシュ対応
- DuckDB スキーマ管理: data.schema.init_schema / get_connection
- ETL パイプライン: data.pipeline.run_daily_etl（差分取得・バックフィル・品質チェック）
- データ品質チェック: data.quality（欠損、スパイク、重複、日付不整合の検出）
- ニュース収集: data.news_collector.fetch_rss / save_raw_news / run_news_collection  
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip サイズ制限
- マーケットカレンダー管理: data.calendar_management（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
- 監査ログ（Audit）: data.audit.init_audit_schema / init_audit_db（監査テーブルの初期化）

---

## 前提・依存関係

最低限必要な外部パッケージ（例）:
- duckdb
- defusedxml

（実プロジェクトでは requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをチェックアウトし仮想環境を作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # その他の依存があれば requirements.txt を用意してインストール
   ```

2. 環境変数を設定
   ルートに `.env`（および任意で `.env.local`）を作成すると、自動的に読み込まれます。
   自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   期待される主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
   - LOG_LEVEL: ログレベル (DEBUG | INFO | ...)

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマを初期化
   例（Python スクリプトまたは対話環境）:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

4. 監査ログ用テーブルを追加する場合:
   ```python
   from kabusys.data.audit import init_audit_schema
   # conn は init_schema で取得した DuckDB 接続
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要な例）

以下はモジュールを直接呼び出す簡単な例です。実際はアプリケーションやバッチスクリプトから呼び出してください。

- J-Quants で ID トークンを取得する:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を渡すと本文中から銘柄コード抽出して紐付けする
  known_codes = {"7203", "6758", "8035"}
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)
  ```

- DuckDB に生データを保存する（jquants_client の保存関数使用例）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=..., date_to=...)
  saved_count = save_daily_quotes(conn, records)
  ```

- マーケットカレンダー更新バッチ（夜間ジョブ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  ```

---

## 実装上の注意・設計メモ

- jquants_client:
  - レート制限: 120 req/min（内部で固定間隔スロットリング）
  - リトライ: 指数バックオフ（最大3回）、408/429/5xx を再試行
  - 401 受信時はリフレッシュトークンでトークンを自動更新して再試行（1回）
  - ページネーション対応（pagination_key）

- news_collector:
  - URL 正規化・トラッキングパラメータ除去・ID は URL の SHA-256（先頭32文字）
  - defusedxml を利用して XML 攻撃を防止
  - リダイレクト先のホストを検査し、プライベート/ループバックアドレスへのアクセスをブロック（SSRF 防止）
  - レスポンスサイズ上限（10MB）、gzip 展開後も上限再チェック

- ETL (data.pipeline):
  - 差分更新ロジック: DB の最終取得日から必要範囲のみ取得
  - backfill_days により数日前から再取得して API の後出し修正を吸収
  - 品質チェックは Fail-Fast ではなく、検出結果を返して呼び出し側で判断

- 環境変数自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を読み込む
  - OS 環境変数は保護され、.env.local による上書きが可能
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成（主要ファイル）

（リポジトリルートの `src/kabusys` 配下）

- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py           — J-Quants API クライアント（取得・保存）
  - news_collector.py          — RSS ニュース収集・保存・銘柄抽出
  - schema.py                  — DuckDB スキーマ定義 & 初期化
  - pipeline.py                — ETL パイプライン（差分取得・品質チェック）
  - calendar_management.py     — マーケットカレンダーの管理・ユーティリティ
  - audit.py                   — 監査ログ用テーブル定義・初期化
  - quality.py                 — データ品質チェック
- strategy/
  - __init__.py                — 戦略層（将来拡張ポイント）
- execution/
  - __init__.py                — 発注/約定/ポジション関連（将来拡張ポイント）
- monitoring/
  - __init__.py                — 監視・メトリクス（将来拡張ポイント）

---

## よくある質問 / トラブルシューティング

- .env がロードされない:
  - プロジェクトルートが .git / pyproject.toml で特定できない場合、自動ロードがスキップされます。
  - 自動ロードを無効化しているときは KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。

- DuckDB の初期化に失敗する:
  - 指定したパスの親ディレクトリが存在しない場合、schema.init_schema は自動作成しますが、権限やパス名に問題がないか確認してください。

- J-Quants API から 401 が返る:
  - refresh token が無効・期限切れの可能性があります。settings.jquants_refresh_token の値を確認してください。

---

## 今後の拡張案（メモ）

- strategy / execution モジュールに具体的な戦略・発注エンジン実装
- 運用用 CLI / サービス化（Systemd / Airflow / Cron 用のラッパー）
- モニタリング・アラート（Slack 通知など）の統合（monitoring パッケージ）
- テスト用のモッククライアント & CI の導入

---

以上がプロジェクトの基本的な README です。必要であれば、インストール用の requirements.txt、サンプル .env.example、実行用スクリプト（run_etl.py など）のテンプレートを追加で作成します。どれを優先しますか？