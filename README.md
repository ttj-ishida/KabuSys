KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買／研究／監視コンポーネント群を含む Python パッケージです。  
設計は本番発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI 補助（News NLP / Regime Detector）などに分かれ、開発・ペーパートレード・本番を環境変数で切り替えて運用できます。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 実口座 / ペーパートレード（MockBroker）を環境切替で選択
  - リスク管理（RiskManager）、注文管理（OrderManager）、突合（Reconciler）を備える
- Monitoring（監視）
  - システム状態、注文ログ、リスク指標をポーリングして SQLite に永続化
  - Kill Switch による安全停止、アラート発行機構を備える
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け（等金額／スコア加重）、株数算出（単元丸め、リスクベース）
  - セクターキャップ、レジーム乗数を適用
- Research（リサーチ）
  - DuckDB を使ったファクタ計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント集約（ai_scores テーブルへ保存）
  - ETF の MA200 とマクロニュースを組み合わせた市場レジーム判定
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
  - ログ設定、プロセス優先度／CPU affinity 設定ユーティリティ
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
----------------

1. Python と依存パッケージをインストール
   - 推奨: Python 3.10+
   - 必要パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合）
   - 例:
     - python -m pip install duckdb psutil openai PyYAML

2. プロジェクトルートに移動し .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 自動的に .env / .env.local が読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いに

4. ディレクトリの作成（data, logs 等）
   - 通常は起動時に作成されますが念のため:
     - mkdir -p data logs

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）  
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）  
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）  
- OPENAI_API_KEY: OpenAI 呼び出し時に必要（AI 機能使用時）  
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）  
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）  
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）  
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）  
- PAPER_FILL_MODE: paper_trading 時の fill 動作（instant / partial / never / reject）  
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）  
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

使い方（起動例）
----------------

- 環境設定（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 説明:
    - プロセス優先度を"high"に変更して起動
    - 監視用 SQLite は Settings.sqlite_path（環境にかかわらず本番 sqlite_path を使用）
    - data/stop_requested.flag を置くとループは安全に終了します

- 発注エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 説明:
    - paper_trading 環境では MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）に記録して本番 DB と分離
    - 起動時に data/stop_requested.flag が既にある場合は起動せず終了
    - 停止は data/stop_requested.flag の作成、もしくは Kill Switch（監視側が data/kill.flag を書く）で行います

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

停止方法・Kill Switch
---------------------
- 手動停止（両スクリプト共通）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution は検知して停止します
- Kill Switch（監視経由での強制停止）
  - 監視コンポーネントが条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine の停止トリガとなります
  - Settings.kill_flag_clear_on_start=1 にすると起動時に kill.flag を自動クリアします（本番では 0 を推奨）

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging で統一設定されます
- デフォルトログディレクトリ: logs/
- ログ名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- 日次ローテーション（30日保持） + コンソール出力（stdout）

DB とスキーマ（監視周り）
-----------------------
- 監視用 DB スキーマは kabusys.monitoring.monitoring_db.init_monitoring_db が作成
- 主なテーブル:
  - system_status: cpu/memory/disk/process_ok 等のポーリング履歴
  - trade_logs: 発注イベントログ（Created / Sent / Filled 等）
  - positions: 保有ポジション（code を主キー）
  - risk_logs: リスクイベント
  - dashboard: 集計（1行のみ、id=1）

主要モジュールの説明
--------------------
- kabusys.config
  - .env 自動読み込み（.env / .env.local、OS 環境変数優先）
  - Settings クラスで全設定を取得
- kabusys.run_execution
  - ExecutionEngine の起動ラッパー。環境に応じた DB を選択
- kabusys.run_monitoring
  - SystemMonitor をポーリングして監視データを記録
- kabusys.monitoring
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db 等
- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment — 候補選定・重み計算・株数算出・セクター制御等
- kabusys.research
  - factor_research（momentum/volatility/value）、feature_exploration（IC 等）
  - DuckDB ベースで分析用処理を提供
- kabusys.ai
  - news_nlp: ニュースを OpenAI でセンチメント化して ai_scores に書込
  - regime_detector: MA200 とマクロニュースで市場レジーム判定
- kabusys.utils
  - logging_setup: 統一ログ設定
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor 起動スクリプト

- execution/                — 発注関連（broker_factory, execution_engine, order_manager...）
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py
  - kill_switch.py
  - alert_manager.py
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

運用上の注意
------------
- .env は機密情報を含むため Git にコミットしないこと（config_setup.py のヘッダにも注意書きあり）。
- KABUSYS_ENV=live の場合は特に注意して、LINE 通知や kill flag 設定を確認すること。
- OpenAI API を使う場面は外部 API 呼出しで失敗する可能性があるため、AI モジュールはフェイルセーフ（失敗時はフォールバック）で設計されていますが、APIキーの管理は厳重に。
- ログディレクトリの作成に失敗した場合はコンソールのみのログ出力になります。

開発・拡張のヒント
------------------
- Research モジュールは DuckDB 接続を受け取って純粋関数で計算するため、データを差し替えれば簡単にローカル検証可能
- AI 周りの API 呼び出しは _call_openai_api をモックすることでユニットテストが可能
- monitoring_db.init_monitoring_db は冪等でマイグレーション（カラム追加）も含むので DB 初期化に利用可能

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

質問・追加ドキュメントの要求があれば、想定ユースケース（デプロイ手順、systemd ユニット例、Dockerfile、ユニットテストの書式等）に合わせた追補資料を作成します。