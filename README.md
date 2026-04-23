# KabuSys

日本株自動売買システムのサンプル実装リポジトリ（ドキュメント兼 README）。

以下はこのコードベースの概要、主要機能、セットアップ・実行方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームを想定したモジュール群です。主な関心事は次のとおりです。

- シグナル生成・ポートフォリオ構築（ファクター計算、候補選定、重み付け、ポジションサイズ算出）
- ExecutionEngine による発注制御（リスク管理、注文管理、ブローカークライアント抽象化）
- 監視機能（システム状態・取引ログ・リスク監視、Kill Switch）
- 研究・解析（DuckDB を用いたファクター計算、IC 計算、特徴量分析）
- AI 補助（ニュースの NLP スコアリング / レジーム判定：OpenAI API を利用）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）
- ロギング・プロセス優先度などのユーティリティ

設計方針として、可能な限りフェイルセーフ（API エラーはスキップし継続）かつルックアヘッドバイアスを避ける実装になっています。

---

## 機能一覧（主要モジュール）

- kabusys.config / config_setup / validate_config
  - .env の自動読み込み/対話式作成/設定検証ツール
- kabusys.run_execution
  - ExecutionEngine 起動スクリプト。`KABUSYS_ENV=paper_trading` 時は MockBroker を使い DB を分離
- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL により間隔変更可）
- kabusys.monitoring.*
  - MonitoringDB（SQLite）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、アラート管理
- kabusys.portfolio.*
  - 候補選定、配分（等金額・スコア重み）、セクター制限、レジーム乗数、株数決定（単元丸め・aggregate cap）
- kabusys.research.*
  - ファクター計算（モメンタム／ボラティリティ／バリュー）、将来リターン、IC、統計サマリー
- kabusys.ai.*
  - news_nlp: OpenAI でニュースをスコアリングし ai_scores に書き込み
  - regime_detector: ETF MA とマクロ記事センチメントを合成して market_regime を算出
- kabusys.tools.paper_verification_report
  - ペーパートレード履歴から検証レポートを生成
- kabusys.utils
  - logging_setup（統一ログ設定）、process_priority（優先度・CPU affinity）

---

## セットアップ手順

以下はローカルで実行する際の最低限の手順の例です。

1. Python 環境準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 必須（基本動作に必要）:
     - duckdb, psutil
   - AI / YAML 機能を使う場合:
     - openai, PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

   （本リポジトリに requirements.txt がある場合はそれを利用してください。）

3. プロジェクトルートに移動（.env 自動ロードはプロジェクトルートの存在（.git または pyproject.toml）を検出して行われます）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 例として必要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他（オプション／デフォルトあり）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱い

6. データディレクトリ準備
   - data/ ディレクトリは自動作成される箇所がありますが、適宜確認してください。
   - logs/ ディレクトリへログが出力されます（logs/<app_name>.log）

---

## 使い方（実行コマンド例）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading のとき、MockBroker を利用し DB は data/paper_trading.db に分離されます
    - エンジン停止には data/stop_requested.flag の作成、または Kill Switch により data/kill.flag が書き込まれる仕組みがあります
    - 実行中は PID ファイル（data/execution.pid 等）を生成します

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番の sqlite_path を使用（環境に依らず）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI 機能のプログラム呼び出し例（コードから）
  - ニューススコア（DuckDB 接続を渡す）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

  （OpenAI API キーは環境変数 OPENAI_API_KEY または引数で指定）

---

## 運用に関する注意点

- KABUSYS_ENV
  - development: 開発用（発注なしの挙動が期待される）
  - paper_trading: ペーパートレード（MockBroker、data/paper_trading.db を使用）
  - live: 本番（実際に発注が行われる）
- Kill Switch
  - KillSwitch は risk モニタ等から data/kill.flag を書き込み ExecutionEngine の停止を促します
  - ExecutionEngine の起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番では 0 推奨）
- 停止フラグ
  - data/stop_requested.flag が存在すると run_execution / run_monitoring は安全に停止します
- ロギング
  - logs/<app_name>.log に日次ローテーションで出力（デフォルトで 30 日保存）
  - コンソール出力は stdout を使用
- データベース
  - DuckDB: 分析用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・発注ログ（デフォルト data/monitoring.db、ペーパートレード時は data/paper_trading.db）

---

## 主要環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用系・任意:
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, 例: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)
- LOG_DIR
- OPENAI_API_KEY（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番通知用）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動削除するか）

（詳細は kabusys.config と config_setup の定義を参照してください）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化 / CRUD
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (参照実装あり)
- execution/               — ExecutionEngine や order_manager 等（本コードベースの一部）
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
- data/（実行時に作成されることが多い）
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading)
  - kabusys.duckdb
  - execution.pid, stop_requested.flag, kill.flag

logs/
- execution.log
- monitoring.log
- ...（日次ローテート）

---

## よくある操作メモ

- 設定を先に検証:
  - python -m kabusys.validate_config
- .env を作りたい / 更新したい:
  - python -m kabusys.config_setup
- ペーパートレード検証:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 監視をテスト的に一回だけ実行したい:
  - MonitoringEngine 等のクラスをインポートして run_once() を呼ぶ（ユニットテストや REPL で）

---

## 最後に

この README はコードベースから抽出した主要な情報をまとめたものです。実際の運用前に必ず:
- .env を適切に設定
- python -m kabusys.validate_config でチェック
- 本番（KABUSYS_ENV=live）では LINE 等のアラート設定・ Kill Switch 動作を再確認

不明点や追加の手順が必要であれば、具体的な利用ケース（ローカル開発 / CI / 本番デプロイ等）を教えてください。必要に応じて起動システムユニット（systemd / supervisor / docker-compose）向けの設定例も作成します。