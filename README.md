# KabuSys

日本株向け自動売買システムの一部（ライブラリ + 起動スクリプト）。  
このリポジトリには、実行エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・リサーチ・AI（ニュースNLP / レジーム判定）などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys はトレーディング戦略の実行・監視・評価を行うための内部ライブラリ群と起動用スクリプト群を提供します。  
主な責務は次のとおりです。

- ExecutionEngine: 発注ロジック、注文管理、リスク管理、ブローカー抽象化（paper/live の分離）
- Monitoring: システム健全性、注文ログ、リスク（ドローダウン・ポジション上限）を定期監視しアラート／Kill Switch を管理
- Portfolio: 候補選定、重み算出、ポジションサイズ決定、セクター制限などの純粋関数群
- Research: DuckDB を利用したファクター計算・特徴量解析ユーティリティ
- AI: OpenAI を利用したニュースセンチメント（ニュースNLP）と市場レジーム判定
- Tools: レポート生成や設定ウィザード等の CLI ツール

設計方針の要点:
- 環境依存設定は `.env` または環境変数で管理
- Paper trading（ペーパートレード）は本番 DB と分離
- ロギングは共通ユーティリティで統一（日次ローテーション）
- OpenAI 連携はフェイルセーフ（API失敗時はスコアを 0 等でフォールバック）

---

## 機能一覧

- 設定ウィザード（`kabusys.config_setup`）
- 起動前設定検証（`kabusys.validate_config`）
- ExecutionEngine 起動スクリプト（`run_execution.py`）
  - KABUSYS_ENV により paper_trading / live の切替
  - paper_trading では専用 SQLite（`data/paper_trading.db` デフォルト）を使用
- Monitoring 起動スクリプト（`run_monitoring.py`）
  - システム状態・データ鮮度・注文ログ・リスク監視
  - ポーリング間隔は環境変数で上書き可能（`MONITOR_POLL_INTERVAL`、デフォルト 60 秒）
- Kill Switch（`data/kill.flag`）による ExecutionEngine 停止制御
- Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）
- Portfolio 構築ユーティリティ（候補選定、重みづけ、ポジションサイズ）
- Research（ファクター計算／特徴量探索）
- AI モジュール
  - ニュース -> センチメントスコア（`kabusys.ai.score_news`）
  - マクロ + MA200 に基づくレジーム判定（`kabusys.ai.regime_detector.score_regime`）
- ユーティリティ
  - ログ設定（`kabusys.utils.logging_setup.setup_logging`）
  - プロセス優先度 / CPU affinity（`kabusys.utils.process_priority`）
  - 監視 DB 管理（マイグレーション含む）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の新しい構文を使用）
- システムに sqlite3 が利用可能（標準ライブラリ）
- 必要パッケージ（最低限の例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（任意、`validate_config` の YAML 検証に使用）

例（venv を使う）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

3. 環境変数の準備
   - 対話式で `.env` を作る場合:
     - python -m kabusys.config_setup
   - あるいはプロジェクトルートに `.env` を直接作成（`.env.example` を参照）

重要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）

自動ロード:
- モジュール import 時にプロジェクトルートの `.env` / `.env.local` を自動でロードします（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化可能）。

---

## 使い方（主要なコマンド）

設定チェック:
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

設定ウィザード（.env 生成）:
- python -m kabusys.config_setup

監視ループ起動（常駐プロセス）:
- python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能
  - 監視は常に本番用 sqlite_path（`Settings.sqlite_path`）を使用

ExecutionEngine 起動:
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し MockBroker が利用されます
  - 起動中に `data/stop_requested.flag` が検知されると安全停止します
  - Kill Switch による停止は `data/kill.flag` を書き込むことで実行エンジンに通知されます

Paper Trading 検証レポート:
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（`--db` で指定可能）
  - 稼働率 / 注文成功率 / レイテンシ等を評価して PASS/FAIL を出力

AI / レジーム判定（ライブラリ呼び出し例）:
- Python スクリプトで直接呼ぶ:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="…")

ログ:
- デフォルトログディレクトリ: logs/
- ログファイル名はアプリケーション名（例: `execution.log` / `monitoring.log`）
- ロギングは `kabusys.utils.logging_setup.setup_logging` により統一されます

停止フロー / フラグ:
- 停止要求ファイル: data/stop_requested.flag（run_* スクリプトが監視）
- Kill Switch ファイル: data/kill.flag（KillSwitch が書き込むと ExecutionEngine に停止指示）
- PID ファイル（ExecutionEngine 用）: data/execution.pid（Settings.pid_file_path）

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` を基準とした主要ファイル／モジュール構成例です。

- kabusys/
  - __init__.py
  - config.py                   — 設定 / .env ロード / Settings クラス
  - config_setup.py             — 対話式 .env ウィザード
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py          — 共通ロギング設定
    - process_priority.py       — 優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB（テーブル作成・永続化）
    - system_monitor.py        — システム監視（CPU/メモリ/ディスク/データ鮮度）
    - trade_monitor.py         — 注文ログ監視（滞留注文・価格異常等）※存在する想定
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - monitoring_engine.py     — 各 monitor を束ねるエンジン
    - alert_manager.py         — アラート送信（LINE 等、実装に依存）※存在する想定
  - execution/
    - execution_engine.py      — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py       — レジーム判定（MA200 + マクロニュース）
  - data/                      — 実行時生成ファイルのデフォルト配置（DB ファイル、flag、pid など）

注: 上記はこのコードベースに含まれる主要ファイルの抜粋です。実際のリポジトリにはさらに詳細なモジュール／補助関数が存在します。

---

## 実装上の注意点 / 運用メモ

- 環境分離:
  - paper_trading と live は DB を分離して運用することを推奨します（paper は PAPER_TRADING_SQLITE_PATH を使用）。
- .env 自動ロード:
  - import 時にプロジェクトルートの `.env` / `.env.local` をロードします。CIやテストで自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Kill Switch / Stop Flag:
  - `data/kill.flag` は KillSwitch による停止トリガです（Execution 側で読み取り）。
  - `data/stop_requested.flag` は run_*.py スクリプトが常時監視している停止要求ファイルです（運用側からの手動停止等に利用）。
- ログディレクトリ作成失敗:
  - ログディレクトリが作成できない場合はコンソール出力のみで継続します（setup_logging がフォールバック処理を行います）。
- DuckDB / SQLite:
  - DuckDB は分析用途（prices_daily 等）向け。監視・トレード履歴は SQLite（monitoring_db）に保持。
- OpenAI 呼び出し:
  - rate limit や一時的な失敗に備えて指数バックオフを採用しています。API キーは `OPENAI_API_KEY` を利用。
- マイグレーション:
  - `init_monitoring_db` はテーブル作成に加え簡易的なマイグレーション（カラム追加）を行います。

---

## 参考コマンドまとめ

- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- ライブラリ利用例（Python スクリプト内）:
  - from kabusys.portfolio import select_candidates, calc_position_sizes
  - from kabusys.ai import score_news

---

この README は主要な使い方と構成をまとめたものです。詳細な内部仕様や API（各モジュールの関数やクラスの引数仕様）は各ソースコード内のドキュメントストリング（docstring）を参照してください。必要であれば各モジュールごとの詳細ドキュメントも作成します。