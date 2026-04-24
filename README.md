README — KabuSys
=================

概要
----
KabuSys は日本株自動売買システムのライブラリ／実行スクリプト群です。  
このリポジトリには、戦略のためのファクター計算・ポートフォリオ構築、実際の発注エンジン、監視・リスク判定、LLM を使ったニューススコアリング、解析用ツールなどが含まれます。

主な特徴
--------
- 戦略研究用モジュール（ファクター計算、特徴量解析、IC 計算など）
- ポートフォリオ構築（候補選定、重み算出、セクター制限、ポジションサイジング）
- ExecutionEngine（発注フロー、リスク管理、order/reconciler 周りの実装を想定）
- Monitoring（システム状態・注文ログ・リスクを定期チェック、Kill Switch による停止）
- Paper Trading を本番 DB と分離して実行可能
- OpenAI（gpt-4o-mini）を利用したニュース NLP と市場レジーム判定
- 各種 CLI：.env ウィザード、設定検証、Paper Trading の検証レポート生成

前提依存関係（代表例）
---------------------
主に以下のパッケージを使用します（実際の requirements.txt に依存してください）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証時に任意）

主要環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant / partial / never / reject）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR — ログレベル・ログ格納ディレクトリ
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"1"=有効、デフォルト 0）

セットアップ手順
----------------
1. リポジトリをクローンして仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールします（例）:
   - pip install duckdb psutil openai pyyaml

   ※ 実際は requirements.txt がある場合はそれを使用してください。

3. .env の初期作成:
   - python -m kabusys.config_setup
     - 対話式ウィザードで必須の環境変数（トークン等）を設定します。
   - 生成後、python -m kabusys.validate_config で検証してください。
     - 警告もエラー扱いにしたい場合は --strict を指定できます。

使い方（主要スクリプト）
------------------------

- 設定ウィザード（.env を対話式作成/更新）
  - python -m kabusys.config_setup
  - オプション: --env-file を指定して別パスの .env を生成可能

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は monitoring DB（Settings.sqlite_path）に対して実行。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込み、本番 DB と分離します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB は env の PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / 研究機能（プログラム呼び出し）
  - kabusys.ai.score_news — ニュース NLP によるスコア付与（DuckDB 接続と target_date を渡す）
  - kabusys.ai.score_regime — レジーム判定（DuckDB 接続と target_date を渡す）
  - kabusys.research.calc_momentum 等 — DuckDB 接続を渡してファクター計算

運用上のファイル・フラグ
----------------------
- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルを検知すると安全に終了します。
- data/kill.flag
  - KillSwitch が書き込むことで ExecutionEngine に停止命令を送るためのフラグ（存在すれば停止）。
- data/execution.pid
  - run_execution が作成する PID ファイル（場所は Settings.pid_file_path で変更可能）。
- logs/<app_name>.log
  - ログはデフォルト logs ディレクトリに出力され、日次ローテート（30日分保持）。LOG_DIR で変更可能。

停止・クリア
-------------
- ExecutionEngine を停止したい（運用者発動の Kill Switch）場合:
  - data/kill.flag を作成（KillSwitch が存在するか判定）。KillSwitch.write は理由を含めてファイルを作成します。
- 停止フラグを手動で立てて run_execution/run_monitoring を終了させたい場合:
  - data/stop_requested.flag を作成
- 起動時に kill.flag を自動クリアしたくない場合:
  - KILL_FLAG_CLEAR_ON_START を "0"（デフォルト）にしてください。 本番環境ではクリアしない運用を推奨します。

ディレクトリ構成（抜粋）
----------------------
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文系監視: ファイル内の他実装を参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — （アラート送信管理: 実装参照）
  - execution/ (発注関連の実装群)
  - portfolio/ (ポートフォリオ構築アルゴリズム)
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores へ書き込み
    - regime_detector.py — ma200 + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール

運用上の注意点 / ベストプラクティス
----------------------------------
- .env は絶対に Git にコミットしないでください（config_setup でヘッダに注意書きがあります）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- Monitoring は常に（環境にかかわらず）Settings.sqlite_path（監視 DB）を使用します。Paper Trading の発注記録は paper_trading DB に分離されます（KABUSYS_ENV=paper_trading 時）。
- OpenAI を使う部位を運用で使う場合は API キーと使用量に注意してください（レート制限・コスト）。
- ログディレクトリが作成できない場合はファイル出力が無効化されコンソール出力のみになります。LOG_DIR を環境で調整してください。
- duckdb / sqlite のファイルパスは環境変数で上書き可能です。運用環境の適切なパスを設定してください。

付録：よく使うコマンド例
-----------------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視開始:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン開始:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

必要に応じて README をプロジェクトの運用ルールやデプロイ手順に合わせて拡張してください。