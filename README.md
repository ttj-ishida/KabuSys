KabuSys — 日本株自動売買システム
概要
- KabuSys は日本株自動売買のための内部ライブラリ群と起動スクリプトを含むプロジェクトです。
- システム監視（Monitoring）、注文実行（Execution）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、AI ベースのニュース NLP（センチメント）、Paper Trading 用ツールなどのコンポーネントで構成されます。
- 本リポジトリはローカル実行・ペーパートレード・本番（live）を想定した設計になっており、設定は .env（環境変数）で管理します。

主な機能
- ExecutionEngine（run_execution.py）: 発注・約定・リスク管理・再整合（reconciler）を含む注文実行エンジン。
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離。
- Monitoring（run_monitoring.py / monitoring/*）: システム状態監視、トレード監視、リスク監視、Kill Switch（停止フラグ）とアラート管理。
  - 監視は SQLite（monitoring DB）へ記録。Monitoring は常に本番 sqlite_path を使用（設定に依存しない）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
- Portfolio（portfolio/*）: 候補選定、配分重み、リスク調整、株数決定（position sizing）など。
- Research（research/*）: DuckDB を用いたファクター計算（momentum, value, volatility）、将来リターン・IC 計算、統計サマリー。
- AI（ai/*）: ニュース記事のセンチメントを OpenAI（gpt-4o-mini 等）で評価し ai_scores へ書き込む機能、マクロ + ETF MA を組み合わせた市場レジーム判定。
- Tools（tools/*）: Paper Trading の検証レポート生成スクリプト（paper_verification_report.py）。
- 設定管理・検証:
  - config_setup.py: .env の対話式ウィザードでの生成・更新。
  - validate_config.py: .env および config/*.yaml の事前検証（--strict オプションで警告を FAIL 扱いに）。

前提（依存関係）
- Python 3.10+ を想定（型記法や | 演算子を使用）。
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（validate_config が config/*.yaml を解析する場合）
- SQLite（標準ライブラリ）・ファイル I/O にアクセス可能であること。

セットアップ手順
1. リポジトリをクローン/配置
   - プロジェクトルートに src/ 以下が来るレイアウトを想定します。

2. 仮想環境の作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt があればそれを使用してください）

4. 環境変数の準備（.env）
   - python -m kabusys.config_setup を実行して対話的に .env を作成／更新するのが手軽です。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番（live）で OpenAI を使う場合は OPENAI_API_KEY を設定。
   - 主要なデフォルトパス（必要に応じて .env で上書き可能）:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - LOG_DIR: logs/
     - LOG_LEVEL: INFO
   - 参考: .env は .env.example を元に作成してください（リポジトリに例ファイルがある場合）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります: python -m kabusys.validate_config --strict

使い方（主なスクリプト）
- 実行エンジン（Execution）
  - 目的: 注文発行・注文管理・リスク管理を行うメインプロセス
  - 実行:
    - KABUSYS_ENV=development (または paper_trading / live) を .env で設定。
    - python -m kabusys.run_execution
  - 特記事項:
    - paper_trading 環境では MockBrokerClient を使い、DB は PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）を使用して本番 DB と分離します。
    - 起動前に kill.flag が存在すると起動をスキップします（停止フラグ）。
    - 実行中に data/stop_requested.flag を置くことで外部からプロセスに停止を要求できます（スクリプト側で検知）。

- 監視プロセス（Monitoring）
  - 目的: システム監視・トレード監視・リスク監視・Kill Switch 評価・アラート送信等
  - 実行:
    - python -m kabusys.run_monitoring
  - 設定:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60）。
    - Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番 monitoring DB）を使用します。

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話形式で .env を作成/更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告で終了コード 1 を返します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数やデフォルト data/paper_trading.db を上書き）

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- OPENAI_API_KEY: AI 関連機能利用時に必要
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: 各 DB のパス
- LOG_DIR / LOG_LEVEL
- MONITOR_POLL_INTERVAL（監視間隔上書き: 秒）
- KILL_FLAG_PATH（kill.flag のパス）
- PID_FILE_PATH（実行エンジンの PID ファイル）

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（logs/ ディレクトリは自動作成を試みます）。
- setup_logging(app_name="execution" | "monitoring" など) が全起動スクリプトから呼ばれ、stdout への StreamHandler も設定されます。

安全性・運用上の注意
- .env は機密情報（API トークン等）を含むため決して Git にコミットしないでください。
- KABUSYS_ENV=live は本番運用です。validate_config は本番向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等のチェック）を行います。
- kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）を本番で有効にするのは危険です（既定は 0）。
- Execution 起動時にプロセス優先度を高（High）に設定しようとしますが、権限不足で失敗する場合があります（警告でスキップ）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定取得（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI 呼び出し・ai_scores 書き込み
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — monitoring DB スキーマ & 永続化ヘルパ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （ファイル中に含まれる想定）トレード監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書込ロジック
    - alert_manager.py       — （ファイル中に含まれる想定）通知管理
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig, run_session 等）
    - broker_factory.py      — BrokerClient の生成（Mock/Live 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                     —（運用時）DB / フラグファイル格納想定（data/monitoring.db 等）
  - utils/
    - logging_setup.py       — 共通ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

開発者向け補足
- DuckDB 接続を渡してファクター計算・AI スコアリングを行う設計になっており、外部 API 呼び出し（kabu API / OpenAI）を使う箇所は抽象化されています。ユニットテストでは OpenAI 呼び出し関数をパッチするなどして外部依存を切り離せます。
- monitoring_db.init_monitoring_db() はスキーマ作成と既存 DB に対する簡単なマイグレーション（カラム追加）を行います。
- research モジュールや portfolio モジュールは純粋関数を中心に設計されており、DB 参照を伴わない純粋計算部分は容易に検証可能です。

よくある実行例
- 初回セットアップ（.env、依存インストール）
  - python -m kabusys.config_setup
  - pip install -r requirements.txt

- 設定検証
  - python -m kabusys.validate_config

- ローカル（paper_trading）で実行エンジンを起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視プロセスを起動（別プロセスで実行）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

免責・注意事項
- 本 README はソースに含まれるモジュール内容に基づく概要と運用手順の要約です。実運用前に validate_config による検証、テスト環境での動作確認を必ず行ってください。
- 実際の売買はリスクを伴います。本番環境での稼働時は設定・ログ・アラートを十分に確認してください。

バージョン
- パッケージ定義内: __version__ = "0.1.0"

その他
- 不足しているドキュメント項目（運用フロー図、DB スキーマ詳細、API クライアント実装、テスト手順など）があれば指定してください。必要に応じて README を拡張します。