# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants API からのデータ取得、DuckDB ベースのスキーマ定義・ETL、ニュース収集、ファクター計算、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。  
主な目的は以下です。

- J-Quants からの株価・財務・カレンダーの差分取得と DuckDB への冪等保存
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース（RSS）収集と銘柄紐付け
- ファクター（Momentum / Volatility / Value 等）計算・探索（Research）
- 発注・約定・監査ログを保存する監査スキーマの提供
- ETL（run_daily_etl）やバッチジョブ（calendar_update_job / run_news_collection）を通した運用

設計上、以下の点を重視しています。

- DuckDB を中核にしたデータレイヤー（Raw / Processed / Feature / Execution）
- 冪等性（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）
- Look-ahead バイアス対策（fetched_at の記録など）
- 外部ライブラリへの過剰依存を避け、標準ライブラリで可能な部分は実装

---

## 主な機能一覧

- 環境設定管理（kabusys.config）: .env 自動読み込み / 必須設定の検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - ページネーション対応、レート制限、リトライ、トークン自動リフレッシュ
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存ユーティリティ（save_daily_quotes 等）
- データスキーマ（kabusys.data.schema）
  - DuckDB のテーブル定義と初期化関数（init_schema / get_connection）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新、バックフィル、run_daily_etl（品質チェック込み）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、raw_news 保存、銘柄抽出・紐付け
- 研究用ファクター計算（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
  - zscore_normalize（kabusys.data.stats）
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の初期化機能

---

## 動作要件

- Python 3.10 以上（Union 型記法 / match などを想定）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（上記は最小セット。パッケージ配布時に requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール

   ローカル開発の場合（プロジェクトルートで）:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   pip install duckdb defusedxml
   ```

2. 環境変数（.env）を用意

   プロジェクトルートに `.env`（およびローカル専用 `.env.local`）を配置すると、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを抑制できます）。

   必須の環境変数（例）:

   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID（必須）

   任意 / デフォルトあり:

   - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 環境 (development|paper_trading|live)（default: development）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

   .env の一例:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB スキーマの初期化

   Python REPL やスクリプトで:

   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # データベースファイルを作成・テーブルを作成
   ```

   監査ログ専用 DB を分けて初期化する場合:

   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な例）

以下に主要なユースケースの使い方を示します。

1. 日次 ETL を実行（市場カレンダー取得 → 株価取得 → 財務取得 → 品質チェック）

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

2. 市場カレンダーの夜間更新ジョブ

   ```python
   from kabusys.data.schema import get_connection
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.config import settings

   conn = get_connection(settings.duckdb_path)
   saved_count = calendar_update_job(conn)
   print(f"saved: {saved_count}")
   ```

3. RSS ニュース収集と銘柄紐付け

   ```python
   from kabusys.data.schema import get_connection
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット（例）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

4. ファクター計算（研究用途）

   ```python
   import duckdb
   from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   target = date(2025, 1, 31)
   mom = calc_momentum(conn, target)
   vol = calc_volatility(conn, target)
   val = calc_value(conn, target)
   normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
   ```

5. J-Quants クライアントを直接利用

   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes
   from kabusys.config import settings
   from datetime import date

   recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
   ```

---

## ディレクトリ構成（抜粋）

src/kabusys パッケージの主要ファイルを示します（実際のプロジェクトは更にファイルがある可能性があります）。

- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                  — J-Quants API クライアント
    - news_collector.py                  — RSS ニュース収集
    - schema.py                          — DuckDB スキーマ定義・初期化
    - stats.py                           — zscore_normalize などの統計ユーティリティ
    - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
    - features.py                         — features の公開インターフェース
    - calendar_management.py             — カレンダー管理 / ジョブ
    - audit.py                           — 監査ログスキーマ初期化
    - quality.py                         — データ品質チェック
    - etl.py                             — ETL 関連公開 API
  - research/
    - __init__.py
    - feature_exploration.py             — 将来リターン / IC / summary 等
    - factor_research.py                 — momentum / volatility / value の計算
  - strategy/                            — 戦略層（骨格）
  - execution/                           — 発注 / 実行層（骨格）
  - monitoring/                          — 監視関連（骨格）

---

## 開発 / テスト時の注意点

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml がある階層）から行われます。テストで自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の API レート制限（120 req/min）やリトライ・トークン更新の挙動に注意して下さい。
- DuckDB の SQL を実行する箇所ではパラメータバインド（?）を使用しています。直接 SQL を変更する場合はインジェクションや型に注意してください。
- news_collector では SSRF 対策（スキームチェック / プライベートアドレス拒否）や XML の安全パーサ（defusedxml）を使用しています。外部入力を渡す場合はこれらの制約を理解してください。

---

## よくある利用フロー（例）

1. .env を作成して必要なシークレットを設定
2. init_schema() で DuckDB を初期化
3. cron / Airflow / Azure Function 等で nightly に run_daily_etl を実行
4. calendar_update_job を定期実行してカレンダーを最新化
5. run_news_collection を定期実行してニュースデータを蓄積
6. 研究環境で kabusys.research の関数群を用いてファクター探索やバックテスト用特徴量を作成
7. strategy / execution 層を実装して signal → order → execution のフローを監査テーブルに記録

---

必要であれば、README にサンプル .env.example、より詳細な CLI / systemd / docker-compose 用の実行例、テーブルスキーマの ER 図、ユニットテストの実行方法などを追加できます。どの情報を充実させたいか教えてください。