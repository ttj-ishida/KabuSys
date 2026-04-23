KabuSys — 日本株自動売買システム
================================

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買を想定したモジュール型システムです。  
主な関心領域は「設定管理」「監視（Monitoring）」「発注実行（Execution）」「ポートフォリオ構築」「リサーチ（ファクター計算）」「AI（ニュース NLP / レジーム判定）」「ユーティリティ」です。  
設計方針として、各機能はできる限り副作用を抑え、DB（DuckDB / SQLite）や外部 API（kabuステーション / J‑Quants / OpenAI）とのインターフェースを分離して実装されています。

主な機能
--------
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local、無効化オプションあり）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン起動スクリプト
  - run_execution: ExecutionEngine の起動（本番 / ペーパートレード切替）
  - ペーパートレード時は MockBrokerClient を利用し DB を完全分離
- 監視
  - run_monitoring: SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL により間隔を変更可）
  - MonitoringEngine による System/Trade/Risk モニタの統合、Kill Switch（flag ファイルによる停止）とアラート起動
  - MonitoringDB: SQLite に監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）を永続化
- リスク管理
  - RiskMonitor: ドローダウンやポジション上限の検出・ログ化
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送信
- ポートフォリオ構築
  - 銘柄選定、重み計算（等金額 / スコア加重）、位置サイズ計算（単元丸め、リスクベース配分）
  - セクターキャップ、レジーム乗数適用ロジック
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン、IC（情報係数）、統計サマリー
  - DuckDB を用いた SQL ベースの高速集計
- AI（OpenAI 統合）
  - ニュースのセンチメントスコア算出（news_nlp.score_news）
  - マクロ＋ETF MA200 を用いた市場レジーム判定（regime_detector.score_regime）
  - OpenAI 呼び出しはリトライや結果バリデーション、フェイルセーフ実装済み
- ツール
  - Paper Trading の検証レポート出力（tools.paper_verification_report）
- ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - 環境設定のパース / .env 読み込みロジック

セットアップ手順
--------------
1. Python 環境
   - 推奨: Python 3.9+
   - 必要外部パッケージ（代表例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config 検証で YAML 検査を有効にする場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

2. プロジェクトルート（.env 自動ロード）
   - 本リポジトリは .git または pyproject.toml を基にプロジェクトルートを自動検出します。
   - 環境変数は優先度: OS 環境 > .env.local > .env
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

3. 対話式で .env を作成
   - python -m kabusys.config_setup を実行し、画面の案内に従って .env を生成してください。
   - 必須項目（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（主なもの）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア。production では 0 推奨）

4. 設定検証
   - python -m kabusys.validate_config
     - --strict を付けると警告もエラー扱い（exit 1）になります。

5. ディレクトリ / ファイル作成
   - デフォルトでは data/ や logs/ は自動作成されます。必要に応じてパスを .env で変更してください。

使い方（起動 / 実行例）
---------------------
- 監視ループを起動（常駐）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 監視スクリプトは process priority を "high" に設定します（内部で psutil を使用）
  - 停止: プロジェクトルート/data/stop_requested.flag を作成すると次のポーリングで終了します

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動せずに終了します
  - 実行中に停止させるには data/stop_requested.flag を作成するか、監視の KillSwitch により data/kill.flag が書き込まれると停止されます
  - 実行中の PID は data/execution.pid に書き込まれます（設定により変更可能）

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで PAPER_TRADING_SQLITE_PATH を上書き可能（環境変数でも指定可）

- AI 関連
  - OpenAI を使う機能（news_nlp, regime_detector）を使う場合は OPENAI_API_KEY を設定してください
  - 実際の呼び出しは関数呼び出しベース（score_news / score_regime）で、DuckDB 接続と target_date を渡して実行します

停止・Kill Switch の仕様
------------------------
- run_monitoring / run_execution の停止フラグ:
  - data/stop_requested.flag — 管理者が外部から "即時停止" を要求するためのファイル。該当ファイルが存在すると各ループは安全に終了します
- KillSwitch（自動停止）
  - 条件（例: ドローダウン閾値超過、ポジション上限超過）が満たされると data/kill.flag が書き込まれます
  - kill.flag が存在すると ExecutionEngine に停止シグナルが送られ、本番発注が停止されます
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨

ログ
---
- ログは stdout に常時出力され、さらに logs/<app_name>.log に日次ローテートで保存されます（30日保持）。logging 設定は kabusys.utils.logging_setup.setup_logging で統一管理されます。
- LOG_DIR 環境変数や setup_logging の引数でログ保存先を変更可能です。

開発上の注意点 / トラブルシューティング
---------------------------------------
- .env の自動読み込みは OS 環境変数を保護します（OS 変数が優先される）。
- DuckDB / SQLite ファイルパスの親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、パーミッション等で失敗する場合は手動作成してください。
- OpenAI の呼び出しはエラー時に指数バックオフでリトライしますが、API キー未設定だと例外を送出する処理があるため、AI 関連処理を実行する場合は必ず OPENAI_API_KEY を設定してください。
- psutil の一部機能（nice, cpu_affinity 等）は権限や OS により制限されるため、アクセス拒否が発生する場合は警告ログのみ出ます（例外は発生しません）。

主要ディレクトリ構成
-------------------
（src/kabusys 以下の主要ファイル・モジュールを抜粋）

- kabusys/
  - __init__.py               — パッケージ定義（__version__）
  - config.py                 — 環境変数 /.env 読み込み / Settings クラス
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 統合）
    - regime_detector.py      — 市場レジーム判定（ETF MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py        — SQLite 監視ログ永続化層
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — （発注監視ロジック）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag の作成 / 検査
    - monitoring_engine.py    — 各モニタを束ねるポーリングエンジン
    - alert_manager.py        — （アラート送信ロジック: LINE 等）
  - execution/
    - execution_engine.py     — ExecutionEngine（発注セッション管理）
    - broker_factory.py       — BrokerClient の生成（本番 / Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・資金配分・単元処理
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（Momentum / Volatility / Value）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - data/                     — デフォルトデータ格納ディレクトリ（DB / flag / pid 等）
  - logs/                     — デフォルトログ出力ディレクトリ

補足: 設定・ファイルのデフォルトパス
-----------------------------------
- DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
- Monitoring SQLite: data/monitoring.db（環境変数 SQLITE_PATH で変更可）
- Paper Trading SQLite: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）
- PID / flag:
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag

ライセンス / Contributing
-------------------------
- この README にはライセンス等は含まれていません。実装をベースにプロジェクトの LICENSE をご確認ください。  
- 貢献や問題報告は通常の GitHub フロー（Issue / PR）を使って行ってください。

よく使うコマンド早見表
---------------------
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- リサーチ / AI 関数は Python API として呼び出し（DuckDB 接続を渡す）

以上がこのコードベースの概要・セットアップ・利用方法とディレクトリ構成です。  
必要であれば、.env の具体例や systemd / docker でのデプロイ例、個別モジュール（ExecutionEngine / MonitoringEngine）の詳細設計ドキュメントも作成できます。ご希望があれば教えてください。