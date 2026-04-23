# KabuSys

日本株向け自動売買システムのライブラリ／実行スクリプト群。  
シグナル算出 → ポートフォリオ構築 → 発注（本番 / ペーパー） → 監視 / アラート / Kill Switch といったワークフローを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の主要機能を持つモジュール化された自動売買基盤です。

- 研究用ファクター計算（momentum, volatility, value 等）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- ExecutionEngine（ブローカークライアントを用いた発注ロジック、ペーパートレード対応）
- 監視コンポーネント（システム状態、注文ログ、リスク監視、Kill Switch）
- AI 支援機能（ニュースの NLP センチメント、レジーム判定）
- 運用支援ツール（.env 設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針としては、DB（DuckDB / SQLite）を用いたデータ管理、外部 API 呼び出しは分離・フェイルセーフ化、ルックアヘッド（未来参照）防止などが挙げられます。

---

## 主な機能一覧

- research
  - calc_momentum, calc_volatility, calc_value（DuckDB を用いたファクター計算）
  - calc_forward_returns / calc_ic / factor_summary（特徴量解析ツール）
- portfolio
  - 銘柄選定（select_candidates）
  - 重み計算（等金額・スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジション決定（lot 単位丸め、リスクベース配分、aggregate cap）
- execution
  - ExecutionEngine、OrderManager、RiskManager、Reconciler（発注フロー）
  - BrokerClientFactory（KABUSYS_ENV による実ブローカ or MockBroker 切替）
- monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、プロセス監視）
  - TradeMonitor（注文の滞留・約定異常検出）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（データ/ファイルベースの停止信号）
  - MonitoringEngine（定期ポーリングとアラート連携）
- ai
  - news_nlp（OpenAI を使ったニュースセンチメントの集約・書き込み）
  - regime_detector（マクロ + ETF MA による市場レジーム判定）
- utils
  - logging_setup（ログのコンソール + 日次ローテートファイル設定）
  - process_priority（プロセス優先度 / CPU affinity 設定）
- tools
  - config_setup（.env 対話ウィザード）
  - validate_config（設定検証 CLI）
  - paper_verification_report（ペーパートレードの検証レポート生成）

---

## セットアップ手順

前提: Python 3.9+（型ヒント・モジュール互換を想定）

1. リポジトリをクローン
   - git clone <repository-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール  
   ※requirements.txt がない場合は主要依存を個別にインストールしてください:
   - pip install duckdb psutil openai

   補足: YAML 検証機能（validate_config の一部）を使う場合は PyYAML を追加:
   - pip install pyyaml

4. データディレクトリの準備
   - data/ ローカルに作成されるファイル: logs/, data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など
   - 例: mkdir -p data logs

5. 環境変数設定
   - .env を作成するか、環境変数で設定します。推奨は .env を config_setup で作る方法（下記参照）。

注意: .env は機密情報を含むため絶対に Git にコミットしないでください。

---

## .env（設定）作成・検証

対話式ウィザードで簡単に .env を作成できます:

- python -m kabusys.config_setup

作成後、設定整合性をチェック:

- python -m kabusys.validate_config
- 本番チェックを厳密に行う場合: python -m kabusys.validate_config --strict

validate_config は必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）やファイルパス、YAML の存在などを確認します。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（ニュース NLP / レジーム判定で必要）
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading の場合、MockBroker が使われ、DB は data/paper_trading.db に保存されます
- PAPER_FILL_MODE（paper トレードの約定モード: instant|partial|never|reject）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- LOG_LEVEL（DEBUG/INFO/...）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（0/1。本番で 1 は危険）

---

## 使い方（主な実行コマンド）

※ルート（project root）から実行することを想定しています。

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV を参照）
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成すると起動を抑止・停止できます
  - data/execution.pid に PID が書き込まれます

- Monitoring を起動（監視ループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト: 60）
  - python -m kabusys.run_monitoring

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュール（ニュース / レジーム）
  - news_nlp や regime_detector は OpenAI API を使います。OPENAI_API_KEY を設定してください。
  - 直接 Python API を呼ぶ形で利用します（例: kabusys.ai.score_news）。

ログ:
- ログは logs/<app_name>.log に日次ローテートで保存されます（デフォルト: logs/）。
- setup_logging(app_name="execution") 等で統一的に設定されます。

停止 / Kill Switch:
- 強制停止トリガーは data/kill.flag（KillSwitch が書き込む）。ExecutionEngine は起動時・実行中にこのフラグを参照します。
- KillSwitch はリスク条件（ドローダウンやポジション上限）で作成されます。
- フラグを削除するには手動でファイルを削除するか、Kill Switch コード経由で clear() を呼びます。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag をクリアしますが、本番では 0 を推奨します。

環境の分離:
- KABUSYS_ENV=paper_trading の場合、発注は MockBroker により模擬発注され、DB は data/paper_trading.db に記録され本番 DB と分離されます。

---

## ディレクトリ構成（主なファイル）

プロジェクトルート（src パッケージ配置想定）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・Settings クラス、自動 .env ロードロジック
  - config_setup.py          — .env 対話型ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコア付け
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）

  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — forward returns / IC / 統計要約

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化・永続化 API
    - system_monitor.py
    - trade_monitor.py        — （注文監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信ロジック、LINE 等）

  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - utils/
    - logging_setup.py
    - process_priority.py

  - tools/
    - paper_verification_report.py
    - __init__.py

データ / ログ関連（プロジェクトルート）
- data/
  - monitoring.db            — SQLite（監視ログ）
  - paper_trading.db         — SQLite（ペーパートレード用）
  - kabusys.duckdb           — DuckDB（価格等分析データ）
  - execution.pid            — ExecutionEngine の PID
  - stop_requested.flag      — スクリプト間停止伝達に利用
  - kill.flag                — Kill Switch（ExecutionEngine 停止シグナル）
- logs/
  - execution.log
  - monitoring.log
  - ...（日次ローテート）

---

## 開発上の注意点 / 設計上の留意点

- .env は機密情報を含むため Git にコミットしないでください。
- AI（OpenAI）呼び出しは外部ネットワーク依存のため、失敗時はフェイルセーフ（スコア 0 等）で継続する設計です。ただし正確な結果を得るには OPENAI_API_KEY の設定が必要です。
- DuckDB を用いることで分析用クエリを高速に実行可能です。prices_daily / raw_financials 等のテーブル設計に依存します。
- 本番環境（KABUSYS_ENV=live）では kill flag の自動クリア等危険な設定を避けてください（validate_config が警告を出します）。
- process priority の設定には psutil が必要で、権限により設定できない場合があります（警告が出てスキップされます）。

---

## 例: よく使うコマンドまとめ

- .env を作る（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 実行（ExecutionEngine）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- 監視ループ
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

---

必要であれば、README に依存パッケージの exact requirements.txt、データベーススキーマの詳解、CI／運用手順（systemd / supervisor 用 unit ファイル例）なども追記できます。どの追加情報が必要か教えてください。