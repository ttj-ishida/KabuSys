# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買システム「KabuSys」のコアライブラリ群です。取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などの機能をモジュール化しています。

主な特徴、セットアップ手順、使い方、ディレクトリ構成を以下にまとめます。

---

## プロジェクト概要

- Python で実装された自動売買フレームワークのコア。
- コンポーネント例：
  - ExecutionEngine（発注・注文管理・リスク管理）
  - Monitoring（システム状態・注文ログ・リスク監視・Kill Switch）
  - Portfolio（銘柄選定・重み付け・ポジションサイズ）
  - Research（ファクター計算、特徴量探索）
  - AI（ニュースセンチメント評価、レジーム判定）
- SQLite（監視ログ等）および DuckDB（分析用）を使用。
- Paper Trading（ペーパートレード）用の DB を分離して実行可能。

---

## 機能一覧

- 設定管理
  - .env 読み込み（自動ローディング / .env.local のサポート）
  - 対話式 .env 作成ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）

- 実行（Execution）
  - 本番 / ペーパートレード切替（`KABUSYS_ENV`）
  - Broker クライアントの抽象化（`BrokerClientFactory` を介して実装）
  - OrderManager / RiskManager / Reconciler を統合した ExecutionEngine（起動スクリプト: `run_execution.py`）
  - Kill Switch（`data/kill.flag` により外部から発火）

- 監視（Monitoring）
  - SystemMonitor（CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視）
  - TradeMonitor（注文ログの監視・滞留注文検出など）
  - RiskMonitor（ドローダウン／ポジション上限監視）
  - MonitoringEngine（ポーリング・アラート連携、Kill Switch 発動）
  - 監視 DB 層（`monitoring_db.py`）: system_status / trade_logs / positions / risk_logs / dashboard

- ポートフォリオ構築
  - 候補選定、等金額／スコア重み、セクター上限適用、ポジションサイズ計算（単元株丸め含む）

- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI 連携）
  - ニュースセンチメント評価（`kabusys.ai.news_nlp`）
  - マクロ＋テクニカルを合成したレジーム判定（`kabusys.ai.regime_detector`）
  - 両モジュールは OpenAI API キーを必要とし、リトライ・パース検証を実装

- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## セットアップ手順

前提:
- Python 3.9+（ソースは型注釈で Python 3.10 以降を想定している箇所あり）
- system-level: DuckDB（Python パッケージで利用）、SQLite は標準ライブラリで利用
- 外部 API を使う場合は OpenAI API キー 等が必要

1. リポジトリをクローンして依存パッケージをインストール
   - 例（仮想環境推奨）:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```
   - requirements.txt がない場合は少なくとも以下をインストールしてください:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config 検証で YAML をパースする場合、無くても動くが検証スキップになります）

2. 環境変数（.env）を用意
   - 自動ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト）に対話式で値を保存します。
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 便利な環境変数（一部）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト、Monitoring DB）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
     - OPENAI_API_KEY: OpenAI を使う場合

   - 自動 .env のロードはデフォルトで有効。無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   警告も FAIL 扱いにする場合は `--strict` を付ける。

4. データディレクトリ作成（必要に応じて）
   - デフォルトで使用するファイル:
     - data/monitoring.db
     - data/paper_trading.db
     - data/kabusys.duckdb
     - logs/（ログ出力）
   - 監視・実行スクリプト起動時に適宜ディレクトリが作られますが、アクセス権やユーザ権限に注意してください。

---

## 使い方（主要スクリプト・モジュール）

ほとんどのスクリプトはモジュールとして実行できます（プロジェクトルートで実行する想定）。

- 設定ウィザード（.env の作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config [--strict]
  ```

- 実行エンジン起動（ExecutionEngine）
  - デーモンやサービスとして起動する想定。ペーパートレード時は環境変数 KABUSYS_ENV=paper_trading を設定してください。
  ```
  python -m kabusys.run_execution
  ```
  - 特記事項:
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル（デフォルト: data/execution.pid）を作成します。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 停止は data/stop_requested.flag を作成することで外部から制御できます。Kill Switch は data/kill.flag を用います。

- 監視プロセス起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。不正な値は 60 秒にフォールバック。
  - Monitoring は常に production の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存せず）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  ```
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 系関数（プログラム的に呼び出す）
  - ニュースセンチメント:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を引数に取ります。OpenAI API キーは引数か環境変数 OPENAI_API_KEY で指定します。

- ログ設定
  - 全スクリプト共通で `kabusys.utils.logging_setup.setup_logging(app_name=...)` を使用
  - デフォルトで stdout と日次ローテートファイル（logs/<app_name>.log）へ出力します。ログディレクトリは LOG_DIR 環境変数で変更可能。

---

## 重要な挙動・運用メモ

- Paper Trading は本番 DB と明確に分離されます（Settings.paper_sqlite_path を使用）。
- Kill Switch（重大リスク検出時）は `data/kill.flag` を書き込み、ExecutionEngine の停止シグナルとして扱われます。`KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは危険です（デフォルト 0 を推奨）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。CI やテスト時に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- プロセス優先度設定には psutil を使用。権限不足で設定できない場合は警告が出ますが処理は継続します。
- DuckDB / SQLite のパスやログレベル等は環境変数で上書き可能です。

---

## ディレクトリ構成

以下は主要ファイル／モジュールの構成（src/kabusys 以下）です。実際のリポジトリルートでは `src/` 配下にパッケージがあります。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数と Settings
    - config_setup.py              — .env 対話ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
    - utils/
      - __init__.py
      - logging_setup.py           — ログ初期化ユーティリティ
      - process_priority.py        — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py           — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py           — （注文監視ロジック）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py           — （アラート送信の抽象）
      - monitoring_engine.py
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - data/  (実行時に使用するデータ/DB/log 等：data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/kill.flag, data/stop_requested.flag, data/execution.pid など)
    - logs/  (ログ出力先デフォルト)

（上記に示した一部ファイル名は実装に依存し、実行環境で存在しない補助モジュールがある場合があります。実際の機能は該当ファイルの実装に依存します。）

---

## 追加の参考情報

- デバッグ・ロギング: `LOG_LEVEL=DEBUG` を設定すると詳細ログが出力されます。
- DB マイグレーション: monitoring_db.init_monitoring_db() は起動時に必要なテーブルと簡易マイグレーションを保証します。
- テスト・CI: モジュールは副作用を抑える設計（例えば日時や外部 API 呼び出し箇所は引数で注入可能）になっています。ユニットテストで外部呼び出しをモックしやすい構造です。

---

必要であれば、README にサンプル .env のテンプレートや運用手順（systemd・supervisord でのデーモン化、Dockerfile／docker-compose の例、CI 用の環境変数管理方法など）を追記します。どの情報を優先して追加しますか？