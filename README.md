KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買／研究基盤の内部ライブラリ群です。  
主な目的は以下のとおりです。

- 戦略のファクター計算・研究モジュール（DuckDB を使用）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行エンジン（ExecutionEngine）およびペーパートレード分離
- 監視（System / Trade / Risk）と Kill Switch
- ニュース NLP（OpenAI）を使ったセンチメント評価、レジーム判定
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

主な機能
--------
- 環境設定管理（.env 自動ロード、Settings クラス）
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
- 監視ループ起動スクリプト（run_monitoring.py）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照（環境に依存せず監視 DB を扱う設計）
- 設定ウィザード（config_setup.py）
  - 対話形式で .env を生成・更新
- 設定検証 CLI（validate_config.py）
  - .env および config/*.yaml の基本チェック
- Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - 稼働率、注文成功率、レイテンシ等のサマリと PASS/FAIL 判定
- 研究モジュール（research/*.py）
  - モメンタム・ボラティリティ・バリューなどのファクター計算
  - 将来リターン、IC（情報係数）、統計サマリなど
- AI 関連（ai/news_nlp.py, ai/regime_detector.py）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価、日次レジーム判定
  - API の失敗時はフェイルセーフ（スコア 0.0 にフォールバックなど）
- 監視サブシステム（monitoring/*）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - KillSwitch によるフラグファイル書き込みで ExecutionEngine を停止させる仕組み
- 汎用ユーティリティ（utils/*）
  - ロギングセットアップ（ファイルローテーション付き）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

要件（推奨）
-----------
- Python >= 3.10
- 主な依存パッケージ（少なくとも実行に必要なもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config 検証で YAML 内容チェックを行う場合は任意）
- その他、環境に応じたパッケージ

インストール例（開発用）
-----------------------
例:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

環境設定
--------
設定は環境変数（またはプロジェクトルートの .env/.env.local）で行います。自動的に .env をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

代表的な環境変数とデフォルト:
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEFAULT INFO）
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- PAPER_FILL_MODE: paper_trading の MockBroker 動作（instant|partial|never|reject）

.env を対話的に作成する:
- python -m kabusys.config_setup

設定検証:
- python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit code 1）

使い方（主要コマンド）
---------------------

1) 実行エンジンを起動（ローカル実行、またはデプロイ先で）
- python -m kabusys.run_execution
  - 起動時に KABUSYS_ENV を設定すると paper_trading / live 等の挙動に切り替わります。
  - paper_trading の場合、MockBroker を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 実行中の終了は data/stop_requested.flag を作成することで検知され、Engine を停止します。
  - PID は data/execution.pid（Settings.pid_file_path のデフォルト）に書き込まれます。

2) 監視ループを起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は monitoring DB（Settings.sqlite_path、デフォルト data/monitoring.db）へログを残します。
  - 監視プロセスの優先度は起動時に High に設定されます（psutil による設定、権限が無ければ警告を出してスキップ）。

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db を指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を使用
  - 出力は標準出力にテキストレポート（稼働率、成功率、レイテンシ指標、PASS/FAIL）

4) AI 関連機能（プログラム経由での呼び出し）
- ニュースセンチメント評価:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY（または api_key 引数）必須

ログ出力
-------
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一されます。
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- 日次ローテート（30 日保存）

停止・Kill Switch（安全停止）
---------------------------
- 実行停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring が監視して起動/ループを終了するために使用
- Kill Switch（自動停止）:
  - Monitoring サブシステムが条件（ドローダウン超過・ポジション上限超過等）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促します
  - Kill flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリア（注意: 本番では 0 推奨）

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py               — Settings / .env 自動ロードロジック
- config_setup.py         — .env 対話型ウィザード
- validate_config.py      — 設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — Monitoring 起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py           — ニュースセンチメント（OpenAI）
  - regime_detector.py    — レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py      — SQLite 監視 DB スキーマ・読み書き
  - system_monitor.py     — システム・データ鮮度監視
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - trade_monitor.py      — （※省略ファイルは存在）取引監視
  - monitoring_engine.py  — Monitor を束ねるエンジン
  - kill_switch.py        — kill.flag の書き込みロジック
  - alert_manager.py      — （通知機能を提供する想定）
- execution/
  - execution_engine.py   — ExecutionEngine 実装（起動・セッション管理）
  - order_manager.py
  - order_repository.py
  - broker_factory.py     — ブローカークライアント生成（本番 / Mock）
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py  — 候補選定・重み付け
  - position_sizing.py    — 株数・丸めロジック
  - risk_adjustment.py    — セクター制限、レジーム乗数
- research/
  - factor_research.py    — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py— 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート CLI
- utils/
  - logging_setup.py      — ログ設定
  - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ

データ・ログファイル（デフォルト）
- data/kabusys.duckdb          — DuckDB（分析データ）
- data/monitoring.db           — 監視用 SQLite（system_status, trade_logs, positions, risk_logs, dashboard）
- data/paper_trading.db        — ペーパートレード専用 SQLite（paper_trading 環境時）
- data/execution.pid           — ExecutionEngine の PID
- data/stop_requested.flag     — 即時停止用フラグ（手動／スクリプトで作成）
- data/kill.flag               — Monitoring による自動停止フラグ
- logs/<app>.log               — ログファイル（例: logs/execution.log）

開発メモ / 注意点
-----------------
- Settings クラスは環境変数を直接参照します（必須変数は _require() によりエラーになる）。.env を用意しておくこと。
- AI モジュールは OpenAI API を呼び出します。API 呼び出しはリトライ・フェイルセーフ設計になっていますが、APIキーは必須です。
- Paper Trading と本番 DB は分離されています（PAPER_TRADING_SQLITE_PATH を利用）。
- run_monitoring は監視 DB に常に本番 sqlite_path を使って接続します（監視と実行の DB 分離を徹底するため）。
- ログディレクトリ作成に失敗するとファイル出力をスキップしてコンソールのみで稼働します。
- プロセス優先度 / CPU affinity の設定は OS に依存し、権限不足で設定に失敗することがあるので警告を出して継続します。

ライセンス・バージョン
----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はプロジェクトルートの LICENSE を参照してください（無い場合はプロジェクトルールに従ってください）。

サンプルコマンドまとめ
---------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

お問い合わせ / 変更履歴
--------------------
- 主要な設計判断やパラメータ（例: ポジション上限、リスクパラメータ、ログ保持日数等）はソース内コメントや PortfolioConstruction.md / StrategyModel.md 等のドキュメントを参照してください（該当ドキュメントが存在する場合）。

以上。必要であれば README にサンプル .env テンプレートや具体的なコマンド例（systemd ユニット、Docker など）を追加しますか？