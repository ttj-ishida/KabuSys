KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視ツール群です。  
モジュールは大きく分けて以下を提供します。

- エンジン実行（ExecutionEngine）: 発注・約定管理・リスク制御
- 監視（Monitoring）: システム状態・滞留注文・リスク監視と Kill Switch
- ポートフォリオ構築: 候補選定、配分、ポジションサイズ計算
- リサーチ: ファクター計算・特徴量解析
- AI 支援: ニュースセンチメント (OpenAI) を使ったスコアリング / レジーム判定
- ユーティリティ: 環境設定ウィザード・設定検証・レポート出力 など

主要な設計方針として、DB（DuckDB / SQLite）を用いたオフライン処理と、
本番／ペーパートレードの分離、外部 API 呼び出しは明示的な設定（OpenAI 等）に依存することを挙げます。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番／ペーパー切替（KABUSYS_ENV）
  - Broker クライアントの抽象化（MockBroker をペーパーで使用）
  - リスク管理（最大ポジション比率・利用率・サーキットブレーカー等）
- Monitoring（run_monitoring.py / monitoring_engine）
  - CPU/メモリ/ディスク・プロセス生存確認・データ鮮度チェック
  - Trade / Risk モニタリング、Kill Switch（data/kill.flag）連携
  - ポーリングループ（環境変数 MONITOR_POLL_INTERVAL で間隔指定）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選出、等重／スコア加重配分、セクター上限適用、ポジションサイズ決定（単元丸め含む）
- リサーチ（research パッケージ）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で実行）
  - 将来リターン計算・IC（情報係数）や統計サマリ
- AI（ai パッケージ）
  - ニュースを OpenAI でスコアリングして ai_scores に格納（score_news）
  - マクロニュースと ETF MA を使った市場レジーム判定（regime_detector）
- ツール
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート出力（tools/paper_verification_report.py）
- ロギングユーティリティ（utils/logging_setup.py）
  - stdout と 日次ローテートファイル（logs/<app>.log）を統一して設定

セットアップ
----------
前提:
- Python 3.8+（プロジェクトの pyproject.toml を参照）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定 YAML を厳密にチェックする場合に任意）

一般的なインストール例:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージインストール（プロジェクトに requirements.txt があればそちらを使用）
   - pip install duckdb psutil openai pyyaml

環境変数（.env）
- プロジェクトは .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 最低限必須:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
- よく使う設定（抜粋）:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/...
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
  - PAPER_FILL_MODE: instant/partial/never/reject（ペーパートレード時の約定挙動）
  - KILL_FLAG_CLEAR_ON_START: 0/1（本番では 0 推奨）
- .env を手早く作る: python -m kabusys.config_setup

設定検証
-------
起動前に設定チェックを推奨:
- python -m kabusys.validate_config
- 警告もエラーにしたい場合: python -m kabusys.validate_config --strict

使い方（実行）
-------------
- ExecutionEngine を起動（通常日次実行など）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録されます。
  - 実行中の PID は data/execution.pid に書き出されます。停止は data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）で行います。

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL で秒単位に指定（デフォルト 60）
  - 監視は Settings に基づき本番 sqlite_path（SQLITE_PATH）を使用してログを永続化します。
  - run_monitoring は data/stop_requested.flag を検知すると終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定

- AI / レジーム機能
  - news_nlp.score_news ／ regime_detector.score_regime は DuckDB 接続と target_date を受け取り処理を行います。
  - 実行には OPENAI_API_KEY が必要（引数でも渡せます）。

停止 / Kill Switch / フラグ
--------------------------
- 停止リクエスト（run_execution / run_monitoring の安全な停止）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution は検知して停止処理を行います。
- Kill Switch（運用停止）:
  - monitoring の KillSwitch は条件成立時に data/kill.flag を書き込みます（Settings.kill_flag_path でパス指定可）。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を指定すると自動でクリアされますが、本番では 0 を推奨します。

ログ
----
- ログは utils/logging_setup.setup_logging によって統一的に設定されます。
- デフォルト出力:
  - コンソール: stdout
  - ファイル（ローテート）: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ログディレクトリは環境変数 LOG_DIR で変更可能（デフォルト logs/）。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読込・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装あり)
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 注意点
-------------
- DB の区別:
  - 監視用 SQLite（monitoring.db）とペーパートレード用 SQLite（paper_trading.db）は分離されています。KABUSYS_ENV=paper_trading の場合は paper DB を使用します。
- 自動 .env ロード:
  - プロジェクトルートを .git または pyproject.toml で自動検出して .env / .env.local を読み込みます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出し:
  - レート制限やネットワーク断に備えリトライ（指数バックオフ）を行いますが、API キー未設定や致命的なエラー時は機能がスキップされる設計です（フェイルセーフ）。
- 本番環境では KABUSYS_ENV=live の設定を慎重に行い、validate_config で警告や必須項目を確認してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

トラブルシューティング
-----------------------
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（警告が出ます）。
- DuckDB / SQLite のパスや親ディレクトリが存在しない場合は validate_config が警告します。起動時に自動作成されるケースがありますが、パーミッション等に注意してください。
- psutil による優先度設定や CPU affinity は環境によって権限が必要です（失敗した場合は警告を出して続行します）。

以上が本リポジトリの概要と基本的な使い方です。具体的な実行や運用手順は運用ポリシーと環境に合わせて調整してください。必要であれば各モジュールの詳細ドキュメント（関数/クラスごとの説明）も作成します。