KabuSys — 日本株自動売買システム（簡易 README）
==================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine 起動スクリプト（発注ロジック・注文管理・リスク管理）
- Monitoring（システム稼働・注文・リスクの監視）
- Portfolio 構築（銘柄選定、重み付け、ポジションサイズ算出）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- ユーティリティ（設定読み込み、ログ設定、プロセス優先度設定、.env ウィザード等）
- 各種ツール（Paper Trading 検証レポート生成など）

主な機能一覧
-------------
- 環境管理
  - .env/.env.local 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 対話式の .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行（Execution）
  - 本番 / Paper Trading の分離（KABUSYS_ENV によって DB を切替）
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - 注文管理、リスク管理、調整・再整合処理
  - 停止フラグ（data/stop_requested.flag）と Kill Switch（data/kill.flag）
- 監視（Monitoring）
  - システム稼働監視（CPU/Mem/Disk、実行プロセスの生存確認）
  - 注文ログ・リスクログの永続化（SQLite）
  - Kill Switch 評価、アラート発行（AlertManager 経由）
- ポートフォリオ構築
  - 候補選定、スコア重み／等分配、セクター上限適用、レジーム乗数
  - ポジションサイズ算出（単元株丸め、aggregate cap のスケール調整）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターン、IC（Information Coefficient）などの解析ユーティリティ
- AI（OpenAI）
  - ニュース記事のセンチメントスコア化（ai.news_nlp）
  - マクロ+ETF 指標を統合した市場レジーム判定（ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
以下はローカルでソースを実行するための一般的な手順です。

1. リポジトリルートで仮想環境作成（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール:
   - 最低限必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML パースを行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を利用してください）

3. .env を作成:
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - または手動でルートに .env を作成（.env.example を参考にしてください）。
   - 自動ロード:
     - config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出し、
       .env を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 設定検証（推奨）:
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ等の準備:
   - デフォルトで SQLite / DuckDB は data/ 配下に作成されます（必要に応じて .env でパスを変更）。
   - ログは logs/ に出力（LOG_DIR 環境変数で変更可）。

使い方（実行例）
----------------

前提:
- プロジェクトルートで実行してください（src がパッケージとして読み込める状態）。
- .env を用意し、必要な環境変数を設定してください。

主なコマンド:
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60 秒）。
    - 監視は常に "本番用" の sqlite_path（Settings.sqlite_path）を使用します。
    - 停止: data/stop_requested.flag ファイルを作成するとループを終了します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録。
    - 起動時に data/stop_requested.flag が既にある場合は起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。停止は stop フラグまたは Kill Switch を使用。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- AI 系機能（スクリプトから呼ぶ / テスト用）
  - ニューススコア生成:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - OpenAI API キーは OPENAI_API_KEY 環境変数または引数で指定してください
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

主要な環境変数（代表例）
-----------------------
（.env に設定して運用してください）

- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） (default: development)
- DUCKDB_PATH: DuckDB ファイルのパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（default: logs）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（1/0）

ログ
----
- ログ設定ユーティリティは kabusys.utils.logging_setup.setup_logging を提供します。
- 出力先:
  - コンソール（stdout）
  - 日次ローテーションファイル: <LOG_DIR>/<app_name>.log（デフォルト logs/）
  - ローテーションは日次、30 日分保持
- 既存ハンドラがある場合は再設定時にクリアして二重出力を防止します。

停止フラグ / Kill Switch
------------------------
- run_execution / run_monitoring はプロジェクト内の data/stop_requested.flag を監視し、存在時には安全に停止します（run_execution は起動中にフラグが立つと Engine.stop を呼びます）。
- KillSwitch（monitoring/kill_switch.py）は drawdown やポジション上限などの条件で data/kill.flag を書き込み、Execution を停止させるために使用します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番での自動クリアは危険なので注意）。

注意・運用上のポイント
-------------------
- KABUSYS_ENV を "live" に設定する場合は十分に設定を確認してください（validate_config が警告を出します）。
- Paper Trading モードは本番 DB と分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使う機能は API コストとレート制限に注意してください。失敗時はフェイルセーフ（スコア 0 など）で続行する実装です。
- ローカルで実行する場合、プロジェクトルートから python -m kabusys.xxx で実行するか、パッケージをインストールして利用してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主なファイル・サブパッケージの概要です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings ラッパ
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ & 永続化ヘルパ
    - system_monitor.py       — システム状態監視
    - trade_monitor.py        — （注文監視関連）
    - risk_monitor.py         — ドローダウン・ポジション監視
    - kill_switch.py          — kill.flag 制御
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （外部通知用）
  - execution/
    - execution_engine.py     — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング
    - regime_detector.py       — レジーム判定
  - tools/
    - paper_verification_report.py

さらに詳しく
--------------
各モジュールのドキュメントはソースの docstring に詳細が記載されています。まずは .env を作成し、python -m kabusys.validate_config で問題がないことを確認してから、python -m kabusys.run_monitoring / python -m kabusys.run_execution を試してください。

質問や補足の希望があれば、どの部分の使い方や設定例（.env の具体例、systemd / supervisor 用のサービス定義、テスト方法など）を詳しく書くか教えてください。