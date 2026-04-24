KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
主な目的は「データ取り込み・ファクター計算・ポートフォリオ構築・発注・監視・リスク制御」を統合した軽量な実行基盤を提供することです。本リポジトリは以下の主要コンポーネントを含みます:

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム状態・注文状態・リスク監視、Kill Switch）
- Research（ファクター計算・特徴量解析）
- Portfolio（候補選定・配分・株数決定）
- AI モジュール（ニュースセンチメント、レジーム判定）
- CLI ツール（環境設定ウィザード、設定検証、Paper Trading レポート）

主な機能
--------
- 実行環境切替（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient を用い、本番 DB と分離した data/paper_trading.db に記録
- ExecutionEngine
  - ブローカークライアント（実ブローカーまたはモック）
  - OrderManager / Reconciler / RiskManager による注文管理とリスク制御
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor：注文滞留や約定異常検出（実装ファイル多数）
  - RiskMonitor：ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch：フラグファイルにより ExecutionEngine 停止トリガー
  - AlertManager（通知送信ロジックを想定）
- Research / Portfolio
  - Momentum, Volatility, Value などのファクター計算（DuckDB を想定）
  - ポートフォリオ候補選定、重み付け、ポジションサイズ計算（lot / rounding / aggregate cap）
- AI（OpenAI）
  - news_nlp: ニュースを LLM でセンチメント評価して ai_scores に書き込み
  - regime_detector: MA200 とマクロニュースの LLM スコアを合成して日次レジーム判定
- ユーティリティ
  - logging_setup（統一ログ設定：stdout + 日次ローテート）
  - process_priority（OSに依存しない優先度・CPU affinity 設定）
- ツール
  - config_setup: .env を対話的に作成・更新
  - validate_config: 起動前に環境・config ファイルを検証
  - paper_verification_report: ペーパートレードログ解析レポート生成

セットアップ手順
----------------
前提
- Python 3.10 以上（PEP 604 の | 型注釈を使用）
- SQLite（標準ライブラリで使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証を行う場合）

例（venv を使う）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を推奨）

3. .env の準備
   - python -m kabusys.config_setup
     - 対話式で .env を生成できます（.env は絶対に Git にコミットしないでください）
   - または .env を手動で作成（下記「環境変数」を参照）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います

環境変数（代表）
----------------
（.env に設定する想定）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う場合
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番通知用（任意）

特記事項:
- .env は自動読み込みされます（プロジェクトルートが特定可能な場合）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- PAPER_FILL_MODE: paper_trading の MockBrokerClient の約定挙動。valid: instant|partial|never|reject

起動・使い方
------------

監視ループ（Monitoring）
- 起動:
  - python -m kabusys.run_monitoring
- 動作:
  - デフォルトで 60 秒ごとに SystemMonitor を走らせます。ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒）。
  - 停止:
    - data/stop_requested.flag が存在するとループが終了します（ファイルを置くだけで停止シグナル）。
  - ログ:
    - logs/monitoring.log に日次ローテートで出力されます（LOG_DIR を変更可）。

Execution（発注エンジン）
- 起動:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db を使います（production DB と分離）。
  - 実行中は data/execution.pid ファイルを作成します。
  - 停止:
    - data/stop_requested.flag が置かれるとエンジンが停止します。
    - KillSwitch（kill.flag）によって ExecutionEngine に停止指示を送ることも可能（Monitoring の判定で書き込む）。
- 注意:
  - 起動前に kill.flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1（ただし本番では危険）

環境設定ウィザード
- python -m kabusys.config_setup
- .env を対話式に生成・更新します

設定検証
- python -m kabusys.validate_config
- --strict を付けると警告で exit(1) になります

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
- 出力: 稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定

AI 機能（ニュース / レジーム判定）
- 環境変数 OPENAI_API_KEY を設定してください
- プログラム的に呼び出し:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)
- OpenAI API はリトライ／バックオフを実装していますが、APIキーの管理と利用コストに注意してください

停止フラグ / Kill Switch
- data/stop_requested.flag
  - run_monitoring / run_execution がループ終了/停止のために監視するファイル
- data/kill.flag
  - Monitoring の KillSwitch が条件を満たした際に書き込み、ExecutionEngine 停止トリガーとして機能
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に自動クリアされます（本番では推奨されません）

ディレクトリ構成
----------------
（パッケージの主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite による監視ログ永続化層
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム状態・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - trade_monitor.py        — 注文状態監視（該当ファイル群）
    - kill_switch.py          — kill.flag 書き込みロジック
    - alert_manager.py        — 通知ロジック（実装想定）
  - execution/
    - execution_engine.py
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
    - news_nlp.py
    - regime_detector.py
  - data/                     — 実行時に使用する SQLite / pid / flag 等を置くことを想定
  - config/                   — yaml 設定ファイル群（system_config.yaml 等）

運用上の注意
-------------
- .env は機密情報（APIキー等）を含むため絶対にコミットしないでください。
- KABUSYS_ENV=live の場合は特に設定を慎重に確認してください（validate_config は本番向けチェックを出します）。
- Logging: デフォルトで stdout と logs/<app>.log に出力します。ログディレクトリの権限・ディスク容量に注意してください。
- AI モジュール利用時は API レートやコスト管理を行ってください。失敗時はフォールバック挙動が組み込まれていますが、設計上外部API依存が存在します。
- DB（SQLite / DuckDB）ファイルはローカルファイルとして扱われます。バックアップ / 同時書き込みに注意してください（SQLite は単一プロセス書き込みが望ましい）。

開発者向けヒント
-----------------
- ログ設定を変更したい場合は kabusys.utils.logging_setup.setup_logging を呼び出す際に引数を指定してください。
- テストでは Settings の自動 env ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- AI の外部呼び出し箇所はテストで unittest.mock.patch による差し替えを想定しています（_call_openai_api 等）。

貢献
----
バグ報告・機能提案は Issue でお願いします。プルリクエストは歓迎しますが、.env やシークレットは含めないでください。

ライセンス
--------
（プロジェクトのライセンス情報をここに記載してください。例: MIT / Apache-2.0 等）

以上。README に含めたい追加情報（例: 実行例、サンプル .env、requirements.txt）や、特定のファイルの詳細な説明が必要であれば教えてください。