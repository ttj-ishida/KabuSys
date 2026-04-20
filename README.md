# KabuSys

日本株自動売買システムの Python コードベースです。  
この README はリポジトリ内の主要スクリプト・モジュール（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニュース処理など）の使い方とセットアップ手順を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムで、以下の機能群を提供します。

- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化（本番 / ペーパートレーディング対応）
- システム監視（SystemMonitor / MonitoringEngine）とアラート / Kill Switch（リスクによる停止）
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ計算、セクター制限）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量解析ツール
- AI を用いたニュース NLP（OpenAI）を使った銘柄センチメント評価 / レジーム判定
- ペーパートレード検証レポート生成ツール

設計上のポイント:
- 環境ごとの DB 分離（paper_trading は専用 SQLite）
- DuckDB を分析用途に利用
- 設定は .env ファイルまたは環境変数で管理
- ログは統一的に設定（コンソール + 日次ローテートファイル）

---

## 主な機能一覧

- run_execution: ExecutionEngine の起動スクリプト。KABUSYS_ENV に応じて本番 / ペーパートレード切替。
- run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）。
- config_setup: 対話式に .env を作成・更新するウィザード。
- validate_config: .env と config/*.yaml の事前チェック CLI。
- tools.paper_verification_report: ペーパートレードの検証レポートを生成。
- portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター調整など純粋関数群。
- research: DuckDB を使ったファクター計算（モメンタム、価値、ボラティリティ）と解析ユーティリティ。
- ai.news_nlp / ai.regime_detector: OpenAI を使ったニュースセンチメント評価・レジーム判定（OpenAI API キー必須）。
- monitoring.*: 監視 DB（SQLite）管理、各種モニター（System、Trade、Risk）、KillSwitch、MonitoringEngine。

---

## セットアップ手順

1. Python 環境の準備
   - Python 3.9+ を想定（プロジェクトの pyproject.toml に準拠してください）。
   - 仮想環境の作成推奨:
     python -m venv .venv
     source .venv/bin/activate  # (UNIX)
2. 依存ライブラリのインストール
   - 必要な外部パッケージ（例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config で YAML 検証を行う場合）
   - pip 例:
     pip install duckdb psutil openai pyyaml
   - ※ 実際の requirements.txt / pyproject に従ってください。
3. .env の作成
   - 対話式ウィザードを利用:
     python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他（任意/デフォルトあり）:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）
     - PAPER_FILL_MODE（paper_trading 時の擬似約定モード: instant|partial|never|reject）
4. 設定の検証（任意だが推奨）
   python -m kabusys.validate_config
   - 警告も厳格扱いにする場合:
     python -m kabusys.validate_config --strict
5. データディレクトリ作成（必要な場合）
   - デフォルトでは logs/、data/ 配下に DB・フラグファイルを作成します。必要に応じてパーミッションを確認してください。

---

## 起動・使い方

基本的にモジュールは以下のようにモジュール実行できます。

- ExecutionEngine を起動（開発/ペーパートレード/本番は KABUSYS_ENV に依存）
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid（デフォルトの PID ファイル）に PID が保存される想定（EngineConfig 側）。

- Monitoring を起動（ポーリング監視）
  python -m kabusys.run_monitoring

  挙動:
  - MONITOR_POLL_INTERVAL 環境変数 (秒) でポーリング間隔を設定可能（デフォルト: 60）。
  - 監視は本番用 sqlite_path（settings.sqlite_path）を使用（KABUSYS_ENV に依らない）。
  - 停止するにはプロジェクトルート/data/stop_requested.flag を作成するか、Ctrl+C。

- ペーパートレード検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- AI ニューススコアリング / レジーム判定（プログラム的利用）
  - ニューススコアリング関数:
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
  - レジーム判定関数:
      from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
  - OpenAI API キーが必要（引数または環境変数 OPENAI_API_KEY）。API 呼び出しはリトライやフォールバック処理を備えています。

- Kill Switch / 停止フラグ
  - KillSwitch はリスク条件発動時に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを渡します（Settings.kill_flag_path を参照）。
  - manual 停止（監視ループ / 実行エンジン）: プロジェクトルート/data/stop_requested.flag を作成すると run_* スクリプトは検知して終了します。

- ログ設定
  - 各スクリプトは起動時に setup_logging(app_name=...) を呼び出して stdout と logs/<app_name>.log（日次ローテーション）へ出力します。LOG_DIR 環境変数でログディレクトリを上書き可能。

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

- データベース / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパー用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）

- AI / 外部
  - OPENAI_API_KEY（AI 機能利用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）

- その他
  - MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject、デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag を自動でクリア）

---

## 停止・フラグ管理

- サービス停止リクエスト（run_execution / run_monitoring 側の即時停止）
  - プロジェクトルート/data/stop_requested.flag を作成すると両スクリプトは次のサイクルで検知して停止します。
- Kill Switch（リスクによるトレード停止）
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）へ理由テキストを書き込みます。ExecutionEngine はこの flag を参照して安全停止する設計です。
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START によって制御されます（本番では 0 推奨）。

---

## 開発者向けメモ

- Paper trading は本番 DB と分離され、MockBrokerClient を使って擬似約定を行います（データ整合性・検証に有効）。
- DuckDB はリサーチ・AI 前処理向けの列指向 DB として使われます。prices_daily / raw_financials / raw_news 等のテーブルを前提とした処理が多いです。
- ロギング、プロセス優先度設定（set_process_priority）、CPU affinity などのユーティリティが utils 以下に実装されています。
- 設定の自動ロード: .env / .env.local をプロジェクトルートから自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - execution/                   — 発注エンジン周り（BrokerFactory 等）
    - (OrderManager / ExecutionEngine / Reconciler / RiskManager 等)
  - monitoring/
    - monitoring_db.py           — SQLite 持続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                 — ニュースセンチメント取得（OpenAI）
    - regime_detector.py         — レジーム判定（MA + マクロセンチメント）
  - data/ (想定する実行時ディレクトリ)
    - monitoring.db (default SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kill.flag
    - stop_requested.flag
  - logs/ (ログ出力先、LOG_DIR で上書き可)

（注）上記はリポジトリ中の主要モジュールを抜粋したものです。より詳細なファイル一覧は実際のソースツリーを参照してください。

---

## よくある運用ワークフロー（例）

1. .env を作成:
   python -m kabusys.config_setup
2. 設定チェック:
   python -m kabusys.validate_config --strict
3. ログディレクトリ / data ディレクトリを作成（必要なら）:
   mkdir -p logs data
4. DuckDB / SQLite に必要なスキーマを準備（初回実行時にスクリプトが作成する場合あり）
5. 監視プロセスを起動:
   python -m kabusys.run_monitoring &
6. ExecutionEngine を起動（本番または paper_trading を .env で切替）:
   python -m kabusys.run_execution &
7. 停止:
   touch data/stop_requested.flag
   （または KillSwitch による自動停止で data/kill.flag が生成される）

---

## ライセンス・注意事項

- .env ファイルには機密情報（APIキー等）が含まれるため、決して Git にコミットしないでください（config_setup もその旨を注意書きしています）。
- 本リポジトリのコードは実際の資金での運用に用いる場合は十分な検証と監査を行ってください。特に本番（KABUSYS_ENV=live）での設定は慎重に。

---

ご不明点があれば、どの機能についてさらに詳しくドキュメント化すべきか教えてください。README を補強して CLI の具体的なオプション説明や systemd ユニット例なども追加できます。