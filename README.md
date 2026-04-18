# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）のリポジトリです。  
このREADME はリポジトリ内のコードを元に、導入・実行・構成方法をまとめたドキュメントです。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 環境変数（主要設定）
- 停止・Kill スイッチの挙動
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買システムの骨格を提供する Python パッケージです。  
主な役割は次の通りです。

- データ処理 / ファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード）
- 監視（System / Trade / Risk）とアラート / Kill スイッチ
- AI を使ったニュース NLP（OpenAI）によるスコア付け・レジーム検出
- 簡易 CLI: .env ウィザード、設定検証、検証レポート生成など

設計方針として、DB は DuckDB（分析） と SQLite（監視・発注ログ等）を併用。  
ペーパートレード（`KABUSYS_ENV=paper_trading`）では本番 DB と分離された SQLite を使用します。

---

## 主な機能一覧

- config
  - .env の自動読み込み（プロジェクトルート検出）
  - 設定ウィザード（`python -m kabusys.config_setup`）
  - 設定検証ツール（`python -m kabusys.validate_config`）
- execution
  - ExecutionEngine を起動する `run_execution.py`（PID ファイル / stop フラグ対応）
  - Paper trading では MockBroker を利用して別 DB に記録
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視 DB 初期化・操作（`monitoring_db.py`）
  - KillSwitch — 条件を満たすと `data/kill.flag` を書き込み Execution を停止
  - 起動スクリプト `run_monitoring.py`（ポーリングループ、ポーリング間隔は環境変数で変更可）
- portfolio
  - 候補選定、等金額 / スコア重み、ポジションサイズ計算、セクター上限・レジーム乗数
- research
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索、将来リターン、IC 計算、統計サマリ
- ai
  - news_nlp: OpenAI を用いた銘柄ごとのニュースセンチメント算出（`score_news`）
  - regime_detector: ma200 + マクロニュースセンチメントから日次レジーム判定（`score_regime`）
- tools
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）
   - Unix/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール  
   （requirements.txt がある場合はそれを使ってください。無い場合は最低限下記パッケージが必要です）
   ```bash
   pip install duckdb psutil openai
   ```
   - optional:
     - PyYAML（`python -m kabusys.validate_config` で config/*.yaml の検証を行う場合）
       ```bash
       pip install pyyaml
       ```

3. 環境変数の設定
   - 対話式ウィザードを使って `.env` を作成：
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは `.env`（もしくは環境変数）を直接設定します。
   - 自動ロード: リポジトリのプロジェクトルート（`.git` または `pyproject.toml` のある場所）を起点に `.env` / `.env.local` を自動読み込みします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定検証（推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする（本番前に推奨）
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリの準備（ログ・データ格納先など）
   - デフォルトでは `data/` と `logs/` を使用します。必要に応じて `.env` の `DUCKDB_PATH`, `SQLITE_PATH`, `LOG_DIR` 等を変更してください。

---

## 使い方（起動 / 実行例）

- ExecutionEngine 起動（本番 / paper_trading に応じて挙動が変わる）
  ```bash
  # そのまま起動
  python -m kabusys.run_execution

  # 環境をペーパートレードに切り替えて起動（.env で設定するか環境変数を一時設定）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録します（本番 DB と分離）。

- Monitoring (ポーリングループ) 起動
  ```bash
  # デフォルト 60 秒間隔
  python -m kabusys.run_monitoring

  # ポーリング間隔を変更（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は常に本番 sqlite_path（`SQLITE_PATH`）を参照します（環境にかかわらず）。

- Paper Trading 検証レポート
  ```bash
  # デフォルト DB パスを使用
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB を明示
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- 設定ウィザード / 検証
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config --strict
  ```

- ライブラリ機能（プログラムから呼び出す）
  - AI スコア付け:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
      - OpenAI API キーは引数か環境変数 `OPENAI_API_KEY`
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - リサーチ / ファクター:
    - kabusys.research.calc_momentum / calc_volatility / calc_value 等

---

## 主な環境変数（概要）

多くは `kabusys.config.Settings` で管理されています。主要なものだけ抜粋します。

- 認証系
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- ログ
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- AI
  - OPENAI_API_KEY（news_nlp / regime_detector で利用）
- その他
  - MONITOR_POLL_INTERVAL（run_monitoring 用。一時的に環境変数で上書き可）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（1 にすると自動 .env 読み込みを無効化）

詳細は `src/kabusys/config.py` を参照してください。

---

## 停止・Kill スイッチの挙動

- stop_requested.flag
  - パス: プロジェクトの `data/stop_requested.flag`（run_* スクリプト内で使用）
  - このファイルが存在すると、`run_monitoring.py`・`run_execution.py` のポーリングループが検知して安全に停止します。
  - 手動でサービスを停止したい場合はこのファイルを作成してください。
- kill.flag
  - KillSwitch（監視ロジック）が条件を満たした場合に `data/kill.flag` を書き込みます。このフラグは ExecutionEngine に対する「緊急停止」要求です。
  - KillSwitch のトリガー例: ドローダウン閾値超過、保有ポジション数上限超過など。
  - 実行時の挙動:
    - Monitoring が KillSwitch を書けば ExecutionEngine は kill.flag を検知して停止するよう設計されています（`KILL_FLAG_PATH` でパス変更可）。
  - Kill flag をクリアするにはファイルを削除してください。`Settings.kill_flag_clear_on_start` が `1` の場合、起動時に自動クリアされますが、本番環境では `0` を推奨します。

---

## ログとデータ

- ログ:
  - デフォルト: `logs/<app_name>.log`（`kabusys.utils.logging_setup.setup_logging` により stdout + 日次ローテートファイルに出力）
  - `LOG_DIR` / `LOG_LEVEL` で設定可能
- 監視 DB:
  - デフォルト: `data/monitoring.db`（SQLite）
  - `kabusys.monitoring.monitoring_db.init_monitoring_db()` が初期化（冪等）
  - マイグレーション: `init_monitoring_db` は既存 DB にカラムがない場合に備えて必要な ALTER を行います（例: `peak_value`, `latency_ms` 追加）

---

## ディレクトリ構成（主なファイル/モジュール）

以下はパッケージ内の主要ファイル/ディレクトリ構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (存在する前提)
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (存在する前提)
    - execution/
      - execution_engine.py (存在する前提)
      - broker_factory.py
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
    - data/ (実行時に作成される想定: DB・flag・pid 等)

注意: 上記の一部モジュール（trade_monitor や alert_manager、execution 内の実装など）がこの README に含まれているソース群以外に存在する想定です。各機能の詳細は該当ファイルを参照してください。

---

## 開発時の注意点 / Tips

- 環境自動読み込み
  - `.env` / `.env.local` はプロジェクトルート（`.git` や `pyproject.toml` があるディレクトリ）から自動ロードされます。CI やテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと安全です。
- OpenAI（AI 機能）
  - `OPENAI_API_KEY` を設定してください。API 呼び出しはリトライ・クリップ等のフェイルセーフを実装していますが、API 利用に係るコスト・レート制限に注意してください。
- 本番運用
  - `KABUSYS_ENV=live` の場合は注意喚起メッセージや追加チェックが有効化されます。LINE 通知周り（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を適切に設定してください。
- デバッグ / ログ
  - `LOG_LEVEL=DEBUG` にすると内部の挙動が詳細に出力されます。問題調査に有効です。

---

必要であれば、README に次のような追加情報も追記できます:
- 具体的な systemd / Supervisor の unit サンプル
- Dockerfile / docker-compose の例
- テスト手順（ユニットテストの実行方法）
- 詳細なデータベーススキーマ図

この README の追加・修正希望があれば、どの項目を詳しくしたいか教えてください。