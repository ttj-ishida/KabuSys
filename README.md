# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
J-Quants から市場データを取得して DuckDB に保存し、特徴量計算・品質チェック・監査ログ・ニュース収集等を行うためのモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB を使ったデータスキーマ管理と冪等保存
- ETL（差分取得・バックフィル）パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と銘柄紐付け
- 研究 / 戦略用のファクター計算（モメンタム・ボラティリティ・バリュー等）
- 監査ログ（order/exec トレーサビリティ）用スキーマ

設計方針として、本ライブラリは「本番の発注 API を直接叩かない」研究・データ整備層と、発注周りの監査・実行スキーマを分離して提供しています。外部依存を最小限にし、DuckDB と標準ライブラリ中心で実装されています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（data/jquants_client.py）
  - raw_prices / raw_financials / market_calendar の冪等保存
- ETL / パイプライン
  - 日次差分 ETL（data/pipeline.run_daily_etl）
  - 個別 ETL（prices, financials, calendar）
- データスキーマ管理
  - DuckDB スキーマ初期化（data/schema.init_schema）
  - 監査ログ用スキーマ（data/audit.init_audit_schema / init_audit_db）
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合（data/quality.run_all_checks 等）
- ニュース収集
  - RSS 取得 / 前処理 / raw_news 保存 / 銘柄抽出（data/news_collector.run_news_collection）
- 研究用ユーティリティ
  - ファクター計算（research/factor_research.py）
  - 将来リターン計算・IC 計算・統計サマリ（research/feature_exploration.py）
  - z-score 正規化（data/stats.zscore_normalize）
- 設定管理
  - .env または環境変数読み込み（config.py）
  - 必須設定の検証（settings オブジェクト）

---

## セットアップ

必要環境
- Python 3.10 以上（| 型注釈を使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全化）

推奨手順（仮にプロジェクトルートにいる想定）:

1. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell/コマンドプロンプト)
   ```

2. 必要パッケージをインストール
   （プロジェクトに pyproject.toml がある前提で editable install するか、最低限の依存を pip で入れる）
   ```bash
   pip install duckdb defusedxml
   # 開発時: pip install -e .
   ```

3. 環境変数（.env）の準備  
   KabuSys はプロジェクトルートの `.env` / `.env.local` を自動読み込みします（テスト時に無効化可能）。最低限必要な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（必須、発注連携がある場合）
   - SLACK_BOT_TOKEN: Slack 通知に使用するトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

   サンプル `.env`（ルートに配置）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

   自動ロードを無効化したい場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（基本例）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect の戻り値）を受け取って動作します。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data import schema

   conn = schema.init_schema("data/kabusys.duckdb")
   # ":memory:" を渡すとインメモリ DB が使えます
   ```

2. 日次 ETL の実行
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")  # 既存接続
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 既知銘柄コードセット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

4. ファクター計算 / 研究用関数
   ```python
   from datetime import date
   import duckdb
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

   conn = duckdb.connect("data/kabusys.duckdb")
   tgt = date(2024, 1, 31)
   mom = calc_momentum(conn, tgt)
   vol = calc_volatility(conn, tgt)
   val = calc_value(conn, tgt)
   fwd = calc_forward_returns(conn, tgt, horizons=[1,5,21])
   ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
   ```

5. 監査ログスキーマの初期化（監査専用 DB）
   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/audit.duckdb")
   ```

6. 品質チェック
   ```python
   from kabusys.data.quality import run_all_checks
   checks = run_all_checks(conn, target_date=date.today())
   for issue in checks:
       print(issue)
   ```

---

## 設定（settings）

kabusys.config.Settings（モジュール変数 settings）から各種設定を取得できます。主なプロパティ:

- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path (Path)
- settings.sqlite_path (Path)
- settings.env / settings.is_live / settings.is_paper / settings.is_dev
- settings.log_level

必須環境変数が未設定の場合は ValueError を送出します。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - news_collector.py               — RSS ニュース収集・保存
    - schema.py                       — DuckDB スキーマ定義・初期化
    - stats.py                        — 統計ユーティリティ（z-score）
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - features.py                     — 特徴量ユーティリティ公開
    - calendar_management.py          — マーケットカレンダー管理
    - audit.py                        — 監査ログスキーマ / 初期化
    - etl.py                          — ETL 形式公開
    - quality.py                      — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py              — Momentum / Value / Volatility など
    - feature_exploration.py          — 将来リターン / IC / summary
  - strategy/                         — 戦略層（パッケージ化のみ、実装は各ファイルへ）
  - execution/                        — 発注実行層（パッケージ化のみ）
  - monitoring/                       — 監視用モジュール（パッケージ化のみ）

---

## 注意点・運用上のヒント

- API レート制限: J-Quants API は制限を考慮して実装（120 req/min）。jquants_client は内部でスロットリングとリトライを行います。
- DuckDB 初期化: 初回は schema.init_schema() を必ず実行してください。既存 DB に接続するだけなら schema.get_connection() を使用します。
- ログ・運用環境: KABUSYS_ENV により挙動（paper/live/dev）を切替可能です。発注機能を有効にする場合は本番環境での設定に細心の注意を払ってください。
- セキュリティ: news_collector は SSRF 対策や defusedxml による安全な XML パースを実装していますが、外部フィードの取り扱いは注意してください。
- テスト: 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（ユニットテスト等で便利です）。
- SQLite は監視用途などで利用する想定（settings.sqlite_path）。

---

## 参考 / 次のステップ

- 実運用では発注（kabu API）や Slack 通知などを組み合わせるためのラッパーと安全なワークフロー（トランザクション・監査）が必要です。audit モジュールや signal/queue スキーマを活用してください。
- 研究用途では research モジュールの関数群を組み合わせて特徴量エンジニアリング→ランキング→シグナル生成のワークフローを作成できます。

---

不明点や README に追加して欲しい利用シナリオ（例: CI 用の DB 初期化、cron 用の ETL 実行コマンドなど）があれば教えてください。必要に応じて具体的なスクリプト例や運用手順を追記します。