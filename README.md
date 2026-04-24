README — KabuSys（日本語）
=======================

概要
----
KabuSys は日本株の自動売買・研究基盤を想定した Python パッケージです。本リポジトリは取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を使ったニュース解析など、運用に必要なコンポーネント群をモジュール化しています。

主な特徴
--------
- ExecutionEngine（発注ロジック）と Monitoring（稼働監視 / Kill Switch）を独立して起動可能
- Paper Trading（ペーパートレード）モードで本番 DB と分離された専用 SQLite を使用
- DuckDB を利用したファクタ計算 / 研究機能（prices_daily / raw_financials 等を想定）
- OpenAI を用いたニュース NLP スコアリング・レジーム判定（gpt-4o-mini を想定）
- ログ出力はコンソール + 日次ローテートファイルを標準で設定
- .env ウィザード、設定検証 CLI、検証レポート等の補助ツールを提供

前提 / 依存関係
---------------
最低限必要な Python パッケージ（代表例）:
- python >= 3.9
- duckdb
- psutil
- openai
- PyYAML（config 検証で YAML のパースを行う場合に必要）

インストール例:
    python -m pip install -r requirements.txt
（requirements.txt がない場合は上記パッケージを個別にインストールしてください）

セットアップ手順
----------------
1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して依存ライブラリをインストール
3. 環境変数設定 (.env) — 対話式ウィザードを推奨

対話式で .env を作成する:
    python -m kabusys.config_setup

ウィザードで設定する主なキー（.env に書き込まれる例）:
- KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 任意（本番アラート用）
- LOG_LEVEL — デフォルト: INFO
- KILL_FLAG_CLEAR_ON_START — 0/1（本番では 0 推奨）

設定検証:
    python -m kabusys.validate_config
--strict を付けると警告も失敗扱い（exit code 1）になります。

環境変数の自動ロード:
- プロジェクトルートに .env / .env.local がある場合、自動的に読み込まれます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（抜粋、デフォルト）
---------------------------------
- KABUSYS_ENV: development | paper_trading | live（default: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- LOG_DIR: logs/
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、監視起動時に使用、default: 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）

使い方
------

起動スクリプト（代表）
- 監視ループを起動（system / trade / risk の監視を行う）:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に「本番 sqlite_path（Settings.sqlite_path）」を使用して監視テーブルに記録します。
  - data/stop_requested.flag（リポジトリ相対）にファイルが作られるとループを抜けます。

- 実行エンジンを起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在する場合はエンジンを起動せず終了します。
  - 実行中は PID ファイル（デフォルト data/execution.pid）を書きます。停止は監視側の stop flag により行われます。

停止 / Kill Switch
- KillSwitch（監視コンポーネント）はリスク基準（ドローダウン・ポジション上限等）を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine はこの kill.flag を検出して安全に停止する仕組みを想定しています。
- stop_requested.flag を作成すると run_monitoring / run_execution 両方が起動中に検出して終了します（運用上の停止手段）。

ログ
- ログは標準出力（stdout）とファイル出力（logs/<app_name>.log、日次ローテーション、30日保持）に出力されます。ログディレクトリは LOG_DIR 環境変数で指定できます。
- ログレベルは LOG_LEVEL で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

ツール / 追加コマンド
- ペーパートレード検証レポート生成:
    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

- AI 系関数（ライブラリ API）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数か環境変数 OPENAI_API_KEY で指定します。

設計上の注意点 / 運用メモ
-----------------------
- ExecutionEngine の paper_trading モードは実発注を行わない想定ですが、設定ミスで本番側 API が叩かれないよう .env の KABUSYS_ENV を慎重に設定してください。
- ローカルでの .env 自動読み込みはプロジェクトルート（.git あるいは pyproject.toml）を基準に行われます。CI やテストで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process priority / CPU affinity の設定は psutil を用いて行います。権限がない環境では設定に失敗することがあります（警告でスキップされます）。
- DuckDB への書き込みや executemany の仕様はバージョン差に影響されることがあります（コード内に互換性対策あり）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py             — 環境設定 / Settings クラス（.env 読み込みロジック含む）
- config_setup.py       — .env 対話式ウィザード
- validate_config.py    — 起動前設定検証 CLI
- run_execution.py      — ExecutionEngine 起動スクリプト
- run_monitoring.py     — Monitoring ポーリングループ起動スクリプト

subpackages:
- ai/
  - news_nlp.py         — OpenAI を使ったニューススコアリング
  - regime_detector.py  — マーケットレジーム判定
- monitoring/
  - monitoring_db.py    — SQLite スキーマ / 永続化ロジック
  - system_monitor.py   — システム / データ鮮度監視
  - trade_monitor.py    — （trade 関連監視ロジック、想定）
  - risk_monitor.py     — ドローダウン / ポジション上限監視
  - kill_switch.py      — kill.flag 管理
  - monitoring_engine.py— 複数モニタの束ね
  - alert_manager.py    — （通知管理）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py    — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度設定ユーティリティ
- tools/
  - paper_verification_report.py

（上記以外にも補助モジュールが含まれます。実際のファイル一覧はリポジトリを参照してください。）

サンプル運用ワークフロー
-----------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / SQLite の初期化は各起動スクリプト内で必要に応じて行われるため、基本的にファイルパスを設定して起動するだけで運用できます。
4. 監視を先に起動:
    MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
5. 実行エンジンを起動:
    python -m kabusys.run_execution
6. 監視が Kill Switch を検出した場合、data/kill.flag が作成され、Execution 側が検出して安全停止します。

ライセンス・貢献
----------------
本 README はコードベースの説明を目的としています。ライセンスやコントリビュート方法はリポジトリのトップレベルにある LICENSE / CONTRIBUTING 等のファイルを参照してください。

補足
----
- コード中にコメントや docstring で多くの運用ルールや実装上の注意が記載されています。運用前に各モジュール（特に execution/, monitoring/, ai/）の docstring を確認することを推奨します。
- 本 README は現時点での主要機能と使い方の概略を示したものです。さらに詳細な運用手順・設計文書はプロジェクト内のドキュメント（Markdown 等）を参照してください。

以上。