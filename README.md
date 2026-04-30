# KabuSys

日本株自動売買システムのサンプル実装（モニタリング・実行・各種レポート生成ツール群）

---

## プロジェクト概要

KabuSys は日本株自動売買を想定した小規模なフレームワークです。  
主に以下の機能を含みます。

- ExecutionEngine: 発注管理・リスク管理・リコンシリエーション
- Monitoring: システム / プロセス / リソースの定期ポーリング記録
- 各種 CLI レポート: Pre-Market, Market-Close, Performance, Signal Queue, Position Reconciliation など
- Paper Trading モード（本番 DB と分離された専用 SQLite を使用）
- .env ベースの設定ウィザードと設定検証ツール

本リポジトリはコマンドラインからの起動を想定したスクリプト群（python -m kabusys.<module>）で構成されています。

---

## 主な機能一覧

- 実行エンジン（run_execution）
  - ブローカークライアントの抽象化（本番 / モック）
  - リスク設定ファイル（config/risk_config.yaml）による制御
  - 起動時リコンシリエーションと Execution Startup レポート生成
  - paper_trading 環境では data/paper_trading.db を使用（本番データと完全分離）

- 監視（run_monitoring）
  - SystemMonitor のポーリングループ
  - MONITOR_POLL_INTERVAL による間隔変更（デフォルト 60 秒）
  - 停止フラグ / PID 管理（data/stop_requested.flag, data/monitoring.pid）

- ザラ場監視 CLI（run_intraday_monitor）
  - 単発表示 / watch モード（定期更新）
  - CPU / メモリ / 注文エラー / ドローダウン等の簡易サマリ

- レポート生成
  - Pre-Market（run_pre_market_report）
  - Market Close（run_market_close_report）
  - Performance（日次/週次/月次）（run_performance_report）
  - Signal Queue（run_signal_queue_report）
  - Position Reconciliation（run_position_reconciliation_report）
  - Execution Startup（起動時要約を operations/execution_startup_report で生成）

- 設定関連
  - 対話式 .env ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）

- Paper Trading 検証用スクリプト（tools/paper_verification_report.py）

---

## 必要条件 / 依存パッケージ

- Python 3.9+
  - zoneinfo を使用しているため 3.9 以上を推奨
- 必要な外部パッケージ（例）
  - duckdb
  - PyYAML
- 標準ライブラリの sqlite3, argparse, logging 等を使用

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb pyyaml
```

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順（簡易）

1. リポジトリをクローンしワークディレクトリへ移動
2. Python 仮想環境を作成して依存パッケージをインストール
3. .env の準備
   - 対話式ウィザードを実行して .env を生成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```
     python -m kabusys.validate_config
     ```
4. 必要に応じて config/*.yaml（特に config/risk_config.yaml）を確認・編集
5. DB ファイルや data ディレクトリは起動時に自動作成されることがありますが、必要に応じて作成してください
   - デフォルトのパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

.env 自動ロードについて:
- パッケージロード時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 重要な環境変数（抜粋）

- 必須（例）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
- Paper Trading
  - PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: instant）
- 監視関連
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_* 系（kill フラグに関する挙動）
- その他
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

詳しくは `src/kabusys/config.py` を参照してください。

---

## 使い方（主要なコマンド）

基本的にはモジュールとして起動します。例: `python -m kabusys.<module>`

- Execution エンジンを起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し `data/paper_trading.db` に記録します。
  - 停止方法: `data/stop_requested.flag` を作成すると起動中のループが終了します。
  - 起動時に起動レポート（Execution Startup Summary）を出力・保存できます。

- Monitoring を起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。
  - 監視用 DB は環境にかかわらず本番の sqlite_path を使用します。
  - 停止方法: `data/stop_requested.flag` を作成

- ザラ場中監視（CLI）
  ```
  python -m kabusys.run_intraday_monitor
  python -m kabusys.run_intraday_monitor --watch --interval 60
  ```

- Pre-Market レポート
  ```
  python -m kabusys.run_pre_market_report
  python -m kabusys.run_pre_market_report --save --json
  ```

- Market Close レポート
  ```
  python -m kabusys.run_market_close_report --date 2026-04-28 --save
  ```

- Signal Queue（翌営業日の発注予定）確認
  ```
  python -m kabusys.run_signal_queue_report
  python -m kabusys.run_signal_queue_report --date 2026-04-28 --save --json
  ```

- Position Reconciliation レポート
  ```
  python -m kabusys.run_position_reconciliation_report
  python -m kabusys.run_position_reconciliation_report --watch --interval 300
  ```

- 運用成績サマリ（daily/weekly/monthly）
  ```
  python -m kabusys.run_performance_report --type daily --from 2026-01-01 --to 2026-04-30
  ```

- Paper Trading 検証レポート（tools）
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

レポートの保存先:
- artifacts/<report_type>/<...> 以下に Markdown / JSON で保存されます（各 save_report 関数参照）。

---

## 停止 / PID / フラグ

- PID ファイル:
  - execution: data/execution.pid（Settings.pid_file_path がデフォルト）
  - monitoring: data/monitoring.pid
- 停止フラグ:
  - data/stop_requested.flag を作成するとループ実行スクリプトは検知して優雅に終了します。
- その他:
  - kill.flag 系の挙動や自動クリアは Settings で制御できます（KILL_FLAG_CLEAR_ON_START 等）。

---

## ディレクトリ構成（主要ファイル）

簡易的な構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - run_intraday_monitor.py  — ザラ場中監視 CLI
  - run_pre_market_report.py — Pre-Market Report CLI
  - run_market_close_report.py — Market Close Report CLI
  - run_performance_report.py  — Performance Report CLI
  - run_signal_queue_report.py — Signal Queue Report CLI
  - run_position_reconciliation_report.py — Position Reconciliation CLI
  - run_performance_report.py
  - run_performance_report.py
  - operations/               — レポート生成ロジック、データ整形関数群
    - pre_market_report.py
    - market_close_report.py
    - performance_collector.py / performance_report.py
    - execution_startup_report.py
    - signal_queue_report.py
    - night_batch_report.py
  - execution/                — Execution 関連（Engine / broker / order 管理 等）
  - monitoring/               — Monitoring 関連（DB 初期化等）
  - tools/                    — 補助ツール（paper_verification_report など）
  - utils/                    — ロギング設定、プロセス優先度設定などユーティリティ

その他:
- config/                    — YAML 設定ファイル（risk_config.yaml 等）
- data/                      — デフォルトの DB / PID / フラグ 保存先（data/*.db, .pid, stop_requested.flag）
- artifacts/                 — レポートの保存先（artifacts/<type>/<date>/...）

---

## 開発・運用上の注意

- 本リポジトリはサンプル実装のため実運用で利用する場合は入念なレビュー・テストが必要です。
- KABUSYS_ENV=live を使用する際は、API キーや取引パスワードなどの取り扱いに十分注意してください。validate_config は本番向けの注意喚起を行います。
- Paper Trading モードでは発注処理が実ネットワークに対して安全に分離されるように設計されています（専用 SQLite に記録）。
- レポート出力や DB 書き込みの場所は環境変数で変更できます。自動起動や監視を組む場合は PID/flag の扱いを運用ルールで統一してください。

---

必要であれば、セットアップ手順の詳細（requirements.txt の整備、systemd / supervisor 用の起動スクリプト例、Docker 化など）や各 CLI のオプション説明を追加で作成します。どの情報を優先して補足しますか？