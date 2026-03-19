# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
DuckDB をデータ層に用い、J-Quants API からのデータ取得、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下レイヤーを想定したモジュール群を提供します。

- Data Platform（取得 → 生データ → 整形 → 特徴量）
  - J-Quants API クライアント（株価・財務・市場カレンダー）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - DuckDB スキーマ定義 / 初期化ユーティリティ
  - ニュース収集（RSS）と銘柄抽出
  - マーケットカレンダー管理
- Research（ファクター計算・探索、IC/forward returns）
- Strategy（特徴量正規化、シグナル生成）
- Execution / Audit（発注・約定・ポジション・監査テーブル定義） — スキーマとインタフェースを提供
- 設定管理（環境変数読み込み、検証）

設計の要点:
- ルックアヘッドバイアス対策（計算は target_date 時点のデータのみを利用）
- 冪等性（DB-upsert / ON CONFLICT を基本）
- 外部依存を最小化（主要な統計処理は標準ライブラリ実装）
- API 呼び出しはレート制御・リトライ・トークンリフレッシュ付き

---

## 主な機能一覧

- 環境変数ベースの設定管理（kabusys.config.Settings）
- J-Quants API クライアント（rate limiter、リトライ、トークンリフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- DuckDB スキーマ定義 & 初期化（data.schema.init_schema）
- ETL パイプライン（差分更新・バックフィル）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース収集（RSS → raw_news 保存、銘柄抽出）
  - fetch_rss / save_raw_news / run_news_collection
- マーケットカレンダー管理（営業日判定・next/prev/get_trading_days、calendar_update_job）
- ファクター計算（research.factor_research）
  - calc_momentum, calc_volatility, calc_value
- 特徴量生成（strategy.feature_engineering.build_features）
  - Zスコア正規化、ユニバースフィルタ、features テーブルへのアップサート
- シグナル生成（strategy.signal_generator.generate_signals）
  - final_score 計算、BUY/SELL 判定、signals テーブルへの保存
- 汎用統計ユーティリティ（data.stats.zscore_normalize）
- 監査ログスキーマ（signal_events / order_requests / executions 等）

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントに union 型表記等を用いているため、少なくとも 3.9 以上を推奨）
- DuckDB を利用可能な環境

1. リポジトリをチェックアウトしてパッケージをインストール（開発モード推奨）
   - pip で依存をインストール（依存はプロジェクトに合わせて調整してください）
     - 必須パッケージ（一例）:
       - duckdb
       - defusedxml
   - 例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb defusedxml
     pip install -e .
     ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください）

2. 環境変数（必須）
   - J-Quants / kabu ステーション / Slack 等に必要な環境変数を設定します。主なもの:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID — 報告先 Slack チャンネル ID（必須）
     - DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 動作環境 ("development" / "paper_trading" / "live")（デフォルト: development）
     - LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みはデフォルト ON）。
     - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   例 .env（最低限の例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データベース初期化
   - DuckDB スキーマを作成します:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")  # ":memory:" も指定可能
     ```

---

## 使い方（クイックスタート例）

以下は Python スクリプトまたは REPL から呼び出す基本例です。

1. DuckDB の初期化（1回だけ）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（J-Quants から差分取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を指定しないと今日を基準に処理
   print(result.to_dict())
   ```

3. 特徴量を作成（research の生ファクター → features テーブルへ）
   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, date(2025, 3, 1))
   print(f"features built: {n}")
   ```

4. シグナルを生成（features と ai_scores を統合して signals テーブルへ）
   ```python
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, date(2025, 3, 1))
   print(f"signals written: {total}")
   ```

5. ニュース収集の実行（RSS 取得 → raw_news 保存 → 銘柄紐付け）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # known_codes は銘柄抽出に使う有効コード集合（例: all codes from prices_daily）
   results = run_news_collection(conn, known_codes=set(["7203", "6758"]))
   print(results)
   ```

6. マーケットカレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

注意:
- これらの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。アプリケーション側で接続を管理してください。
- J-Quants の API 呼び出しにはレート制限や認証があるため、実行時には環境変数の設定や API 利用条件に注意してください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 に設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成（抜粋）

リポジトリの主要モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得＋保存）
    - news_collector.py       — RSS 収集・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義 & init_schema
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — 市場カレンダー管理 / calendar_update_job
    - audit.py                — 監査ログスキーマ
    - features.py             — zscore_normalize の再エクスポート
    - stats.py                — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum, calc_volatility, calc_value
    - feature_exploration.py  — forward returns, IC, factor_summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py  — build_features
    - signal_generator.py     — generate_signals
  - execution/                — 発注・執行層（パッケージ骨格）
  - monitoring/               — 監視・通知関連（パッケージ骨格）

ファイルの場所や内容は実装に従います。上記は主要 API と処理のエントリポイントを示しています。

---

## 開発者向けメモ

- DuckDB の SQL を実行する際は型や NULL の扱いに注意してください（モジュール内で多くの CASE / COUNT チェックを実施しています）。
- J-Quants API 呼び出しはページネーション対応、rate limiting、リトライ、トークンリフレッシュを組み込んであります。テスト時は _request 関数や _urlopen をモックすることを推奨します。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト時に影響を与える場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化してください。
- 大量データの挿入はチャンク分割やトランザクションで実装されています（news_collector や jquants_client.save_* など）。

---

## サポート / 貢献

バグ報告や機能追加の提案は Issue を立ててください。プルリクエストは歓迎します。コントリビューション時はコード整形、型ヒント、ユニットテストを付けていただけると助かります。

---

以上。必要であれば「サンプル .env の完全版」や「よく使う CLI スクリプト例」などの追記を作成します。どの部分を詳しく書いてほしいか教えてください。