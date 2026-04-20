# KabuSys — README

KabuSys は日本株向けの自動売買／リサーチ基盤の軽量フレームワークです。本リポジトリは以下の主要機能を提供します。
- 戦略リサーチ（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、株数計算）
- 実行系（ExecutionEngine：ブローカー接続／発注管理／リスク制御）
- 監視系（System / Trade / Risk モニタ、Kill Switch、ログ永続化）
- Paper Trading 用検証レポート
- ニュース NLP / レジーム判定（OpenAI を用いた LLM ベースの補助機能）

以下はコードベース（src/kabusys）に基づく使い方とセットアップ手順、ディレクトリ構成の説明です。

---

## 主要機能一覧
- research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- portfolio
  - 候補選定、等配分/スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - 株数計算（単元丸め、aggregate cap）
- execution
  - ExecutionEngine（発注・注文管理・リスク管理・reconciler 等）
  - BrokerFactory による本番 / PaperTrading（Mock）切替
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視 DB（system_status / trade_logs / positions / risk_logs / dashboard）
  - Kill Switch（data/kill.flag による Execution 停止）
- ai
  - ニュース NLP（OpenAI で銘柄別センチメント算出）
  - レジーム判定（MA + マクロセンチメントの合成）
- tools
  - Paper Trading の検証レポート生成スクリプト

---

## 前提 / 必要環境
- Python 3.10 以上（コード中で `X | Y` の型ヒントを使用）
- 主要外部ライブラリ（最低限）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（`validate_config` で YAML 検証を行いたい場合）
- 推奨：仮想環境（venv / venvwrapper / poetry など）

例（最小セットのインストール）:
pip install duckdb psutil openai PyYAML

※ requirements.txt がある場合はそれを使用してください。

---

## 初期セットアップ
1. リポジトリをクローンしてルートへ移動
   - プロジェクトルートは .git または pyproject.toml により自動検出されます。

2. 仮想環境を作成・有効化し、依存関係をインストール

3. .env を作成
   - 対話式ウィザードで作成するのが簡単です：
     python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - 任意・デフォルト:
     - KABUSYS_ENV=development（development / paper_trading / live）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

4. DB / ディレクトリ
   - デフォルトでは以下ファイルを使用・作成します（必要に応じて .env で上書き）
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/（LOG_DIR 環境変数で変更可）
   - PID / flag ファイル: data/execution.pid, data/stop_requested.flag, data/kill.flag

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

---

## 使い方（起動・コマンド）
プロジェクトはモジュールとして起動する形になっています。以下は主要スクリプトの例。

- 監視ループ（SystemMonitor 単体の起動）
  - デフォルトでは MONITOR_POLL_INTERVAL=60 秒
  - 起動:
    python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止:
    data/stop_requested.flag を作成するとループが終了します（stop フラグ検知）。

- ExecutionEngine（発注エンジン）起動
  - paper_trading モードでは MockBroker を使用し、専用 DB を使用（data/paper_trading.db）
  - 起動:
    python -m kabusys.run_execution
  - 停止:
    data/stop_requested.flag を作成するとエンジンを停止します。
  - PID ファイル:
    data/execution.pid（開始時に書き込み、終了時に削除されます）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成（tools）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI 関連（OpenAI API キー必須）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime は内部関数で OpenAI を呼びます。
  - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡します。

---

## 主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — 動作モード
  - paper_trading: MockBroker を使い data/paper_trading.db を使用
  - live: 実取引モード（注意して使用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（ログ保存先）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒）
- OPENAI_API_KEY（AI 機能で必須）
- KILL_FLAG_CLEAR_ON_START（起動時に data/kill.flag を自動クリアするか。0/1）

注意: .env は自動的に読み込まれます（プロジェクトルートが特定できる場合）。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## Kill / Stop の仕組み
- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルの存在を監視し、存在すると安全に停止します。
- Kill Switch（自動停止）
  - RiskMonitor → KillSwitch の評価で条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルが送られます。
  - 実稼働では KILL_FLAG_CLEAR_ON_START を 0（自動クリアしない）にしておくことを推奨します。

---

## ログ
- ロギングは kabusys.utils.logging_setup.setup_logging で統一管理されます。
- デフォルト: stdout と 日次ローテーションのファイルハンドラ（logs/<app_name>.log）
- ログレベル・ログディレクトリは環境変数や引数で調整可能。

---

## トラブルシューティング / 注意点
- validate_config は PyYAML がないと config/*.yaml の中身検証をスキップします（警告）。
- AI 機能を使用するときは OPENAI_API_KEY を必ず設定してください。未設定時は例外になります。
- Paper Trading と本番 DB は明確に分離されています（paper_trading モードは paper_sqlite_path を使用）。
- process_priority が起動時に "high" に設定されますが、権限不足で設定に失敗する場合があります（警告が出ます）。
- DuckDB / SQLite のファイルパスの親ディレクトリがない場合、警告が出ます（起動時に自動作成されることが多いです）。
- データベースマイグレーション（monitoring_db）により古い DB にカラム追加を行います（起動時に実行）。

---

## ディレクトリ構成（src/kabusys ベース）
主要ファイル / モジュールを抜粋して示します。

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数 / 設定読み込み
    - config_setup.py             — .env 対話式ウィザード
    - validate_config.py          — 設定検証 CLI
    - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - ai/
      - news_nlp.py               — ニュース NLP（OpenAI）
      - regime_detector.py        — 市場レジーム判定（MA + LLM）
    - data/                       — （データ関連モジュールが想定）
    - execution/
      - execution_engine.py       — 実行エンジン本体（EngineConfig 等）
      - order_manager.py
      - order_repository.py
      - risk_manager.py
      - reconciler.py
      - broker_factory.py
    - monitoring/
      - monitoring_db.py          — SQLite 永続化層
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
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

プロジェクトルートには .env（作成）、config/*.yaml（設定テンプレート）、data/（DB・flag・pid）、logs/（ログ）などが想定されます。

---

## 開発・拡張のヒント
- ファクター計算・リサーチ機能は DuckDB を利用する想定です。prices_daily / raw_financials 等のテーブルを準備してください。
- ExecutionEngine のブローカー実装は抽象化されているため、実ブローカー用クラス／MockBroker の切り替えを実装して利用します。
- AI 機能（news_nlp / regime_detector）は外部 API 呼び出しを伴うため、ユニットテストでは _call_openai_api をモックしてください。
- monitoring の各種閾値は Settings 経由で設定可能です（.env に値を追加）。

---

必要に応じて README に追記します。追加で載せたい項目（例: 実行例のスクリーンショット、より詳細な設定項目一覧、CI / デプロイ手順など）があれば教えてください。