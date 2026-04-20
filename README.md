KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システムのコアライブラリ群です。
主要コンポーネント（ExecutionEngine / Monitoring / Portfolio構築 / Research / AI連携）を含み、
ローカル開発からペーパートレード、本番運用までを想定しています。

要点
- Pythonパッケージとして提供されるモジュール群（src/kabusys 以下）
- SQLite / DuckDB をデータ永続化に利用
- OpenAI（gpt-4o-mini）を用いたニュースNLP・レジーム判定機能を含む
- プロセス優先度設定・統一ログ設定・監視/キルスイッチ機能を搭載

機能一覧
--------
主な機能（モジュール別）
- 起動スクリプト
  - run_execution.py: ExecutionEngine（発注エンジン）起動。KABUSYS_ENV=paper_trading で MockBroker を利用し DB を分離。
  - run_monitoring.py: SystemMonitor ポーリングループ（監視）起動。MONITOR_POLL_INTERVAL で間隔変更可能。

- 設定管理 / ツール
  - config.py: 環境変数/.env の読み込み・Settings API
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml のチェック CLI

- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder: 候補選定・重み計算
  - portfolio.position_sizing: 発注株数計算（単元丸め、aggregate cap）
  - portfolio.risk_adjustment: セクター上限・レジーム乗数

- リサーチ
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - research.feature_exploration: 将来リターン・IC・統計サマリー

- AI（OpenAI）連携
  - ai.news_nlp: ニュース記事をまとめて LLM でセンチメント評価 → ai_scores に格納
  - ai.regime_detector: ma200 とマクロニュースの LLM 評価を合成して市場レジームを判定 → market_regime に格納

- 監視（Monitoring）
  - monitoring.monitoring_db: SQLite による監視ログ層（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring.system_monitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存確認
  - monitoring.trade_monitor: 発注ログの整合性チェック（滞留注文、異常約定など）
  - monitoring.risk_monitor: ドローダウンやポジション数上限の監視・リスクログ記録
  - monitoring.kill_switch: しきい値を超えた場合 data/kill.flag を作成して ExecutionEngine に停止指示
  - monitoring.monitoring_engine: 各モニタとアラート管理を組み合わせたポーリングエンジン

- その他ユーティリティ
  - utils.logging_setup: StreamHandler + 日次ローテートファイルハンドラをルートロガーに設定
  - utils.process_priority: Windows / POSIX を吸収したプロセス優先度 / CPU affinity 設定

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>
   - ソースは src/ 以下にあることを前提に記載しています。

2. Python 環境（仮想環境）を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 注意: requirements.txt は含まれていないため主要依存を例示します。
     - pip install duckdb psutil openai
     - PyYAML は config YAML のパース確認用（任意）: pip install pyyaml
   - sqlite3 は標準ライブラリ（別途不要）

4. .env を作成
   - 対話式ウィザード:
     - PYTHONPATH=src python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他（例）:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - OPENAI_API_KEY（AI機能利用時）

5. 設定検証
   - PYTHONPATH=src python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリ
   - デフォルトで data/ や logs/ を作成します（必要に応じて手動作成可）。
   - Execution / Monitoring の PID / フラグは data/ 以下に保存されます（例: data/execution.pid, data/kill.flag, data/stop_requested.flag）。

使い方（起動・実行例）
---------------------
※ src/ を PYTHONPATH に含める（またはパッケージインストール後に -m で実行）

- ExecutionEngine を起動
  - PYTHONPATH=src python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBroker を用い data/paper_trading.db に記録（本番 DB と分離）
  - 実行前に data/stop_requested.flag が存在する場合は起動しません

- Monitoring を起動
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視データにアクセスします

- 設定ウィザード（.env 作成）
  - PYTHONPATH=src python -m kabusys.config_setup

- 設定検証
  - PYTHONPATH=src python -m kabusys.validate_config
  - PYTHONPATH=src python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で上書き可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI 機能（プログラムから利用）
  - ニュースセンチメント付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

停止・Kill フラグ
-----------------
- 実行中プロセスの停止:
  - data/stop_requested.flag を作成すると run_* のループが検知して停止します（run_execution/run_monitoring が参照）。
- Kill Switch（監視側が自動的に発動）
  - 監視でドローダウン等の閾値を超えた場合、monitoring.kill_switch が data/kill.flag を書き込み、ExecutionEngine 側がこれを検出して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

主要環境変数（抜粋）
---------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- LOG_LEVEL, LOG_DIR: ログ関連

簡単な .env の例
-----------------
（config_setup で自動生成することを推奨）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成（主要ファイル）
-------------------------------
src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py
    run_execution.py
    run_monitoring.py

    utils/
      __init__.py
      logging_setup.py
      process_priority.py

    monitoring/
      __init__.py
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py  (アラート関連: 実装によっては外部通知連携)

    execution/
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
      (実行系の詳細実装)

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    ai/
      news_nlp.py
      regime_detector.py
      __init__.py

    monitoring/
      tools and DB helpers...
    tools/
      paper_verification_report.py

（注）上記はこのコードベースに含まれる主要ファイルの抜粋です。

設計上の注意点 / 運用メモ
------------------------
- 本番（KABUSYS_ENV=live）では各種設定（LINE 通知、KILL_FLAG_CLEAR_ON_START 等）に注意してください。validate_config に本番向けガードがあります。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定します（psutil を使用）。権限により設定に失敗する場合がありますがログに記録して継続します。
- DuckDB / SQLite のパスは .env で調整してください。ペーパートレードは専用の SQLite を使用して本番 DB と分離します。
- OpenAI 呼び出し部分は外部 API 依存のためリトライ・フォールバック処理を実装済みですが、APIキーやレートに注意してください。

開発・デバッグ
---------------
- ログは標準出力 + logs/<app_name>.log（デフォルト）に出力されます。LOG_DIR / LOG_LEVEL によって調整可能です。
- 単体モジュールは PYTHONPATH=src 下で python -m で実行可能です。外部接続（kabu API / OpenAI）をモックして単体テストを作成すると安全です。
- config.py はプロジェクトルート（.git または pyproject.toml）を自動検出して .env を自動読込します。自動読込を無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サポート / 貢献
----------------
- バグや改善提案は Issue を立ててください。Pull Request は歓迎します。
- 重要な変更（DB スキーマ、挙動変更など）はドキュメント・マイグレーション手順を同梱してください。

以上。何か特定機能についての詳細ドキュメント（API 使用例、DB スキーマ、デプロイ手順など）が必要であれば教えてください。