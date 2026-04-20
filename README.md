# KabuSys

日本株向けの自動売買システムの一部を実装したリポジトリです。  
このREADMEはコードベースの主要コンポーネント、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。主な機能は以下の通りです。

- ExecutionEngine（発注エンジン）：実際の発注／ペーパートレードを切り替え可能
- Monitoring（監視）：システムの稼働状況や注文状況、リスクの常時監視とアラート・Kill Switch
- Research：DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリューなど）
- Portfolio：銘柄選定・重み付け・ポジションサイズ計算（純粋関数群）
- AI モジュール：ニュースセンチメント（OpenAI）を用いたスコアリング、レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード、設定検証ツール
- ツール：Paper Trading の検証レポート生成スクリプト 等

設計上の注意点として、データ取得や外部 API 呼び出しはモジュールごとに分離され、ペーパートレード時は本番 DB と分離される仕組みが備わっています。

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み（プロジェクトルート検出）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン（Execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント生成（モッククライアントあり）
  - リスクマネージャ / 注文管理 / 照合（Reconciler）を統合
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログ永続化（monitoring_db）
  - Kill Switch（data/kill.flag）で ExecutionEngine を停止可能
- 研究・リサーチ
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量解析、IC 計算、前方リターン計算
- AI
  - ニュースの NLP スコアリング（OpenAI）
  - 市場レジーム判定（MA + マクロニュース）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一的なログセットアップ（logs/*.log、日次ローテーション）
  - プロセス優先度・CPU affinity 管理

---

## セットアップ手順

※ 以下はプロジェクトルートで実行する前提です。Python のバージョンはプロジェクトポリシーに合わせてください（一般的には 3.9+ を想定）。

1. Python 仮想環境の作成（任意）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージのインストール（最低限）
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (設定ファイル検証に任意)
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - ※ requirements.txt があれば `pip install -r requirements.txt` を利用してください。

3. 環境変数 / .env の準備
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を手動で作成してください。.env の主なキーは README 内「環境変数」を参照。

4. DB / ディレクトリ
   - デフォルトで `data/`、`logs/` を使用します。起動時に自動作成されますが、アクセス権を確認してください。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルトは `development`
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を使う場合の API キー
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- MONITOR_POLL_INTERVAL に不正な値を与えた場合はデフォルトにフォールバックします。
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1=クリア、0=クリアしない。production は 0 推奨）
- PAPER_FILL_MODE: ペーパートレードの fill モード（instant/partial/never/reject）

※ .env 自動読み込み: プロジェクトルートが特定できる場合、`.env` と `.env.local` が自動で読み込まれます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要コマンド）

各モジュールは Python モジュール実行経由で起動できます（プロジェクトルートで実行）。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告もエラー扱いにする
  ```

- ExecutionEngine 起動
  - ペーパートレード（分離された DB を使用）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 本番（実際に発注）
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - 起動中に `data/stop_requested.flag` を作るとエンジンは停止します。ExecutionEngine の PID は `data/execution.pid` に書き込まれます。

- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます。0 以下や不正値はデフォルト 60 にフォールバックします。
  - 監視は常に本番の sqlite_path を参照します（環境に依らず monitoring.db を使用）。
  - 停止は `data/stop_requested.flag` を作成するとループを抜けます。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能（デフォルト: data/paper_trading.db）。

- AI 関連（ニューススコアリング、レジーム判定）
  - `OPENAI_API_KEY` が必要です。以下のように呼び出す関数群を利用します（スクリプト化済みではありません）。
    - kabusys.ai.score_news
    - kabusys.ai.regime_detector.score_regime

---

## ログ・データファイル

- ログ: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテート、30 日保存）
- データ:
  - monitoring DB: data/monitoring.db（Settings.sqlite_path）
  - paper trading DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - DuckDB: data/kabusys.duckdb
- フラグ / PID:
  - data/kill.flag — Kill Switch（ExecutionEngine を停止するための理由テキストを格納）
  - data/stop_requested.flag — 制御用ストップフラグ（run_* スクリプトのシャットダウン）
  - data/execution.pid — 実行エンジンの PID（run_execution が管理）

---

## ディレクトリ構成

以下は主要ファイルを抜粋したディレクトリ構成（簡易版）です。

- src/
  - kabusys/
    - __init__.py
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — Monitoring 起動スクリプト
    - config.py                       — 環境変数 / Settings
    - config_setup.py                 — .env 対話ウィザード
    - validate_config.py              — 設定検証 CLI
    - utils/
      - logging_setup.py              — ログ設定ユーティリティ
      - process_priority.py           — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py              — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py (存在前提)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (存在前提)
    - execution/
      - execution_engine.py           — 実行ロジック（EngineConfig, ExecutionEngine）
      - broker_factory.py             — Broker クライアント生成
      - order_manager.py
      - order_repository.py
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
    - tools/
      - paper_verification_report.py
    - data/ (runtime)
      - monitoring.db
      - paper_trading.db
      - stop_requested.flag
      - kill.flag
      - execution.pid
    - logs/ (runtime)
      - execution.log
      - monitoring.log
      - ... 

注意: 一部ファイルは README 作成時の抜粋に基づき説明しており、リポジトリ全体のファイル一覧とは異なる場合があります。

---

## 動作上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します。誤って Kill Switch を自動クリアすると安全機構が無効になります。
- AI 機能を使う場合は OpenAI API の利用制限・コストを考慮してください。失敗時はフォールバック動作が実装されていますが、API キーの管理に注意してください。
- ログディレクトリ / data ディレクトリの権限を確認してください。ログファイル作成に失敗した場合はコンソール出力のみになります。
- ペーパートレードは production DB と明確に分離されるように実装されています（PAPER_TRADING_SQLITE_PATH を使用）。

---

## よく使うコマンド例

- .env の作成 / 更新:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- ペーパートレード起動:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- 監視プロセス起動（ポーリング間隔 30 秒に変更）:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースに基づく概要説明です。実際の導入・運用にあたっては config/*.yaml（もし存在する場合）や各モジュール内のドキュメント、設定例（.env.example）を参照し、必須環境変数や運用ポリシーを十分に確認してください。必要であれば README に追記、改善を行います。