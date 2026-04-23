# KabuSys

日本株自動売買システムのモジュール群（ライブラリ & 起動スクリプト）。  
このリポジトリは取引実行・監視・リサーチ・ポートフォリオ構築・AIによるニュース評価などの機能を含む、運用向けのコンポーネント群です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の関心領域を持つモジュールで構成されています。

- Execution: 発注エンジン（本番 / ペーパートレード切替対応）
- Monitoring: システム状態、発注ログ、リスク、Kill Switch 等の監視
- Portfolio: 候補選定、ウェイト計算、ポジションサイジング、セクター制約などの純関数群
- Research: ファクター計算・特徴量探索（DuckDB を用いたオフライン分析）
- AI: OpenAI API を利用したニュースの NLP スコアリングや市場レジーム判定
- Tools: ペーパートレードの検証レポート生成等のユーティリティスクリプト
- Utils: ログ設定、プロセス優先度設定、設定読み込みユーティリティ等

設計上の特徴:
- 環境変数と `.env` による設定管理
- DuckDB / SQLite をデータストアに利用
- 本番とペーパートレードのデータ分離（ペーパートレードでは専用 DB を使用）
- フェイルセーフ（API 失敗時はスキップ or フォールバックする実装方針）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading で MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- 設定管理 / CLI
  - config_setup.py: 対話式で `.env` を生成・更新するウィザード
  - validate_config.py: `.env` と config/*.yaml の基本チェックを行う検証ツール
- モニタリング
  - system_monitor/trade_monitor/risk_monitor を組み合わせた MonitoringEngine
  - monitoring_db: SQLite スキーマ定義と永続化ロジック
  - kill_switch: 条件で `data/kill.flag` を書き、ExecutionEngine を停止させる仕組み
- Execution（取引）
  - ExecutionEngine、OrderManager、RiskManager、Reconciler、BrokerClientFactory など（本コードベース内に実装の入口あり）
  - ペーパートレード用 DB 分離、発注ログ（trade_logs）記録
- Research & Portfolio
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC、統計サマリ等
  - portfolio: 候補選定、重み計算、ポジションサイジング、セクターキャップ、レジーム乗数
- AI
  - news_nlp: ニュース記事を OpenAI でスコアリングし ai_scores に書き込む
  - regime_detector: ETF MA とマクロニュースで市場レジーム判定、DB へ保存
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## 前提 / 必要パッケージ（例）

- Python 3.9+
- 推奨ライブラリ（pip でインストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config yaml の検証を行う場合）
- その他: SQLite は標準で利用可能

例（仮想環境を作成してインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

パッケージ管理ファイルがないため、必要な依存を適宜インストールしてください。

---

## セットアップ手順（初期設定）

1. リポジトリをクローン / プロジェクト内に入る
2. 仮想環境の作成・有効化（上記参照）
3. 必要パッケージのインストール
4. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabuAPI パスワード、DB パス、KABUSYS_ENV などを順に尋ねます。

5. 設定の検証
   ```bash
   python -m kabusys.validate_config
   ```
   必要に応じて `--strict` オプションで警告も失敗扱いにできます。

6. データディレクトリ作成（.env のデフォルトで data/ 以下を利用）
   ```bash
   mkdir -p data logs
   ```

7. OpenAI を使う機能を利用する場合は環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に API キーを渡してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: Execution は MockBroker を使用し `data/paper_trading.db` を使用
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- LOG_LEVEL: ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

---

## 使い方（コマンド例）

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  # strict モード:
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（SystemMonitor）
  ```bash
  python -m kabusys.run_monitoring
  # 環境変数でポーリング間隔を上書き:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  注意: Monitoring は環境にかかわらず Settings.sqlite_path（本番 path）を使用して監視テーブルを初期化・書き込みします。

- 実行エンジン起動（ExecutionEngine）
  ```bash
  python -m kabusys.run_execution
  ```
  KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します。

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（ライブラリ関数）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  これらは DuckDB 接続 (duckdb.DuckDBPyConnection) を受け取ります。

---

## 停止 / Kill 機構

- run_monitoring.py / run_execution.py はプロジェクトルートの `data/stop_requested.flag` を監視し、存在を検知するとループを終了します（安全停止）。
- Kill Switch: `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送れます（KillSwitch モジュールで評価・書き込み）。
- 実行中の ExecutionEngine は `data/execution.pid`（デフォルト）に PID を書きます。

KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動クリアします（本番では注意）。

---

## ロギング

- ログは stdout とファイル出力（デフォルト `logs/<app_name>.log`）の両方に出力されます。ログの設定は `kabusys.utils.logging_setup.setup_logging` を利用。
- デフォルトログディレクトリ: logs/
- ログローテーション: 日次、バックアップ 30 日分

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite スキーマと永続化 API
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — （発注ログ監視等）※（実装ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 複数モニタを束ねるランナー
    - alert_manager.py — 通知管理（LINE 等、実装箇所に依存）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（EngineConfig 等）
    - broker_factory.py — Broker クライアント生成（Mock / 実ブローカ）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
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
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（実際のプロジェクトルートには data/ と logs/ を配置してください。config/*.yaml は追加設定ファイルです。）

---

## 開発者向け備考

- DuckDB を使ったリサーチ関数は副作用がない純粋関数設計を意識しており、prices_daily / raw_financials / raw_news 等のテーブルを読み取ります。
- AI 呼び出し部（news_nlp / regime_detector）は OpenAI API のエラーを耐性を持って扱い、リトライ／フォールバック（0.0）を行います。テスト用途では内部の API 呼び出し関数をモック可能です。
- MonitoringDB はスキーマのマイグレーション（列追加）を実行時に行うため、既存 DB との互換を一定程度保ちます。
- process_priority と logging のユーティリティはクロスプラットフォーム（Windows / POSIX）に配慮した実装です。権限不足等で失敗しても警告ログを出してスキップします。

---

## よく使うコマンドまとめ

- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視開始:
  - python -m kabusys.run_monitoring
- 実行エンジン開始:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

README は以上です。必要であれば、README に含めるサンプル .env のテンプレートや、依存関係の requirements.txt 例、実行フロー図（起動シーケンス）などを追加できます。どの情報を優先して追加しますか？