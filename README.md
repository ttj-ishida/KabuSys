# KabuSys

日本株自動売買システム（ライブラリ & 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・分析・AI支援モジュールを含む自動売買基盤の一部実装です。production／paper_trading（ペーパー）モードの分離や、監視・Kill Switch 等の安全機構を備えています。

---

## 概要

- 自動売買エンジン（ExecutionEngine）と監視プロセス（MonitoringEngine）を分離して実行可能
- Paper Trading モードではモックブローカークライアントを使い、本番 DB と分離された SQLite に記録
- DuckDB を使った研究用ファクタ計算・特徴量探索機能を搭載
- OpenAI を使ったニュース NLP（センチメント）および市場レジーム判定モジュールを実装
- 監視ログは SQLite（monitoring.db）へ永続化。各種アラートや Kill Switch が発動可能
- .env ウィザード（interactive）・設定検証ツールあり

---

## 主な機能一覧

- execution
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - Paper Trading 切替（`KABUSYS_ENV=paper_trading`）
  - 発注管理・リスク管理・リコンサイル機能（実装モジュール群）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を統括する MonitoringEngine（`run_monitoring.py`）
  - Kill Switch（閾値超過で Execution 停止用フラグを書き込む）
  - 監視ログ永続化（SQLite テーブル群の作成/マイグレーション）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・特徴量サマリ
- portfolio
  - 候補選定・重み計算（等配分・スコア加重）
  - セクター制限・レジーム乗数適用
  - 株数決定（リスクベース・lot 単位の丸め・aggregate cap）
- ai
  - ニュースセンチメント（OpenAIを用いたスコアリング）
  - 市場レジーム判定（MA + マクロセンチメントの合成）
- tools
  - Paper Trading 検証レポート生成スクリプト（`paper_verification_report.py`）
- ユーティリティ
  - 環境設定ウィザード（`.env` 生成補助）
  - 設定検証 CLI（環境変数・config YAML のチェック）
  - 統一ログ設定ユーティリティ（ファイル + stdout）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要要件（推奨）

- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証を行う場合）
- 標準モジュール: sqlite3, logging, threading, datetime など

インストール例（virtualenv 推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
（プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 初回の環境変数設定（.env）:
   - 対話式ウィザードを実行して `.env` を生成
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV（development | paper_trading | live）
     - OPENAI_API_KEY（AI 機能を使う場合）
5. 設定の検証（任意推奨）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリ作成（.env のパスに依存）
   - デフォルトでは `data/` に DB やフラグファイルを配置します（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` を .env で上書き可能）
7. ログ出力先
   - デフォルト `logs/`。`LOG_DIR` 環境変数で変更可能

注意:
- `kabusys.config` は起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` を自動ロードします。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（代表コマンド）

- 監視プロセスを起動（デフォルト 60 秒ポーリング）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する: 環境変数 `MONITOR_POLL_INTERVAL`（秒）を設定
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します（`run_monitoring` はこのファイルを監視します）。

- ExecutionEngine を起動:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合はモックブローカーを使用し、Paper Trading 用 DB（既定: `data/paper_trading.db`）に記録します。例:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - `run_execution` も `data/stop_requested.flag` を参照して起動中に停止します。

- 環境設定ウィザード（.env 生成）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## 停止・Kill Switch の運用

- 停止フラグ（Graceful stop）
  - `data/stop_requested.flag` を作成すると `run_monitoring` / `run_execution` のループが検知して終了処理を行います。
- Kill Switch（自動停止）
  - 監視ロジック（RiskMonitor 等）が設定閾値を超えると `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
  - Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動で `kill.flag` を削除しますが、本番では `0` を推奨します（安全上の理由）。

---

## 環境変数の主要一覧

（`.env.example` に準拠してください）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring の上書き）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1）

---

## ログ

- ログは `kabusys.utils.logging_setup.setup_logging` を通して設定されます。
  - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定
  - デフォルトログディレクトリ: `logs/`
  - ログファイル名: `<app_name>.log`（例: `execution.log`, `monitoring.log`）

---

## 開発者向け情報（API・モジュール概要）

- kabusys.config — 環境変数読み込み / Settings クラス
- kabusys.config_setup — .env 対話ウィザード
- kabusys.validate_config — 起動前の設定チェック CLI
- kabusys.utils.logging_setup — ログ設定ユーティリティ
- kabusys.utils.process_priority — プロセス優先度・CPU affinity 設定
- kabusys.monitoring.* — MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
- kabusys.execution.* — ExecutionEngine, OrderManager, RiskManager, BrokerClientFactory（ブローカー抽象）
- kabusys.portfolio.* — portfolio construction（候補選定、重み、サイズ計算、セクター制約）
- kabusys.research.* — ファクター計算、特徴量探索
- kabusys.ai.* — news_nlp（ニューススコアリング）、regime_detector（市場レジーム判定）
- kabusys.tools.paper_verification_report — Paper Trading の検証レポート生成スクリプト

---

## ディレクトリ構成（主なファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - broker_factory.py
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
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/ (上記)
    - tools/
      - paper_verification_report.py

（上のリストは主要ファイルの抜粋です。実装の詳細は各モジュールを参照してください。）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）での起動前に `validate_config` を必ず実行し、LINE 通知設定などの警告を確認してください。
- kill.flag / stop_requested.flag の運用ルールを組織で明確にしておくこと（誤った自動クリア設定は危険）。
- Paper Trading はあくまで検証用です。本番と DB を完全に分離して運用してください。
- OpenAI を使う処理は API 呼び出し・レート制限・エラーに強い設計になっていますが、コストとレート制限に注意してください。

---

## 貢献・拡張のヒント

- BrokerClient の実装を追加して実口座接続を行う（secure storage にパスワードを保管する等の配慮を）
- strategy モジュールを実装して ExecutionEngine にシグナルを渡す
- ログ／メトリクスを Prometheus / Grafana 等で可視化するためのエクスポータを追加
- DuckDB スキーマ（prices_daily / raw_financials 等）向けのデータ投入スクリプトを整備

---

この README はコードの主要な使い方と構成をまとめたものです。詳細な実装や拡張は各モジュールの docstring / コメントを参照してください。必要であれば、特定のモジュール（例: ExecutionEngine の起動オプションや AI モジュールのテスト方法）についてさらに詳しいドキュメントを作成します。