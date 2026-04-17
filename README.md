# KabuSys — README

本リポジトリは日本株向けの自動売買 / 研究 / 監視基盤の一部を実装した Python コードベースです。  
このドキュメントはコードベース（src/kabusys 以下）から抽出した主要機能・使い方・セットアップ手順・ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（実行例）
- 環境変数（主な設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な目的は以下の通りです。

- 戦略のリサーチ（ファクター算出、特徴量解析）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- 実行（ExecutionEngine、OrderManager、ブローカ連携、リコンシリエーション）
- 監視（System / Trade / Risk のポーリング、アラート送信、kill フラグ）
- AI（ニュースセンチメントによるスコアリング／レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針のポイント：
- DuckDB/SQLite を用いたデータ処理と永続化
- 本番と Paper Trading を分離（Paper 時は専用 DB と MockBroker）
- LLM 呼び出しはフェイルセーフ（API 失敗時のフォールバック）
- ルックアヘッドバイアス回避（日時参照の扱いに注意）

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env ファイルの自動読み込み（プロジェクトルート検出）
  - Settings クラスで環境変数をラップ

- Execution 系
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて Paper/Live 動作）
  - order_manager, order_repository, reconciler — 発注・状態管理・リコンシリエーション

- Monitoring 系
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - monitoring_db — SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - AlertManager — LINE Push を使った通知
  - KillSwitch — フラグファイルで ExecutionEngine を停止

- Portfolio（ポートフォリオ構築）
  - portfolio_builder — 候補選定、等配分・スコア配分
  - position_sizing — 株数算出（risk_based / equal / score）
  - risk_adjustment — セクターキャップ、レジーム乗数

- Research（ファクター・特徴量）
  - factor_research — Momentum / Volatility / Value 等のファクター計算（DuckDB 上で実行）
  - feature_exploration — 将来リターン、IC、統計サマリー

- AI（LLM 連携）
  - news_nlp — raw_news を LLM（OpenAI）でスコアリングし ai_scores に書き込み
  - regime_detector — ma200 とマクロニュースで市場レジーム判定

- Tools
  - tools/paper_verification_report.py — Paper Trading 実行ログから検証レポートを生成
  - monitoring/streamlit_dashboard.py — Streamlit ダッシュボード

- Utils
  - process_priority — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

1. Python（推奨: 3.10+）を用意し、仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じてプロジェクト専用の requirements.txt を作成してください）

3. プロジェクトルートに .env を作成（自動ロードされます）
   - config.py がプロジェクトルート（.git または pyproject.toml を探索）を検出すると .env/.env.local を自動読み込みします
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. data ディレクトリ（デフォルト DB 保存先）を作成
   - mkdir -p data

5. OpenAI API を使う機能を利用する場合は API キーを設定
   - export OPENAI_API_KEY="sk-...."

注意：
- psutil によるプロセス優先度設定はプラットフォームや権限によって失敗することがあります（ログ警告でスキップされます）。
- DuckDB/SQLite のファイルパスは Settings で環境変数により変更可能です（以下参照）。

---

## 簡単な使い方（実行例）

- ExecutionEngine を起動（デフォルト: KABUSYS_ENV=development）
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、Paper 専用 DB に記録されます。
  - 実行:
    - python -m kabusys.run_execution
  - 停止は data/stop_requested.flag または data/kill.flag を利用（kill.flag は強制停止トリガー）

- Monitoring を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

- AI スコア／レジーム判定（ライブラリ関数から使用）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 主な環境変数（Settings）

- KABUSYS_ENV: 起動環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必要）
- PAPER_FILL_MODE: paper trading の約定モード（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite のパス（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視/制御用設定
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

.sample .env（例）
  JQUANTS_REFRESH_TOKEN=your_jquants_token
  KABU_API_PASSWORD=your_kabu_password
  OPENAI_API_KEY=sk-...
  KABUSYS_ENV=development
  PAPER_FILL_MODE=instant

---

## 注意事項 / 運用上のポイント

- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と切り離されています（PAPER_TRADING_SQLITE_PATH）。
- LLM 呼び出し（OpenAI）はレート制限・タイムアウトを考慮してリトライ実装がありますが、API キーや料金に注意してください。
- run_execution/run_monitoring は stop フラグ（data/stop_requested.flag）や kill.flag に反応します。強制停止や自動停止ロジックは KillSwitch により管理されます。
- streamlit ダッシュボードは監視 DB に対して読み取り専用で起動してください（起動例は README 上部参照）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他ブローカー/エンジン/リポジトリ関連ファイル — 一部ファイルは省略)
  - utils/
    - __init__.py
    - process_priority.py
  - research, data, etc.

data/ 以下（実行時に生成／使用）
- data/monitoring.db (監視用 SQLite — デフォルト)
- data/paper_trading.db (Paper Trading 用 SQLite)
- data/kabusys.duckdb (DuckDB)
- data/execution.pid, data/kill.flag, data/stop_requested.flag などの制御ファイル

---

## 最後に

この README は現在のコードベースから主要な点を抜粋してまとめたものです。個々のモジュールには詳細な実装コメントが含まれているため、さらに詳しい挙動確認や拡張を行う際は各モジュール（特に ai/*.py、monitoring/*.py、execution/*.py、portfolio/*.py）を参照してください。不明点があればどの部分を深掘りしたいか教えてください。