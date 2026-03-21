# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、特徴量作成、戦略シグナル生成、ニュース収集、監査／スキーマ管理などを含むモジュール化された実装を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネント群を提供します。

- J-Quants API からの市場データ・財務データ・マーケットカレンダー取得（レート制御・リトライ・トークンリフレッシュ対応）
- DuckDB を使ったローカルデータベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL（差分取得・保存・品質チェックを含む）による日次データ更新パイプライン
- research 層によるファクター計算（Momentum / Volatility / Value 等）および解析ユーティリティ（IC, forward returns, summary）
- strategy 層での特徴量整形（正規化・ユニバースフィルタ）とシグナル生成（BUY/SELL 判定）
- ニュース収集（RSS）と銘柄抽出・DB 保存
- 監査ログ（発注→約定のトレーサビリティ）を保持するためのスキーマ・ユーティリティ

設計方針としては、ルックアヘッドバイアス回避、冪等性（ON CONFLICT 等）、テスト容易性（引数注入・トークン注入）、外部依存の最小化（標準ライブラリ優先）を重視しています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（レート制御・リトライ、トークン自動リフレッシュ）
  - 日足・財務・カレンダーのフェッチと DuckDB への冪等保存
- data/schema
  - DuckDB 用のテーブル定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema() による初期化
- data/pipeline
  - 差分更新を自動算出する ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェックとの統合
- data/news_collector
  - RSS 取得、前処理、raw_news への冪等保存、記事 ↔ 銘柄紐付け
  - SSRF対策、受信サイズ制限、ID 冪等化
- data/calendar_management
  - market_calendar を利用した営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - カレンダー更新バッチ（calendar_update_job）
- data/stats
  - zscore_normalize（クロスセクションの Z スコア正規化）
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 研究向けユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）
- strategy
  - build_features（生ファクターの正規化・ユニバース適用→features テーブルへ保存）
  - generate_signals（features + ai_scores を統合し BUY/SELL シグナルを作成→signals 保存）
- audit
  - 発注・約定フローの監査テーブル定義（signal_events / order_requests / executions など）

---

## セットアップ手順

前提: Python 3.9+（型ヒントに | が使われているため 3.10 以降が適切なケースもあります）。DuckDB を利用します。

1. リポジトリをチェックアウトしてパッケージをインストール（開発環境）:
   - pip install -e . など（setup/pyproject がある前提）
   - 依存ライブラリ（最低限）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

2. 環境変数 / .env
   - KabuSys は起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID — Slack 通知先 Channel ID
   - 任意（例とデフォルト）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG / INFO / ...（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env 読み込みを無効化
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
   - .env の書式: KEY=VALUE。export プレフィックスやクォート、コメントをある程度サポートします。

3. データベース初期化
   - DuckDB ファイルを作成・スキーマを初期化します（親ディレクトリがなければ自動作成）。
   - 例:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（代表的な例）

以下は Python から直接呼び出す簡単な例です。実運用では CLI やワーカーから呼ぶことを想定します。

1. DuckDB の初期化
   - from kabusys.data.schema import init_schema
   - conn = init_schema("data/kabusys.duckdb")

2. 日次 ETL 実行（J-Quants からの差分取得・保存・品質チェック）
   - from kabusys.data.pipeline import run_daily_etl
   - result = run_daily_etl(conn)  # target_date を指定可能

3. 特徴量作成（strategy 層）:
   - from kabusys.strategy import build_features
   - from datetime import date
   - count = build_features(conn, date(2025, 1, 1))  # 例: ある日付の features を作成

4. シグナル生成:
   - from kabusys.strategy import generate_signals
   - total = generate_signals(conn, date(2025, 1, 1))  # BUY/SELL を signals テーブルへ保存

5. ニュース収集ジョブ:
   - from kabusys.data.news_collector import run_news_collection
   - known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット（抽出に使用）
   - stats = run_news_collection(conn, known_codes=known_codes)

6. カレンダー更新バッチ:
   - from kabusys.data.calendar_management import calendar_update_job
   - saved = calendar_update_job(conn)

7. J-Quants の生データフェッチ（個別利用）:
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   - recs = fetch_daily_quotes(date_from=..., date_to=...)
   - save_daily_quotes(conn, recs)

注意:
- ほとんどの公開 API は冪等（同日分を置き換える等）を前提に設計されています。
- run_daily_etl 等は内部でトランザクションとエラーハンドリングを行い、部分的な失敗があっても他の処理を継続します。戻り値（ETLResult）で問題点を確認してください。

---

## 重要な環境変数

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API のリフレッシュトークン。get_id_token() により idToken を取得します。
- KABU_API_PASSWORD (必須): kabu ステーション API に接続するためのパスワード。
- SLACK_BOT_TOKEN (必須): Slack 通知用の Bot Token。
- SLACK_CHANNEL_ID (必須): Slack の通知先チャネル ID。
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）。
- SQLITE_PATH (任意): 監視用途の SQLite パス（デフォルト: data/monitoring.db）。
- KABUSYS_ENV (任意): 環境識別（development / paper_trading / live）。
- LOG_LEVEL (任意): ログレベル（DEBUG 等）。

プロジェクト起動時は `.env` / `.env.local` を用意しておくと運用が楽です。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys 以下）の主なファイルと概要です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定（自動 .env ロード・必須チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save 系）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize
    - features.py
      - zscore_normalize の再エクスポート
    - calendar_management.py
      - market_calendar 管理・営業日ユーティリティ・calendar_update_job
    - audit.py
      - 監査ログ用 DDL（signal_events / order_requests / executions 等）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - strategy/
    - __init__.py
      - build_features, generate_signals をエクスポート
    - feature_engineering.py
      - ファクター正規化・ユニバースフィルタ・features テーブルへの UPSERT
    - signal_generator.py
      - final_score 計算、BUY/SELL 判定、signals への保存
  - execution/
    - __init__.py
      - （発注層のためのプレースホルダ）
  - その他
    - monitoring（__all__ に含まれるが本コードベースでは実体ファイルは省略されている可能性があります）

---

## 開発 / テスト時のヒント

- 自動 .env ロードを無効化したいとき:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（主にユニットテストで .env の影響を避けたいとき）。
- DuckDB はメモリ DB（":memory:"）で init_schema() を呼べます。テスト時の使い捨て DB に便利です。
- 外部ネットワーク呼び出し（J-Quants / RSS）をモックすることで単体テストを容易にできます。jquants_client の _request 部分や news_collector._urlopen を差し替えられるよう設計されています。
- ログレベルを DEBUG にして各処理の詳細なログを確認できます（LOG_LEVEL 環境変数）。

---

## 注意事項 / 制約

- 本リポジトリのコードは取引ロジックおよび外部 API への接続を含むため、本番口座で動かす前に十分なテストと監査を行ってください。
- 戦略・発注ロジックには stop/trailing 等の完全実装が一部未実装（コメントで意図が記載されている箇所あり）です。特に execution 層との結合は慎重に行ってください。
- DuckDB の外部キーや ON DELETE 挙動はバージョン依存の差分をコメントで扱っているので、使用している DuckDB バージョンの挙動を確認してください。

---

もし README に追記したい具体的な使用例（cron / Airflow / systemd の設定例、Slack 通知のフロー、CI 設定、サンプル .env.example など）があれば、それに合わせて内容を拡張します。