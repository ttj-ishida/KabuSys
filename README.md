KabuSys — 日本株自動売買システム
================================

この README は、提供されたコードベース（src/kabusys 以下）を前提にしたローカル開発／運用向けの概要・セットアップ・使い方ドキュメントです。主要な起動スクリプトや設定方法、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買フレームワークです。主な機能は以下の通りです。

- 注文実行エンジン（ExecutionEngine）／ブローカー接続の抽象化（paper/live 切替対応）
- 監視（Monitoring）：システム状態、注文ログ、リスク監視、Kill Switch 等
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- リサーチ：ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析
- AI モジュール：ニュース NLP によるセンチメント評価、レジーム判定（OpenAI 使用）
- 運用支援ツール：.env ウィザード、設定検証、Paper Trading レポート生成 等
- ログ、DB（DuckDB / SQLite）を用いたデータ永続化および分析

機能一覧
--------
- run_execution.py
  - ExecutionEngine の起動スクリプト。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し paper_trading DB（data/paper_trading.db）に記録して本番 DB と分離。
  - 起動時に PID ファイルを書き、停止フラグ（data/stop_requested.flag）で終了を制御。

- run_monitoring.py
  - SystemMonitor をポーリングする監視スクリプト。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視ログは SQLite（settings.sqlite_path）へ記録。

- monitoring パッケージ
  - MonitoringDB（SQLite）: system_status, trade_logs, risk_logs, positions, dashboard 等のスキーマ定義・永続化ロジック
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager / MonitoringEngine 等の実装

- portfolio パッケージ
  - 候補選定、等重・スコア重み、セクター上限適用、レジーム乗数、株数計算（lot 単位で丸め）など

- research パッケージ
  - ファクター計算（momentum/value/volatility）、forward returns、IC 計算、統計サマリー

- ai パッケージ
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメント集約・ai_scores 書き込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を算出

- utils
  - logging_setup: ログ出力（コンソール + 日次ローテーションファイル）
  - process_priority: プロセス優先度（high/normal/low）、CPU affinity 設定ユーティリティ

- tools
  - paper_verification_report: Paper Trading 用の運用検証レポート生成スクリプト

セットアップ手順
----------------

1. リポジトリを取得（既にある想定）

2. Python 環境の準備
   - Python 3.9+（コードは型注釈を使用）
   - 推奨: 仮想環境を用意して依存をインストール

     例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt

   依存の主要例（requirements.txt が無い場合の参考）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で YAML 検証を有効にする場合）
   - その他プロジェクト固有の依存があれば requirements.txt を参照

3. 環境変数 / .env の準備
   - 対話式ウィザードで .env を作る:
     python -m kabusys.config_setup

   - 必須環境変数（最低限設定すること）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - 主要な環境変数とデフォルト
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を使う機能で必要（ai モジュール）
     - MONITOR_POLL_INTERVAL: run_monitoring 用（秒）

   ※ .env はリポジトリにコミットしないこと（config_setup のヘッダにも注意書きあり）。

4. DB 初期化
   - monitoring のスキーマは各スクリプト起動時に自動で作成されます（init_monitoring_db を呼ぶため）。
   - DuckDB 用の初期データは必要に応じて用意してください（prices_daily, raw_financials 等）。research/ai モジュールはこれらのテーブルを参照します。

5. ログディレクトリ
   - デフォルト: logs/
   - write 権限が必要。logging_setup が自動作成を試みますが、失敗した場合はコンソールログのみになります。

使い方（主要コマンド）
--------------------

- 環境ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証（.env、config/*.yaml 等の事前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も失敗扱い

- ExecutionEngine を起動（本番/ペーパートレードに応じて .env の KABUSYS_ENV を設定）
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に data/stop_requested.flag を作成するとエンジンは停止します。
  - PID ファイルを data/execution.pid に書きます（設定で上書き可能）。

- Monitoring を起動（SystemMonitor のループ）
  python -m kabusys.run_monitoring

  挙動:
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - monitoring は設定にかかわらず production の sqlite_path（Settings.sqlite_path）を使って監視ログに書き込みます。
  - 停止は data/stop_requested.flag を作成するか Ctrl-C。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  環境変数:
    PAPER_TRADING_SQLITE_PATH を指定している場合はそれが既定の DB パスになります。

停止・Kill スイッチ
-------------------
- stop_requested.flag (data/stop_requested.flag)
  - run_execution/run_monitoring はこのファイルの存在をチェックし、存在する場合は起動を抑止または実行中の停止トリガーとして扱います（両スクリプトで使用）。

- kill.flag (Settings.kill_flag_path / data/kill.flag)
  - KillSwitch が条件を満たすと（例: ドローダウン大、ポジション数上限超過）このファイルを書き込みます。
  - ExecutionEngine は kill.flag を監視して自身を停止させる設計です（Kill Switch による外部停止機構）。
  - Settings.KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番環境では 0 を推奨します。

設定詳細・重要な設計注意点
------------------------
- Settings クラス（kabusys.config）により .env の自動読み込みを行います（.env / .env.local をプロジェクトルートから読み込む）。テストで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。
- DB 分離:
  - 監視ログ（monitoring）は settings.sqlite_path （デフォルト data/monitoring.db）を使用。
  - Paper Trading は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
- OpenAI (news_nlp, regime_detector)
  - API キーは OPENAI_API_KEY（または各関数の api_key 引数）で指定する必要があります。
  - API エラー時はフォールバック（スコア 0.0）や再試行を行う実装でフェイルセーフ設計。
- ログ設定
  - logging_setup.setup_logging(app_name="...") を呼ぶことで stdout + 日次ローテートファイル出力を統一的に設定します。
- プロセス優先度
  - 主要スクリプトは set_process_priority("high") を最初に呼び、優先度を上げようとします（権限がない場合は警告でスキップ）。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys をルートとした相対パス）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / DB ラッパー
    - system_monitor.py
    - trade_monitor.py        — （コード省略分ありが存在想定）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （実装ファイルが存在すればアラート管理）
    - monitoring_engine.py

  - execution/
    - execution_engine.py    — ExecutionEngine（起動ロジック）
    - broker_factory.py      — ブローカクライアントの生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py

  - tools/
    - paper_verification_report.py
    - __init__.py

運用上のヒント
--------------
- 本番運用では KABUSYS_ENV=live とし、LINE 通知や各種閾値を十分に確認してください（validate_config で live 時のガードチェックあり）。
- .env は機密情報を含むため Git にコミットしないでください。
- データベースやログディレクトリは定期バックアップ・ローテーションを検討してください。
- OpenAI を用いる機能は API 利用料が発生するため、利用頻度とバッチ設定（_BATCH_SIZE、トークン制限）に注意してください。

サポート / 追加情報
-------------------
この README はコード内 docstring と実装に基づいて生成しています。各モジュール内に詳細な docstring と使用例が記載されていますので、より深い仕様確認や拡張は該当モジュールのソースを参照してください。

必要であれば README にサンプル .env テンプレートや起動サービス定義（systemd ユニットファイル例）を追加できます。どの情報が必要か教えてください。