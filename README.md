KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。  
主な目的は「戦略（シグナル） → ポートフォリオ構築 → 発注（Execution）」を安全に自動化し、監視・検証・リスク管理を組み合わせて本番運用できることです。コードベースは以下の機能群で構成されています。

主な機能一覧
-------------
- Execution
  - ExecutionEngine を中心に発注処理を実行（KABUSYS_ENV により paper_trading / live を切替）
  - BrokerClientFactory により実際のブローカー or MockBrokerClient を抽象化
  - リスク管理（RiskManager）、OrderManager、Reconciler などを統合
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - kill.flag による外部停止（Kill Switch）、stop_requested.flag による停止制御
  - SQLite に監視ログを永続化（monitoring_db）
- Portfolio construction
  - 候補選定（select_candidates）、重み計算（等金額/スコア加重）
  - リスク調整（セクター上限・レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap）
- Research
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Information Coefficient）計測、統計サマリー
  - DuckDB を用いた分析ワークフロー
- AI（OpenAI）
  - news_nlp: ニュース記事のセンチメントを LLM（gpt-4o-mini 等）で評価して ai_scores に保存
  - regime_detector: MA・マクロニュースを組み合わせて市場レジーム（bull/neutral/bear）を判定
- ツール
  - config_setup: .env を対話式に作成・更新するウィザード
  - validate_config: 環境変数と config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード結果の検証レポート生成

前提 / 必要要件
---------------
- Python 3.9+
- SQLite（標準で組み込み）
- DuckDB（python duckdb パッケージ）
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config が YAML 検証を行うため）
- （任意）必要な OS 権限：プロセス優先度設定や CPU affinity を行う際に権限が必要な場合があります

インストール（例）
-----------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合は以下を目安に）
   - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに .env を配置（または config_setup で生成）

セットアップ手順
---------------
1. .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - 生成された .env を絶対に Git にコミットしないでください。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります。

3. データベース初期化
   - 実行時に監視用 SQLite（デフォルト: data/monitoring.db）と DuckDB（デフォルト: data/kabusys.duckdb）が必要になります。多くの初期化は実行スクリプトが自動で行います（monitoring のテーブルは init_monitoring_db により冪等で作成）。

主要な環境変数（代表）
---------------------
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルトは development。
  - paper_trading: MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db）に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60） — run_monitoring で参照
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0、本番では 0 推奨）

起動・使い方（主要スクリプト）
----------------------------
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用し MockBrokerClient を選択
    - data/stop_requested.flag が存在すると起動しない/停止する
    - data/execution.pid に PID を書き込む（設定により変更可）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録
    - stop_requested.flag を検知するとループ終了

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db でデータベースパスを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / 研究系（ライブラリ関数として利用）
  - ニュースセンチメント付与:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...)  （conn は duckdb.connect(...)）
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

監視・停止フラグ
----------------
- 停止要求（run_execution/run_monitoring の外部停止）
  - data/stop_requested.flag: 存在を確認してプロセスを停止するトリガー
  - data/kill.flag: Kill Switch（KillSwitch クラス）によって書き込まれ、ExecutionEngine 停止の合図に使用
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアする（本番では 0 を推奨）

ログ
---
- ログは stdout とファイル（logs/<app_name>.log）に出力されます。ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されています。
- ログローテーション: 日次、30 日分保持

ライブラリ / モジュールの使い方（簡易）
---------------------------------
- ポートフォリオ構築 API（純粋関数群）
  - kabusys.portfolio.select_candidates(...)
  - kabusys.portfolio.calc_equal_weights(...)
  - kabusys.portfolio.calc_score_weights(...)
  - kabusys.portfolio.calc_position_sizes(...)
  - kabusys.portfolio.apply_sector_cap(...)
  - kabusys.portfolio.calc_regime_multiplier(...)

- 研究・ファクター計算（DuckDB 接続を渡す）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

- 監視 DB 操作（直接使用する場合）
  - MonitoringDB（kabusys.monitoring.monitoring_db）で system_status / trade_logs / positions / risk_logs / dashboard を操作可能

プロジェクト構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数/自動 .env ロード/Settings
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor 起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py                  — ニュースセンチメント（OpenAI）
  - regime_detector.py           — マーケットレジーム判定
- monitoring/
  - monitoring_db.py             — SQLite 監視 DB 層
  - system_monitor.py            — システム状態・データ鮮度監視
  - trade_monitor.py             — (trade 関連監視) ※実装ファイルあり
  - risk_monitor.py              — ドローダウン・ポジション上限監視
  - kill_switch.py               — Kill Switch の管理
  - monitoring_engine.py         — 各 Monitor を束ねる
  - alert_manager.py             — (アラート通知) ※実装ファイルあり
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

データ / ログ
- data/                          — デフォルト DB / flag / pid 等を格納する想定ディレクトリ
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb
  - stop_requested.flag
  - kill.flag
  - execution.pid
- logs/                          — ログファイル保存先（LOG_DIR により変更可）

運用上の注意
------------
- .env は機密情報を含むため Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）稼働時は LOG_LEVEL / KILL_FLAG_CLEAR_ON_START / LINE 通知設定 等を慎重に確認してください（validate_config の live ガードあり）。
- OpenAI API を利用する機能は API 料金が発生します。レート制限や課金に注意して利用してください。
- run_execution/run_monitoring は stop flag（stop_requested.flag）や kill.flag の存在を参照して停止・制御します。これらのファイルは適切に管理してください。

その他
-----
詳細な実装や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクトに存在する前提でコードはそれに従った設計になっています。開発・運用の際は当該ドキュメントと併せて参照してください。

--- 
質問や README に追加したい情報（例: 具体的な起動例、依存関係の pin された requirements.txt、追加の運用手順）があれば教えてください。必要に応じて README を拡張します。