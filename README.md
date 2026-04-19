KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視ライブラリ群です。本リポジトリはトレーディングエンジン（ExecutionEngine）、監視モジュール（Monitoring）、ポートフォリオ構築、ファクター計算、AI を使ったニュース解析などのコンポーネントを含みます。設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API 失敗時は安全側へフォールバック）」を重視しています。

主な機能
---------
- 実行エンジン起動スクリプト
  - `run_execution.py`：ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し DB を分離。
- 監視・アラート
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動。CPU/メモリ/ディスク監視、データ鮮度チェック、プロセス生存監視など。
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager による総合監視と自動停止機構。
- 環境設定支援
  - `config_setup.py`：対話式で `.env` を生成・更新するウィザード。
  - `validate_config.py`：起動前に環境変数や config/*.yaml の検証を行う CLI。
- 研究・ファクター計算
  - `research.factor_research`：モメンタム、バリュー、ボラティリティ等のファクター計算（DuckDB を使用）。
  - `research.feature_exploration`：将来リターン、IC、統計サマリー等のユーティリティ。
- ポートフォリオ構築
  - 候補選定、重み計算（等分・スコア加重）、セクター制限、ポジションサイズ決定（単元株丸め・集約キャップ）。
- AI（OpenAI）連携
  - `ai.news_nlp`：ニュース記事を LLM（gpt-4o-mini）でセンチメント評価し `ai_scores` に書き込み。
  - `ai.regime_detector`：ETF とマクロニュースを組み合わせて市場レジームを判定。
- 運用ツール
  - `tools.paper_verification_report`：ペーパートレード DB を集計して検証レポートを生成。

セットアップ手順
----------------
1. リポジトリをクローンして Python 仮想環境を作る（推奨）。
   - python >= 3.9（コードは型アノテーション等を使用）
   - 仮想環境例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - 最低限の依存（例）:
     - duckdb
     - psutil
     - openai
     - （推奨）PyYAML（config 検証で使用）
   - pip install duckdb psutil openai PyYAML

3. 環境変数 / .env の用意
   - 対話式で作成する:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（抜粋）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（分離用）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR など
   - 自動ロード:
     - ルートに `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数が優先）。
     - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗にするには `--strict` を指定。

使い方（主要コマンド）
--------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH または data/paper_trading.db) を使用します。本番 DB と完全に分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。エンジンは PID ファイル（デフォルト: data/execution.pid）を作成します。
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で DB を指定できます。
- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定した上で、該当モジュールの関数を呼び出してください（スクリプト的な CLI は提供されていないため、実行は Python からの関数呼び出しが想定されます）。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime

運用上の注意
------------
- ペーパートレードと本番の DB は分離されています。ペーパートレード時は `KABUSYS_ENV=paper_trading` を使用してください。
- Kill Switch:
  - RiskMonitor が閾値を超えた場合 `data/kill.flag` が書き込まれ、ExecutionEngine に停止シグナルを送ります（KillSwitch）。
  - `KILL_FLAG_CLEAR_ON_START` が `1` のときは起動時に自動で kill.flag をクリアしますが、本番では `0` を推奨します。
- ログ:
  - デフォルトは `logs/` ディレクトリに日次ローテーションで保存されます（`kabusys.utils.logging_setup`）。
- OpenAI 使用:
  - API エラーやレートリミットに対してはリトライとフォールバックが実装されていますが、API キー管理・コストに注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
（リポジトリのルートに `src/kabusys/` が置かれる想定。以下は主要ファイル/モジュールの抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor, alert_manager 等のファイル)
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
  - execution/               — Execution 関連の実装（BrokerFactory, Engine, OrderManager 等）
  - data/                    — 実行時に作成されるファイル群（例: monitoring.db, paper_trading.db, kill.flag, execution.pid）
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （上記 YAML は存在しない場合があるため validate_config は警告を出します。生成スクリプトがある場合はそれを使ってください）

よく使う環境変数（抜粋）
-----------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用）
- LOG_LEVEL: DEBUG/INFO/...
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）

サポート・拡張ポイント
---------------------
- DuckDB を使ったバッチ的なファクター計算・研究機能は拡張しやすい設計です（SQL と組み合わせて新しいファクターを追加可能）。
- Broker クライアントまわりは Factory パターンで切り替え可能（実際のブローカー実装と Mock を差し替え）。
- ロギング、プロセス優先度設定、CPU アフィニティなど実稼働向けのユーティリティを提供。

ライセンス / バージョン
---------------------
- パッケージバージョンは `kabusys.__version__` を参照してください（現在: 0.1.0 相当のコードベース）。

補足
----
- 本 README はコードベース（src 以下）を読んでまとめた説明です。詳細な実装や追加の起動オプションは該当ファイルの docstring / コメントを参照してください。
- 実運用前に `python -m kabusys.validate_config` で設定を確認し、テスト環境で動作検証を行ってください。