README
=====

概要
---
KabuSys は日本株向けの自動売買・研究プラットフォームのコアライブラリ群です。本リポジトリには以下を含みます：
- 実行エンジン（ExecutionEngine）起動スクリプト
- システム監視（Monitoring）・Kill Switch
- ポートフォリオ構築（候補選定、重み計算、株数計算、セクター制約）
- ファクター計算・研究用ユーティリティ（DuckDB を使用）
- AI を使ったニュース NLP / レジーム判定（OpenAI API）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- ペーパートレード検証レポート生成ツール

主要な設計方針：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV による切り替え）
- ルックアヘッドバイアスを避けるため日付参照は明示的に引数で渡す実装が多い
- 外部 API 呼び出し（OpenAI など）はキー提供が必須で、失敗時はフォールバックして安全に継続する設計

機能一覧
-------
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカーファクトリによる live / paper_trading 切替
  - 注文管理、リスクマネージャ、再整合（Reconciler）との連携
- Monitoring
  - SystemMonitor（CPU/メモリ/Disk、プロセス生存、データ鮮度）
  - TradeMonitor（trade_logs 監視：滞留注文・約定異常など）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件成立時に data/kill.flag を書き込んで ExecutionEngine を停止）
  - MonitoringEngine（定期ポーリング・アラート送信）
  - 監視ログ永続化（SQLite：monitoring_db）
- Portfolio construction
  - 候補選定（select_candidates）
  - 重み計算（等分配・スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター上限適用、レジーム乗数
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Spearman）計算、統計サマリ
  - DuckDB を使った SQL ベースの集計
- AI（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
  - 両者とも OpenAI API キーを必要とし、レート制限や一時エラーに対するリトライ機構を実装
- ツール
  - .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート（tools/paper_verification_report.py）

前提条件
--------
- Python 3.9+（型アノテーション等を使用）
- 推奨ライブラリ（requirements.txt を用意している想定）：
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証をフルに行う場合）
- OS による差異：process priority / cpu affinity の一部機能は Windows / POSIX で異なる（psutil に依存）

セットアップ手順
---------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は少なくとも duckdb, psutil, openai をインストールしてください）

4. 環境変数の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（ルートに .env）。例（最小）:
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
   - 自動読み込みはデフォルトで有効（config.py）。自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL として扱う場合:
     python -m kabusys.validate_config --strict
   - PyYAML がインストールされていないと config/*.yaml の中身検証はスキップされます

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
- OPENAI_API_KEY: AI モジュールで必要
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- LOG_DIR（デフォルト logs/）
- MONITOR_POLL_INTERVAL（監視ループのインターバル秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading のマッチング動作: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか 1 / 0）

使い方（実行例）
----------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（バックグラウンド実行等は OS の手段で）
  - python -m kabusys.run_execution
  - 備考: KABUSYS_ENV=paper_trading のときは data/paper_trading.db に記録され、本番 DB と分離されます

- Monitoring を起動（定期ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトは 60 秒。停止は data/stop_requested.flag の作成、または KeyboardInterrupt（Ctrl+C）

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 系（スクリプト内部 API）
  - ニューススコアリング（外部呼び出し例）
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

  - レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

ログ設定
-------
共通のログ設定ユーティリティ:
- kabusys.utils.logging_setup.setup_logging(app_name="execution")
- デフォルトで stdout と日次ローテートファイル（logs/<app_name>.log）へ出力
- LOG_DIR / LOG_LEVEL 環境変数で制御

データファイル・フラグ
---------------------
- デフォルトの DB/ファイル:
  - data/kabusys.duckdb (DuckDB)
  - data/monitoring.db (SQLite: 監視用)
  - data/paper_trading.db (SQLite: ペーパートレード用)
  - data/execution.pid (ExecutionEngine の PID ファイル)
  - data/kill.flag （Kill Switch トリガー）
  - data/stop_requested.flag （run_*.py が監視している停止フラグ）
- Kill Switch:
  - kill_switch.evaluate() が条件成立すると data/kill.flag を書き込む
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動的にクリアされる（本番では 0 推奨）

ライブラリ / API の簡単な使い方
-------------------------------
- ポートフォリオ
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - 純粋関数群であり、外部 DB 参照なし。ユニットテストが容易。

- Research（DuckDB 接続必須）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - DuckDB コネクションを渡して使用。prices_daily / raw_financials 等のテーブルを参照。

- Monitoring DB
  - from kabusys.monitoring.monitoring_db import init_monitoring_db, MonitoringDB
  - SQLite 接続を渡し、init_monitoring_db(conn) でテーブル作成・マイグレーションを実行

注意事項 / 開発メモ
------------------
- .env は決してリポジトリへコミットしないこと（config_setup でも書き出し時に注意喚起あり）
- 一部機能は外部 API キー（OpenAI など）を必要とし、不在時は ValueError を投げる箇所があります
- DuckDB/SQLite のファイルパスは環境変数で設定可能。監視は常に sqlite_path（monitoring.db）を参照します
- ペーパートレード時は DB を完全に分離しているため、本番 DB に影響を与えません
- process priority / cpu affinity の設定は権限や OS に左右されるため、権限不足時は警告を出してスキップします

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理、自動 .env ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py         (参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         (参照)
  - execution/                 (ExecutionEngine 周りの実装)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

付録: よく使うコマンド一覧
--------------------------
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行開始 (ExecutionEngine): python -m kabusys.run_execution
- 監視開始 (Monitoring): MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

ライセンス・貢献
----------------
（この README では記載していません。リポジトリの LICENSE を参照してください）

お問い合わせ
------------
不具合報告や質問はリポジトリの Issue（またはプロジェクト内連絡手段）にお願いします。