README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買システムの骨格実装（モジュール群）です。本リポジトリは主に以下の機能を備えます。

- 発注・実行エンジン起動スクリプト（ExecutionEngine）
- システム監視・アラート（Monitoring）
- ペーパートレード用検証ツール（レポート生成など）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- リサーチ（ファクター計算・特徴量探索）
- AI モジュール（ニュースセンチメントによるスコアリング / レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード / 検証）

主要な設計方針
- 環境変数による設定管理（.env 自動読み込み）
- DuckDB を分析用途に、SQLite を監視・発注ログ用に使用
- Paper Trading（ペーパートレード）は本番 DB と分離可能
- OpenAI を用いた NLP 処理は API キー依存（未設定時は明示的にエラー）

機能一覧
-------
- 設定関連
  - config_setup: 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - validate_config: .env と config/*.yaml の検証 CLI（python -m kabusys.validate_config）
- 実行（Execution）
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV によってペーパートレードモードあり）
- 監視（Monitoring）
  - run_monitoring: SystemMonitor のポーリングループを常駐起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - monitoring_engine: 個別モニタを束ねてアラート／KillSwitch 評価
  - RiskMonitor / SystemMonitor / TradeMonitor / KillSwitch 実装
- AI
  - news_nlp.score_news: ニュースを集約して OpenAI でセンチメントスコアを計算・DBへ書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースで市場レジーム判定
- リサーチ
  - factor_research: momentum / volatility / value ファクター計算（DuckDB 経由）
  - feature_exploration: 将来リターン・IC（Spearman）計算など
- ポートフォリオ構築
  - portfolio_builder / risk_adjustment / position_sizing（候補選定、セクター制限、株数決定）
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成

セットアップ手順
----------------
前提
- Python 3.10+（type hints 等を利用）
- システムにより追加で duckdb ライブラリのネイティブ依存が必要な場合あり

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がない場合は上記を手動でインストール）
   - OpenAI を使わない場合は openai を省いて構いません（ただし AI 機能は無効になります）。

3. ディレクトリ作成
   - data/ および logs/ は自動作成されますが、手動で準備しておくと権限エラーを避けられます。
     - mkdir -p data logs

4. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
   - これにより .env ファイルが生成されます（.env は絶対に Git にコミットしないでください）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を利用する場合の API キー
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 実行時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

使い方（主要コマンド）
--------------------

1. 設定のウィザード
   - python -m kabusys.config_setup
   - 対話形式で .env を生成または更新します。

2. 設定の検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3. ExecutionEngine を起動（本番またはペーパー）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。
   - プロセスは data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成するか、kill.flag を利用します。

4. Monitoring を起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
   - 監視は Settings に従って sqlite_path（監視 DB）と duckdb_path に接続します。
   - 停止はプロジェクトルート/data/stop_requested.flag を作成することで検出され終了します。

5. Paper Trading 検証レポートの生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定や DB パス指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

6. AI 系処理（例）
   - ニューススコアリング: kabusys.ai.score_news を呼び出す（プログラムから直接）
   - OpenAI API キーは OPENAI_API_KEY 環境変数か関数引数で指定

停止・Kill Switch
----------------
- 実行エンジン停止フラグ（外部からの停止要求）
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検出して終了処理を行います。
- Kill Switch（リスク超過時に ExecutionEngine を停止）
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込み、ExecutionEngine 側でこれを検出して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

ログ
----
- ログはデフォルト logs/ に保存され、アプリ名ごとにファイルが作成されます（例: logs/execution.log, logs/monitoring.log）。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます。
- 標準出力にもログを出すため、cron 等での起動でもログ収集が容易です。

データベースの取り扱い
--------------------
- DuckDB: 分析用（prices_daily, raw_financials, raw_news 等を格納して解析を行う）
  - デフォルト: data/kabusys.duckdb
- SQLite:
  - 監視・履歴用（monitoring.db、trade_logs, risk_logs, positions, dashboard 等）
    - デフォルト: data/monitoring.db
    - run_monitoring は環境にかかわらずこの sqlite_path を使用します（監視は production DB を参照する想定）
  - ペーパートレード専用 DB（paper_trading.db）: KABUSYS_ENV=paper_trading のとき ExecutionEngine が使用

ディレクトリ構成
----------------
ルート: src/kabusys 以下を想定しています（抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート
  - ai/
    - news_nlp.py            — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — monitoring DB（SQLite）アクセス層
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限チェック
    - trade_monitor.py       — （トレード監視、実装あり）
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各モニタを束ねる実行エンジン
    - alert_manager.py       — （アラート送信、実装あり）
  - execution/               — ExecutionEngine 関連（OrderManager, BrokerFactory, Reconciler 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・リスク制限
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum / value / volatility 等のファクター計算
    - feature_exploration.py — IC, forward returns, summary 等
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

補足 / 運用上の注意
------------------
- .env は機密情報（APIキー・パスワード等）を含みます。絶対にリポジトリへコミットしないでください。
- KABUSYS_ENV=live の場合は本番動作になります。設定（LINE 通知、kill flag の取り扱いなど）を慎重に確認してください。
- OpenAI 呼び出し部分は API 料金が発生します。テスト時はモックして利用してください（関数を patch する設計になっています）。
- run_monitoring の MONITOR_POLL_INTERVAL は短くし過ぎないでください（デフォルト 60 秒）。

よくあるコマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパー検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / バージョン
----------------------
- パッケージバージョンは kabusys.__version__（現状 0.1.0）
- ライセンス情報はリポジトリのトップレベルに配置してください（本 README には含めていません）。

お問い合わせ・開発
-----------------
- 開発・拡張: 各モジュールは単体でテストしやすい純粋関数（research / portfolio 等）と副作用を持つ I/O 層（monitoring_db / execution 等）で設計されています。ユニットテストやモックを導入して段階的に検証してください。

以上。README の内容をプロジェクトの実態に合わせて適宜補完・調整して利用してください。