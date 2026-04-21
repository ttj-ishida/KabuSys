README
=====

概要
----
KabuSys は日本株の自動売買／分析プラットフォームのコアライブラリ群です。本リポジトリには以下の主要機能が含まれます。

- 注文実行エンジン（ExecutionEngine）の起動スクリプト
- 監視（Monitoring）コンポーネント（システム状態・注文・リスク監視）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- リサーチ用ファクター計算・特徴量解析
- AI を使ったニュースセンチメント（OpenAI）／レジーム判定
- 環境設定ウィザード・設定検証ツール
- Paper Trading 向けの検証レポート生成スクリプト

この README はローカル開発・運用で必要なセットアップ手順、使い方、ディレクトリ構成を示します。

主な機能一覧
--------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番または paper_trading を切替）
  - run_monitoring.py: SystemMonitor を用いたポーリング監視ループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- 環境管理 / ツール
  - config_setup.py: .env を対話式に生成・更新するウィザード
  - validate_config.py: .env や config/*.yaml の前提チェック CLI
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成
- 監視
  - monitoring_engine / system_monitor / trade_monitor / risk_monitor / kill_switch / monitoring_db
  - kill.flag / stop_requested.flag による ExecutionEngine 停止シグナル
- 注文／実行関連（execution パッケージ: BrokerFactory / ExecutionEngine / OrderManager / RiskManager 等）
- ポートフォリオ（portfolio パッケージ）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ（research パッケージ）
  - ファクター計算（momentum, volatility, value）、将来リターン、IC、統計サマリー
- AI（ai パッケージ）
  - news_nlp: ニュースを OpenAI に投げて銘柄スコア化
  - regime_detector: MA とマクロニュースで市場レジーム判定

前提（依存関係）
----------------
主なランタイム依存パッケージ（プロジェクトの requirements.txt が無い場合は手動でインストールしてください）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証は任意）
- 他: 標準ライブラリ（sqlite3, threading, logging 等）

セットアップ手順
----------------

1. リポジトリをクローン / 取得
   - git clone ... またはソースを配置

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb psutil openai PyYAML
   - 実際の運用に合わせて必要なライブラリを追加してください。

4. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
     - ウィザードに従い J-Quants トークン / kabu API パスワード 等を入力してください。
   - 生成された .env は決して Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正してください。--strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備（必要に応じて）
   - デフォルトの DB/ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db (paper_trading 環境時)
     - ログディレクトリ: logs/
   - 実行時に自動作成されますが、権限や配置を確認してください。

主要環境変数（抜粋）
--------------------
Settings モジュールで利用される主な環境変数（デフォルト値があるものは示す）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject, デフォルト: instant)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1, デフォルト: 0)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- OPENAI_API_KEY（AI 機能利用時に必要）

使い方（主要コマンド例）
----------------------

1) ExecutionEngine を起動する
- ローカル実行（開発用）
  - KABUSYS_ENV=development python -m kabusys.run_execution
    - development: 実際の注文は行わない（発注を行わない実装想定）
- Paper Trading（モックブローカー・paper DB を使用）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - PAPER_TRADING_SQLITE_PATH で DB パスを変更できます
- 本番
  - KABUSYS_ENV=live python -m kabusys.run_execution
    - 実行前に validate_config で設定を入念に確認してください
- 実行中、data/execution.pid に PID が書き込まれます。停止シグナルは data/stop_requested.flag（起動スクリプトが監視）や data/kill.flag（監視コンポーネントが作成）で行います。

2) Monitoring（監視ループ）を起動する
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用（monitoring は環境にかかわらず本番 sqlite_path を参照します）

3) .env の設定ウィザード
- python -m kabusys.config_setup

4) 設定検証
- python -m kabusys.validate_config
- 厳格モード（警告も失敗扱い）:
  - python -m kabusys.validate_config --strict

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション: --db で DB パスを指定（優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

6) AI 関連（news_nlp / regime_detector）
- OPENAI_API_KEY を設定してから利用してください。
- news_nlp.score_news / regime_detector.score_regime は DuckDB 接続および target_date を渡して使用します。
- CLI ラッパーは用意していませんがテストやスケジューラから呼び出せます。

停止 / Kill Switch
------------------
- ExecutionEngine 側ではプロセス起動スクリプトが data/stop_requested.flag を監視します。
  - stop を要求する場合はプロジェクトルート/data ディレクトリに stop_requested.flag を作成してください。
- 監視側（MonitoringEngine / KillSwitch）はリスク閾値等を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine は起動時に kill.flag をチェックし、必要に応じて起動を抑止したり停止処理を行います。
- KILL_FLAG_CLEAR_ON_START=1 にすると ExecutionEngine 起動時に kill.flag を自動でクリアする設定があります（本番では通常 0 推奨）。

ログ
----
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- ログディレクトリは環境変数 LOG_DIR で上書きできます。デフォルト: logs/
- 各スクリプトは setup_logging(app_name=...) を使って統一的にログ設定を行います。

データベース
-----------
- DuckDB: 分析・prices_daily/raw_financials などの大規模データ格納（Settings.duckdb_path）
- SQLite:
  - 監視ログ: Settings.sqlite_path（デフォルト data/monitoring.db）
  - Paper Trading 用: Settings.paper_sqlite_path（paper_trading 環境時に使用）
- monitoring_db.init_monitoring_db(conn) はテーブルを冪等に作成します（マイグレーション処理を含む）

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - ... (trade_monitor, alert_manager 等)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ... (Execution 関連)
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - data/ (実行時に作成されるデータ / DB / フラグファイル等を想定)
  - logs/ (ログファイル出力先)

補足 / 運用上の注意
------------------
- 本番環境（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START 設定に十分注意してください。validate_config.py は live 時に追加警告を出します。
- AI（OpenAI）機能は API 呼び出し回数とレイテンシ、コストに注意してください。news_nlp/regime_detector 共にレート制限や 5xx を考慮した再試行ロジックを持ちますが、運用負荷は事前に評価してください。
- paper_trading 環境では発注はモック経由で記録用の別 DB に保存され、本番 DB と論理的に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- ログディレクトリや DB ファイルの権限、バックアップ方針は運用ポリシーに従ってください。

ライセンス / バージョン
------------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現時点: 0.1.0）
- ライセンス情報はリポジトリのルートにある LICENSE 等を参照してください（本 README には含めていません）。

お問い合わせ / 開発者向け
-----------------------
- 開発中は .env に機密情報を含むため、決して Git にコミットしないでください。
- ユニットテストや CI を整備する際は、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動 .env ロードを無効化し、テスト専用の環境変数注入を行ってください。
- モジュール/関数単位での利用（research.calc_momentum 等）は DuckDB 接続や引数を渡して直接呼び出せます。テストしやすい純粋関数設計が意識されています。

以上。運用や導入で不明点があれば具体的なユースケース（ローカルデバッグ、本番デプロイ、Paper Trading の検証等）を教えてください。さらに詳細な手順や systemd / Supervisor / Docker での実行方法も補足できます。