# KabuSys

日本株自動売買システムの一部（ライブラリ・起動スクリプト・ユーティリティ集）。  
この README はソースツリー（src/kabusys 以下）に基づく概要、機能一覧、セットアップと実行手順、使い方、ディレクトリ構成をまとめたものです。

注意: この README は提供されたコードスニペットに基づき作成しています。実運用ではさらにドキュメントや運用手順の整備、十分なテストを行ってください。

---

## プロジェクト概要

KabuSys は日本株自動売買（ExecutionEngine）および監視（Monitoring）／リサーチ／ポートフォリオ構築／AI（ニュースNLP・レジーム判定）等の機能を含むモジュール群です。  
主要な設計方針は以下の通りです：

- 環境変数（.env）で設定を管理。自動読み込み機能あり（無効化可能）。
- 実行環境は `KABUSYS_ENV`（development / paper_trading / live）で切替。
- paper_trading モードでは Mock ブローカーを使い、本番 DB と分離した専用 SQLite を利用。
- DuckDB をデータ分析・ファクター計算に利用。
- OpenAI（gpt-4o-mini 等）でニュースセンチメント等の処理を実装（API キー必要）。
- 監視（Monitoring）ではシステム状態、発注ログ、リスク監視、Kill Switch 等を備える。

---

## 機能一覧（抜粋）

- 実行 / 監視起動スクリプト
  - run_execution.py — ExecutionEngine 起動（paper_trading 用分岐）
  - run_monitoring.py — SystemMonitor のポーリングループ起動
- 設定管理
  - config.py — 環境変数 / .env 自動読み込みと Settings ラッパー
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 設定チェック CLI
- 監視
  - monitoring_engine.py — 複数 Monitor を束ねるエンジン
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py 等
  - monitoring_db.py — SQLite による永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- リサーチ / ファクター計算
  - research/factor_research.py, feature_exploration.py
- AI（OpenAI 連携）
  - ai/news_nlp.py — ニュースのセンチメント評価と ai_scores 書き込み
  - ai/regime_detector.py — ETF MA とマクロセンチメントの合成による市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成
- ユーティリティ
  - utils/logging_setup.py — ログ設定（stdout + 日次ローテーションファイル）
  - utils/process_priority.py — プラットフォームを吸収したプロセス優先度 / CPU affinity 設定

---

## セットアップ手順（開発環境向けの例）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（プロジェクトに依存ファイルがないため代表的な依存を示します）。
   - pip install duckdb psutil openai
   - 開発時には PyYAML（validate_config の YAML 検証に任意）:
     - pip install pyyaml

3. データ・ログディレクトリを作成（通常は起動時に自動作成されますが明示的に作る場合）:
   - mkdir -p data logs

4. 環境変数の準備
   - 対話式ウィザードで .env を作る（推奨）:
     - python -m kabusys.config_setup
   - または .env を手動作成。必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（よく使うもの）:
     - KABUSYS_ENV (development|paper_trading|live)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LOG_LEVEL (DEBUG|INFO|...)
     - LOG_DIR (デフォルト: logs/)
     - MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔 秒)
     - PAPER_FILL_MODE (instant|partial|never|reject)
     - KILL_FLAG_CLEAR_ON_START (1=起動時に kill.flag を自動クリア)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視の起動（監視プロセス単体）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
  - 監視は Settings に従い（duckdb/sqlite のパス等）動作します

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録します（本番 DB と分離）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

ログの設定:
- 管理ユーティリティ `kabusys.utils.logging_setup.setup_logging(app_name=...)` により、標準出力と logs/<app_name>.log（日次ローテーション）が有効になります。
- LOG_DIR / LOG_LEVEL で挙動を変更可能。

停止・Kill Switch:
- 監視 / 実行スクリプトはプロジェクトルート下のフラグファイルで停止を検知します:
  - data/stop_requested.flag — run_* スクリプトが監視する“停止要求”フラグ（run_execution/run_monitoring が参照）
  - data/kill.flag — KillSwitch が書き込むファイル。ExecutionEngine 側で参照して停止する設計（KillSwitch は Settings.kill_flag_path 経由でパスを取得します）
- 実行開始時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 推奨）。

Paper trading の分離:
- paper_trading 環境では SQLite DB を PAPER_TRADING_SQLITE_PATH で指定でき、本番の monitoring.db と分離されます。

AI 機能:
- OpenAI API を用いる機能（news_nlp, regime_detector）は OPENAI_API_KEY を必要とします。
- API 呼び出しはリトライ・バックオフ処理付きで実装されていますが、API 失敗時はフェイルセーフ（スキップやデフォルト値）で続行します。

---

## 典型的な運用フロー（例）

1. .env を作成（config_setup）
2. 設定検証（validate_config）
3. duckdb / sqlite の初期データを準備（データパイプライン等）
4. 監視プロセス起動:
   - python -m kabusys.run_monitoring
5. ExecutionEngine 起動（別プロセス）
   - python -m kabusys.run_execution
6. 監視が Kill Switch を検出したら kill.flag を書込み、Execution を停止させる
7. 作業終了後、stop_requested.flag を作成して run_* スクリプトを安全に停止するか、プロセスに SIGINT を送る

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development|paper_trading|live) — デフォルト development
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能を利用する場合)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- LOG_DIR (ログ出力先、デフォルト logs/)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒)
- PAPER_FILL_MODE (instant|partial|never|reject)
- KILL_FLAG_CLEAR_ON_START (0|1)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

---

## ディレクトリ構成（src/kabusys の主要ファイル）

- src/kabusys/
  - __init__.py
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - config.py                — Settings / .env 自動読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）処理
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ & 永続化クラス
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
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
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/               — Execution 系（OrderManager 等、スニペットに登場）
  - data/                    — 実行時に使用される DB / フラグファイル（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/stop_requested.flag, data/kill.flag）

---

## 追加メモ / トラブルシューティング

- validate_config の YAML パースチェックは PyYAML がないとスキップされます。PyYAML を入れると config/*.yaml のパース検証を行います。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合は警告が出ますが、多くの起動処理でディレクトリは自動作成されます。
- run_monitoring のポーリング間隔に 0 以下を指定すると無効扱いになり、デフォルト（60秒）にフォールバックします。
- OpenAI API を使う機能は API キーと利用ポリシーに注意してください（コスト・レート制限）。
- プロセス優先度設定（process_priority）は権限や OS により失敗する可能性があり、その場合は警告が出ますが続行します。

---

必要があれば README に次の内容を追加できます：
- 詳細な .env.example（サンプル）
- 各 DB スキーマの詳細（monitoring_db は一部実装済み）
- ExecutionEngine / BrokerClient の起動フロー図
- デプロイ・監視運用手順（systemd / Docker / 監視アラート設定）

ご希望があれば、上記のいずれかを展開して追記します。