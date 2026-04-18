# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）。

このリポジトリは、マーケットデータ処理、ファクター計算、ポートフォリオ構築、発注実行（本番 / ペーパートレード切替）、監視・アラート、LLM を使ったニュース評価など、システム全体の主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定ウィザード（.env の対話的作成/更新）
- 起動前の設定検証 CLI（必須環境変数・設定ファイル・パス等のチェック）
- ExecutionEngine 起動スクリプト（本番 / paper_trading モード対応）
  - paper_trading 時は MockBroker を用いて data/paper_trading.db に記録（本番 DB と分離）
- Monitoring（System / Trade / Risk のポーリング監視）
  - kill.flag による外部からの停止シグナル送出
  - stop_requested.flag によるプロセス自動停止
- 監視ログ格納用 SQLite（monitoring.db）と分析用 DuckDB（kabusys.duckdb）
- Paper Trading 検証レポート生成ツール
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限など）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ）
- ニュース NLP（OpenAI を利用した銘柄別センチメントスコアリング）
- 市場レジーム判定（ETF の MA とマクロニュースを LLM で評価して判定）

---

## 前提（推奨環境・依存）

- Python 3.9+（typing の構文等を使用）
- 必要なライブラリ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

インストール例（venv を作成した上で）:
```bash
pip install duckdb psutil openai PyYAML
```
（プロジェクトで requirements.txt があればそちらを使用してください）

---

## 主要ファイル / コマンド

- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

## セットアップ手順（最短）

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成し activate
3. 依存ライブラリをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式で作る（推奨）:
     - python -m kabusys.config_setup
   - 既存 .env を使用する場合はプロジェクトルートに配置
5. 設定検証（問題がないか確認）
   - python -m kabusys.validate_config
   - 問題があれば .env を修正して再検証
6. データディレクトリ（data/）を作成（必要に応じて）
   - SQLite / DuckDB のデフォルトパス:
     - data/monitoring.db（監視用 SQLite）
     - data/kabusys.duckdb（分析用 DuckDB）
     - data/paper_trading.db（paper_trading 用 SQLite、KABUSYS_ENV=paper_trading の場合使用）
7. 起動
   - 監視: python -m kabusys.run_monitoring
   - 実行エンジン: python -m kabusys.run_execution

---

## 環境変数（主なもの・説明）

- KABUSYS_ENV
  - 設定値: development | paper_trading | live
  - 挙動分岐（例: paper_trading では MockBrokerClient を使用）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY
  - news_nlp / regime_detector などの LLM 呼び出しで使用
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の注文約定モード）
  - instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR（ログ出力ディレクトリ、デフォルト: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
- KILL_FLAG_CLEAR_ON_START（0/1。本番で 1 は危険）
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 設定するとプロジェクト起動時の .env 自動ロードを無効化

自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml を探索）を見つけた場合、自動で `.env` を読み込みます（OS 環境変数は上書きされません）。`.env.local` が存在すればそれで上書きされます。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

例（最小 .env）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 実行/運用メモ

- run_execution
  - KABUSYS_ENV=paper_trading の場合、Paper Trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。本番 DB と完全に分離されます。
  - 実行中は data/execution.pid に PID を書きます（PID ファイルの扱いは Settings.pid_file_path に従います）。
  - data/stop_requested.flag が存在すると、起動を中止または実行中に停止します。

- run_monitoring
  - 監視ループが起動し、MonitoringDB（SQLite）へ system_status / trade_logs / risk_logs / positions / dashboard を永続化します。監視は KABUSYS_ENV に関係なく本番 sqlite_path を使います（設定により変更可能）。
  - 停止: data/stop_requested.flag を置くとループが終了します。
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定できます（秒、デフォルト 60）。

- Kill Switch
  - Kill switch は `KillSwitch` が評価して `data/kill.flag` を作成することで ExecutionEngine に停止シグナルを送ります。書き込みは冪等（既に存在すれば上書きしない）。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨。自動クリアを許可すると意図せず Kill Switch を解除してしまうリスクがあります。

- ロギング
  - ログは stdout（StreamHandler）とファイル（logs/<app_name>.log）に日次ローテーションで出力されます。ログディレクトリは環境変数 LOG_DIR またはデフォルト `logs/`。
  - ログローテーションは TimedRotatingFileHandler（backupCount=30）で保持されます。

---

## よく使うコマンド例

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - エラーがあると exit code 1、--strict を付けると警告も失敗扱いになります

- 実行エンジン起動（デーモン化は任意のプロセスマネージャで）
  - python -m kabusys.run_execution

- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または、DB パスを指定: --db /path/to/paper_trading.db

---

## ディレクトリ構成（主なファイル）

以下はリポジトリ内の主要モジュールとスクリプトの概観です（src/kabusys 配下を想定）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（LLM + ETF MA）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム / データ鮮度監視
    - trade_monitor.py       — （trade チェックロジック）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — （アラート送信管理）
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 発注株数計算（単元丸め等）
    - risk_adjustment.py     — セクター上限 / レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - data/                    — 実行時に使用する DB やフラグファイル（デフォルトパス）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/                    — ログファイル出力先（デフォルト）

（実際のリポジトリでは追加のモジュールやサブパッケージが含まれる可能性があります）

---

## 運用上の注意 / トラブルシューティング

- 本番運用時は必ず KABUSYS_ENV=live を確認し、LINE 通知等の設定を見直してください（validate_config は live 時の追加警告も出します）。
- OpenAI を利用するモジュールは API キーが必須。API 呼び出し失敗時はフェイルセーフでスコアを 0 にする等の処理が入っていますが、API キーがない場合は実行前に環境変数 OPENAI_API_KEY を設定してください。
- ログディレクトリの作成に失敗するとファイル出力は無効化され、標準出力のみになります。権限やパスを確認してください。
- SQLite / DuckDB のパスは .env で設定可能。デフォルトでは `data/` 下に作成されます。データファイルのバックアップ・アクセス権に注意してください。
- kill.flag / stop_requested.flag / execution.pid の取り扱いを誤るとプロセスが停止しない・起動しない場合があります。運用スクリプトや Supervisor と組み合わせる場合はこれらのファイル操作ロジックを理解しておくことを推奨します。

---

必要であれば、この README をもとにさらに詳細な運用ガイド（デプロイ手順、systemd ユニット例、監視ダッシュボードの設定、ログローテーションの確認手順など）を作成します。どの情報を追加したいか教えてください。