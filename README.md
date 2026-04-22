KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム（小規模モジュール群）です。  
主な機能は次の通りです:

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの分離（paper_trading モードでモックブローカー使用）
- 監視モジュール（SystemMonitor / TradeMonitor / RiskMonitor）によるプロセス・資産・オーダー状態のポーリングとアラート/Kill Switch
- ポートフォリオ構築（候補抽出、重み計算、ポジションサイズ算出、セクター制約など）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメントスコア化・市場レジーム推定）
- Paper Trading 検証レポート生成ツール
- 設定ウィザード / 設定検証 CLI（.env / config/*.yaml）

特徴
----
- 設定は .env / 環境変数ベース。config_setup.py の対話ウィザードで初期化可能
- paper_trading（ペーパートレード）環境は本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用 DB、SQLite を監視・トレードログ用 DB に使用
- ロギングは統一的に setup_logging を使用（コンソール + 日次ローテートファイル）
- OpenAI API 呼び出しはリトライ／バリデーションを備えた堅牢実装
- モジュールは純粋関数的実装（研究 / ポートフォリオ計算）は DB に依存しない部分も多い

必要要件（例）
--------------
- Python 3.9+（コードは型注釈に Python 3.9+ の構文を使用）
- パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（標準ライブラリ）
- OpenAI 利用時は OPENAI_API_KEY

（実行環境に応じて requirements.txt を用意して pip install してください）

主な機能一覧
--------------
- 設定管理
  - config_setup.py: .env 作成ウィザード
  - validate_config.py: 起動前チェック（必須 env や config/*.yaml の検証）
  - kabusys.config.Settings: 環境・パス・閾値等の参照ユーティリティ
- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - monitoring_engine / monitors: SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager
- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（リスクベース・等配分等）
  - apply_sector_cap, calc_regime_multiplier
- 研究（Research）
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary
- AI（OpenAI）
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロセンチメントで market_regime を判定
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成

セットアップ手順
----------------

1. リポジトリをクローン、またはパッケージ配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール
   - 例: pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があればそれを使用）
4. 必要ディレクトリを作成
   - mkdir -p data logs
5. 環境変数 (.env) の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照）
   - 必須環境変数（validate_config に基づく）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意 / 主要な環境変数:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能利用時)
     - LOG_LEVEL (DEBUG/INFO/...)
     - PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の約定挙動
     - MONITOR_POLL_INTERVAL（run_monitoring 起動時に参照）
6. 設定検証（オプション）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗として扱います

使い方
------

基本的な実行例:

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパートレードは KABUSYS_ENV で切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 動作中に data/stop_requested.flag を作成すると安全に停止します（同様に run_execution は data/execution.pid を使用）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で調整可能:
    - export MONITOR_POLL_INTERVAL=30
  - 監視ループも data/stop_requested.flag の存在で終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI / レジーム判定（ライブラリ呼び出し例）
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

プロセス制御 / Kill Switch
- KillSwitch は監視結果に基づいて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 実行開始時に Kill Flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できます（本番では推奨されません）。
- run_execution/run_monitoring は data/stop_requested.flag を参照して終了します。

環境変数の重要な挙動
- KABUSYS_ENV:
  - development: 開発（発注なし）
  - paper_trading: ペーパートレード（MockBrokerClient、paper_trading DB を使用）
  - live: 本番（実注文）
- PAPER_FILL_MODE（paper_trading 時）:
  - instant, partial, never, reject のいずれか
- MONITOR_POLL_INTERVAL（run_monitoring 用）:
  - 秒単位（デフォルト 60）、1 未満は無効でデフォルトにフォールバック
- LOG_DIR / LOG_LEVEL:
  - ログ格納先とログレベル（setup_logging が使用）

ディレクトリ構成
-----------------

（リポジトリの src/kabusys を起点に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ・永続化層
    - system_monitor.py
    - trade_monitor.py       — （コード上では参照あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジックの想定箇所）
  - execution/
    - execution_engine.py    — 実行ロジック（参照）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - data/  (実行時に作成される想定)
  - logs/  (ログ出力用)

補足 / 運用上の注意
-------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）での実行前に validate_config.py で設定を入念にチェックしてください。
- OpenAI を利用する AI 機能は API 料金が発生します。テスト時はモック化を推奨します（モジュール内で _call_openai_api を差し替え可能）。
- run_execution/run_monitoring は data/stop_requested.flag による安全停止、及び execution.pid を使用したプロセス管理を行います。運用スクリプトで適切に監視してください。
- DuckDB/SQLite のパスは Settings で設定可能。paper_trading は専用 SQLite を使用して本番 DB と分離します。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。
- ライセンス情報はリポジトリに含めてください（この README には含まれていません）。

以上がこのコードベースの概要と利用ガイドです。必要であれば:
- requirements.txt の例
- systemd / Supervisor 用のサービスユニット例
- 実行例・デバッグ手順（ログの読み方、DB の中身確認 SQL）
などを追記します。どれを優先して追加しますか？