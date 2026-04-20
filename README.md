KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・研究・監視ユーティリティ群を含む Python パッケージです。
README はコードベース（src/kabusys 以下）を元に作成しています。

概要
----
KabuSys は次を目的としたモジュール群を提供します。

- 自動発注実行エンジン（ExecutionEngine）
- 実行／注文／リスクの監視（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- AI を用いたニュースセンチメント / 市場レジーム判定（OpenAI）
- 開発運用向けツール（設定ウィザード、設定検証、ペーパートレード検証レポート 等）

主な機能一覧
--------------
- Execution:
  - run_execution.py: ExecutionEngine を起動（本番/ペーパー切替）。
  - BrokerClientFactory による本番/モックブローカー切替。
  - 発注履歴・ポジションは SQLite / DuckDB と連携。

- Monitoring:
  - run_monitoring.py: SystemMonitor のポーリングループを実行。
  - MonitoringEngine による System / Trade / Risk モニタの定期実行。
  - kill.flag による外部からの停止指令（Kill Switch）。
  - 監視ログ永続化（SQLite via monitoring_db.py）。

- Portfolio construction:
  - 銘柄選定（select_candidates）
  - 重み計算（等分・スコア加重）
  - 単元株丸め・リスクベースの数量算出（calc_position_sizes）
  - セクター上限・レジーム調整（apply_sector_cap, calc_regime_multiplier）

- Research:
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン／IC 計算、ファクター統計サマリ

- AI:
  - ニュースのセンチメントスコアリング（OpenAI 使用）: ai.news_nlp.score_news
  - マーケットレジーム判定（ma200 + マクロニュース LLM 合成）: ai.regime_detector.score_regime

- ツール:
  - config_setup.py: .env の対話式ウィザード生成
  - validate_config.py: 環境変数・config/*.yaml の事前検証
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... (リポジトリ URL)

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install duckdb psutil openai
   - 追加（任意）: PyYAML（config YAML 検証用）
     - pip install pyyaml

   （requirements.txt がない場合は上記を個別にインストールしてください）

4. データ/ログ用ディレクトリの作成（多くは自動作成されますが事前準備する場合）
   - mkdir -p data logs

5. 環境変数設定 (.env)
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env ファイルを手動作成（例）:
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0

   - Settings モジュールは自動で .env/.env.local をプロジェクトルートから読み込みます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

使い方（主要スクリプト）
-----------------------

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 役割:
    - Settings に基づき本番/ペーパー DB を選択
    - BrokerClient を生成（paper_trading 環境では MockBrokerClient を使用）
    - ExecutionEngine を別スレッドで起動し PID ファイルを書き込む
    - data/stop_requested.flag を作成すると安全に停止

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します
  - data/stop_requested.flag を検知すると監視ループを終了

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に生成・更新します（--env-file でパス指定可）

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（デフォルト data/paper_trading.db）

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY: OpenAI を使う機能で必要（ai.news_nlp, ai.regime_detector）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_PATH: kill.flag のパス（Settings により data/kill.flag がデフォルト）
- PID_FILE_PATH: execution.pid のパス（Settings デフォルトは data/execution.pid）

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では .env の管理・ LINE 通知設定 等を十分に確認してください。validate_config は live 環境に関する注意を出します。
- Kill Switch（data/kill.flag）を利用すると ExecutionEngine を停止できます。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（自動クリアされてしまうため）。
- run_execution は paper_trading モードではペーパートレード専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と分離します。
- OpenAI API 利用部分は API 利用制限・コストに注意してください。API 呼び出しはリトライ・バックオフを実装していますが、キー漏洩防止・利用料管理が必要です。
- ログは logs/<app_name>.log に日次ローテートされます（logs ディレクトリが作成できない場合はコンソール出力のみ）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルと役割の一覧（抜粋）。

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    （ExecutionEngine と発注周りの実装）

- kabusys/monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化レイヤ
  - system_monitor.py — システム / データ鮮度監視
  - trade_monitor.py — 発注/約定の整合性監視（省略表示）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - monitoring_engine.py — 各モニタの束ねとアラート発生

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・スケーリング
  - risk_adjustment.py — セクター上限・レジーム乗数

- kabusys/research/
  - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py — forward returns / IC / 統計サマリ

- kabusys/ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — レジーム判定（MA200 + LLM 合成）

- kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- kabusys/utils/
  - logging_setup.py — ログ設定ユーティリティ（console + 日次ローテート）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補足（開発・テスト）
-------------------
- DuckDB はローカルの分析 DB として使われます。prices_daily / raw_financials 等のテーブルが必要です（データ準備は別途）。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必要です。テスト時はモック（unittest.mock）で _call_openai_api を差し替えてください。
- validate_config は PyYAML が入っていれば config/*.yaml のパース検証も行います。未インストールだと YAML の検証はスキップされますが警告が出ます。
- process_priority は psutil を利用します。適切な権限がない環境では設定が失敗して警告が出ますが起動は継続します。

最後に
------
この README は src/kabusys の実装に基づいて作成しています。各モジュールの詳細な挙動や追加オプションは該当ソースコードの docstring / コメントを参照してください。仕様変更や拡張を行う際は config/*.yaml・.env の取り扱いと本番/ペーパー切替の整合性に注意してください。