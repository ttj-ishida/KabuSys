KabuSys — 日本株自動売買システム（README）
概要
- KabuSys は日本株向けの自動売買基盤の一部実装です。シグナル計算（research）、ポートフォリオ構築（portfolio）、発注実行（execution）、監視（monitoring）、AI を用いたニュース解析（ai）などのコンポーネントを含みます。
- 設計方針：本番とペーパートレードの分離、ルックアヘッドバイアス回避、フェイルセーフ（API失敗や部分障害を許容）を重視しています。

主な機能一覧
- 環境設定ウィザード（config_setup）: .env を対話式に作成・更新
- 設定検証ツール（validate_config）: .env と config/*.yaml の事前チェック（--strict オプションあり）
- ExecutionEngine 起動スクリプト（run_execution）:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に書き込む（本番 DB と分離）
  - プロセス優先度を自動設定、停止フラグ（data/stop_requested.flag）による安全停止
- Monitoring（run_monitoring / monitoring エンジン）:
  - システム・注文・リスク監視（SystemMonitor / TradeMonitor / RiskMonitor）
  - kill.flag による ExecutionEngine 停止シグナル出力、監視結果の SQLite 永続化（monitoring.db）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- Portfolio 構築ユーティリティ:
  - 候補選定、等金額・スコア加重配分、セクターキャップ、ポジションサイズ計算（単元丸め等）
- Research（ファクター計算・特徴量探索）:
  - モメンタム / ボラティリティ / バリュー等のファクター、将来リターン・IC 計算、統計サマリー
  - DuckDB を用いた SQL + Python 実装
- AI（news_nlp / regime_detector）:
  - OpenAI（gpt-4o-mini を想定）でニュースセンチメントを算出し ai_scores に保存
  - マクロニュース＋ETF MA を組み合わせた市場レジーム判定（market_regime への書き込み）
  - API 呼び出しはリトライとフェイルセーフあり
- ツール:
  - paper_verification_report: ペーパートレード DB を解析して稼働率・注文成功率・レイテンシ等をレポート出力

依存関係（代表）
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を利用する場合）
- PyYAML（config/*.yaml の詳細検証を有効にする場合）
- 標準ライブラリ: sqlite3, logging, datetime 等

セットアップ手順
1. リポジトリをクローンし、仮想環境を用意
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （検証で YAML を使う場合）pip install pyyaml

3. .env を作成（推奨: 対話式ウィザードを利用）
   - python -m kabusys.config_setup
   - 代表的な環境変数（defaults を参考）
     - KABUSYS_ENV=development|paper_trading|live
     - JQUANTS_REFRESH_TOKEN=（必須）
     - KABU_API_PASSWORD=（必須）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=（AI を使う場合）
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

4. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトで data/ 以下に DB やフラグファイルを作成します（存在しない親ディレクトリは自動作成される箇所もあります）。
   - 主なファイル:
     - data/kabusys.duckdb（DuckDB、デフォルト: data/kabusys.duckdb）
     - data/monitoring.db（監視用 SQLite）
     - data/paper_trading.db（ペーパートレード用 SQLite）
     - data/execution.pid（ExecutionEngine の PID）
     - data/kill.flag（Kill Switch）
     - data/stop_requested.flag（run_* スクリプトの外部停止フラグ）

使い方（代表コマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（フォアグラウンド）
  - python -m kabusys.run_execution
  - 注意: 起動時に KABUSYS_ENV を適切に設定してください。paper_trading の場合は本番 DB とは別の paper_trading.db を使用します。

- Monitoring 起動（監視ポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で秒単位に設定（例: MONITOR_POLL_INTERVAL=30）

- 停止
  - 実行中のプロセスを外部から停止したい場合は data/stop_requested.flag を作成します（scripts はこのフラグを検知して安全に終了します）。
  - ExecutionEngine を強制停止させたい（Kill Switch）場合は data/kill.flag を書き込むと run_execution 側で検出します（KillSwitch は原因理由を書き込みます）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI モジュールの利用（Python API）
  - ニュースのセンチメントを付けて DB に書き込む（例、DuckDB 接続を渡す）
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, datetime.date(2026, 4, 1), api_key="sk-...")

  - レジーム判定を実行して market_regime に書き込む
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, datetime.date(2026, 4, 1), api_key="sk-...")

主要設計上のポイント（運用に関係する注意点）
- Settings（kabusys.config）:
  - 自動でプロジェクトルートの .env / .env.local を読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。.env の読み込みは OS 環境変数を保護します。
  - KABUSYS_ENV により live / paper_trading / development の挙動が切り替わります。
  - PAPER_FILL_MODE（ペーパートレードの約定動作）や PAPER_TRADING_SQLITE_PATH などペーパートレード向け設定あり。

- DB 分離:
  - 監視ログは sqlite（SQLITE_PATH）へ永続化。
  - 分析用データは DuckDB（DUCKDB_PATH）。
  - ペーパートレードは PAPER_TRADING_SQLITE_PATH に分離され、本番 DB を汚さない設計。

- 監視・Kill Switch:
  - RiskMonitor がドローダウンやポジション数の監視を行い、KillSwitch が条件に応じて data/kill.flag を作成します。ExecutionEngine は kill.flag を検出して停止できます。

- プロセス優先度:
  - run_execution/run_monitoring の起動時に set_process_priority("high") を試みます。権限不足等で失敗してもログに WARN を出して継続します。

ディレクトリ構成（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定読込ロジック
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
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
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在、未全文掲載)
  - execution/                  (発注関連コンポーネント: Engine, BrokerFactory, OrderManager, OrderRepository 等)
  - data/                       （スキーマ定義・パイプライン等は別モジュールにある想定）
  - utils/
    - process_priority.py
  - research, portfolio, ai, monitoring 等の各サブモジュール多数

追加のヒント・運用メモ
- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- 本番稼働前に必ず python -m kabusys.validate_config を実行して設定の不備を検出してください（KABUSYS_ENV=live の場合は特に LINE 通知設定や Kill Flag の自動クリア設定に注意）。
- OpenAI を利用する処理は API キーの管理とコスト制御に注意してください。AI 呼び出しはリトライ処理とスコア検証を行いますが、運用側でもレートや呼び出し頻度を制御してください。
- DuckDB と SQLite ファイルのパスは Settings で設定可能。バックアップ・権限管理を運用ポリシーに従って行ってください。

以上がリポジトリの概要と運用に必要な基本説明です。必要であれば README をもとに運用手順書（起動/停止手順、監視アラートの対応フロー、DB 管理手順など）を追記します。どの情報を追加したいか教えてください。