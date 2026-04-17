README
======

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームです。  
主なコンポーネントは次のとおりです。

- ExecutionEngine：発注ロジック（本番 / ペーパートレード対応）
- MonitoringEngine：システム・注文・リスク監視、Kill Switch（自動停止）
- Portfolio モジュール：銘柄選定、重み付け、株数決定
- Research モジュール：ファクター計算、特徴量解析、IC 計算
- AI モジュール：ニュースの NLP スコアリング、レジーム判定（OpenAI API利用）
- Tools：ペーパートレード検証レポート生成など
- Utilities / Config：環境変数管理、対話式設定ウィザード、設定検証

機能一覧
--------
- 実行（ExecutionEngine）
  - KABUSYS_ENV によるモード切替（development / paper_trading / live）
  - paper_trading では MockBroker を使用し本番 DB と分離（data/paper_trading.db）
  - PID ファイルによるプロセス監視・stale PID 検出
- 監視（MonitoringEngine）
  - SystemMonitor：CPU/メモリ/ディスク、プロセス存否、データ鮮度検査
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch：閾値超過時に data/kill.flag を書いて ExecutionEngine に停止シグナル送信
  - アラート発行フック（LINE 等と連携可能）
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスクベース割当、セクターキャップ、レジーム乗数
  - 単元株丸め、利用可能現金に合わせたスケーリング
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）算出、統計サマリー
- AI（OpenAI）
  - ニュース記事のセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
  - 再試行・エラーハンドリングやレスポンス検証を備えた堅牢な実装
- ツール
  - Paper Trading 検証レポート生成（稼働率・注文成功率・レイテンシなど）

セットアップ手順
----------------
前提
- Python 3.10+
- システムに sqlite3 が利用可能（標準ライブラリ）
- 推奨パッケージ：duckdb, psutil, openai, PyYAML（設定検証で optional）

例（Unix/macOS）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必須パッケージのインストール
   - pip install duckdb psutil openai
   - （設定検証で YAML を使いたい場合）pip install pyyaml

3. 環境変数の初期設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいはプロジェクトルートに .env を直接作成（下記のサンプル参照）

必須環境変数（代表）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — AI 機能を使う場合（任意だが AI 機能を使うなら必須）

主なオプション（デフォルトは括弧内）
- KABUSYS_ENV (development) — 実行モード: development | paper_trading | live
- DUCKDB_PATH (data/kabusys.duckdb) — DuckDB ファイルパス
- SQLITE_PATH (data/monitoring.db) — 監視用 SQLite（monitoring）DB
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — ペーパートレード専用 DB（paper_trading モード）
- LOG_LEVEL (INFO)
- PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject")
- KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動削除するか

サンプル .env（最小）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
（.env は Git にコミットしないこと）

使い方
------
設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

設定ウィザード（.env 作成）
- python -m kabusys.config_setup

ExecutionEngine を起動（本番／ペーパー共通）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定しておくと MockBroker が使われ、paper_trading 用 DB を使用します。
  - 実行はデーモン的にスレッドでセッションを走らせます。終了は data/stop_requested.flag の作成または Ctrl+C。

Monitoring を起動
- python -m kabusys.run_monitoring
  - デフォルトは 60 秒間隔でポーリング。MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は KABUSYS_ENV にかかわらず production 用 sqlite_path（Settings.sqlite_path）を参照します。

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

AI 機能（Python から直接呼び出す例）
- DuckDB コネクションを作成し関数を呼ぶ:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026, 4, 10), api_key="sk-...")

停止方法（安全に）
- 手動停止: data/stop_requested.flag を作成すると run_* スクリプトのループが検出して終了します（PID ファイル等と併用）。
  - 例: mkdir -p data && touch data/stop_requested.flag
- Monitoring が KillSwitch 条件を満たすと data/kill.flag を生成し、ExecutionEngine 側がそれを検出して停止します。

注意点
- paper_trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を利用）。
- Monitoring は本番用 sqlite_path を参照するため、監視 DB を別にしたい場合は環境変数で調整してください。
- AI 機能を利用するには OPENAI_API_KEY が必要です。API 呼び出しは再試行やクリップ等の保護を行っていますが、API の利用料金／レート制限には注意してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py                   — パッケージ定義、バージョン
- config.py                     — 環境変数読み込み・Settings
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py          — レジーム判定（MA200 + LLM）
  - __init__.py
- monitoring/
  - monitoring_db.py            — SQLite 監視 DB 層（初期化 / CRUD）
  - monitoring_engine.py        — 各 Monitor の束ね（Polling loop）
  - system_monitor.py           — CPU/プロセス/データ鮮度監視
  - trade_monitor.py            — 注文滞留・約定異常監視
  - risk_monitor.py             — ドローダウン・ポジション制限監視
  - kill_switch.py              — kill.flag 管理
  - alert_manager.py            — （アラート送信をまとめるモジュール）
- execution/
  - （注文・ブローカー関連の実装群）
- portfolio/
  - portfolio_builder.py        — 候補選定・重み計算
  - position_sizing.py          — 株数計算・上限/スケーリング
  - risk_adjustment.py          — セクター上限・レジーム乗数
- research/
  - factor_research.py          — Momentum/Volatility/Value 計算
  - feature_exploration.py      — 将来リターン・IC・統計
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
- data/                         — 実行時に DB / フラグ等を置くディレクトリ（デフォルト）
  - monitoring.db (SQLITE_PATH のデフォルト)
  - kabusys.duckdb (DUCKDB_PATH のデフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
  - execution.pid
  - stop_requested.flag / kill.flag

付録：よく使う操作例
--------------------
- 設定ウィザードを使って .env を作る:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン（ペーパートレード）を起動:
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution

- 監視ループを起動（ポーリング 30 秒間隔にする例）:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問題が発生した場合や追加ドキュメントが必要な箇所（例：ExecutionEngine の詳細な設定、Broker の実装、アラート送信設定など）はご相談ください。