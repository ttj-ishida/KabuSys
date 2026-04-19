KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリは以下の主要機能を持つコンポーネント群で構成されています。

- 注文実行エンジン（ExecutionEngine、paper_trading モード対応）
- 監視サブシステム（System / Trade / Risk のポーリング・アラート・Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ（ファクター計算・特徴量探索・IC 計算）
- AI 補助（ニュースのセンチメント評価、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定等）
- 運用支援スクリプト（.env ウィザード、設定検証、Paper Trading レポート）

安全性を考慮して、paper_trading（疑似発注）と live（実口座）は明確に分離されています。

主な機能一覧
--------------
- Execution
  - KABUSYS_ENV に応じた Broker クライアント選択（paper_trading では MockBroker を使用）
  - ExecutionEngine による注文の発行／管理、OrderRepository/OrderManager/RiskManager 等の統合
- Monitoring
  - SystemMonitor: CPU/Mem/Disk、プロセス生存確認、データ鮮度監視
  - TradeMonitor: 注文滞留／約定異常などの検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送信
  - MonitoringEngine: 上記モニタ群を束ねたポーリングループ（本番は継続実行）
- Portfolio
  - 候補選定（スコア順）
  - 重み計算（等金額、スコア加重）
  - セクター集中制限、レジーム乗数、ポジションサイズ決定（単元丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた SQL ベース）
  - 将来リターン計算、IC（スピアマン）や統計サマリ
- AI
  - news_nlp: OpenAI API 経由でニュースを銘柄ごとにセンチメント評価し ai_scores に保存
  - regime_detector: ETF（1321）MA とマクロニュースの LLM センチメントを合成し market_regime を決定
- ツール
  - config_setup.py: 対話式に .env を生成／更新するウィザード
  - validate_config.py: .env と config/*.yaml の簡易検証 CLI
  - tools.paper_verification_report: Paper Trading の稼働/成功率/レイテンシなどをまとめるレポート

セットアップ手順
----------------

前提
- Python 3.9+ を想定（実行環境に合わせて適宜）
- システムに DuckDB, psutil, OpenAI SDK 等の依存パッケージをインストールしてください。

推奨インストール例（仮想環境内）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

- 依存パッケージ（例）
  - pip install duckdb psutil openai
  - PyYAML は設定ファイル検証（validate_config）を有効にしたい場合に必要: pip install pyyaml

環境変数 / .env
- 環境変数は以下の優先順位で読み込まれます:
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env
- 自動ロードはデフォルトで有効。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 重要な環境変数（Settings で参照されるもの、デフォルト値は Settings の docstring/実装参照）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live, default: development)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB の上書き、default: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/...)
  - OPENAI_API_KEY (AI 機能を使う場合に必要)
  - その他: LOG_DIR, KILL_FLAG_CLEAR_ON_START, PID_FILE_PATH 等

.env を作る（対話式）
- python -m kabusys.config_setup
  - ウィザードで .env を生成・更新できます。

設定検証
- python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱い（exit code 1）になります。
  - PyYAML 未インストール時は YAML の中身検証はスキップされます。

初期ディレクトリ作成
- logs/ や data/ は実行時に自動生成されることが多いですが、運用環境では事前に権限やマウントを確認してください。

使い方（主要スクリプト）
-----------------------

注: すべてのスクリプトはパッケージをモジュール実行する想定です。

1. 監視 (Monitoring)
- 開始:
  - python -m kabusys.run_monitoring
  - デフォルトで MONITOR_POLL_INTERVAL=60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
- 停止:
  - プロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了。
- 監視は Settings.sqlite_path（本番の sqlite パス）を使います（環境に依らず本番監視 DB を利用）。

2. 注文実行エンジン (Execution)
- 起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、デフォルトで PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録され、本番 DB と分離されます。
- 停止:
  - data/stop_requested.flag を作成するとエンジン停止シグナルとして検出され、ExecutionEngine.stop() が呼ばれます。
  - KillSwitch は条件に応じて data/kill.flag を書き込み、外部からの停止（安全停止）を誘発します。
- PID 管理:
  - run_execution は data/execution.pid へ PID ファイルを書く仕組み（Settings.pid_file_path で上書き可）。

3. Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db で SQLite ファイルを指定しない場合、PAPER_TRADING_SQLITE_PATH 環境変数 → data/paper_trading.db の順で探索されます。

4. AI / レジーム判定（プログラム的に呼び出す）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡し、target_date に紐づくニュースを元に ai_scores テーブルを更新します。
  - api_key は引数で渡すか環境変数 OPENAI_API_KEY を利用します。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - market_regime テーブルへ冪等的に書き込みます。
- いずれも OPENAI_API_KEY が必須（引数 or 環境変数）。

設定の挙動（運用上の注意）
- KABUSYS_ENV:
  - development: 開発向け（発注なし）
  - paper_trading: ペーパートレード（MockBroker、別 DB）
  - live: 実運用（実発注） — 設定ミスは重大な損失につながる可能性があるため注意
- Kill Switch / stop フラグ:
  - data/kill.flag は KillSwitch によって作成され、ExecutionEngine に停止シグナルを送るためのファイルです（KillSwitch.clear() で削除可能）。
  - stop_requested.flag は run_* スクリプトのループ終了用のフラグです（管理者が安全にプロセスを終了させるために使用）。
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力（TimedRotatingFileHandler、デフォルト 30 日分保持）。
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

ディレクトリ構成（抜粋）
---------------------

リポジトリの主要ファイル・ディレクトリの概観（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings
  - config_setup.py             — .env 対話ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py          — ログ設定ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py          — SQLite DB 初期化・読み書き層
    - system_monitor.py         — システム・データ鮮度監視
    - risk_monitor.py           — ドローダウン / ポジション上限監視
    - trade_monitor.py          — （滞留注文や約定異常検出）※実装参照
    - kill_switch.py            — Kill Switch（flag ファイル操作）
    - monitoring_engine.py      — 各 Monitor を束ねる
    - alert_manager.py          — （アラート通知の集中処理）※実装参照
  - execution/
    - execution_engine.py       — ExecutionEngine 本体（起動／run_session）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み付け
    - position_sizing.py        — 株数決定・aggregate cap
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py        — Momentum / Volatility / Value
    - feature_exploration.py    — forward returns / IC / summary
  - ai/
    - news_nlp.py               — ニュースセンチメント（OpenAI）
    - regime_detector.py        — レジーム判定（ETF + macro sentiment）
  - tools/
    - paper_verification_report.py — Paper Trading 向けレポート生成スクリプト
  - data/                       — データおよびフラグファイルを格納するディレクトリ（runtime）

補足／運用上のヒント
--------------------
- 本番運用前に python -m kabusys.validate_config を実行して設定の欠落やパスの問題を検出してください。
- KABUSYS_ENV=live の際は LINE 通知等のアラート先設定（LINE_CHANNEL_ACCESS_TOKEN、LINE_USER_ID）を必ず確認してください。
- OpenAI を用いる機能は API 呼び出しに費用が発生します。テスト時はキーを設定せず無効化して動作確認してください。
- DuckDB / SQLite の DB ファイルは適切なパーミッション・バックアップを設定してください。
- logs/ や data/ はコンテナ運用時にボリュームで永続化することを推奨します。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス表記はこの README に含まれていません。配布時に適切なライセンスファイルを追加してください。

最後に
------
この README はコードベースの主要な使い方・設計意図の要約です。各モジュールの詳細な挙動やパラメータは該当するソースコードの docstring を参照してください。必要であれば、運用手順書（デプロイ手順、監視ダッシュボード、復旧手順など）や追加の設定例を作成します。