# KabuSys

日本株自動売買システムのコアライブラリ群（README）。  
この README はリポジトリ内の主要スクリプト・モジュールの利用方法、設定方法、構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム取引を想定したモジュール群です。  
主な機能は以下の通りです:

- データパイプライン / DuckDB を用いたファクター計算・調査（research）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- Execution エンジン（発注管理、リスク管理、リコンシリエーション）
- Monitoring（システム状態、注文ログ、リスク監視）と Kill Switch（停止フラグ）
- AI モジュール（ニュースのセンチメント評価、レジーム判定） — OpenAI API を利用
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- Paper Trading 用検証ツール（検証レポート生成）

設計方針として、実運用に向けた冪等性・フェイルセーフや、ルックアヘッドバイアス回避が考慮されています。

---

## 機能一覧（抜粋）

- run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading と live を切替）
- run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- monitoring: system/trade/risk の監視、監視ログの永続化（SQLite）
- portfolio: 候補選定、等重・スコア重み、リスク調整、ポジションサイズ計算
- research: ファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン、IC・統計要約
- ai: ニュース NLP（OpenAI）による銘柄別スコアリング、レジーム判定
- tools: Paper Trading 検証レポート生成スクリプト
- config_setup.py: .env を対話的に生成/更新するウィザード
- validate_config.py: .env と config/*.yaml の事前検証 CLI
- utils: ロギング設定、プロセス優先度設定など

---

## 前提条件 / 依存パッケージ

（実行環境に応じて必要なモジュールをインストールしてください）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を使う場合）
- （その他：標準ライブラリのみで動く部分も多い）

pip での例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ requirements.txt はリポジトリにない想定のため、必要なパッケージを上記から導入してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
2. 依存パッケージをインストール（上記参照）
3. 環境変数ファイル (.env) を作成する
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定検証を行う:
     ```
     python -m kabusys.validate_config
     ```
     --strict を付けると警告もエラー扱いになります。
4. data/ や logs/ ディレクトリ等は自動作成されますが、必要に応じて配置を確認してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: execution モード（development / paper_trading / live）（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

例（.env に書く最低限）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 実行方法

- 監視ループ（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - run_monitoring は data/stop_requested.flag を検知すると終了します。

- 実行エンジン（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
  - run_execution は data/stop_requested.flag を検知すると優雅に停止します。
  - ExecutionEngine の PID ファイルは data/execution.pid（Settings.pid_file_path で変更可）。

- .env ウィザード（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB を指定する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- AI モジュールはプログラムから呼び出せます（例）:
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, target_date, api_key="...")

---

## 停止と Kill Switch

- run_monitoring / run_execution は両方ともプロセス間で利用するフラグファイルを監視します:
  - data/stop_requested.flag: 実行スクリプトを終了させるための外部停止フラグ（存在を検知したら停止）
  - data/kill.flag: Monitoring の KillSwitch が発動した場合に書き込まれるファイル。ExecutionEngine は起動時にこのフラグを検査したり、設定により自動クリアを行うことができます（KILL_FLAG_CLEAR_ON_START）。
- KillSwitch は監視結果（ドローダウン超過、ポジション上限超過など）に応じて書き込まれます。書き込みは冪等で既存ファイルがある場合はスキップされます。

---

## ログ

- ログはデフォルトで標準出力 (stdout) とファイル（logs/<app_name>.log、日次ローテーション、30日保持）に出力されます。
- ログディレクトリは環境変数 LOG_DIR または引数で変更可能。
- 各スクリプトは最初に setup_logging(app_name=...) を呼び出しています。

---

## 開発メモ / 安全設計のポイント

- Paper Trading は本番 DB と明確に分離されるよう設計（PAPER_TRADING_SQLITE_PATH）。
- AI 呼び出し（OpenAI）は API 失敗時にフェイルセーフ（0.0 にフォールバック）やリトライ戦略を実装。
- 監視・リスクログは SQLite（monitoring_db）に永続化。DB のスキーマは init_monitoring_db で冪等に作成／マイグレーションされます。
- ルックアヘッドバイアスを避けるため、target_date に対する集計は常に過去データのみを参照するよう設計されています。
- process 優先度や CPU affinity は utils/process_priority.py でプラットフォームを抽象化して設定可能（権限不足等は警告でスキップ）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下。実際のリポジトリに合わせて調整してください）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings クラス（.env 自動ロード機能含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading レポート生成
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し、ai_scores 書込み）
    - regime_detector.py      — レジーム判定（ETF + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文・約定監視（概要）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch 実装（kill.flag 書込）
    - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py        — アラート送信抽象（実装により LINE 等へ通知）
  - execution/
    - execution_engine.py     — ExecutionEngine（注文実行ループ）
    - broker_factory.py       — BrokerClientFactory（Mock / 実ブローカ切替）
    - order_manager.py
    - order_repository.py
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
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - data/                    — デフォルトの data フォルダ（DB、flag、pid などが置かれる）

---

## よくある操作例

- 監視を60秒間隔で起動:
  ```
  python -m kabusys.run_monitoring
  ```
- 監視を30秒に変更:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Execution を paper_trading で起動（.env で KABUSYS_ENV=paper_trading を設定）:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- Paper Trading 検証レポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 開発 / 貢献

- コードのスタイルやユニットテスト、CI 設定は別途リポジトリ方針に従ってください。
- AI モジュールをローカルでテストする際は OPENAI_API_KEY を設定するか、モック関数に差し替えてください（関数内部で API 呼び出し箇所は patch 可能に設計されています）。

---

何か追加してほしい項目（例: 各モジュールの API 使用例や、ExecutionEngine / Broker の詳細設計ドキュメント）があればお知らせください。README を拡張してコマンド例や設定サンプルを追加します。