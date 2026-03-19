# KabuSys

日本株向けの自動売買システム用ライブラリ群。市場データの収集・ETL、特徴量生成、戦略シグナル生成、ニュース収集、カレンダー管理、監査ログなどを DuckDB を中心に実装しています。

主に研究（Research）→ データ基盤（Data）→ 戦略（Strategy）→ 実行（Execution）までのワークフローをサポートするモジュール群を提供します。

---

## 主要機能（サマリ）

- データ取得
  - J-Quants API クライアント（株価・財務・市場カレンダー取得、ページネーション/リトライ/レート制御/トークン自動更新）
  - RSS ベースのニュース収集（SSRF 対策、XML セキュリティ、トラッキングパラメータ除去）
- データ基盤
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - ETL パイプライン（差分取得、バックフィル、品質チェック統合）
  - カレンダー管理（営業日判定、前後営業日取得、夜間カレンダー更新ジョブ）
- 研究用ユーティリティ
  - ファクター計算（モメンタム・ボラティリティ・バリューなど）
  - 将来リターン / IC（Spearman）計算、統計サマリ
  - Z スコア正規化ユーティリティ
- 戦略
  - 特徴量生成（research で計算した raw factor を正規化して features テーブルへ保存）
  - シグナル生成（features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals テーブルへ書き込み）
- ニュース処理
  - RSS フェッチ、記事前処理、記事保存（raw_news）、銘柄コード抽出と紐付け
- 監査・トレーサビリティ
  - シグナル→発注→約定を追跡する監査テーブル群

---

## 環境変数（主な設定項目）

設定は環境変数またはプロジェクトルートの `.env`, `.env.local` から自動読み込みされます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 環境: `development` / `paper_trading` / `live`（デフォルト: `development`）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: `INFO`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 で無効化）
- KABUSYS の DB パス:
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: `data/monitoring.db`）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: `http://localhost:18080/kabusapi`）

環境変数は `kabusys.config.settings` 経由で取得できます。

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.10 以上（typing の | 記法を利用しています）、DuckDB を利用します。

1. 仮想環境作成・有効化
   - Unix/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージのインストール（最低限）
   ```bash
   pip install duckdb defusedxml
   ```
   ※ 実際のプロジェクトでは追加の依存（例えば Slack SDK、テスト用ライブラリ など）があるかもしれません。requirements.txt があればそれに従ってください。

3. 環境変数設定
   - プロジェクトルートに `.env`（および `.env.local`）を作成して必須変数（JQUANTS_REFRESH_TOKEN 等）を設定します。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動読み込みが不要なテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. データベース初期化（DuckDB スキーマ作成）
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してスキーマを作る
     # or in-memory:
     # conn = init_schema(":memory:")
     ```

---

## 使い方（主要な利用例）

以下は代表的なワークフローの呼び出し例です。すべて DuckDB 接続オブジェクト（DuckDBPyConnection）を渡して利用します。

- 日次 ETL（市場カレンダー、株価、財務データ、品質チェック）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量ビルド（features テーブルへの書き込み）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  cnt = build_features(conn, target_date=date(2025, 3, 18))
  print(f"features 更新件数: {cnt}")
  ```

- シグナル生成（features と ai_scores を使って signals テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 3, 18))
  print(f"生成されたシグナル合計: {total}")
  ```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 有効な銘柄コードのセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: new_saved_count, ...}
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"カレンダー更新で保存された件数: {saved}")
  ```

- J-Quants からデータを取得して直接保存（低レベル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  recs = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,3,18))
  saved = save_daily_quotes(conn, recs)
  ```

---

## 開発者向けメモ / 設計上のポイント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行います。テスト実行時などで自動読み込みを抑制する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使ってください。
- J-Quants クライアントはレート制御（120 req/min）・リトライ・トークン自動更新等を備えています。HTTP レスポンスのページネーションに対応しています。
- DuckDB のテーブルは ON CONFLICT / DO UPDATE を多用して冪等性を担保しています。
- 研究モジュール・戦略モジュールはルックアヘッドバイアス回避の観点から、常に target_date 時点までのデータのみを参照する設計です。
- ニュース収集では SSRF 対策・XML インジェクション対策（defusedxml）・レスポンスサイズ制限等の安全対策を実装済みです。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント
    - news_collector.py — RSS ニュース収集・保存
    - schema.py — DuckDB スキーマ定義・初期化
    - stats.py — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - features.py — data.stats のエクスポートインターフェース
    - calendar_management.py — 市場カレンダー管理 / 更新ジョブ
    - audit.py — 監査ログ用テーブル定義
    - (その他: quality, audit utilities 等が想定される)
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — 特徴量集約・正規化・features テーブル書き込み
    - signal_generator.py — final_score 計算・BUY/SELL シグナル生成
  - execution/
    - __init__.py — 実行（発注）層の雛形（将来的に broker 接続等）
  - monitoring/ — 監視・アラート系モジュール（存在が示唆される）

（上記はコードベースに含まれる主なファイルの抜粋です。実際のリポジトリでは README 以外のドキュメントやテスト、CI 設定などが追加されている可能性があります。）

---

## ライセンス・貢献

- この README はコードの構造と役割に基づいた概要ドキュメントです。実際のライセンス表記やコントリビュートガイドがリポジトリに含まれている場合はそちらに従ってください。

---

もし README に追加したい実行スクリプト（例: cron 用の runner、systemd ユニット、Dockerfile、requirements.txt の正確な内容など）があれば、その情報を提供してください。セットアップ手順や使用例をより具体的に追記します。