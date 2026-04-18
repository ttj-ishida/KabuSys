KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買・研究・監視ユーティリティ群をまとめた Python モジュール群です。  
実運用（ExecutionEngine）、監視（Monitoring）、ファクター計算／リサーチ、AI を使ったニュースセンチメント評価、ポートフォリオ構築ユーティリティなどを含みます。

主な特徴
--------
- ExecutionEngine：kabuステーション等のブローカークライアントを通じた発注・注文管理（paper_trading と live を分離）
- Monitoring：システム稼働監視、データ鮮度チェック、滞留注文検出、リスク監視（ドローダウン・ポジション上限）と Kill Switch
- Research：DuckDB を用いたファクター計算（Momentum / Volatility / Value）・将来リターン・IC 計算等
- AI モジュール：OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価と市場レジーム判定
- Portfolio：銘柄選定、重み計算、ポジションサイズ決定、セクター上限などの純関数的ユーティリティ
- ツール群：環境設定ウィザード、設定検証、Paper Trading 検証レポート生成 等
- ログ・プロセス管理ユーティリティ：統一的なログ設定、プロセス優先度設定、kill フラグによる停止制御

必須外部依存（主なもの）
-----------------------
実行に必要な主要ライブラリ（実際の requirements.txt を参照してください）:
- Python 3.9+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML （config の検証を行う場合）
- その他（標準ライブラリのみで動く部分が多い）

セットアップ手順
----------------

1. リポジトリ取得・仮想環境
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を推奨）

3. 環境変数の設定（.env）
   - 対話的に .env を作成・更新するには:
     - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
   - 主要な環境変数（.env 例）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

   注意:
   - 本番 (KABUSYS_ENV=live) 設定時は API キー・パスワードや通知先の確認を厳重に行ってください。
   - .env は絶対にバージョン管理にコミットしないでください。

基本的な使い方
--------------

起動スクリプト
- 監視ループを起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト: 60）
    - 監視は常に本番用の sqlite_path（SQLITE_PATH）を参照します（環境に依存せず）
    - 停止フラグ: プロジェクトの data/stop_requested.flag を作成するとループは終了します

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録され、本番 DB とは分離されます
    - 起動時に data/stop_requested.flag があると起動しません
    - 実行中に data/stop_requested.flag が作成された場合、Engine に停止信号を送り安全に終了します
    - PID ファイル: data/execution.pid（デフォルト。Settings.pid_file_path で変更可）

ツール
- 環境ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
    - --strict を付けると警告もエラー扱いにして終了コード 1 を返します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

AI（OpenAI）関連
- ニュース NLP（銘柄センチメント取得）
  - kabusys.ai.score_news(...) を呼び出す、または内部の仕組みに従って運用バッチで実行
  - 必要: OPENAI_API_KEY（引数でも与えられる）

- 市場レジーム判定
  - kabusys.ai.regime_detector.score_regime(...)

監視 / Kill Switch
- KillSwitch: データベース監視（ドローダウンやポジション上限）に基づいて data/kill.flag を書き込み、ExecutionEngine に停止指示を出します
- Kill フラグの場所は Settings.kill_flag_path（デフォルト: data/kill.flag）
- ExecutionEngine は起動時に kill フラグの自動クリア設定（KILL_FLAG_CLEAR_ON_START）を確認するオプションを持ちます（本番では 0 推奨）

設定の重要ポイント（要確認）
- KABUSYS_ENV:
  - development: ローカル開発（発注なし）
  - paper_trading: ペーパートレード（仮想発注）
  - live: 本番（実際に発注）
  - live 時は通知設定（LINE 等）や Kill Switch 設定を慎重に確認してください

- データベース:
  - DuckDB: 分析用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・注文履歴（デフォルト data/monitoring.db）
  - paper_trading 用の SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

- PAPER_FILL_MODE（paper_trading 時の約定挙動）
  - instant | partial | never | reject のいずれか（デフォルト: instant）

ログ
----
- 共通ログ初期化ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - デフォルト: logs/<app_name>.log を日次ローテーション（30日保持）で出力
  - 環境変数 LOG_DIR / LOG_LEVEL で上書き可能
  - コンソール出力は stdout に送られます

ディレクトリ構成（主要ファイル）
----------------------------

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 側の永続化層（テーブル初期化・簡易操作）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （滞留注文・約定異常等の検出）※実コード参照
    - risk_monitor.py        — ドローダウン・ポジション上限チェック
    - kill_switch.py         — kill.flag 書込ロジック
    - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py       —（通知管理: LINE 等。実装参照）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（セッションラン）
    - order_manager.py       — 発注ロジック
    - order_repository.py    — 注文永続化
    - broker_factory.py      — BrokerClient の生成（Mock / 実ブローカー）
    - risk_manager.py        — リスク制御ロジック
    - reconciler.py          — ブローカー状態とリポジトリの整合
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 発注株数・丸めロジック
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value などの計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py            — ニュースから銘柄別センチメント算出（OpenAI）
    - regime_detector.py     — マクロ＋ETF MA による市場レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
    - __init__.py

運用上の注意
------------
- 本番環境（KABUSYS_ENV=live）では API キー・パスワードの管理、Kill Switch 設定（KILL_FLAG_CLEAR_ON_START の値を 0 推奨）、通知設定（LINE）を厳重に確認してください。
- OpenAI API を利用する機能は外部サービス課金やレスポンスの不確実性に依存します。エラー時のフォールバックやレート制限対策（実装済）を理解した上で運用してください。
- SQLite / DuckDB ファイルは適切なバックアップおよびディスク容量管理が必要です（監視ロジックはディスク使用率を監視しますが、ロギングや DB 増加に注意）。

よくある操作例
---------------
- .env を対話で作る:
  - python -m kabusys.config_setup

- 設定チェック:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視の手動実行（1 回だけ検査を実行したい場合は MonitoringEngine をテスト用に使うか system_monitor.check_once() を使う）
  - python -m kabusys.run_monitoring

- エンジン起動:
  - python -m kabusys.run_execution

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張
----------------
- duckdb のテーブル（prices_daily, raw_financials, raw_news など）が前提になります。データパイプラインは kabusys.data.pipeline 等（別モジュール）を参照してください。
- BrokerClient 実装は broker_factory 経由で差し替えられます。テスト用に Mock を用意して運用できます。
- ログや PID 管理は utils/logging_setup.py / run_execution.py の pid_file を参照してください。プロセスマネージャ（systemd / supervisor / cron）からの起動を想定しています。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はプロジェクトルートの LICENSE を参照してください（無ければプロジェクト管理者に確認してください）。

最後に
------
この README はコードベースの主要コンポーネントと基本運用手順をまとめたものです。詳細な API 仕様や内部のアルゴリズム（StrategyModel.md、PortfolioConstruction.md 等のドキュメント）が別にある想定ですので、運用前にそちらも参照してください。運用時の安全策（Kill Switch、ログ・監視、paper_trading での動作確認）を忘れずに行ってください。