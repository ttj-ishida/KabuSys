# KabuSys

日本株向けの自動売買システム（ライブラリ・ユーティリティ群）。  
このリポジトリは、戦略・ポートフォリオ構築、実行エンジン、監視、リサーチ、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動 / CLI）
- 環境変数（主な設定項目）
- 安全上の注意（本番運用時のポイント）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム売買を想定したモジュール群です。主要な責務は次のとおりです。

- 戦略研究・ファクター計算（DuckDB を想定した時系列処理）
- ポートフォリオ構築（候補選定、重み付け、単元丸め、ポジションサイジング）
- 実行（ExecutionEngine：ブローカークライアント経由の発注管理、リスク管理、リコンシリエーション）
- 監視（System / Trade / Risk モニタ、Kill Switch、アラート）
- AI 支援（ニュースのセンチメント解析・レジーム判定：OpenAI）
- 運用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計は「本番データと検証データの分離」「ルックアヘッドバイアス防止」「外部 API の呼び出しは明示的な設定（API キー）で行う」などを重視しています。

---

## 機能一覧

主な機能（モジュール）：

- config: 環境変数 / .env の読み込み・管理（自動読み込み・保護機能あり）
- config_setup: 対話式ウィザードで .env を作成・更新
- validate_config: 起動前検証（必須環境変数 / ファイル / YAML 構文など）
- run_execution: ExecutionEngine 起動スクリプト（実発注 or ペーパートレード切替）
- run_monitoring: SystemMonitor ポーリングループ起動スクリプト
- monitoring:
  - MonitoringDB: SQLite による監視ログ永続化（system_status / trade_logs / risk_logs / positions / dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager（アラート送信は LINE 等を想定）
- portfolio:
  - portfolio_builder: 候補選定・重み計算（等重・スコア加重）
  - position_sizing: 発注株数計算（単元丸め・リスクベース・キャップ適用）
  - risk_adjustment: セクター上限・レジーム乗数
- research:
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB SQL）
  - feature_exploration: 将来リターン、IC、統計サマリ
- ai:
  - news_nlp: OpenAI を用いたニュースセンチメント集約・ai_scores への書き込み（ペナルティやリトライ実装あり）
  - regime_detector: マクロニュース + ETF MA によるレジーム判定
- tools:
  - paper_verification_report: ペーパートレード DB を解析して検証レポート出力
- utils:
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定（Windows / POSIX 対応）

---

## セットアップ手順

前提:
- Python 3.10+（型注釈に union types 等を使用）
- 主要な依存ライブラリ（例: duckdb, psutil, openai, PyYAML が一部機能で必要）をインストールしてください。

例（pipenv / venv / pip 等を利用）:
1. 仮想環境作成・有効化（任意）
2. 必要パッケージのインストール（例）
   pip install duckdb psutil openai

PyYAML を検証まで行う場合:
   pip install pyyaml

注意: requirements.txt は本リポジトリに含まれていないため、運用環境では必要なバージョンを合わせて管理してください。

初期設定 (.env):
1. 対話式ウィザードで .env を作成
   python -m kabusys.config_setup

2. 生成された .env を確認し、必要な秘密情報（J-Quants, kabu API, OPENAI_API_KEY など）を設定してください。

DB 初期化:
- run_execution / run_monitoring 起動時に必要な DB テーブルは自動で作成されます（monitoring_db.init_monitoring_db）。

---

## 使い方

主要な CLI / スクリプト:

- 環境設定ウィザード（.env の作成・更新）
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も失敗扱いにする

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に取引ログを記録します。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行中は data/execution.pid を利用する（PID ファイルのパスは Settings で変更可能）。

- 監視ループ起動（SystemMonitor を定期実行）
  python -m kabusys.run_monitoring

  挙動:
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
    例: export MONITOR_POLL_INTERVAL=30
  - stop フラグ（data/stop_requested.flag）を検知するとループを終了します。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず本番 DB を見る仕様）。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パス指定可能（優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

ログ設定:
- setup_logging() を各起動スクリプトが呼び出しています。ログは stdout と logs/<app_name>.log（日次ローテート）に出力されます。LOG_DIR 環境変数でログディレクトリを変更できます。

停止 / Kill:
- 実行エンジンを外部から停止するには監視コンポーネントが書き込む data/kill.flag を利用します。KillSwitch は条件を満たすと kill.flag を書き込み、ExecutionEngine はこれを検出して安全停止できます。
- 監視・実行スクリプト自体の即時停止には data/stop_requested.flag を作成してください。run_monitoring/run_execution はこのファイルを監視して安全に終了します。
  例: touch data/stop_requested.flag

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（validate_config により必須）
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（monitoring）パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading）パス。デフォルト: data/paper_trading.db
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで必要）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（テスト等で使用）

簡易 .env サンプル:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

注意: .env は機密情報を含むため、絶対に Git 等へコミットしないでください。

---

## 安全上の注意（本番運用時のポイント）

- KABUSYS_ENV=live を設定すると本番動作になります。validate_config は live 環境で追加警告を表示します。LINE 通知や kill flag の設定など、必ず事前に確認してください。
- KILL_FLAG_CLEAR_ON_START は生産環境で 1 にしないでください（自動クリアは危険）。
- run_execution は起動時に data/stop_requested.flag をチェックします。運用開始前に stop flag を確認してください。
- PID ファイル / flag ファイルは data/ ディレクトリ下に作られる想定です。実行ユーザーに対するディレクトリのパーミッションに注意してください。
- OpenAI API の使用はコストとレイテンシを伴います。API キーとレート制限に対する対策（リトライ・バックオフ）は実装されていますが、運用ルールを定めてください。

---

## ディレクトリ構成（主なファイル・モジュール）

下は src/kabusys 以下の主要ファイル群の一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / .env 自動読み込み・Settings
  - config_setup.py          # .env 対話ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            # ニュース → OpenAI → ai_scores 書き込み
    - regime_detector.py     # マクロ + MA によるレジーム判定

  - monitoring/
    - monitoring_db.py       # SQLite テーブル作成 / MonitoringDB API
    - system_monitor.py      # システム状態・データ鮮度監視
    - trade_monitor.py       # （省略: Trade 監視ロジック）
    - risk_monitor.py        # ドローダウン / ポジション上限監視
    - kill_switch.py         # kill.flag 書き込み / 判定
    - monitoring_engine.py   # 各 Monitor を束ねる
    - alert_manager.py       # （外部通知ラッパー: LINE 等を想定）

  - execution/
    - execution_engine.py    # ExecutionEngine（発注ループ等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py      # BrokerClient の生成（実ブローカ / Mock 切替）
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

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

その他:
- data/  : 実行時に生成される DB / PID / flag ファイルのデフォルト配置（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）
- logs/  : ログ出力先（デフォルト）

---

もし README に追加してほしい具体的な内容（例: 実行例ログ、API モックの説明、TradeMonitor の詳しい仕様、実行エンジンの設定パラメータ説明など）があれば教えてください。必要に応じてサンプル .env のテンプレートや運用手順（デプロイ手順、systemd サービス定義例等）も作成します。