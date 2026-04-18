README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための小規模な Python アプリケーション群です。本リポジトリは以下の主要機能を含みます。

- 実運用・ペーパートレード用の ExecutionEngine（発注・オーダー管理・リスク管理）
- System / Trade / Risk を総合的に監視する Monitoring（kill switch を含む）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP / レジーム判定（OpenAI API を利用したセンチメント評価）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証、レポート生成等）

特徴
----
- モジュール化された監視・実行コンポーネント（monitoring, execution）
- DuckDB / SQLite を用いたデータストレージ（分析用 / 監視用に分離）
- Paper Trading モード：本番 DB と分離して data/paper_trading.db に記録
- OpenAI を使ったニュース解析（AI スコアの算出／市場レジーム判定）
- 設定ウィザード（.env 自動生成）と検証ツール（起動前チェック）
- ログは stdout と日次ローテートファイルの両方に出力（logs/*.log）

動作前提（簡易）
----------------
- Python 3.10 以上（PEP 604 の union 型記法（|）などを使用しているため）
- 必要なライブラリ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- SQLite（標準ライブラリで利用）
- インターネット接続（OpenAI API を利用する場合）、および kabuステーション が必要な場合はその API に接続可能な環境

セットアップ手順
----------------
1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - pip install duckdb psutil openai PyYAML
   - （要件ファイル requirements.txt があれば pip install -r requirements.txt）

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - ウィザードが対話形式で .env を生成します（デフォルト: プロジェクトルート/.env）。
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict オプションを付けると警告も失敗扱いになります（exit code 1）。

4. データディレクトリとログディレクトリ
   - デフォルトでは data/ と logs/ を使用します。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を変更してください。
   - 実行時にログディレクトリが存在しなければ attempt で作成されます。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading 時は MockBroker を用い、DB は data/paper_trading.db に分離されます
- OPENAI_API_KEY: OpenAI を利用する機能で必須
- DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant, partial, never, reject）

使い方（主要コマンド）
--------------------

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録します。
    - 起動中は data/execution.pid を作成します（PID ファイルは Settings で変更可能）。
    - 停止は次のいずれか:
      - data/stop_requested.flag を作成（監視ループ / 実行スレッドは検知して終了）
      - kill.flag（KillSwitch）が作成された場合、ExecutionEngine に停止シグナルを送ります

- Monitoring 起動（システム監視）
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
    - Monitoring は常に本番 sqlite_path を参照（環境に関わらず monitoring DB は共通で使用）。
    - 監視は SystemMonitor / TradeMonitor / RiskMonitor を呼び出し、必要に応じて KillSwitch を発動します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - ペーパートレード用 SQLite を集計して uptime・約定率・レイテンシ等を表示します。

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - プログラム API としては kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用します。
  - 例（スクリプト経由）:
    - 要スクリプトラッパーまたはスケジューラから呼び出すことを想定しています。

監視・停止フロー（概念）
-----------------------
- stop_requested.flag:
  - 実行/監視のループ終了用のフラグファイル（data/stop_requested.flag）。存在を検知するとループを抜けるようになっています。
- kill.flag:
  - KillSwitch（RiskMonitor の結果から）によって生成される停止フラグ。ExecutionEngine は起動時または稼働中にこのフラグの存在を確認して安全停止します。
- PID ファイル:
  - data/execution.pid（実行エンジンの PID 保存先。Settings.pid_file_path で変更可）

ログ
----
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力され、日次ローテーションで 30 日分保持されます。
- LOG_LEVEL, LOG_DIR は環境変数で制御可能。アプリ起動時に setup_logging(app_name="...") を呼び出して統一的に設定されます。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソース配下の主要なディレクトリ・ファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - system_monitor.py
    - trade_monitor.py       — （trade_monitor 実装あり）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信管理; LINE 等）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注ワークフロー）
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
    - news_nlp.py            — ニュースセンチメント算出（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF 指標）
  - data/                   — 既定のデータ/DB 保存先（実行時に生成）
  - logs/                   — ログ保存先（デフォルト）

（上記はコードベースから抜粋した代表ファイル群です）

よくある運用タスク
------------------
- 起動順序:
  1. .env 作成（config_setup）
  2. 設定検証（validate_config）
  3. 必要な DB（DuckDB / SQLite）は初回起動時に自動生成されます（必要に応じてデータロード）
  4. 実行エンジン（run_execution）を起動
  5. 監視（run_monitoring）を常時起動（別プロセス / サービスとして）

- 停止:
  - data/stop_requested.flag を作成すると両プロセスはループを終了します（安全停止）。
  - KillSwitch により自動で data/kill.flag が書かれると ExecutionEngine は停止します（本番時は注意）。

- ログ参照:
  - logs/execution.log, logs/monitoring.log などを確認してください。
  - DEBUG レベルで詳細を得るには LOG_LEVEL=DEBUG を .env に設定して再起動。

セキュリティ上の注意
------------------
- .env は機密情報（API キー・パスワード）を含むため絶対に Git へコミットしないでください。
- config_setup.py の注記にもあるように .env を Git 管理しないことを徹底してください。
- 本番環境（KABUSYS_ENV=live）は特に設定値を慎重に確認してください（validate_config の警告を参照）。

開発者向けメモ
--------------
- テスト: 各コンポーネントは pure function / 小単位に分かれているため単体テストを書きやすい設計です。AI 呼び出しや外部 API 呼び出しはモック可能なよう公開関数を分離しています。
- 自動 .env ロード: config.py はプロジェクトルート（.git または pyproject.toml がある階層）から .env/.env.local を自動的に読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル .env（最小例）
---------------------
以下はウィザードで設定される主要キーの一例（実際の値はご自身の環境に合わせて設定してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

サポート / 貢献
----------------
- バグ報告や機能改善の提案は Issue を通して受け付けてください。
- 大きな変更を行う場合は事前に Issue で相談してください。

以上が本プロジェクトの概要・セットアップ・運用の要点です。追加で README に載せたい内容（例: データロード手順、DB スキーマ詳細、API エンドポイント仕様など）があればお知らせください。