# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ群。  
実取引（live）・ペーパートレード（paper_trading）・開発（development）に対応し、監視・実行・ポートフォリオ構築・ファクター計算・AI を使ったニュース解析等のコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要（Project Overview）

KabuSys は以下を目的とした Python ベースのモジュール群です。

- 日次・リアルタイムの売買戦略実行（ExecutionEngine）
- システム/注文/リスクの監視とアラート（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ファクター計算・リサーチ用ユーティリティ（DuckDB を用いた計算）
- OpenAI（LLM）を用いたニュースセンチメント評価・市場レジーム判定
- ペーパートレード用ツールと検証レポート生成

設計方針の一部：
- 環境変数（.env/.env.local）で設定を管理
- DuckDB（分析）・SQLite（監視・注文ログ）を併用
- 本番/ペーパートレードは DB を分離
- ログは統一的な logging 設定（コンソール + 日次ローテーション）

---

## 機能一覧（Features）

主な機能（モジュール）:

- 実行関連
  - run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV により MockBroker 使用可）
  - BrokerClientFactory / OrderManager / RiskManager / Reconciler（発注・リスク管理周り）

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - MonitoringEngine: System / Trade / Risk Monitor を束ね、Kill Switch や Alert を処理
  - MonitoringDB: SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch: データ/閾値に応じて `data/kill.flag` を書き込み停止シグナルを送信

- ポートフォリオ構築
  - portfolio_builder: 候補選定・重み計算（等分配・スコア加重）
  - position_sizing: 株数決定（リスクベース・重みベース等）
  - risk_adjustment: セクター上限・レジーム乗数

- リサーチ
  - research.factor_research: Momentum / Volatility / Value ファクター等の計算（DuckDB 使用）
  - research.feature_exploration: 将来リターン計算・IC（Information Coefficient）等

- AI（OpenAI 連携）
  - ai.news_nlp: ニュースを LLM でセンチメント評価して ai_scores に書き込み
  - ai.regime_detector: ETF MA と LLM を組み合わせた市場レジーム判定

- ツール
  - config_setup.py: .env の対話式作成ウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

- ユーティリティ
  - utils/logging_setup.py: ログ設定（コンソール + 日次ファイルローテーション）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - config.py: 環境変数読み込み・Settings ラッパー（自動 .env ロード機能あり）

---

## セットアップ手順（Setup）

前提
- Python 3.10 以上（Union Types (A | B) を使用）
- 仮想環境の利用を推奨

手順の例:

1. リポジトリをクローン、仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必要な外部パッケージ（少なくとも）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合に推奨）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. 環境変数設定
   - プロジェクトルートに .env を作成するか、環境変数を直接設定します。
   - 対話的に作成する:
     - python -m kabusys.config_setup
   - 主要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用、デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI モジュール使用時に必要)
     - LOG_LEVEL, LOG_DIR など

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL として扱う場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトの SQLite/DuckDB パスは `data/` に配置されます。必要に応じて先にディレクトリを作成してください（logging_setup は logs/ を作成します）。

---

## 使い方（Usage）

基本的な起動例と利用例を示します。

環境（例）
- 開発: KABUSYS_ENV=development（発注なし）
- ペーパートレード: KABUSYS_ENV=paper_trading（MockBroker 使用、paper DB に記録）
- 本番: KABUSYS_ENV=live（実ブローカーに接続）

1. .env を作成 / 更新
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3. 実行エンジン起動（ExecutionEngine）
   - 簡易:
     - python -m kabusys.run_execution
   - 注意:
     - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）に記録されます。
     - 実行開始前に `data/stop_requested.flag` があると起動をスキップします。
     - 実プロセスの PID ファイルは data/execution.pid に書き出されます（設定で変更可）。

4. 監視ループ起動（SystemMonitor）
   - python -m kabusys.run_monitoring
   - モニタのポーリング間隔を変更する:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は常に本番の sqlite_path を使用します（monitoring 用は環境に依存しません）。
   - 停止フラグ `data/stop_requested.flag` を作成するとループが終了します。

5. ペーパートレード検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で代替可）

6. AI 関連（OpenAI）
   - ニューススコアリング:
     - ai.news_nlp.score_news(conn, target_date, api_key=...)
     - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で指定）
   - レジーム判定:
     - ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - 注意:
     - API 呼び出しはリトライ/バックオフやフォールバック（失敗時は安全側の値）を実装していますが、API 利用に伴うコストやレート制限に注意してください。

7. ログ
   - デフォルトは logs/<app_name>.log（app_name は "execution"/"monitoring" 等）
   - コンソール出力は stdout、ファイルは日次でローテーション（30 日保持）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- OPENAI_API_KEY — LLM 機能を使用する場合に必須
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL / LOG_DIR
- KILL_FLAG_CLEAR_ON_START — 本番起動時の kill.flag 自動クリア（危険）

設定は .env / .env.local を通じてロードされます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## ディレクトリ構成（Directory structure）

リポジトリ内 /src/kabusys 以下の主なファイル・モジュール構成（抜粋）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/Settings 管理（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 永続化（schema + helper）
    - monitoring_engine.py    — 各 Monitor を束ねる Engine
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 発注ログ監視（滞留注文等）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - alert_manager.py        — （アラート送信ラッパー、実装参照）
  - execution/
    - execution_engine.py     — 実行エンジン本体（session 実行）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
    - news_nlp.py             — ニュースの LLM スコアリング
    - regime_detector.py      — レジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/                     — （実行時に生成される: DB, PID, flag など）
  - logs/                     — ログファイル出力先（デフォルト）

（実際のリポジトリ tree を参照してください。上記は主要ファイルの抜粋です）

---

## 運用上の注意 / 補足（Notes）

- KABUSYS_ENV=live の場合は設定ミスが重大な実取引リスクに直結します。validate_config で設定を慎重に確認してください。
- kill.flag（Settings.kill_flag_path）/ stop_requested.flag（プロジェクトの data 側）を使って安全にプロセスを停止できます。KILL_FLAG_CLEAR_ON_START は本番で 1 に設定しないでください。
- Paper Trading は本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- AI モジュールは OpenAI API を利用します。API のコスト・レート制限に注意し、API キー管理を厳重に行ってください。
- ログディレクトリ作成に失敗した場合、ファイル出力はスキップされコンソール出力のみになります。

---

必要があれば、README にチュートリアル例（実際の ExecutionEngine のパラメータや、ai.score_news 実行サンプルコード）を追加します。どの例を追加したいか教えてください。