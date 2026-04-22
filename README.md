KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージです。本リポジトリは以下の機能群を備えます。

- 実行エンジン（ExecutionEngine）: 注文発行・リスク管理・リコンシリエーションを行う
- 監視機構（Monitoring）: システム状態・注文/約定・リスクを定期的にチェックし、Kill Switch を発動可能
- ポートフォリオ構築ユーティリティ: 銘柄選定・重み計算・ポジションサイズ計算・セクター制限
- リサーチ/ファクター計算: モメンタム・ボラティリティ・バリュー等の計算、IC/統計サマリ
- AI 補助モジュール: ニュースの LLM ベースのセンチメントスコア算出・市場レジーム判定
- 運用支援ツール: .env 作成ウィザード、設定検証、Paper Trading 検証レポート 等

主な設計方針:
- 本番／ペーパートレードで DB を分離（paper_trading モードでは専用 SQLite を使用）
- DuckDB を分析用 DB として使用。DuckDB 接続を受け取る純粋関数群を提供
- OpenAI（gpt-4o-mini）を用いる NLP 処理は API キーを外部で指定し、失敗時は安全にフォールバック

機能一覧
--------
- 実行系
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて MockBroker を使用）
  - ブローカーファクトリ、OrderManager、OrderRepository、RiskManager、Reconciler を含む
- 監視系
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔制御）
  - MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard を管理
  - RiskMonitor, TradeMonitor, SystemMonitor, MonitoringEngine, KillSwitch, AlertManager（通知管理は実装箇所に依存）
- ポートフォリオ
  - 銘柄候補選定（select_candidates）
  - 等配分・スコア配分（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- リサーチ
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC（calc_forward_returns, calc_ic）
  - 統計サマリ（factor_summary）
- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約して LLM に投げ、ai_scores に書き込む
  - regime_detector.score_regime: マクロニュース + ETF MA を組み合わせてレジーム判定・永続化
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成

前提条件 / 必要ライブラリ
-----------------------
- Python 3.9+
- 依存パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML の構文チェックを行いたい場合、任意）
- 推奨: 仮想環境（venv / poetry / pipenv 等）

セットアップ手順
----------------
1. リポジトリをクローンしてソースディレクトリに移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は最低限: pip install duckdb psutil openai
   - （PyYAML を使う場合）pip install pyyaml

4. .env の作成（推奨: 対話式ウィザードを利用）
   - python -m kabusys.config_setup
   - J-Quants リフレッシュトークン（JQUANTS_REFRESH_TOKEN）や KABU_API_PASSWORD 等は必須
   - KABUSYS_ENV は development / paper_trading / live のいずれか

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります

使い方（実行例）
----------------
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 注意: 起動時に data/execution.pid や data/stop_requested.flag 等のフラグを確認します。
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、データは data/paper_trading.db に記録されます。

- 監視ループを起動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は常に「本番」用 sqlite_path を使用します（monitoring は環境に依存せず本番 DB を参照）

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を直接指定: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- .env の生成/編集:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告でエラー終了します

- AI 関連（プログラムから呼び出し例）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="sk-...")

重要な環境変数
----------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用関連:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - OPENAI_API_KEY: OpenAI API を使う際に必要
  - PAPER_FILL_MODE: paper_trading の MockBroker のフィルモード（instant/partial/never/reject）
  - PAPER_TRADING_SQLITE_PATH: paper_trading DB のパス（デフォルト data/paper_trading.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - LOG_LEVEL, LOG_DIR
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- 監視ループ:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

運用メモ / 実装上の注意
---------------------
- データベース:
  - init_monitoring_db() は監視用 SQLite を初期化（冪等）。既存 DB のマイグレーションも一部対応（列追加等）。
  - paper_trading モードは paper_sqlite_path を使用して本番 DB と分離。
- Kill Switch:
  - RiskMonitor が検知した重大アラートを KillSwitch が data/kill.flag に書き込み、ExecutionEngine は起動中にこのフラグを検出して停止します。
  - 本番環境で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動で消す設定が有効になりますが、注意が必要です。
- ロギング:
  - setup_logging() は stdout と日次ローテートされたファイル（logs/<app_name>.log）を設定します。ログディレクトリは LOG_DIR または logs/。
- プロセス優先度:
  - run_execution/run_monitoring は起動時に set_process_priority("high") を呼んでプロセス優先度を上げます。権限不足時は警告が出ます。
- AI API:
  - OpenAI 呼び出しはリトライやバックオフを実装しているが、API キーの管理とコストに注意してください。
  - news_nlp・regime_detector は外部 API を使用するため、API キー未設定時は ValueError を送出します（使わないなら無視可）。
- テストとサンドボックス:
  - KABUSYS_ENV=development では発注が行われないような実装想定（各 Broker の Mock 実装に依存）。
  - Paper Trading は発注ロジックの検証に便利です（専用 DB に記録される）。

ディレクトリ構成 (主要ファイル)
-----------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — Execution 系の実装群（broker_factory 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

付録: よくある運用コマンド
------------------------
- .env を作る（対話式）
  - python -m kabusys.config_setup
- 設定チェック
  - python -m kabusys.validate_config
- 実エンジン起動（デーモンは別途 systemd / supervisor などで管理推奨）
  - python -m kabusys.run_execution
- 監視プロセス起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張
----------------
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）は外部データパイプラインで用意する必要があります（kabusys.data.pipeline モジュール等を参照）。
- Broker 実装や通知（LINE 等）は各社 API トークンを .env に設定することで有効化できます。
- 追加の監視ルールやアラートチャンネルは monitoring/alert_manager.py を拡張してください。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = 0.1.0（src/kabusys/__init__.py）
- ライセンス情報は本リポジトリの LICENSE ファイルを参照してください（存在する場合）。

おわりに
--------
この README はコードベースから主要な使用方法・設計方針を抜粋した概要です。実運用前に必ず python -m kabusys.validate_config による事前チェックを行い、.env 設定と DB パスを正しく構成してください。必要があれば用途に応じた systemd ユニットやコンテナ化を検討してください。