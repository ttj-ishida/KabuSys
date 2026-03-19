KabuSys
======

日本株向けの自動売買・データプラットフォーム用 Python パッケージの README（日本語）です。本プロジェクトはデータ収集（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査（トレーサビリティ）までをカバーするモジュール群を提供します。

要点
----
- 言語: Python
- DB: DuckDB をデータレイヤとして採用
- 目的: J‑Quants 等からの市場データ取得 → ETL → 特徴量生成 → シグナル生成 → 実行/監視（モジュール化）
- 設計方針: 冪等性、ルックアヘッドバイアス防止、API レート制御、堅牢なエラーハンドリング

機能一覧
--------
主な機能（コード内モジュールに対応）:

- 環境設定
  - 自動 .env ロード（プロジェクトルートにある .env / .env.local を優先して読み込み）
  - 必須環境変数の検証（settings オブジェクト）

- データ取得 / 保存（kabusys.data.jquants_client）
  - J‑Quants API から株価（日足）、財務データ、取引カレンダーを取得
  - レート制限・リトライ・トークン自動リフレッシュ処理を実装
  - DuckDB への冪等保存（ON CONFLICT を用いた更新）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（バックフィル対応）、保存、品質チェックの統合ジョブ
  - 日次 ETL 実行用の run_daily_etl を提供

- スキーマ管理（kabusys.data.schema）
  - DuckDB のテーブル定義・初期化（Raw / Processed / Feature / Execution 層）
  - init_schema / get_connection を提供

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、raw_news へ保存
  - 記事 → 銘柄コード紐付け（抽出ルール）を提供

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（スピアマン）・統計サマリー、Zスコア正規化

- 戦略（kabusys.strategy）
  - 特徴量作成（build_features）：research の raw factor を正規化・フィルタして features テーブルへ
  - シグナル生成（generate_signals）：features と ai_scores を統合して BUY/SELL シグナルを作成

- 実行・監査（execution / data.audit）
  - signals, signal_queue, orders, trades, executions, positions 等のテーブルと監査ログ設計

セットアップ手順
----------------

1. Python と依存パッケージのインストール（最低限の例）
   - Python 3.8+ を想定（プロジェクトの要件に合わせてください）
   - 依存パッケージ（例）
     - duckdb
     - defusedxml
   - インストール例:
     - pip install duckdb defusedxml

2. ソースの配置
   - パッケージは src/kabusys 配下に実装されています。プロジェクトルートに pyproject.toml や .git があれば自動的に .env が読み込まれます。

3. 環境変数 (.env)
   - プロジェクトルートに .env（および任意で .env.local）を作成します。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_station_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development   # development / paper_trading / live
     - LOG_LEVEL=INFO
   - 自動読み込みを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   .env の簡易例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化
   - Python REPL もしくはスクリプトから実行:
     ```
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - メモリ DB を使いたい場合:
     ```
     conn = init_schema(":memory:")
     ```

基本的な使い方
--------------

以下に主要なワークフローの使用例を示します。すべて DuckDB の接続（duckdb.DuckDBPyConnection）を渡す設計です。

1) 日次 ETL を実行する
   - 市場カレンダー、株価、財務データを差分取得して保存し、品質チェックを行います。
   - 例:
     ```
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_daily_etl

     conn = init_schema(settings.duckdb_path)
     result = run_daily_etl(conn)  # target_date を明示することも可能
     print(result.to_dict())
     ```

2) 特徴量を作成（build_features）
   - research の生ファクターを正規化して features テーブルへ保存します（冪等）。
   - 例:
     ```
     from datetime import date
     from kabusys.config import settings
     from kabusys.data.schema import get_connection
     from kabusys.strategy import build_features

     conn = get_connection(settings.duckdb_path)
     n = build_features(conn, target_date=date(2025, 1, 15))
     print(f"upserted {n} features")
     ```

3) シグナル生成（generate_signals）
   - features / ai_scores / positions テーブルを参照し、signals テーブルに BUY/SELL を書き込みます。
   - 例:
     ```
     from datetime import date
     from kabusys.config import settings
     from kabusys.data.schema import get_connection
     from kabusys.strategy import generate_signals

     conn = get_connection(settings.duckdb_path)
     total = generate_signals(conn, target_date=date(2025,1,15))
     print(f"generated {total} signals")
     ```

4) ニュース収集ジョブ
   - RSS フィードの収集と DB への保存を実行します。
   - 例:
     ```
     from kabusys.config import settings
     from kabusys.data.schema import get_connection
     from kabusys.data.news_collector import run_news_collection

     conn = get_connection(settings.duckdb_path)
     results = run_news_collection(conn)
     print(results)  # {source_name: saved_count, ...}
     ```

5) J‑Quants クライアントの直接利用（テストやデバッグ用）
   - トークン自動取得 / fetch_daily_quotes 等を呼べます。
   - 例:
     ```
     from kabusys.data.jquants_client import fetch_daily_quotes
     records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
     ```

ディレクトリ構成
----------------

主要なファイル/パッケージ構成（src/kabusys 配下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数管理（settings）
  - data/
    - __init__.py
    - schema.py                  — DuckDB スキーマ定義・初期化
    - jquants_client.py          — J‑Quants API クライアント（取得・保存）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - news_collector.py          — RSS ニュース収集と保存
    - calendar_management.py     — 市場カレンダー管理ユーティリティ
    - audit.py                   — 監査ログ用スキーマ・DDL
    - features.py                — データユーティリティの公開
    - stats.py                   — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py         — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py     — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py     — build_features
    - signal_generator.py        — generate_signals
  - execution/                   — 発注・execution 用モジュール（パッケージ）
  - monitoring/                  — 監視系モジュール（Slack 通知等、未詳細化）
  - その他モジュール...

設計・運用上の注意
-----------------
- 冪等性: 多くの保存関数は ON CONFLICT を使い冪等的に保存します。再実行が安全な設計です。
- ルックアヘッドバイアス対策: ETL / feature / signal では target_date 時点までのデータのみを使用する方針です。
- 環境の保護: OS 環境変数がある場合 .env の上書きを防ぐロジックがあります。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。
- テスト性: jquants_client の id_token 注入や news_collector._urlopen のモックなど、テストしやすさを考慮して設計されています。
- カレンダー: market_calendar がないときは土日ベースのフォールバックを行います。可能であれば calendar を先に取得しておくことを推奨します。

よくある運用スクリプト（例）
---------------------------
- 夜間バッチ（ETL → features → signals → enqueue orders）
  - run_daily_etl → build_features → generate_signals → execution 層へ渡す（実行は別モジュール）

補足
----
- ここに示したコマンドやコード例は、このリポジトリ内のモジュール API に基づく参考例です。実運用ではログ設定、エラーハンドリング、監視、シークレット管理、証券会社 API との連携（kabu ステーション）等の追加実装が必要になります。
- 依存パッケージ一覧はプロジェクトの pyproject.toml / requirements.txt を参照してください（本リポジトリの抜粋に依存ファイルが含まれていない場合は上記の主要依存をインストールしてください）。

以上。必要なら README に入れるサンプル .env.example や具体的な CI / systemd / cron の実行例、依存パッケージ版指定などを追加で作成します。どれを追加しますか？