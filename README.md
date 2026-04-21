README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なフレームワークです。本リポジトリは次を提供します。

- 実行エンジン (ExecutionEngine)：発注・リスク管理・再調整などの実行ロジック（本番 / ペーパートレード対応）
- 監視コンポーネント (Monitoring)：システム稼働状況・注文ログ・リスク監視と Kill Switch の管理
- ポートフォリオ構築ユーティリティ：候補選定、重み付け、ポジションサイズ算出、セクター制約などの純粋関数群
- リサーチ機能：ファクター計算、将来リターン、IC 計算、統計サマリー
- AI 補助（OpenAI 統合）：ニュースの NLP スコアリング、レジーム判定（OpenAI API を利用）
- 運用用ユーティリティ：設定ウィザード、設定検証、ペーパートレード検証レポート生成、ログ設定 等

主な特徴
--------
- 環境切替：KABUSYS_ENV により development / paper_trading / live を切替
- ペーパートレード分離：paper_trading モードでは専用の SQLite（data/paper_trading.db）を使用
- 監視・Kill Switch：稼働率・ドローダウン・ポジション上限等で自動的に停止フラグを書き込める
- DuckDB を利用した高速な時系列 / 財務データ処理（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントやマクロセンチメントの評価（オプション）
- ロギング：コンソール + 日次ローテートファイル（logs/）を標準化

必要条件
--------
- Python 3.10 以上（型表記で | 演算子を使用）
- 主な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config/*.yaml の検証を行う場合、任意）
- SQLite とファイルシステム（data/、logs/ 等）への書き込み権限

セットアップ手順
---------------
1. リポジトリをクローン・作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （検証用に PyYAML を入れる場合）pip install pyyaml

4. 初期設定ファイル (.env) を作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - または .env を手動で作成 .env.example を参照して必要な値を設定

主要な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading モードで使用; デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う場合に設定
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

設定検証・ウィザード
-------------------
- .env を対話的に作成/更新:
  - python -m kabusys.config_setup
- 設定検証（.env と config/*.yaml の基本チェック）:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになる: python -m kabusys.validate_config --strict

使い方（運用）
--------------
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 動作: Settings を読み、環境に応じて本番または paper_trading 用 DB 接続・BrokerClient を作成し、ExecutionEngine をスレッドで実行。停止は data/stop_requested.flag を作成するか kill.flag を利用。

- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
  - 動作: SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、必要に応じて kill.flag を書き込み・LINE 等へ通知（設定されている場合）。MONITOR_POLL_INTERVAL で間隔を上書き可。

- Paper Trading 検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能

- AI スコアリング / レジーム判定（プログラム呼び出し）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーは引数か OPENAI_API_KEY 環境変数で指定

停止・Kill Switch
----------------
- 実行エンジンは以下のフラグで停止制御されます:
  - data/stop_requested.flag: run_execution / run_monitoring のループを終了させるローカル停止フラグ
  - data/kill.flag: KillSwitch によって書き込まれる停止シグナル（ExecutionEngine は起動時にこのフラグの有無をチェック）
- KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動で削除します（本番では 0 推奨）

ログ
----
- ログは標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）へ出力されます。
- ログ関連設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- LOG_DIR 環境変数でログ保存先を変更できます。

主要モジュール（概要）
--------------------
- kabusys.config
  - 環境変数・.env 自動読み込み、Settings クラス（アプリ設定の集中管理）
- kabusys.config_setup
  - .env 対話式ウィザード
- kabusys.validate_config
  - 起動前に環境設定と config/*.yaml を検証する CLI
- kabusys.run_execution
  - ExecutionEngine 起動スクリプト（本番 / ペーパートレード分岐、DB 初期化、PID 管理）
- kabusys.run_monitoring
  - SystemMonitor をポーリングする監視プロセス起動スクリプト
- kabusys.monitoring
  - monitoring_db: SQLite テーブル定義と永続化ラッパ
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager
- kabusys.execution
  - ExecutionEngine、OrderManager、RiskManager、Reconciler、BrokerClientFactory 等（発注ロジック）
- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment（候補選定・重み・株数算出・セクター制約）
- kabusys.research
  - factor_research, feature_exploration（モメンタム・ボラティリティ・バリュー等の計算、IC、統計）
- kabusys.ai
  - news_nlp, regime_detector（OpenAI を使った NLP スコアリング・レジーム判定）
- kabusys.tools
  - paper_verification_report（ペーパートレード検証レポート生成）
- kabusys.utils
  - logging_setup, process_priority（ログ設定・プロセス優先度 / CPU affinity）

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py                — パッケージ定義
- config.py                  — Settings / .env 自動読み込み
- config_setup.py            — .env 対話式ウィザード CLI
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring 起動スクリプト

- ai/
  - news_nlp.py              — ニュース NLP スコアリング
  - regime_detector.py       — 市場レジーム判定
- monitoring/
  - monitoring_db.py         — SQLite スキーマ + 永続化クラス
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
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では特に LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を慎重に確認してください。
- OpenAI を利用する機能は API 利用料が発生します。API キーの管理とコストに注意してください。
- データファイル（DuckDB/SQLite/ログ等）はデフォルトで data/ や logs/ に作成されますが、環境変数で変更できます。
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を参照）。

開発者向け
----------
- ユニットテストやモジュール間の依存を切るため、AI 呼び出し部分はラップされており、テスト時はモック差し替えが可能です（例: unittest.mock.patch）。
- DuckDB 接続をテストで差し替えれば、ファイル I/O を伴わない高速なユニットテストが書けます。
- 設計は「副作用を最小化する純粋関数 + 永続化層（monitoring_db）」で分離されています。ビジネスロジックはライブラリ関数として呼び出せます。

サンプルコマンドまとめ
---------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
- 本リポジトリに含まれるライセンス情報や貢献ガイドラインは別途 LICENSE / CONTRIBUTING ファイルを参照してください（無い場合は管理者に問い合わせてください）。

以上。運用や実装に関して具体的な質問（例: 特定モジュールの API、設定例、トラブルシュート） があればお知らせください。