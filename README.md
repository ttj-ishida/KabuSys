# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
市場データの ETL、ニュースによる AI スコアリング、ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（DuckDB 保存、品質チェック付き）
- RSS によるニュース収集と LLM を使った銘柄別センチメントスコアリング
- マクロセンチメント＋テクニカル指標による「市場レジーム」判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量解析ユーティリティ
- 発注〜約定の監査ログ用スキーマ初期化と監査ユーティリティ
- 設定管理（.env 自動読み込み、環境変数による設定）

設計上の共通方針として「ルックアヘッドバイアスを防ぐ」「DuckDB を用いた冪等保存」「外部 API 呼び出し時の堅牢なリトライ／フェイルセーフ」を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch_* / save_*）
  - 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - ニュース収集（RSS の取得・前処理・raw_news への保存ロジック）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログ（監査テーブル DDL と初期化ユーティリティ）
  - 汎用統計ユーティリティ（Zスコア正規化など）
- ai/
  - ニュース NLP（銘柄ごとのセンチメントを OpenAI に問い合わせて ai_scores に保存する score_news）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成して market_regime に保存する score_regime）
- research/
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 特徴量探索（将来リターン計算、IC、統計サマリー）
- config.py
  - 環境変数と .env 自動読込（.env, .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
- audit/schema の初期化と監査用 DB 初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.9+（typing の Union 表記などに対応していることを想定）
- 基本的に Unix 系 OS を想定（Windows でも動作しますが path の扱い等に注意）

1. リポジトリを取得
   - ソースが `src/kabusys` 配下にあることを想定します。

2. 仮想環境を作成して有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   - minimal（実行に必要な主要パッケージ）
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発用に package を editable インストールする場合（pyproject.toml / setup.py がある前提）
     ```bash
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置すると、自動で読み込まれます（ただしテスト等で無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。
   - 主要な環境変数（必須 / 任意）例:
     - 必須（ETL 実行など一部機能で必要）:
       - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
       - KABU_API_PASSWORD=your_kabu_station_password
     - OpenAI:
       - OPENAI_API_KEY=your_openai_key (score_news / score_regime を API キー引数で渡さない場合に参照)
     - オプション:
       - LINE_CHANNEL_ACCESS_TOKEN=（通知用）
       - LINE_USER_ID=
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - PID_FILE_PATH=data/execution.pid
       - KILL_FLAG_PATH=data/kill.flag
       - KILL_FLAG_CLEAR_ON_START=0 or 1
       - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
       - KABUSYS_ENV=development|paper_trading|live
       - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

   - `.env` の書式はシェル風（export を許容、クォート・コメント処理あり）です。`.env.example` を参考に作成してください（リポジトリに例が無い場合は上記キーを参照）。

---

## 使い方（主要なユースケース例）

以下は Python REPL やスクリプトでの利用例です。事前に環境変数（OpenAI / J-Quants 等）を設定してください。

- DuckDB 接続と基本操作例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP による銘柄スコアリング（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用 DuckDB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
  ```

- 市場カレンダー API を差分で取得して保存
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  saved = calendar_update_job(conn)
  print(f"保存したレコード数: {saved}")
  ```

注意:
- OpenAI の呼び出しは内部で retry/backoff を行いますが、API キーの利用料に注意してください。
- DuckDB のバージョンや設定によっては executemany の空リストがエラーになるため、モジュール側で回避済みです。

---

## .env の自動読み込みについて

- 実行時にプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を起点として `.env` → `.env.local` を順に読み込みます。
  - OS 環境変数が優先され、`.env.local` は `.env` より優先で上書きします。
- 自動ロードを無効化するには環境変数を設定します:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル・概要）

（ソースルート: src/kabusys）

- __init__.py
  - パッケージ初期化、公開 API の一覧
- config.py
  - Settings クラス: 環境変数のラッパー（J-Quants / kabu / LINE / DB パス / 監視設定 等）
  - .env 自動読み込みロジック
- ai/
  - __init__.py
  - news_nlp.py — ニュースを集約して OpenAI に送り、ai_scores に書き込む機能
  - regime_detector.py — ETF 1321 の MA とニュースセンチメントを合成して market_regime に書き込む機能
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch_* / save_* / get_id_token 等）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
  - calendar_management.py — market_calendar 管理 / 営業日判定ユーティリティ / calendar_update_job
  - news_collector.py — RSS 収集と前処理、SSRF 対策、raw_news への保存ロジック
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログテーブル DDL と初期化機能（init_audit_schema / init_audit_db）
  - etl.py — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / rank / factor_summary

各モジュールは docstring に処理フローと設計方針が記載されているので、実装の詳細・制約・失敗時の挙動（フェイルセーフ）を参照してください。

---

## 運用上の注意

- OpenAI / J-Quants などの API はレート制限と課金が発生します。ローカルでのテストは必ず限定的に行ってください。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に保存されます。バックアップ・マイグレーション戦略を検討してください。
- 本ライブラリには実際の発注（broker）接続は含まれていません。発注ロジックを接続する場合は監査ログ（order_requests / executions）を通じて二重発注防止やトレーサビリティを確保してください。
- 環境に応じて KABUSYS_ENV を設定し（development / paper_trading / live）、live 環境では特に安全策を講じてください。

---

必要であれば README に「コマンドラインツール」「CI ワークフロー」「.env.example のテンプレート」などを追加します。どの情報がさらに必要か教えてください。