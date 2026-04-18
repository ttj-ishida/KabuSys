README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコアライブラリです。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine: 発注実行・リスク管理・注文管理の実装（本番 / ペーパートレード両対応）
- Monitoring: システム稼働監視、取引監視、リスク監視、Kill Switch（停止フラグ）管理
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算、セクター制約やレジーム乗数
- Research: DuckDB を用いたファクター計算（モメンタム / バリュー / ボラティリティ等）や特徴量解析
- AI ユーティリティ: ニュース NLP によるセンチメント評価、レジーム判定（OpenAI API 経由）
- Tools: Paper Trading 検証レポート生成などのユーティリティスクリプト
- 設定ユーティリティ: .env を対話式で作成するウィザードや設定検証 CLI

主な設計方針:
- DuckDB + SQLite を使い分け（分析用 DuckDB、監視・履歴は SQLite）
- 本番 / ペーパートレードを明確に分離（PAPER_TRADING 用の専用 DB 等）
- 外部 API 呼び出し（OpenAI など）は失敗時にフォールバックしフェイルセーフを重視

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading.db に記録
  - プロセス優先度の設定、PID ファイル管理、停止フラグの検出
- 監視ループ起動スクリプト（run_monitoring.py）
  - システム状態・データ鮮度・取引状況の定期チェック、Monitoring DB への記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整
- MonitoringDB（SQLite）による永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
- RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch によるアラート発生と停止フラグ書き込み
- Portfolio モジュール（候補選定 / 等金額・スコア加重 / リスクベースの株数算出 / セクター制約）
- Research モジュール（DuckDB 接続を受け取りファクター計算・将来リターン・IC 計算）
- AI モジュール
  - news_nlp.score_news: ニュースを LLM に送り銘柄別センチメントを ai_scores テーブルへ保存
  - regime_detector.score_regime: ma200 とマクロニュースの LLM 評価を組み合わせて日次レジーム判定
- ユーティリティ
  - config_setup.py: .env の対話的生成
  - validate_config.py: .env / config/*.yaml の簡易検証
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成

要件（主な依存）
----------------
- Python 3.9+
- パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite は標準ライブラリで利用
- いくつかのモジュールは外部の BrokerClient 実装等に依存（実行時に適切な設定が必要）

セットアップ手順
----------------
1. リポジトリをクローン/配置
   - 例: git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （開発用）PyYAML を使う場合: pip install pyyaml

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を設定してください。

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリの作成（任意）
   - デフォルトの DB / ログパスは data/ および logs/ 下に作成されます（ソフト的に自動作成される箇所もあります）。

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading: 発注は MockBrokerClient を使い data/paper_trading.db に記録
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring は常に本番 sqlite_path を使用
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR (デフォルト: logs/)
- KILL_FLAG_CLEAR_ON_START (0/1)
- PID_FILE_PATH / KILL_FLAG_PATH — 実行中プロセス管理に使用
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

起動・使い方
-------------
- Execution Engine を起動（本番 or paper_trading は KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution

  実行時仕様（概要）:
  - プロセス優先度を "high" に設定し起動
  - paper_trading の場合は paper_sqlite_path（data/paper_trading.db など）を使用して DB を分離
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止信号を送れます
  - PID ファイル: data/execution.pid（デフォルト）

- Monitoring を起動:
  - python -m kabusys.run_monitoring

  仕様:
  - MONITOR_POLL_INTERVAL で指定した秒数でポーリング（デフォルト 60）
  - 監視ログは sqlite_path（data/monitoring.db）に記録
  - 停止フラグ: data/stop_requested.flag を検知するとループ終了

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- .env の初期作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

プログラム的 API（例）
---------------------
- AI スコアリング（プログラムから呼ぶ場合）:
  - from kabusys.ai import score_news
  - result_count = score_news(duckdb_conn, target_date, api_key="…")

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="…")

- Portfolio / Research の各関数はモジュールとしてインポートして利用可能:
  - from kabusys.portfolio import select_candidates, calc_position_sizes, apply_sector_cap
  - from kabusys.research import calc_momentum, calc_value, calc_volatility

ログと監視
-----------
- ログ:
  - デフォルトでは logs/ ディレクトリに日次ローテートされるログファイルを出力します（例: logs/execution.log, logs/monitoring.log）
  - ログレベルは LOG_LEVEL で調整可能

- Kill Switch / 停止フラグ:
  - KillSwitch は条件（ドローダウン超過やポジション上限など）を満たすと data/kill.flag を書き込みます
  - ExecutionEngine は data/stop_requested.flag や execution.pid を使って制御します

ディレクトリ構成（主なファイル）
------------------------------
以下は主要なパッケージ構成の抜粋です（src/kabusys 下）。

- kabusys/
  - __init__.py
  - config.py                   — 環境変数・.env の自動読み込みと Settings
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照されるが省略)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照されるが省略)
  - utils/
    - logging_setup.py
    - process_priority.py

開発者向けメモ / 注意点
----------------------
- Monitoring の init_monitoring_db は冪等実行され、既存 DB に対して必要なマイグレーション（カラム追加等）も行います。
- Monitoring は「環境にかかわらず」Settings.sqlite_path（= data/monitoring.db など）を使用する設計です（監視データは本番 DB を用いるため注意）。
- paper_trading モードは本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API を使う箇所（news_nlp / regime_detector）は API の失敗・レート制限を考慮したリトライ実装がされていますが、API キーやネットワーク環境の準備を行ってください。
- 実行スクリプトは process priority を "high" に変更しようとします（psutil が必要）。権限がない場合は警告が出てスキップされます。

トラブルシューティング
----------------------
- .env があるにもかかわらず環境変数が読み込まれない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が 1 に設定されていないか確認
  - プロジェクトルートの判定は .git または pyproject.toml を基準に行われます
- ログファイルが作れない場合:
  - 権限やディスク残量、LOG_DIR の設定を確認。ファイル出力に失敗しても標準出力（stdout）にはログが出ます。
- OpenAI など API 呼び出しでエラーが出る場合:
  - OPENAI_API_KEY が設定されているか確認し、ネットワーク接続とレート制限状況を確認してください。

最後に
-----
この README はコードベース（src/kabusys 以下）の主要な機能と使い方を要約したものです。さらに詳しい設計や仕様はソース内の docstring やコメント（PortfolioConstruction.md 等の外部ドキュメント参照箇所）を参照してください。質問や特定の使い方のサンプルが必要であればお知らせください。