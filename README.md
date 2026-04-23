KabuSys — 日本株自動売買システム
================================

本ドキュメントは、リポジトリ内の主要コンポーネント・起動方法・設定方法・ディレクトリ構成を日本語でまとめた README です。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買／リサーチ基盤です。主な機能は以下のとおりです。

- 実取引（ExecutionEngine）とペーパートレード（MockBrokerClient）を切り替えて実行可能
- システム監視（SystemMonitor / MonitoringEngine）とアラート・Kill Switch（kill.flag）管理
- 注文・リスク管理（OrderManager / RiskManager / Reconciler）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数等）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）および特徴量探索（IC 等）
- AI（OpenAI）を利用したニュース・マクロセンチメント解析（news_nlp, regime_detector）
- ペーパートレードの検証レポート生成ツール

主要な設計注記:
- 環境変数と .env（.env.local）で設定を読み込む（自動読み込み機能あり、無効化可能）
- ログはコンソール（stdout）と日次ローテーションファイル（logs/<app>.log）に出力
- 本番用の SQLite（monitoring.db）とペーパートレード用の SQLite（paper_trading.db）は分離
- OpenAI を使う機能は API キーが必要（環境変数 OPENAI_API_KEY または引数）

機能一覧（抜粋）
----------------
- 設定管理
  - config.py / config_setup.py: .env の作成・読み込み。Settings クラスでアプリ設定を提供。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI。

- 実行系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番/ペーパー切替）。
    - ペーパートレード時は MockBrokerClient を使用し data/paper_trading.db に記録。
    - 停止フラグ（data/stop_requested.flag）で安全停止。
  - run_monitoring.py: SystemMonitor をポーリング起動（MONITOR_POLL_INTERVAL 環境変数で間隔変更可能、デフォルト 60 秒）。

- 監視 / キルスイッチ
  - monitoring/monitoring_engine.py, system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py
  - monitoring_db.py: SQLite に永続化するテーブル群（system_status, trade_logs, positions, risk_logs, dashboard）。
  - Kill Switch（data/kill.flag）で ExecutionEngine 停止シグナル発行。

- ポートフォリオ
  - portfolio/portfolio_builder.py: 候補選定、等配分・スコア加重配分。
  - portfolio/position_sizing.py: 発注株数計算（リスクベース / equal / score）、単元株丸め、aggregate cap。
  - portfolio/risk_adjustment.py: セクターキャップ、レジーム乗数。

- リサーチ
  - research/factor_research.py: モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB 利用）。
  - research/feature_exploration.py: 将来リターン計算、IC 等の統計解析。

- AI
  - ai/news_nlp.py: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores テーブルへ格納。
  - ai/regime_detector.py: ETF（1321）MA200 とマクロセンチメントを合成して market_regime を判定。

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して PASS/FAIL レポートを生成。

事前準備（環境）
----------------
必須 / 推奨ライブラリ（要インストール）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config で YAML 検証を行う場合に必要）

インストール例:
- 仮想環境を作成してライブラリをインストールしてください。
  - pip install -r requirements.txt （requirements.txt があれば）
  - または個別に: pip install duckdb psutil openai pyyaml

設定 (.env)
----------
プロジェクトルートに .env を置くことで環境変数を管理できます。対話式ウィザードで生成可能:

- .env を作成 / 更新:
  - python -m kabusys.config_setup

- 生成後の検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

主な環境変数（必須・重要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR）
- PAPER_FILL_MODE（ペーパートレード実行モード: instant|partial|never|reject、デフォルト instant）
- KILL_FLAG_CLEAR_ON_START（本番での Kill Switch 自動クリアを制御、デフォルト 0）

よく使うファイル／フラグ
- data/stop_requested.flag: run_monitoring / run_execution が存在を検知して停止します。
- data/kill.flag: KillSwitch が作成。ExecutionEngine の停止トリガー。
- data/execution.pid: ExecutionEngine の PID を格納（run_execution で使用）。
- logs/: デフォルトログディレクトリ。日次ローテーションでログを保持。

使い方（コマンド例）
------------------

1) .env を生成して設定
- python -m kabusys.config_setup
- 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定する

2) 設定を検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱い

3) 監視プロセス起動
- MONITOR_POLL_INTERVAL を指定して間隔を変更できます（秒）。
- 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトは 60 秒
  - 起動時にプロセス優先度を high に設定します
  - 停止は data/stop_requested.flag を作成するか Ctrl+C

4) 実行エンジン起動（Execution）
- KABUSYS_ENV により動作が変わります
  - paper_trading の場合: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
- python -m kabusys.run_execution
- 停止は data/stop_requested.flag を作成するか ExecutionEngine 側からの Kill Switch により行われます

5) ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db。--db で別パス指定可能。

6) AI 系（ニューススコア、レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=...) — DuckDB 接続を渡して呼び出し
- ai/regime_detector.score_regime(conn, target_date, api_key=...)
- 実行には OPENAI_API_KEY が必要。失敗時はフェイルセーフで続行（既定のフォールバック挙動あり）。

停止・Kill Switch
-----------------
- 手動停止（run_monitoring / run_execution）:
  - data/stop_requested.flag を作成すると両スクリプトは検知して安全に停止します。
- Kill Switch（自動停止）:
  - RiskMonitor が条件に合致すると KillSwitch が data/kill.flag を作成します。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動クリアされるため、本番では注意（推奨は 0）。

基本的な挙動の補足
-----------------
- run_monitoring は Monitoring 用の SQLite（settings.sqlite_path）を使います。環境に関係なく production の sqlite_path を使用します（監視は常に本番 DB の状況を監視する想定）。
- run_execution は KABUSYS_ENV が paper_trading の場合、paper_sqlite_path を使い本番 DB とは完全分離します。
- ロギングは kabusys.utils.logging_setup.setup_logging を用いて統一されます。ログディレクトリが作れない場合はコンソール出力のみになります。

ディレクトリ構成（主要ファイル）
--------------------------------
src/
  kabusys/
    __init__.py
    config.py                  -- 環境変数/Settings
    config_setup.py            -- .env 対話ウィザード
    validate_config.py         -- 設定検証 CLI
    run_monitoring.py          -- SystemMonitor ポーリング起動スクリプト
    run_execution.py           -- ExecutionEngine 起動スクリプト

    utils/
      __init__.py
      logging_setup.py         -- ログ設定ユーティリティ
      process_priority.py      -- プロセス優先度 / CPU affinity 設定

    monitoring/
      monitoring_db.py         -- SQLite 永続化層
      system_monitor.py        -- システム状態・データ鮮度監視
      trade_monitor.py         -- 発注ログ監視（ファイル内に同名ファイルがある想定）
      risk_monitor.py          -- ドローダウン・ポジション上限監視
      kill_switch.py           -- kill.flag 管理
      monitoring_engine.py     -- 全 Monitor を束ねる

    execution/                  -- Execution 関連（OrderManager 等）
      ... (エンジン・OrderRepository 等の実装ファイル)

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    ai/
      news_nlp.py               -- ニュース NLP（OpenAI）
      regime_detector.py        -- レジーム判定（MA200 + マクロセンチメント）
      __init__.py

    tools/
      __init__.py
      paper_verification_report.py

注意事項 / 運用上のヒント
------------------------
- 本番（KABUSYS_ENV=live）での設定ミスは重大なので validate_config で必ずチェックしてください。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup も README に警告を出力します）。
- Kill Switch / stop flag の扱いには注意。KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険です。
- OpenAI API を使用する機能はコスト・レイテンシ・API 利用制限に注意して運用してください（リトライ/バックオフ実装あり）。
- DuckDB / SQLite はローカルファイル DB です。バックアップや適切なパス設定を行ってください。

ライセンス・バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

この README はコードベースの主要部から情報を抽出して作成しています。細かい挙動や追加オプションは各モジュール（特に execution/* や monitoring/*）のドキュメント / ソースコードを参照してください。必要であれば各モジュールごとの詳細 README を追記できます。