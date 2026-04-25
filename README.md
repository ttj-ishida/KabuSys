# KabuSys

日本株向け自動売買システムのコアライブラリ群（README）。  
このドキュメントはリポジトリ内の主要スクリプト・モジュールに基づいて機能概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買および関連する調査・監視機能を提供するモジュール群です。主な目的は次のとおりです。

- 売買シグナルに基づく銘柄選定・ポートフォリオ構築・発注（ExecutionEngine を通じて）
- 実行系の監視・リスク検知と Kill Switch による安全停止
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- Paper Trading（ペーパートレード）用分離DBおよび検証レポートの生成
- ニュースを用いた NLP（OpenAI）によるセンチメント評価と市場レジーム判定

主に次の技術スタックを想定しています（コードより推察）:
- Python 3.9+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- sqlite3（標準ライブラリ）
- （オプション）PyYAML（config の検証に使用）

---

## 機能一覧（抜粋）

- 環境設定管理
  - .env 読み込み (自動ロード)、対話式ウィザード (`kabusys.config_setup`)
  - 設定検証 CLI (`kabusys.validate_config`)
- 実行エンジン
  - `run_execution.py`：ExecutionEngine 起動スクリプト
  - Paper Trading 環境では MockBrokerClient を利用し DB を分離
- 監視・アラート
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動
  - MonitoringDB（SQLite）による永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - RiskMonitor（ドローダウン・ポジション上限監視）、TradeMonitor、SystemMonitor、KillSwitch、MonitoringEngine
- ポートフォリオ構築
  - 候補選定、スコア配分、等重配分、ポジションサイジング、セクターキャップ、レジーム乗数など（pure functions）
- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - ニュース NLP による銘柄センチメント（ai.news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector）
- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）: `utils.logging_setup.setup_logging`
  - プロセス優先度・CPU affinity 設定: `utils.process_priority`
- ツール
  - Paper Trading の検証レポート生成: `kabusys.tools.paper_verification_report`

---

## セットアップ手順

以下はローカル開発 / 実行環境の一般的な手順です。実際の依存関係はプロジェクトの requirements ファイル等を参照してください。

1. リポジトリをクローンし、仮想環境を作成／有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai

   ※ PyYAML は config 検証で任意（`pip install pyyaml`）。

3. 環境変数 / .env の準備
   - 対話式ウィザードで .env を初期作成:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに手動で .env を配置
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（paper_trading用: instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB のパス）

4. 設定の検証（起動前推奨）
   - python -m kabusys.validate_config
   - 本番に近い確認をする場合は `--strict` を付けて警告も失敗扱いにする

5. データディレクトリの準備（必要に応じて）
   - data/ ディレクトリを作成（DB / PID / flag 保存用）
   - logs/ ディレクトリ（ログ保存）

---

## 使い方

基本的な起動例と主要オプションの説明。

- ExecutionEngine を起動（通常モード / 本番判定は KABUSYS_ENV）
  - python -m kabusys.run_execution
  - Paper Trading の場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - Paper Trading 時は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します（本番 SQLite と分離）。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには:
    - export MONITOR_POLL_INTERVAL=30  # 秒（デフォルト 60）
  - run_monitoring は監視用の sqlite_path を本番パス（Settings.sqlite_path）で使用します（KABUSYS_ENV にかかわらず本番 path を参照する実装）。

- .env の対話作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）
  - 例: ai.news_nlp.score_news(duckdb_conn, target_date, api_key=...)
  - 注意: 使用するモデルはコード中で gpt-4o-mini に設定されています。API の利用料金・制限に注意してください。

- Kill Switch / 停止フラグ
  - kill.flag（Settings.kill_flag_path）を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch モジュール）。
  - run_execution/run_monitoring では data/stop_requested.flag や data/execution.pid 等のファイルも使用しています。これらの取り扱いに注意してください。

---

## 主要設定（環境変数）とデフォルト

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
- KABU_API_PASSWORD: 必須（kabuステーション API）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- OPENAI_API_KEY: OpenAI 利用時に必要
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db（paper_trading 用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定振る舞い）
- LOG_LEVEL: ログレベル（INFO など）

設定は .env で管理することが推奨されます。`python -m kabusys.config_setup` で対話的に作成できます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイルとディレクトリの概要です（提供されたコードを基に整理）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み / Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（Paper Trading の分離対応）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ初期化と MonitoringDB クラス
    - system_monitor.py
      - システム監視（CPU/MEM/DISK、データ鮮度、PID チェック）
    - trade_monitor.py
      - （コード未表示だが発注・約定関連の監視を想定）
    - risk_monitor.py
      - ドローダウン・ポジション数監視
    - kill_switch.py
      - kill.flag 書き込みによる停止シグナル
    - monitoring_engine.py
      - 各モニタを束ねるポーリングエンジン
    - alert_manager.py
      - （アラート送信管理、LINE などを想定）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - （これらは発注・注文管理のコア）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/ (ランタイム生成想定)
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading 用）
    - execution.pid, kill.flag, stop_requested.flag など
  - logs/ (ランタイム生成想定)
    - execution.log, monitoring.log など

---

## 開発上の注意点 / 実行上の注意

- DB の初期化: MonitoringDB は接続時に必要なテーブルを冪等に作成します（init_monitoring_db）。
- Paper Trading: paper_trading 環境では実取引に影響を与えないように paper_sqlite_path を分離している点に注意してください。
- Kill Switch: 本番運用時は KILL_FLAG_CLEAR_ON_START の設定に注意（本番では 0 が推奨）。
- OpenAI 使用時の注意: API キー管理、モデル指定、コストに注意してください。API 呼び出しはリトライや安全なフォールバック実装が組まれていますが、API障害時は機能が限定されることがあります。
- ログ: logging_setup により stdout と日次ローテートファイルに出力されます。ログディレクトリの作成権限等に注意してください。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要があれば README に含める例 .env.template、requirements.txt、サービス unit ファイル（systemd）や docker-compose 構成のサンプル、各モジュール（ExecutionEngine / Monitor）の詳しい動作フロー図なども作成します。どの追加情報が必要か教えてください。