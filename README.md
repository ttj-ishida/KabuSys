# KabuSys — 日本株自動売買基盤

KabuSys は日本株のデータ収集・ETL・特徴量生成・リサーチ・監査ログを備えた自動売買基盤の骨格です。J-Quants API や RSS ニュースを取り込み、DuckDB を用いてデータを管理し、ファクター計算や品質チェック、監査テーブルを提供します。

## 概要（Project Overview）
- データ取得：J-Quants API 経由で株価日足・財務データ・マーケットカレンダーを取得し DuckDB に保存
- ニュース収集：RSS フィードから記事を収集し正規化して保存、銘柄コード抽出を行う
- ETL：差分取得・バックフィル・品質チェック（欠損／スパイク／重複／日付整合性）
- 研究（Research）：ファクター（モメンタム／バリュー／ボラティリティ等）の計算、将来リターン／IC 計算、統計サマリー
- 監査（Audit）：シグナル→発注→約定までを追跡する監査テーブル群
- スキーマ管理：DuckDB スキーマの初期化・接続ユーティリティ

## 主な機能（Features）
- 環境変数自動読み込み（プロジェクトルートの `.env` / `.env.local`、無効化フラグあり）
- J-Quants API クライアント（レート制御・リトライ・自動トークンリフレッシュ・ページネーション）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- DuckDB スキーマの冪等的初期化（Raw / Processed / Feature / Execution / Audit 層）
- RSS ニュース収集（SSRF 対策、gzip 上限、XML デコード安全化、記事ID 正規化）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ファクター計算（モメンタム・ボラティリティ・バリューなど）と Z スコア正規化
- 研究用ユーティリティ（将来リターン計算、IC 計算、統計サマリー）
- 監査ログ（signal_events / order_requests / executions など）とトレーサビリティ確保

## 必要な環境変数
以下はコードで参照される主な環境変数です（README 用に抜粋）。

必須（実行する機能により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意・デフォルトあり:
- KABUSYS_ENV — 実行環境。allowed: `development`, `paper_trading`, `live`（デフォルト `development`）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — `1` を設定すると `.env` 自動読み込みを無効化

.env の読み込み順序:
- OS 環境変数 > .env.local > .env
- 自動ロードはプロジェクトルート（.git または pyproject.toml がある位置）を基準に行う

## セットアップ手順（Setup）
例: 仮想環境を使ったセットアップ

1. Python 環境（推奨: 3.9+）を用意し、仮想環境を作成・有効化します。
   - Linux / macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール（本リポジトリのセットアップファイルが無い場合、最低限の依存を示します）
   ```
   pip install duckdb defusedxml
   ```
   ※ 実運用では HTTP クライアントや Slack 用クライアント等も必要になる可能性があります。

3. 環境変数を設定するか `.env` を作成します（例: `.env`）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマを初期化します（後述の「使い方」を参照）

## 使い方（Usage）

以下は主要な機能の利用例です。Python スクリプトや REPL から実行できます。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL を実行（J-Quants から差分取得 → 保存 → 品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 引数で target_date や id_token を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブを回す
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes を渡すと記事と銘柄の紐付け処理が行われる
  known_codes = {"7203", "6758", "9984"}  # など
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  momentum = calc_momentum(conn, target_date=date(2024, 1, 31))
  # momentum は各銘柄に対する dict のリスト
  ```

- 将来リターン / IC 計算（研究用）
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  # forward_records = calc_forward_returns(conn, date(2024,1,31))
  # calc_ic は factor_records と forward_records を結合してスピアマンρを返す
  ```

- 監査スキーマ初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

注意:
- 研究モジュールは prices_daily / raw_financials のみにアクセスし、本番発注 API 等にはアクセスしません。
- J-Quants API 呼び出しにはレート制限・リトライ・トークン更新が実装されていますが、実行時には API 利用料や制約に注意してください。
- KABUSYS_ENV が `live` の場合は実際の発注や運用に関わる処理が有効になる想定のため、環境値の設定に注意してください。

## ディレクトリ構成（Directory Structure）
以下は本コードベースの主要ファイル・モジュールの一覧と概要（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings オブジェクト（アプリ設定）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py
      - RSS 収集・記事前処理・保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL パイプライン（run_daily_etl、run_prices_etl 等）
    - quality.py
      - データ品質チェック（欠損/スパイク/重複/日付整合性）
    - calendar_management.py
      - 市場カレンダー管理（営業日判定、更新ジョブ）
    - etl.py
      - ETL 用の公開インターフェース（ETLResult エクスポート）
    - features.py
      - 特徴量関連の公開インターフェース
    - audit.py
      - 監査ログ用テーブルの定義と初期化
  - research/
    - __init__.py
      - 研究用ユーティリティの公開
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー等
    - factor_research.py
      - momentum / volatility / value のファクター計算
  - strategy/
    - __init__.py
    - （戦略モデルやシグナル生成ロジックを格納する場所）
  - execution/
    - __init__.py
    - （注文発行・ブローカ連携・ポジション管理関連）
  - monitoring/
    - __init__.py
    - （監視・メトリクス収集/通知など）

## 補足・設計上のポイント
- DuckDB を中核に据え、Raw → Processed → Feature → Execution / Audit の層でデータを管理します。
- ETL は差分更新・バックフィルを考慮しており、品質チェックは Fail-Fast ではなく検出ログを返す設計です（呼び出し元が判断）。
- ニュース収集は SSRF や XML Bomb 等の安全対策を組み込んでいます（defusedxml、URL 検証、受信サイズ上限など）。
- J-Quants クライアントはレート制御・リトライ・トークンリフレッシュを実装しており、ページネーションと取得タイムスタンプ（fetched_at）を保持します。
- 環境変数の自動読み込みは便利ですが、テスト時などに KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して無効化できます。

---

もし README に追加したいこと（例: CI / テスト方法、具体的な依存パッケージ一覧、例データの初期ロード手順、運用上の注意点など）があれば教えてください。必要に応じてサンプルスクリプトや docker-compose の雛形も作成できます。