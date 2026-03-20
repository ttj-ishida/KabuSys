# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。  
DuckDB を用いたデータレイク、J-Quants API からのデータ取得、ファクター計算、特徴量生成、シグナル生成、ニュース収集、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の層を持つ日本株自動売買システム向けライブラリです。

- Data (ETL / スキーマ / ニュース収集 / カレンダー管理)
- Research (ファクター計算・解析)
- Strategy (特徴量エンジニアリング、シグナル生成)
- Execution / Monitoring（発注・監視用インターフェース／テーブル設計・監査）

設計方針の主なポイント:
- ルックアヘッドバイアスを排除する設計（target_date 時点のデータのみ使用）
- DuckDB を中心とした冪等なデータ保存（ON CONFLICT / トランザクション）
- API 呼び出しはリトライ・レートリミット制御・トークン自動リフレッシュ対応
- 外部ライブラリへの依存は最小限（duckdb, defusedxml 等）

---

## 主な機能一覧

- J-Quants API クライアント（株価 / 財務 / カレンダー取得、ページネーション・リトライ・レート制御）
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン（日次差分取得、バックフィル、品質チェック呼び出し）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量作成（Zスコア正規化、ユニバースフィルタ、features テーブルへの書き込み）
- シグナル生成（特徴量＋AIスコア統合 → BUY/SELL シグナル生成、冪等書き込み）
- ニュース収集（RSS フィード取得、前処理、raw_news / news_symbols への保存）
- マーケットカレンダー管理（営業日の判定・next/prev_trading_day 等）
- 監査ログ（signal_events / order_requests / executions 等のテーブル定義）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに PEP 604 の `|` を使用）
- duckdb, defusedxml などが必要

1. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   最低限の依存例:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクト配布時は requirements.txt / pyproject.toml 等を参照してください）

3. 環境変数設定
   プロジェクトルートに `.env` / `.env.local` を置いて環境変数を管理できます。自動ロードはデフォルトで有効です（.git または pyproject.toml を探索してプロジェクトルートを特定します）。テスト等で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須環境変数（実行する機能に応じて必要）:
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
   - KABU_API_PASSWORD : kabu ステーション API パスワード（execution 層利用時）
   - SLACK_BOT_TOKEN : Slack 通知を使う場合
   - SLACK_CHANNEL_ID : Slack 通知チャンネル
   省略可能:
   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

   .env の例（最小）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース初期化
   Python REPL またはスクリプトで DuckDB スキーマを初期化します。
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # デフォルトだと data/kabusys.duckdb に作成
   ```

---

## 使い方（簡単なワークフロー例）

以下は代表的な操作のサンプルです。実運用ではジョブスケジューラ（cron / systemd timer / Airflow 等）から呼び出します。

1. 日次 ETL（市場カレンダー・株価・財務を差分取得して保存）
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 特徴量作成（features テーブルに書き込む）
   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2024, 1, 10))
   print(f"upserted features: {n}")
   ```

3. シグナル生成（signals テーブルに BUY/SELL を書き込む）
   ```python
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   count = generate_signals(conn, target_date=date(2024, 1, 10))
   print(f"signals written: {count}")
   ```

4. ニュース収集（RSS → raw_news に保存、銘柄紐付け）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # known_codes: 銘柄抽出に使う有効なコードのセット（例、prices_daily から取得）
   known_codes = {"7203", "6758", "6501"}  # 実際には DB から動的取得推奨
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

5. カレンダー更新ジョブ（夜間）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

備考:
- ETL / pipeline.run_daily_etl は品質チェック（quality モジュール）を呼び出します。品質チェックの結果は ETLResult.quality_issues に格納されます。
- generate_signals は ai_scores / features / positions / prices_daily を参照します。重みや閾値は引数で上書き可能です。

---

## ディレクトリ構成

主要ファイル・モジュールの概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 系）
    - news_collector.py     — RSS 収集・前処理・DB 保存
    - schema.py             — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - features.py           — data.stats の再エクスポート
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py— マーケットカレンダー管理（営業日判定等）
    - audit.py              — 監査ログ用テーブル定義
    - quality.py?           — （品質チェックモジュールを想定）
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Volatility/Value 等ファクター計算
    - feature_exploration.py— 将来リターン・IC・統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py— features テーブル構築（正規化・ユニバースフィルタ）
    - signal_generator.py   — final_score 計算、BUY/SELL 生成
  - execution/
    - __init__.py           — 発注層（現状スケルトン）
  - monitoring/             — 監視用モジュール（場所確保）

（実際のツリーはリポジトリのルート構成に依存しますが、上記が主要なモジュール群です）

---

## 設定と動作モード

- KABUSYS_ENV（development / paper_trading / live）により実行モードを切替。settings.is_live / is_paper / is_dev プロパティで利用可能。
- LOG_LEVEL によりログ出力レベルを設定。
- 環境変数は .env / .env.local から自動的に読み込まれる（OS 環境変数が優先、.env.local が .env 上書き）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。

---

## 開発者向けメモ

- 冪等性・トランザクションに注意して実装されています。DB 書き込みは日付単位の置換や ON CONFLICT を用いるパターンが多いです。
- J-Quants API 呼び出しは内部でレートリミットとリトライを実装しています。401 受信時はトークン自動更新を試みます。
- ニュース収集は SSRF 対策（リダイレクト検査 / プライベートIP検査）、XML の安全パース（defusedxml）を行います。

---

## 例: 初期化から ETL → シグナル生成までの最小手順

1. .env を用意して環境変数を設定
2. DB 初期化
   ```bash
   python - <<'PY'
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   init_schema(settings.duckdb_path)
   print("DB initialized:", settings.duckdb_path)
   PY
   ```
3. 日次 ETL とシグナル生成
   ```bash
   python - <<'PY'
   from kabusys.config import settings
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.strategy import build_features, generate_signals
   from datetime import date

   conn = init_schema(settings.duckdb_path)
   etl_res = run_daily_etl(conn)
   trading_day = etl_res.target_date
   build_features(conn, trading_day)
   generate_signals(conn, trading_day)
   print("Done for", trading_day)
   PY
   ```

---

## ライセンス / 貢献

本ドキュメントはコードベースに基づく簡易 README です。実際のリポジトリには LICENSE や Contributing ガイドを追加してください。

---

必要ならば README にサンプル .env.example や運用時の Cron / systemd の例、より詳細な API 仕様やテーブルスキーマの説明を追記できます。どの情報を追加希望か教えてください。