# KabuSys

日本株自動売買システム（ライブラリ＆起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注（Execution）・監視（Monitoring）・研究（Research）・AI補助（ニュースNLP / レジーム判定）などを含む自動売買システムのコア機能群を提供します。モジュールはテスト容易性と運用安全性を重視して設計されています。

---

## 概要

主な設計方針・特徴：

- モジュール分割（execution, monitoring, portfolio, research, ai, tools, utils 等）
- 設定は環境変数 / .env ファイルで管理（`kabusys.config.Settings`）
- ExecutionEngine は本番 / ペーパートレードを明確に分離
- Monitoring は専用の監視 DB（SQLite）へログを収集・アラート判定・Kill Switch を制御
- DuckDB を分析用に利用（ファクター計算や研究処理）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・レジーム判定支援（任意）
- ログ管理は統一された `setup_logging` ユーティリティで日次ローテーションを行う

---

## 主な機能一覧

- Execution
  - Broker クライアント抽象化（実口座 / Mock）
  - OrderManager, RiskManager, Reconciler, ExecutionEngine
  - Paper trading（`KABUSYS_ENV=paper_trading`）は専用 SQLite（`data/paper_trading.db`）に記録

- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク・データ鮮度・プロセス検出）
  - TradeMonitor（滞留注文・異常約定などの検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じて `data/kill.flag` を書き込み Execution を停止）
  - MonitoringEngine（複数監視を束ねたポーリングループ）
  - 監視ログ永続化（SQLite 用の `monitoring_db` ヘルパー）

- Portfolio（純粋関数）
  - 候補選定、等分配／スコア配分、ポジションサイズ計算、セクター上限適用、レジーム乗数

- Research（DuckDB 使用）
  - モメンタム / バリュー / ボラティリティファクター計算
  - 将来リターン計算、IC（Information Coefficient）等の統計処理

- AI（OpenAI 連携）
  - ニュース記事を LLM でスコア化して `ai_scores` に保存（`kabusys.ai.news_nlp`）
  - レジーム判定（ETF MA + マクロニュース + LLM）（`kabusys.ai.regime_detector`）

- ユーティリティ
  - 設定ウィザード（`.env` の対話生成）`kabusys.config_setup`
  - 設定検証 CLI（必須環境変数・YAML など）`kabusys.validate_config`
  - Paper Trading 検証レポート生成ツール `kabusys.tools.paper_verification_report`

---

## セットアップ手順

前提：
- Python 3.9+（コードは型ヒント等を使用）
- pip / 仮想環境推奨
- DuckDB（Python パッケージ）、psutil、openai（AI 機能利用時）、PyYAML（`validate_config` が YAML 検証を行う場合）等が必要

例（仮想環境作成とパッケージインストール）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

   ※ 実際の依存はプロジェクトの requirements.txt があればそちらを使用してください。

3. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定します。
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 最低必須（README ベースの最小例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - （任意）OPENAI_API_KEY=...（AI 機能を使う場合）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告をエラーとして扱いたい場合は `--strict` を付けます。

5. ディレクトリと DB
   - デフォルトでは以下ファイル/ディレクトリが使用されます（必要に応じ .env で上書き）:
     - data/monitoring.db（SQLite）
     - data/paper_trading.db（Paper Trading）
     - data/kabusys.duckdb（DuckDB）
     - logs/（ログ出力）
   - 初回起動時に必要ディレクトリは自動作成されることが多いですが、権限等に注意してください。

---

## 使い方（起動・主なコマンド）

- 設定ウィザード（.env の初期作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading → MockBroker を使用、`data/paper_trading.db` に記録（本番 DB と分離）
    - KABUSYS_ENV=live → 実ブローカーを使用（要正しい設定）
  - 停止方法:
    - プロセスに SIGINT（Ctrl+C）
    - または `data/stop_requested.flag` を作成すると安全にシャットダウンされます。
  - 実行時は `data/execution.pid` を出力します（`Settings.pid_file_path`）。

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60秒）
  - 監視は環境に関係なく本番の SQLite（`Settings.sqlite_path`）を使用してログ保存します
  - 停止フラグ:
    - run_monitoring はプロジェクトルートの `data/stop_requested.flag` を監視してループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: `data/paper_trading.db`。別パス指定は `--db PATH` または環境変数 `PAPER_TRADING_SQLITE_PATH`

- AI スコアリング / レジーム判定（プログラム呼び出し）
  - OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または引数）
  - 例（Python から呼ぶ）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")

    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="sk-...")

  - これらは DuckDB 接続と対象日を受け取り、DB を更新します。AI 呼び出しは冗長性とリトライを持ちフェイルセーフ化されています。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live。デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能利用時）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒））
- KILL_FLAG_CLEAR_ON_START（本番で Kill Switch 自動クリアを許可するか。0 推奨）

設定は .env か環境変数で行います。`kabusys.config_setup` で対話的に .env を作成できます。

---

## 停止 / Kill フラグの挙動

- data/stop_requested.flag
  - run_execution.py や run_monitoring.py のループを安全に終了させるために用いるファイル。
  - 存在を検出するとプロセスはグレースフルに停止します。

- data/kill.flag
  - KillSwitch により書き込まれるファイル。ExecutionEngine に停止シグナルを伝えるために使用します（Execution はこのファイルを検知して停止します）。
  - 本番環境での自動クリア設定（KILL_FLAG_CLEAR_ON_START）は慎重に扱ってください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（stdout + 日次ファイルローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化・永続化ラッパ
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
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

- data/                      — デフォルトの DB / フラグファイル格納場所（run 時に使用）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - stop_requested.flag
  - kill.flag
  - execution.pid

- logs/                      — ログ出力ディレクトリ（`setup_logging` により自動作成）

---

## 開発時の注意 / 実運用上のガイド

- 本番（live）環境は慎重に運用してください。`validate_config` は本番用チェック（LINE 通知設定等）を含みます。
- Paper Trading は本番 DB と完全分離されます（`PAPER_TRADING_SQLITE_PATH`）。
- OpenAI 利用は API コストとレイテンシに注意。AI 呼び出しはリトライやフェイルセーフを備えていますが、運用ポリシーを策定してください。
- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます（30日分保持）。
- `MONITOR_POLL_INTERVAL` は監視の負荷と検知遅延のトレードオフを考慮して調整してください（デフォルト 60 秒）。
- プロセス優先度設定（set_process_priority）は可能な範囲で High に設定しますが、環境によっては権限や OS の違いでスキップされます。

---

## ライセンス / バージョン

- パッケージバージョンは `kabusys.__version__ = "0.1.0"` に設定されています。
- ライセンス情報が別途ある場合はプロジェクトルートの LICENSE を参照してください（本抜粋では含まれていません）。

---

この README はリポジトリ内の主要コード（起動スクリプト・設定・監視・AI・ポートフォリオ・リサーチ）から要点を抽出して作成しています。運用・拡張に際しては各モジュール（特に Execution / Risk / BrokerClient）の実装詳細を確認してください。