# KabuSys

日本株自動売買システムのコアライブラリ群（README）。  
この README はリポジトリ内のスクリプト・モジュールから生成可能な機能と起動手順をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究パイプラインを想定したモジュール群です。主に以下の役割を持ちます。

- 注文実行エンジン（ExecutionEngine）およびその支援コンポーネント（OrderManager / RiskManager 等）
- システム監視・アラート（Monitoring） — システム状態・注文状況・リスク監視と Kill Switch
- ポートフォリオ構築（候補選定 / 重み算出 / ポジションサイズ算出 / セクター制約）
- 研究用ファクター計算・特徴量解析（duckdb を用いたファクター計算）
- ニュース NLP（OpenAI を用いたニュースセンチメント集約）とレジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証、ツールスクリプト）

設計上、
- DuckDB / SQLite をデータ層として使用
- OpenAI API 連携は任意（APIキーを設定することで有効）
- Paper Trading（ペーパートレード）用に実運用 DB と分離したモードを持つ

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
  - 停止フラグファイル（data/stop_requested.flag）を検出してセッション停止
  - PID ファイルを書き出し（data/execution.pid）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視結果は SQLite（monitoring.db）に永続化

- monitoring package
  - MonitoringDB: 監視用 SQLite テーブルの初期化・読み書き
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch: 条件に応じて data/kill.flag を作成して ExecutionEngine に停止シグナルを送信
  - AlertManager（アラート送信ロジックは別実装想定）

- portfolio package
  - 銘柄選定（select_candidates）、重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ適用・レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- research package
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 先行リターン計算、IC（情報係数）、統計サマリ（feature_exploration）

- ai package
  - news_nlp.score_news: raw_news を OpenAI に送って銘柄別センチメントを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）MA やマクロニュースを用いて市場レジームを判定・保存

- utils
  - logging_setup.setup_logging: 統一的なログ出力（stdout + 日次ローテーションファイル）
  - process_priority.set_process_priority / set_cpu_affinity: OS に依存しない優先度設定

- scripts / ツール
  - kabusys.config_setup: 対話式 .env 作成ウィザード
  - kabusys.validate_config: .env / config/*.yaml の前検証スクリプト
  - kabusys.tools.paper_verification_report: ペーパートレード DB から検証レポート生成

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型注釈に Python 3.10 の構文を使用）
- システムに sqlite3 が入っている（標準ライブラリ）
- 任意で OpenAI を利用する場合は API キーが必要

1. レポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最小（必須）:
     - duckdb
     - psutil
   - OpenAI 機能を使う場合:
     - openai
   - validate_config の YAML 検証を有効にしたい場合:
     - pyyaml

   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

   （リポジトリに requirements.txt があれば `pip install -r requirements.txt` を使ってください）

4. 初期設定ファイル（.env）を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - または .env.example を参照して手動で .env を作成してください。

5. 設定検証（オプション）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い
   ```

6. データディレクトリやログディレクトリは自動作成されますが、必要に応じて先に `data/` `logs/` を作成しても構いません。

---

## 主要な環境変数（Settings で参照するもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う設定（デフォルトを示します）:
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live") — デフォルト "development"
- DUCKDB_PATH: 分析用 DuckDB ファイル（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（data/paper_trading.db）
- LOG_LEVEL: ログレベル（INFO）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に data/kill.flag を自動クリア（本番は 0 推奨）
- OPENAI_API_KEY: OpenAI を使う場合の API キー
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

注意: run_monitoring は監視用の sqlite_path（SQLITE_PATH）を常に使用します。実行エンジン（run_execution）は KABUSYS_ENV に応じて paper_sqlite_path / sqlite_path を切り替えます。

---

## 使い方（起動例）

- 実行エンジン（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading にしたい場合:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 既に data/stop_requested.flag が存在すると起動せず終了します（安全機能）。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変える:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- .env を対話式で作成
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB を別パスのファイルに指定する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- ライブラリ的に関数を呼ぶ例（Python REPL）
  ```py
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026,4,10))
  ```

- OpenAI を利用する機能（news_nlp / regime_detector）を使う場合は OPENAI_API_KEY を環境変数か関数引数で渡してください。

---

## 停止・Kill の扱い

- run_execution / run_monitoring は両方ともプロジェクトルート配下の data/stop_requested.flag の存在を監視し、存在するとループを終了または停止処理を開始します。外部から停止したい場合はフラグファイルを作成してください:
  ```
  mkdir -p data
  touch data/stop_requested.flag
  ```

- KillSwitch は条件（ドローダウンやポジション上限など）を満たすと data/kill.flag を書き込み、ExecutionEngine を停止するためのシグナルとして利用します。KILL_FLAG_CLEAR_ON_START を有効にすると起動時に自動的にクリアされます（本番では無効推奨）。

---

## ディレクトリ構成（概要）

以下は src/kabusys 以下の主要ファイル／ディレクトリ構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite のテーブル初期化・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信を担う想定のコンポーネント）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/                    — 実行時に使用する SQLite / DuckDB / flag ファイル等（デフォルト）
  - logs/                    — ログファイル（デフォルト）

（上記は実装上の主要モジュールを抜粋したものです）

---

## 補足 / 実運用上の注意

- 本リポジトリは実際の注文や資金の操作を行う可能性があるため、本番運用時は KABUSYS_ENV を正しく設定し、`.env` に機密情報を含めたまま Git にコミットしないでください。
- KILL_FLAG_CLEAR_ON_START を本番で `1` に設定すると、Kill Switch が誤って無効化されるリスクがあるため推奨されません。
- OpenAI 等の外部 API を使用する機能は API 呼び出し回数やエラー時の挙動（リトライやフォールバック）を考慮して利用してください。
- process_priority / CPU affinity の設定は OS 権限の制約（権限不足）で失敗することがあります。ログを確認してください。
- DuckDB / SQLite のパスは Settings により上書きできます。データの分離（本番 vs ペーパー）を運用ルールとして確立してください。

---

必要であれば README に含めるコマンド例の補足（systemd ユニットファイル例、Dockerfile / docker-compose、CI 設定例など）や、各サブモジュールの API 使用例（関数シグネチャや戻り値の詳細）を追記できます。どの情報を優先して追加しますか？