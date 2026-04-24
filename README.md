README.md

KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした Python コードベースです。本リポジトリには以下の主要機能が含まれます。

- 注文実行エンジン（ExecutionEngine）と発注ラッパ
- 監視コンポーネント（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
- ファクター計算・特徴量探索（Research）
- ニュースの NLP によるセンチメント評価（OpenAI API 経由）
- Paper Trading 検証レポート生成ツール
- 環境設定ウィザード・設定検証ツール
- 一貫したログ設定・プロセス優先度ユーティリティ

主な特徴
--------
- 実行環境を KABUSYS_ENV（development / paper_trading / live）で切替可能
- Paper Trading は本番 DB と分離（data/paper_trading.db を使用）
- DuckDB を使った分析向けデータレイク（デフォルト: data/kabusys.duckdb）
- SQLite を監視・ログ用 DB として利用（デフォルト: data/monitoring.db）
- OpenAI（gpt-4o-mini など）を使ったニュース NLP / レジーム判定機能
- 監視ループは環境変数でポーリング間隔を調整可能（MONITOR_POLL_INTERVAL）
- kill.flag による安全停止 (Kill Switch)、stop_requested.flag によるプロセス停止シグナル
- ログはコンソール + 日次ローテーションファイル（logs/<app_name>.log）に出力

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 環境
   - 推奨: 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 直接インストールする場合の最低依存例:
     - pip install duckdb psutil openai pyyaml

   （注）openai, duckdb, psutil, PyYAML などが一部機能で必要です。テストや開発用の軽量依存は別途管理してください。

4. 環境変数の初期作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - .env を対話的に作成／更新します。
   - 重要項目:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live
     - OPENAI_API_KEY（ニュース NLP / レジーム判定を使う場合）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合は --strict を付ける:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要なら）
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite: data/monitoring.db
     - Paper trading DB: data/paper_trading.db
     - logs/（ログ出力ディレクトリ）
   - これらの親ディレクトリは setup ロジックや logging 設定で自動作成されますが、パーミッション等を確認してください。

使い方（主要スクリプト）
--------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話的に生成 / 更新します。
    - --env-file オプションで保存先を指定可能。

- 設定検証 CLI
  - python -m kabusys.validate_config
    - 起動前に .env と config/*.yaml の整合性をチェック。
    - --strict をつけると警告もエラー扱いで exit(1) に。

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
    - 監視は常に本番 sqlite_path（Settings.sqlite_path）を参照します（環境に関わらず）。
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループを抜けます。

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 実行中の停止は data/stop_requested.flag の作成で検知して停止します。
    - エンジン PID は data/execution.pid に出力されます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
    - レポートは稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定を出力します。

- ライブラリ的利用
  - portfolio, research, ai などのモジュールは import して計算関数を利用できます。
    - 例: from kabusys.portfolio import select_candidates, calc_equal_weights
    - 例: from kabusys.research import calc_momentum, calc_volatility
    - 例: from kabusys.ai import score_news

重要な環境変数（主なもの）
------------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY：OpenAI API を使う機能で必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）※paper_trading 環境で使用
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR（ログ保存先、デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。1=クリア。production では 0 推奨）

ログと監視
----------
- ログは setup_logging() により stdout と logs/<app_name>.log（日次ローテーション）へ出力されます。
- Monitoring 系は MonitoringDB（SQLite）へ履歴を永続化します（system_status, trade_logs, positions, risk_logs, dashboard）。
- KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（flag は手動削除または起動時の自動クリア設定で消去）。

停止フラグ
--------
- 停止ループ: data/stop_requested.flag を作成すると run_monitoring / run_execution のループまたはスレッドが安全に停止します。
- Kill Switch: KillSwitch が判定すると data/kill.flag を生成し ExecutionEngine 停止を誘発します（実行前に KILL_FLAG_CLEAR_ON_START=1 を使うと自動でクリア可能だが本番では推奨されません）。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_monitoring.py            — 監視ループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - data/                        — （データファイル: sqlite, duckdb など 実行時に生成）
  - logs/                        — ログファイル
  - utils/
    - logging_setup.py           — 共通ログ設定
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

ドキュメント / 設計ノート
-----------------------
- 各モジュールの docstring に設計方針・参照先（PortfolioConstruction.md, StrategyModel.md 等）の要点が記載されています。実装の詳細・理論的背景は該当ドキュメントを参照してください（別途リポジトリ内に含めている可能性があります）。

開発・テストに関する注意
------------------------
- 自動で .env を読み込む仕組みが有効になっています。テスト時に自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を使うユニットテストは外部 API に依存しないように _call_openai_api をモックしてテストすることが想定されています。
- DuckDB / SQLite への書き込みは実データに影響を与えるため、テスト時は tmp ディレクトリや一時 DB を使用してください。

よくある操作例
--------------
- .env を作成して検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 監視の手動実行（1 回のみテスト）:
  - Python REPL や小さなスクリプトから MonitoringEngine を組み立て run_once() を呼ぶことが可能（unittest 用フックあり）。

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 追加情報
-------------------
- リポジトリ内の docstring を参照してください。各モジュールのトップに使用方法や注意点が記載されています。
- 依存関係や実行環境の詳細が必要な場合は requirements.txt を確認または作成し、環境を固定してください。

ライセンス
---------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE ファイルを参照してください（存在しない場合はプロジェクト管理者に確認してください）。

以上。README の補足や特定の操作手順（例: Docker 化、CI 設定、詳細な設定項目の説明など）をご希望の場合は、用途に応じて追加ドキュメントを作成します。