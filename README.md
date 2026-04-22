KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を行うコードベースです。  
主に次を提供します：

- 実運用向けの ExecutionEngine 起動スクリプト（発注・リスク管理・再整合）
- システム稼働・注文・リスクを記録・監視する Monitoring
- Paper Trading 用の分離された DB・検証レポート生成ツール
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）ユーティリティ群
- DuckDB を使ったファクター計算・リサーチ機能
- OpenAI を利用したニュース NLP / レジーム判定モジュール（API キー必須）
- 設定ウィザード・設定検証 CLI、統一ログ設定ユーティリティ など

機能一覧
--------
主な機能（抜粋）:

- 実行系
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV による paper/live の切替）
  - ExecutionEngine は paper_trading 時に MockBroker を使い DB を分離
- 監視系
  - run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringDB: SQLite に system_status / trade_logs / positions / risk_logs / dashboard を保持
  - KillSwitch: リスク基準で data/kill.flag を書き込み ExecutionEngine 停止をトリガ
  - RiskMonitor / TradeMonitor / SystemMonitor / MonitoringEngine：アラート判定・通知呼び出しポイント
- ツール
  - config_setup: .env を対話的に作成/更新
  - validate_config: .env / config/*.yaml の事前検証（--strict オプションあり）
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）
- 研究・補助
  - research.factor_research, research.feature_exploration: DuckDB 上のファクター計算・IC 等
  - portfolio.*: 候補選定、重み付け、単元丸めを行う純粋関数群
  - ai.news_nlp / ai.regime_detector: OpenAI を用いたニュースセンチメント / 市場レジーム判定

セットアップ手順
----------------

前提
- Python 3.9+（開発環境により要調整）
- DuckDB, psutil, OpenAI SDK などの依存パッケージが必要

推奨手順（UNIX 系の例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）PyYAML があると validate_config が config/*.yaml を検証できます: pip install pyyaml

3. ディレクトリ作成（ログ・DB 保存用）
   - mkdir -p data logs

4. .env の初期作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

5. 設定検証
   - python -m kabusys.validate_config
   - 本番準備では --strict オプションを推奨: python -m kabusys.validate_config --strict

注意点
- .env の自動ロード: プロジェクトルート（.git または pyproject.toml を基準）を検出すると
  自動的に .env, .env.local を読み込みます（ただし OS 環境変数は優先）。
  自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Paper Trading は本番 DB と分離：
  - デフォルト本番 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定モード）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（logs 保存先）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視・停止制御）

使い方（実行例）
----------------

一般的な起動・停止方法：

- 実行エンジン起動（デフォルト環境設定に従う）
  - python -m kabusys.run_execution
  - paper_trading モードで起動する場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- 停止方法（Graceful）
  - プロジェクトルート/data/stop_requested.flag を作成すると run_monitoring/run_execution は検知して終了します
  - KillSwitch が条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine の停止トリガになります
  - run_execution は実行中に _EXECUTION_PID (data/execution.pid) を使ってプロセス管理する設計です

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL とする）: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ライブラリとしての利用例
- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
- 研究用ファクター計算（DuckDB コネクションが必要）:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
- ニュース NLP（OpenAI API キーが必要）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

ログ
---
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテート）に出力されます
- setup_logging 関数でログ設定を統一しており、各起動スクリプトは最初に呼び出しています
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/

ディレクトリ構成（主要ファイル）
----------------------------
以下は src/kabusys 配下の主要モジュールと目的の簡単な一覧です。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading の DB 分離あり）
- config.py
  - 環境変数読み込み・Settings クラス（.env 自動ロード、バリデーション）
- config_setup.py
  - 対話式 .env 作成ウィザード
- validate_config.py
  - 起動前チェック CLI（環境変数・config YAML チェック）
- tools/paper_verification_report.py
  - Paper Trading 検証レポート生成ツール
- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・読み書きラッパー
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py (監視周りの各種コンポーネント)
- execution/
  - ExecutionEngine, OrderManager, RiskManager, Reconciler, broker_factory など（発注・リスク制御）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（純粋関数群）
- research/
  - factor_research.py, feature_exploration.py（DuckDB ベースのファクター・解析）
- ai/
  - news_nlp.py（ニュースセンチメント→ai_scores）
  - regime_detector.py（市場レジーム判定）
- utils/
  - logging_setup.py（ログ初期化）
  - process_priority.py（プロセス優先度 / CPU affinity 設定）
- data/
  - （実行時に生成するディレクトリ。DB・PID・flag ファイルを置く）
- logs/
  - ログファイル出力先（自動生成）

開発・拡張時の注意
------------------
- DuckDB 接続は読み取り重視。research/ai の処理は DB の整合性や日時フィルタに注意（ルックアヘッド禁止設計）。
- OpenAI 関連は API エラーやレート制限のリトライ処理を入れていますが、API キー・コストに注意して運用してください。
- 本番（KABUSYS_ENV=live）では kill/kill_flag 等の設定を慎重に扱い、LOG_LEVEL 等も適切に設定してください。
- .env を絶対にバージョン管理にコミットしないでください（config_setup.py のヘッダにも明記あり）。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = 0.1.0
- ライセンス情報はリポジトリのトップレベルにある LICENSE（存在する場合）を参照してください。

問い合わせ / 開発
-----------------
- 実装詳細の確認や機能追加はコード内ドキュメント（docstrings）・コメントを参照してください。
- 新しい config/*.yaml を追加した場合は validate_config での検証処理を更新してください。

以上が簡潔な導入・操作ガイドです。必要であれば各モジュールの使い方（API 参照や具体的な例）を追記します。