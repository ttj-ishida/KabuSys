KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向け自動売買フレームワーク「KabuSys」のコードベースです。  
ポートフォリオ構築、ポジションサイズ計算、注文実行エンジン、監視・アラート、研究用ファクター計算、LLMを用いたニュースセンチメント評価などを含むモジュール群で構成されています。

主な内容
--------
- ポートフォリオ構築（候補選定・重み付け・単元丸め）
- ポジションサイズ計算（リスクベース／等分配／スコア加重）
- リスク制御（セクター上限、ドローダウン監視、ポジション上限）
- ExecutionEngine（発注処理） — paper_trading の場合は MockBroker を使用して発注を分離
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- 研究モジュール（ファクター計算・特徴量探索）
- AI モジュール（OpenAI を使ったニュースセンチメント評価・市場レジーム判定）
- CLI ユーティリティ：設定ウィザード、設定検証、ペーパートレード検証レポート生成

機能一覧
--------
- config_setup.py: 対話式で .env を生成・更新するウィザード
- validate_config.py: .env と config/*.yaml の設定検証（--strict オプションあり）
- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading / live 動作切替）
- run_monitoring.py: SystemMonitor のポーリングループ実行（MONITOR_POLL_INTERVAL で間隔指定可）
- monitoring/*: monitoring DB（SQLite）操作、各種モニタ、KillSwitch、MonitoringEngine
- portfolio/*: 候補選定、重み計算、ポジションサイズ、リスク調整
- research/*: ファクター計算（momentum/volatility/value）、特徴量解析、IC 計算
- ai/*: news_nlp（記事→銘柄別スコア）, regime_detector（マクロ+ETF 指標からレジーム判定）
- tools/paper_verification_report.py: Paper Trading の検証レポート生成

前提・依存（主なもの）
--------------------
- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意:
  - PyYAML（config/*.yaml の中身検証に使用。未インストール時は検証をスキップ）
- SQLite は標準ライブラリで使用
- （環境に応じて）J-Quants / kabuステーション等の資格情報（環境変数）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトで requirements.txt を用意している場合はそれを使用）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに沿って J-Quants トークンや KABU_API_PASSWORD などを入力してください。
   - 作成後、python -m kabusys.validate_config で検証してください。
     - --strict を付けると警告も FAIL 扱いになります。

設定（環境変数）
----------------
主に .env で管理します（config_setup が自動生成）。主要な変数例:

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: MockBroker を使い data/paper_trading.db へ記録（本番 DB と分離）
    - live: 実際に発注が行われるモード（注意）

- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)

- ログ/プロセス
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR (ログ保存先, デフォルト: logs/)
  - PID_FILE_PATH (ExecutionEngine の pid ファイル, デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (kill.flag のパス, デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag をクリアするか: 0/1)

- OpenAI
  - OPENAI_API_KEY (ai/news_nlp, ai/regime_detector を使う場合)

起動と使い方
------------

1. 設定検証
   - python -m kabusys.validate_config
   - オプション: --strict（警告もエラー扱い）

2. ExecutionEngine を起動（本番または paper_trading）
   - python -m kabusys.run_execution
   - 動作モードは KABUSYS_ENV による:
     - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録
     - live: 実際のブローカークライアントを使用
   - 停止制御:
     - data/stop_requested.flag が作られると起動中のエンジンは安全に停止します。
     - Kill Switch（監視側）が書き込む data/kill.flag により外部から停止指示が出せます。
   - 実行中は PID ファイル（data/execution.pid）を出力します。

3. Monitoring を起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト: 60）。
     - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視ループは data/stop_requested.flag を検知すると終了します。
   - 監視は "Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する" ので注意。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で DB パスを指定可能（優先順位: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

5. AI モジュール（プログラムから呼び出す）
   - ai/news_nlp.score_news(conn, target_date, api_key=None)
     - conn: duckdb 接続オブジェクト
     - target_date: date 型（スコア対象日）
     - api_key: OpenAI API キー（None の場合は環境変数 OPENAI_API_KEY を参照）
   - ai/regime_detector.score_regime(conn, target_date, api_key=None)
   - どちらも API キーが未設定だと ValueError を投げます。API 呼び出しの失敗は多くの場合フェイルセーフでスコア 0 相当にフォールバックします。

運用上の注意
------------
- ログ:
  - kabusys.utils.logging_setup.setup_logging を経由して stdout と日次ローテートファイル（logs/<app_name>.log）に出力します。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。権限がない場合は警告が出ます。
- Kill Switch:
  - RiskMonitor がしきい値を超えると KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動クリアは危険）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等にテーブル作成および列追加（簡易マイグレーション）を行います。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py .................. 環境変数 / Settings
- config_setup.py ........... .env 対話式ウィザード
- validate_config.py ........ 設定検証 CLI
- run_execution.py .......... ExecutionEngine 起動スクリプト
- run_monitoring.py ......... Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py (注: alert 管理の実装がある想定)
- execution/                 (ExecutionEngine 周りの実装群、broker ファクトリ等)
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py

（補足）上記に示したファイル以外にも execution や data 関連のモジュールが存在します。運用時は該当モジュールの README/ドキュメントも参照してください。

サンプル .env（抜粋）
-------------------
# J-Quants / kabu API
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# 実行設定
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

よくある運用コマンド例
--------------------
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベースの主要な使い方・設計意図の概要を記したものです。各モジュール内部に詳細な docstring / コメントがあり、実装の注意点や挙動、設計上の前提（例: ルックアヘッドバイアス回避等）が記載されています。運用前に config_setup → validate_config を必ず実行し、KABUSYS_ENV の値（特に live モード）に注意してお使いください。