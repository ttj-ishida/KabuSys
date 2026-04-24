README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なフレームワークです。本リポジトリは以下の主要機能を備えています。

- ExecutionEngine（発注エンジン）: 本番／ペーパートレード双方に対応した発注実装（BrokerClientFactory により実ドライバ／モック切替）
- Monitoring（監視）: システム稼働状況や注文履歴、リスク指標のポーリング監視と永続化
- Portfolio Construction: 候補選定、重み計算、ポジションサイズ計算、セクターキャップ等の純粋関数群
- Research: DuckDB を用いたファクター計算・特徴量解析（モメンタム／ボラティリティ／バリュー等）
- AI モジュール: ニュース記事のセンチメント集計（OpenAI）や市場レジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード・検証ツール 等

特徴
----
- SQLite（監視 DB / ペーパートレード DB）と DuckDB（分析用）を併用
- 本番とペーパートレードの明確な分離（PAPER_TRADING_SQLITE_PATH）
- .env ベースの設定管理と対話式ウィザード（config_setup.py）
- Kill Switch（data/kill.flag）や stop フラグファイル（data/stop_requested.flag）による運用停止制御
- ログはコンソールと日次ローテーション（logs/*.log）に出力

セットアップ手順
----------------

前提
- Python 3.10 以上推奨（PEP604 の | 型や match 等を想定）
- SQLite（標準ライブラリに含まれる）
- Git レポジトリのルートをプロジェクトルートとして検出する仕組みあり

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意: pip install PyYAML   （config/*.yaml の内容検証を行いたい場合）
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt

4. 初期設定（.env）の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成された .env を編集して必要な環境変数を確認してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトでは data/ 以下に DB や PID / フラグファイルが配置されます。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を調整してください。

主要環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に注文を記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API を使うモジュールで利用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に data/kill.flag を自動クリアするか（"1" でクリア）

使い方
------

起動スクリプト（モジュール実行推奨）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）

- 発注エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定するとモックブローカーを使い data/paper_trading.db に記録されます
  - run_execution は data/stop_requested.flag の存在を検知して停止します。起動時に既にフラグがあると起動せず終了します。

設定操作
- .env 対話式生成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）

ツール
- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB を指定する場合: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を設定

ライブラリの呼び出し例（Python REPL）
- AI ニューススコア（日次）を書き込む:
  - from datetime import date
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, date(2026, 4, 1), api_key="sk-...")

- レジームスコア生成:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, date(2026, 4, 1), api_key="sk-...")

- ファクター計算（Research）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - calc_momentum(conn, date(2026,4,1))

運用上のファイル・フラグ
- data/stop_requested.flag
  - run_monitoring や run_execution のポーリングループはこのファイルの存在を検知して安全終了します。外部プロセス（デプロイシステムなど）から停止を促す際に用いてください。
- data/kill.flag
  - KillSwitch が書き込むファイルで、ExecutionEngine に対する停止（Kill Switch）を表します。実行エンジンは起動時にこのフラグを検知すると起動を行わない、または運用側で明示的に扱います。
- PID ファイル
  - data/execution.pid（ExecutionEngine 用デフォルト）

ログ
- デフォルトのログディレクトリ: logs/
- 各アプリ（execution / monitoring など）ごとに <app_name>.log を日次ローテーションで出力します。ログ設定は kabusys.utils.logging_setup.setup_logging で制御されます。

ディレクトリ構成
----------------
（src/kabusys をルートとした主要ファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 読み込みロジック
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で ai_scores 生成
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化・永続化レイヤ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （取引監視：滞留注文等）※詳細はソース参照
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 書き込みロジック
    - monitoring_engine.py   — 各モニタまとめ
    - alert_manager.py       — （アラート送信：LINE 等、実装参照）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - broker_factory.py      — Broker クライアントの生成
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
  - monitoring/
    - ...（上記）
  - data/                    — データ処理関連（pipeline / stats 等）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成スクリプト
  - utils/
    - logging_setup.py        — ログ共通設定
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

補足・運用ノウハウ
-----------------
- KABUSYS_ENV を "live" に切り替えると本番モードになります。設定（API トークン・LINE 通知先 等）を十分に確認してください。
- config_validate（validate_config）は起動前チェックに有用です。--strict を CI に組み込むと設定不備の検出が厳密になります。
- AI（OpenAI）モジュールを使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライやフェイルセーフを備えていますが、コストとレイテンシの制御は運用で管理してください。
- ログディレクトリや data/ 配下は運用環境で適切に永続化・バックアップしてください。

ライセンス・貢献
----------------
- 本ドキュメントにはライセンス情報は含まれていません。実プロジェクトでは LICENSE ファイルを追加して下さい。
- バグ報告・機能提案は Issue を作成してください。

以上。必要であれば各モジュールや起動シーケンスのより詳細な説明（ExecutionEngine 内部構成、OrderManager の挙動、DB スキーマ詳細など）を追加します。どの項目を詳述しますか？