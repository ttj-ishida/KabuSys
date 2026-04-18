KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（ライブラリ＋起動スクリプト群）です。  
主要機能は以下の通りです。

- 実行エンジン (ExecutionEngine) — 注文送信・オーダー管理・リスク管理（本番 / ペーパートレード切替）
- 監視 (Monitoring) — システム状態・データ鮮度・注文ログのポーリング監視とアラート / Kill Switch
- ポートフォリオ構築 — 候補選定、配分（等重／スコア重み）・リスク調整・株数算出
- 研究・特徴量計算 — ファクター（モメンタム / バリュー / ボラティリティ）や将来リターン / IC 等
- AI ユーティリティ — ニュースのセンチメント評価（OpenAI）・市場レジーム判定
- ユーティリティスクリプト — .env ウィザード、設定検証、Paper Trading レポートなど
- 永続化：DuckDB（分析向け） / SQLite（監視・トレードログ）

主な設計方針
- 本番とペーパートレードのデータを分離（PAPER_TRADING 用 DB）
- ルックアヘッドバイアスを避けるため、日付計算は明示的に行う
- フェイルセーフ（API 失敗時のフォールバック）を重視
- ロギングは統一的にセットアップ（stdout + 日次ローテートファイル）

機能一覧
----------
- run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用）
- run_monitoring: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）
- config_setup: 対話式 .env 生成ウィザード
- validate_config: .env / config/*.yaml の起動前検証 CLI
- tools.paper_verification_report: ペーパートレードの稼働・注文成功率・レイテンシ等の検証レポート生成
- portfolio: 候補選定・重み付け・数量決定・セクター制約・レジーム調整（純粋関数群）
- research: ファクター計算・特徴量探索・IC 計算
- ai: ニュース NLP（OpenAI）によるセンチメント、レジーム判定
- monitoring: DB 永続層（monitoring_db）、System/Trade/Risk モニタ、KillSwitch、MonitoringEngine
- utils: ログ設定、プロセス優先度 / CPU affinity 設定など

セットアップ手順
----------------

1. Python とパッケージのインストール（例）
   - 推奨: Python 3.10+
   - 必須・推奨パッケージ（pip インストール例）:
     pip install duckdb psutil openai
   - 追加（YAML 検証用, 任意）:
     pip install pyyaml

2. リポジトリの配置
   - ソースはパッケージ形式で src/kabusys 以下に配置されています。作業ディレクトリはプロジェクトルート（.git や pyproject.toml があるディレクトリ）で操作してください。

3. 環境変数 (.env) の用意
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - 主要な環境変数（デフォルト値・必須）
     - 必須:
       - JQUANTS_REFRESH_TOKEN (必須)
       - KABU_API_PASSWORD (必須)
     - 任意／デフォルト:
       - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
       - DUCKDB_PATH: data/kabusys.duckdb
       - SQLITE_PATH: data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
       - LOG_LEVEL: INFO
       - OPENAI_API_KEY: OpenAI を使う場合に設定
       - PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の約定挙動)
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で利用。デフォルト 60）

4. 設定検証
   - 自動検証を実行:
     python -m kabusys.validate_config
   - --strict をつけると警告も FAIL 扱い:
     python -m kabusys.validate_config --strict

5. ディレクトリ・ファイルの作成
   - 実行時に data/ や logs/ は作成されますが、権限やパスに注意してください。

使い方
--------

- ExecutionEngine を起動（本番 / ペーパートレードに応じ DB を切替）
  python -m kabusys.run_execution

  備考:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_sqlite_path（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。
  - 実行中に data/stop_requested.flag を作成すると Engine に停止シグナルを送ります。
  - 実行中は data/execution.pid に PID を書きます。

- Monitoring（ポーリング）を起動
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  備考:
  - デフォルトのポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書きできます（1 以上の整数）。
  - Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用して監視ログを永続化します。
  - 停止用: data/stop_requested.flag を作成すると監視ループが終了します。

- .env の対話式設定
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連
  - ニュースセンチメント / レジーム判定は OPENAI_API_KEY 環境変数が必要です。
  - API 呼び出しはリトライ・バックオフ等の安全対策がありますが、API キーやレート制限に注意してください。

重要ファイル・設定の説明
------------------------
- data/stop_requested.flag: 起動中プロセスに停止を要求するためのフラグ。run_monitoring / run_execution はこれを検知して安全停止します。
- data/kill.flag: KillSwitch が書き込むフラグ（監視がルールに従って Execution を強制停止させる用途）。
- data/execution.pid: ExecutionEngine が起動時に書き込む PID ファイル（プロセス管理用）。
- logs/: setup_logging によりログファイル（アプリごとに日次ローテート）を格納します。

ディレクトリ構成 (主要部分)
--------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・設定読み込み
- config_setup.py          — .env ウィザード
- validate_config.py       — 起動前チェック CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py       — SQLite テーブル作成・永続化層
  - system_monitor.py
  - trade_monitor.py       — （存在：注文ログ監視等）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       — （アラート通知管理）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py       — ログ初期化ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity

（注）上記は抜粋です。全体は src/kabusys 下にモジュール単位で分かれています。

運用上の注意
-------------
- 本番運用前に必ず python -m kabusys.validate_config で設定を確認してください。
- KABUSYS_ENV=live の場合は LINE 通知 / kill flag の設定などを慎重に行ってください（validate_config がガードします）。
- OPENAI_API_KEY を用いる機能は API 利用料・レート制限に注意して運用してください。
- run_monitoring は監視 DB（デフォルト data/monitoring.db）へログを書きます。監視は本番 DB にアクセスして状態を評価します（監視は本番 sqlite_path を使用する点に注意）。
- run_execution は paper_trading モード時に paper DB（data/paper_trading.db）に書き込みます。本番データと混ざらないことを確認してください。

トラブルシュート
----------------
- .env を作成しても環境変数が読み込まれない場合:
  - プロジェクトルート（.git または pyproject.toml）が正しく検出されないと自動ロードをスキップします。手動で環境変数をエクスポートするか、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動ロードを制御してください。
- DuckDB / SQLite への接続エラー:
  - 指定パスのディレクトリ存在・権限を確認してください。validate_config は親ディレクトリ存在チェックを行います。
- OpenAI API 関連のエラー:
  - API キー、ネットワーク、リクエスト制限を確認。モジュールはリトライ実装があるため、一時的なエラーは自動的に再試行されます。

ライセンス / バージョン
------------------------
パッケージバージョンは kabusys.__version__（現状 "0.1.0"）。ライセンス情報はリポジトリのトップレベルに置いてください（本コードには明示的なライセンスファイルは含まれていません）。

最後に
------
本 README はソースコード内の docstring / 設計コメントを基に要点をまとめたものです。実際の運用前に config/*.yaml（存在する場合）や環境固有の運用手順を確認してください。必要であれば、特定コンポーネント（AI / Execution / Monitoring）の詳細ドキュメントを別途作成できます。