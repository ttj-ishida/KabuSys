README
=====

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を行う小規模なシステム群です。
本リポジトリは以下の主要機能をモジュール化して提供します。

- 発注実行エンジン（ExecutionEngine）
- 監視デーモン（Monitoring）
- ペーパートレード検証レポート生成ツール
- ポートフォリオ構築ユーティリティ（候補選定・重み・株数計算）
- ファクター計算・特徴量探索（Research）
- ニュース NLP / レジーム判定（OpenAI を使ったスコアリング）
- 環境設定ウィザード / 設定検証ツール

設計上のポイント
- 環境変数（.env）ベースで設定を管理（kabusys.config）。
- paper_trading モードでは本番 DB と分離して data/paper_trading.db を使用。
- 監視は環境にかかわらず本番の sqlite DB（default: data/monitoring.db）を使う設計。
- OpenAI を利用する機能は API キーを環境変数 OPENAI_API_KEY で供給する。
- ログはコンソール（stdout）と日次ローテートファイル（logs/*.log）に出力。

主な機能一覧
----------------
- 実行
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて MockBroker を選択）
  - ExecutionEngine は停止フラグ（data/stop_requested.flag / data/kill.flag / data/execution.pid）を扱う
- 監視
  - run_monitoring.py: SystemMonitor を定期ポーリングして状態を記録
  - MonitoringEngine: System / Trade / Risk Monitor を束ね、Kill Switch と通知を評価
  - RiskMonitor: ドローダウンやポジション上限の監視とリスクログ記録
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み Execution を停止
- ツール
  - config_setup.py: .env の対話式作成・更新ウィザード
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成
- 研究（Research）
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - research.feature_exploration: 将来リターン計算、IC（Information Coefficient）等
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定・等配分/スコア配分
  - portfolio.position_sizing: 株数算出（リスクベース、等配分など）
  - portfolio.risk_adjustment: セクターキャップ、レジーム乗数
- AI（OpenAI）
  - ai.news_nlp: ニュース記事の銘柄別センチメントを OpenAI で評価して ai_scores に書き込み
  - ai.regime_detector: ETF等の MA とマクロニュースを合成して市場レジーム判定

セットアップ手順
----------------
前提
- Python 3.10+（コード内で | 型注釈や最新の typing 機能を使用）
- OS: Linux / macOS / Windows（process priority 周りはプラットフォーム依存挙動あり）

依存ライブラリ（最低限）
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証を使う場合）
インストール例:
    pip install duckdb psutil openai PyYAML

プロジェクト初期化
1. リポジトリをクローン／展開
2. 仮想環境を作成・有効化（推奨）
3. 必要ライブラリをインストール（上記参照）
4. data/ と logs/ ディレクトリを作成（ログ・DB保存用）
    mkdir -p data logs

.env の準備
- 対話的に作成する（推奨）
    python -m kabusys.config_setup
- または手動で .env を作成。主な環境変数:
  - 必須:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
  - 推奨・その他:
    - KABUSYS_ENV (development | paper_trading | live)  デフォルト: development
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
    - LOG_LEVEL（DEBUG/INFO/… デフォルト: INFO）
    - OPENAI_API_KEY（AI 機能を使う場合）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）

設定検証
    python -m kabusys.validate_config
必要に応じて --strict を付けると警告も失敗として扱う。

使い方（主要コマンド）
--------------------
- 監視ループ起動（デフォルトポーリング間隔 60 秒）
    python -m kabusys.run_monitoring
  - 環境変数で間隔を変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に設定された sqlite_path（監視用 DB）を使います。

- 実行エンジン起動
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
  - 実行中は data/execution.pid（デフォルト）が作成されます。停止は data/stop_requested.flag または kill.flag がトリガーされます。

- ペーパートレード検証レポート
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。デフォルト: data/paper_trading.db

- .env 作成ウィザード
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

運用上の注意
- 監視（run_monitoring）は MONITOR_POLL_INTERVAL 環境変数で秒数を指定できます。1 秒未満・0 は無効でデフォルト 60 秒にフォールバックします。
- 実行エンジン停めるための flag:
  - data/kill.flag: KillSwitch により書き込まれると ExecutionEngine が停止します。
  - data/stop_requested.flag: 各 run_* スクリプトがループ停止判定で使用。
- KILL_FLAG_CLEAR_ON_START=1 を本番 (KABUSYS_ENV=live) で設定するのは危険です（自動で kill.flag をクリアしてしまうため）。デフォルトは 0。
- OpenAI を使用する機能は API キーの用意が必要。API 制限やエラーは指数バックオフでリトライしますが、失敗時は安全にフォールバックする設計です。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト

subpackages
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）による ai_scores 書き込み
  - regime_detector.py     — レジーム判定（MA + マクロニュース）
- monitoring/
  - monitoring_db.py       — SQLite のテーブル作成と永続層
  - system_monitor.py      — システム状態 / データ鮮度監視
  - trade_monitor.py       — （取引ログ監視/未表示の実装あり）
  - risk_monitor.py        — ドローダウン／ポジション上限の監視
  - kill_switch.py         — kill.flag 制御
  - monitoring_engine.py   — 各 Monitor の統合実行
  - alert_manager.py       — （アラート送信ロジック、実装参照）
- portfolio/
  - portfolio_builder.py   — 候補選定・重み付け
  - position_sizing.py     — 発注株数算出
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（Momentum/Value/Volatility）
  - feature_exploration.py — 将来リターン・IC・サマリー
- tools/
  - paper_verification_report.py — Paper Trading レポート生成
- utils/
  - logging_setup.py       — 標準化されたログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

DB / ファイルパス（デフォルト）
- data/kabusys.duckdb        — DuckDB（分析／prices_daily 等）
- data/monitoring.db         — 監視用 SQLite（system_status, trade_logs 等）
- data/paper_trading.db      — ペーパートレード専用 SQLite（paper_trading モード）
- data/execution.pid         — ExecutionEngine の PID ファイル（デフォルト）
- data/kill.flag             — Kill Switch が書き込む停止フラグ
- data/stop_requested.flag   — run_* スクリプトの停止フラグ
- logs/<app_name>.log        — 日次ローテートログ（logs ディレクトリ）

環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- OPENAI_API_KEY（AI 機能を利用する場合）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1、デフォルト 0）

補足
- YAML の構成ファイル（config/*.yaml）は存在が期待されています。validate_config は PyYAML がインストールされている場合に内容パースまで検証します。
- 一部モジュール（data パッケージ等）はこの README に含まれる抜粋以外のコードと連携します。実運用前に validate_config で設定・パスの確認を行ってください。

ライセンス・貢献
----------------
- 本ドキュメントはコードベースの説明用です。実際のライセンスファイル（LICENSE）がプロジェクトに含まれている場合はそちらを参照してください。
- バグ報告・機能改善はプルリクエスト歓迎です。テスト/CI の整備がある場合はその手順に従ってください。

以上。必要であれば README に含める実行例のさらに詳細なコマンドや .env のテンプレート、サンプルデータの作成手順を追記します。どの情報を追加しますか？