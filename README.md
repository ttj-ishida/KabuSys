README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。本リポジトリは以下の主要コンポーネントを含みます。

- 注文実行エンジン（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk Monitor と Kill Switch）
- ポートフォリオ構築（候補選定・配分・株数計算・セクター制限）
- リサーチ（ファクター計算・特徴量探索）
- AI 周りの機能（ニュースセンチメント / レジーム判定、OpenAI API 利用）
- 開発用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

設計上の注意点
- 環境変数で挙動を切り替えます（KABUSYS_ENV: development / paper_trading / live）。
- Paper Trading モードでは MockBrokerClient を使い、発注ログは専用の SQLite（data/paper_trading.db）へ記録して本番 DB と分離します。
- 監視（monitoring）は KABUSYS_ENV に関わらず常に本番用の sqlite_path を使用します（監視データの一元化）。
- AI 機能は OpenAI API（例: gpt-4o-mini）を利用します。利用時は OPENAI_API_KEY を設定してください。

主な機能
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - ブローカークライアント生成（本番 / mock を切り替え）
  - OrderRepository / OrderManager / RiskManager / Reconciler の組み立て
  - 実行スレッド管理、PID ファイル、停止フラグ監視

- 監視起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして DB にログ保存
  - Kill Switch 評価により kill.flag を書く（ExecutionEngine 停止トリガ）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）

- 監視永続化層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルの作成・マイグレーション
  - ログ書き込み・ダッシュボードの upsert 等のユーティリティ

- ポートフォリオ構築（portfolio/）
  - 候補選定（スコア順・上位 N）
  - 等重・スコア加重の重み計算
  - 株数決定（リスクベース、等配分等）、単元（lot）単位で丸め、aggregate cap のスケーリング
  - セクター上限適用、レジームに応じた投下乗数計算

- リサーチ（research/）
  - Momentum / Value / Volatility 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ機能

- AI（ai/）
  - ニュースセンチメントの LLM スコアリング（raw_news → ai_scores）
  - マクロニュース＋ETF の MA200 乖離を組み合わせた市場レジーム判定（market_regime テーブルへ書き込み）
  - OpenAI API 呼び出しはリトライ・バリデーション・クリッピングを備えた実装

- 開発・運用ユーティリティ
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）

セットアップ手順
--------------
1. Python 環境
   - 推奨: Python 3.9+
   - 仮想環境を作成して有効化します:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - requirements.txt がない場合は必要なパッケージを個別に入れてください。主な依存:
     - duckdb
     - psutil
     - openai
     - （開発時）PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 環境変数（.env）
   - プロジェクトルートに .env を作成するか、対話式ウィザードを利用します:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なデフォルト
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定してください（score_news / score_regime が必要）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付ける

使い方
------
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 停止方法:
    - data/stop_requested.flag を作成すると実行中のエンジンは検出して終了します（run_execution が参照）。
    - Kill Switch（監視側）が致命的条件で data/kill.flag を書くとエンジン停止を促します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用してログ保存します（KABUSYS_ENV に依存しない）。

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラーとして扱い exit(1) になります。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH

主要な環境変数（一覧）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)

- データベース
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用データベース、デフォルト data/paper_trading.db)

- ロギング
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR（ログ出力先。デフォルト logs/）

- AI
  - OPENAI_API_KEY（AI 機能で必須）

- 監視・Kill Switch
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（0/1。本番では 0 推奨）

- 監視間隔
  - MONITOR_POLL_INTERVAL（run_monitoring で上書き可能、デフォルト 60 秒）

停止フラグ / PID
----------------
- 停止リクエスト:
  - data/stop_requested.flag — run_execution / run_monitoring はこのファイルの存在を見て終了処理を行います。
- Kill Switch:
  - data/kill.flag — 監視コンポーネントが致命的条件を検知するとこのファイルを書き込み ExecutionEngine 停止を促します。
- PID:
  - data/execution.pid — 実行エンジンの PID ファイル（Engine 起動時に扱います）。

ログ
----
- ログはコンソール（stdout）とファイル（logs/<app_name>.log）へ出力され、日次ローテーション（30日保持）されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging から統一的に行われます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数/設定読み取り
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py                — ニュースセンチメント（OpenAI 呼び出し）
  - regime_detector.py         — 市場レジーム判定（MA200 + マクロ）
- monitoring/
  - monitoring_db.py           — SQLite テーブル定義・永続化層
  - system_monitor.py          — システム状態・データ鮮度監視
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - trade_monitor.py           — （trade 監視ロジック）
  - monitoring_engine.py       — Monitor を束ねる
  - kill_switch.py             — kill.flag の管理
  - alert_manager.py           — （アラート送信ロジック）
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
- monitoring/
  - monitoring_db.py (上記)
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

補足・運用上の注意
------------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知などのアラート設定を確認してください。
- KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動クリアしますが、本番では推奨されません（安全性低下）。
- AI 機能は API の利用料金や呼び出し制限に注意してください（リトライ・バックオフの実装あり）。
- DuckDB / SQLite のパスやログディレクトリは環境変数で柔軟に指定できます。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

お問い合わせ
------------
実装や運用に関する質問があれば、リポジトリ管理者または開発チームへ問い合わせてください。README に未記載の詳細（CI、デプロイ手順、運用 runbook 等）は別途提供される想定です。