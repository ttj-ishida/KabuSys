# KabuSys

日本株向けの自動売買システムのコアライブラリ群です。発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・リスク管理、リサーチ・ファクター計算、AI を用いたニュース評価等の機能を含みます。

---

## 概要

KabuSys は以下のコンポーネントで構成された、現物／ペーパートレードに対応した自動売買フレームワークです。

- Execution: 発注ロジック、OrderManager、RiskManager、Reconciler、ExecutionEngine
- Monitoring: システム状態・注文・リスクの定期監視、Kill Switch、アラート
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research: DuckDB を用いたファクター計算・将来リターン計算・IC 等の統計解析
- AI: OpenAI を使ったニュースセンチメント（score_news）や市場レジーム判定（score_regime）
- Utils & Tools: ログ設定、プロセス優先度設定、設定ウィザード / 検証、紙トレード検証レポート等

設計方針の一部:
- 環境変数 / .env による設定を想定
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と完全分離（`data/paper_trading.db`）
- DuckDB は分析用（デフォルト `data/kabusys.duckdb`）
- ロギングは共通ユーティリティで統一（コンソール + 日次ローテートファイル）

---

## 機能一覧

主要機能の抜粋：

- 発注・注文管理、約定追跡、リスク制御（最大ポジション比、ドローダウン等）
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（flagファイルによる停止指示）
- Paper Trading 用の MockBrokerClient による分離されたテスト環境
- Portfolio Construction: 候補選定、等重・スコア加重、リスクベース発注、単元株丸め、aggregate cap
- Research: Momentum、Volatility、Value 等のファクター計算、将来リターン・IC・統計サマリ
- AI モジュール: ニュース単位で LLM によるセンチメント集計（gpt-4o-mini を想定）、市場レジーム判定
- 設定支援: 対話式 .env 作成ウィザード（config_setup）と設定検証 CLI（validate_config）
- ツール: Paper Trading の検証レポート生成（tools.paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローン／取得。

2. Python 環境を作成（推奨: venv / pyenv）。

   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   ※ requirements.txt がない場合は、duckdb, psutil, openai, PyYAML（任意）などをインストールしてください。

3. .env の初期作成（対話式ウィザード）

   ```
   python -m kabusys.config_setup
   ```

   ウィザードで J-Quants トークン、kabuAPI パスワード、KABUSYS_ENV 等を入力して .env を生成します。

4. 設定検証

   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの準備（通常は自動作成されますが確認）

   - デフォルト DB / ファイルパス（.env で変更可能）
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログディレクトリ: logs/

6. （AI 機能を使う場合）OpenAI API キーを設定

   ```
   export OPENAI_API_KEY="sk-..."
   # または .env に設定
   ```

---

## 使い方

主要な起動スクリプト・コマンドと使い方を示します。

- 実行エンジン（ExecutionEngine）を起動

  - 本番・開発・ペーパートレードは環境変数 KABUSYS_ENV で制御（`development` / `paper_trading` / `live`）。
  - Paper Trading 時は MockBrokerClient を使い、paper_trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録される。

  ```
  python -m kabusys.run_execution
  ```

  実行動作のポイント:
  - プロセス優先度を high に設定（psutil により OS に応じて設定）
  - stop 指示ファイル（data/stop_requested.flag）が存在する場合は起動しない / 実行中は検出して停止
  - execution.pid に PID を書き出します

- 監視ループ（Monitoring）を起動

  ```
  python -m kabusys.run_monitoring
  ```

  オプション・挙動:
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を指定（デフォルト 60 秒）
  - 監視は MonitoringDB（sqlite）に書き込み、DuckDB は分析用に接続
  - stop 指示ファイル（data/stop_requested.flag）を検知するとループを終了

- 設定ウィザード

  ```
  python -m kabusys.config_setup
  ```

- 設定検証

  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート

  SQLite (paper trading DB) から集計レポートを生成します。

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（コードから利用）

  - ニュースセンチメント（ai.news_nlp.score_news）:

    score_news(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: Optional[str])

    - OpenAI API キーが必要。api_key 引数または環境変数 OPENAI_API_KEY。
    - raw_news / news_symbols / ai_scores テーブルを前提。

  - レジーム判定（ai.regime_detector.score_regime）:

    同様に DuckDB 接続と API キーが必要です。

注意事項:
- Paper Trading は本番 DB と分離されます（settings.is_paper 判定により paper_sqlite_path を使用）。
- Kill Switch により重大なリスク（ドローダウンやポジション上限）を検知した場合、data/kill.flag を書き込み ExecutionEngine を停止できます。KILL_FLAG_CLEAR_ON_START は起動時に kill.flag を自動消去するかの設定（本番では 0 推奨）。

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB （デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring にのみ適用）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効）

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル / モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env のロード・Settings 定義
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — 共通ロギング設定（stdout + 日次ローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/
    - (OrderManager, ExecutionEngine, BrokerFactory, RiskManager, Reconciler, etc.)
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ + 永続化ラッパー
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
  - ai/
    - news_nlp.py             — ニュースの LLM スコアリング
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロ NLP）
  - tools/
    - paper_verification_report.py

- data/                      — デフォルトで使われる DB / PID / flag ファイルの格納先（自動作成）
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - stop_requested.flag
  - kill.flag

- logs/                      — ログファイル（app_name ごとに daily ローテート）

---

## 開発・運用時の留意点

- 本番（KABUSYS_ENV=live）では特に LINE 通知・kill switch の設定を確認してください（validate_config の live チェック参照）。
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite のスキーマはコード内で初期化・マイグレーションが行われます（monitoring_db.init_monitoring_db 等）。
- AI を用いる機能は API キーを必要とし、外部 API の失敗を考慮したフェイルセーフ実装になっています（失敗時はスコア 0.0 にフォールバック等）。
- run_execution / run_monitoring は stop フラグ（data/stop_requested.flag）を検出して安全に停止します。外部からの強制停止信号はこのファイルの作成によって行うことができます。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 起動（Execution / Monitoring）
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README の内容や使用方法で不明点があれば、どの機能（Execution / Monitoring / AI / Portfolio / Research）の詳細を深掘りしたいか教えてください。必要であれば使用例や設定例（.env テンプレート）も作成します。