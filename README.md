# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行・監視・リサーチ・AI 支援（ニュースセンチメント等）を含む自動売買システムのコア部分を示すコードベースです。実運用向けの安全装置（Kill Switch、監視、リスク管理）やペーパートレード用分離 DB などの機能を備えています。

以下は本プロジェクトの README（日本語）です。

目次
- プロジェクト概要
- 主な機能
- 前提 / 必要パッケージ
- セットアップ手順
- 使い方（起動 / CLI）
- 主要環境変数
- 停止 / Kill / フラグの扱い
- ディレクトリ構成（主要ファイルと説明）
- 補足（ログ・DB・自動 .env 読込）

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主に次の要素を提供します。

- データ解析 / リサーチ（DuckDB を用いたファクター計算）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- 実行エンジン（BrokerClient 抽象に基づく発注）
- 監視（システム稼働／データ鮮度／取引状況監視、Kill Switch）
- AI 支援（ニュースセンチメント / レジーム判定 / OpenAI 連携）
- 各種ユーティリティ（ログ設定、プロセス優先度設定等）
- ペーパートレード（実アカウントと分離された SQLite）

設計方針として、ルックアヘッドバイアスを防ぐために日付参照を外部から渡す/固定する、DB 書き込みは冪等にする、API失敗時はフェイルセーフで継続する、などが盛り込まれています。

---

## 主な機能一覧

- 環境設定ウィザード（config_setup.py）
- 設定検証 CLI（validate_config.py）
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
- 監視ループ起動スクリプト（run_monitoring.py）
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視データ永続化（monitoring_db.py, SQLite）
- リスク監視（drawdown / position limit）
- Kill Switch（kill.flag を書くことで ExecutionEngine に停止指示）
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- AI モジュール（news_nlp: ニュースセンチメント、regime_detector: 市場レジーム）
- Research モジュール（ファクター計算、forward return、IC 計算）
- Portfolio モジュール（候補選定・重み付け・ポジションサイズ計算）
- ユーティリティ（ログ設定、プロセス優先度／CPU affinity 設定）

---

## 前提 / 必要パッケージ

（使用する環境や要件により変わります。最低限の依存を列挙します）

必須（実行に必要な Python パッケージの例）
- duckdb
- psutil
- openai

開発 / オプション
- PyYAML（config/*.yaml の構文チェックを行う validate_config 時に使用。未インストールでも動作します）
- sqlite3（標準ライブラリ）
- その他：標準ライブラリ（threading, logging, pathlib, etc.）

インストール例:
pip install duckdb psutil openai pyyaml

（requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順（素早く始める）

1. リポジトリをクローンして作業ディレクトリに入る

2. Python 環境を作成（推奨: venv / pyenv）
   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージをインストール
   pip install duckdb psutil openai pyyaml

4. 必要ディレクトリ作成（data, logs）
   mkdir -p data logs

5. 環境変数（.env）を作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - または .env を手動作成（.env.example を参照／作成）

6. 設定検証（任意）
   python -m kabusys.validate_config
   --strict をつけると警告も失敗扱いになります。

7. DuckDB / SQLite データベース（デフォルトパスは data/kabusys.duckdb, data/monitoring.db）
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH を変更

---

## 主要環境変数（代表的なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV
  - development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、発注はモックで data/paper_trading.db に記録
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の模擬約定動作。instant/partial/never/reject）
- LOG_LEVEL（default: INFO）
- LOG_DIR（ログファイル出力先、default: logs/）
- PID_FILE_PATH（ExecutionEngine の pid ファイルパス、default: data/execution.pid）
- KILL_FLAG_PATH（Kill Switch ファイルパス、default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1、default: 0）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）。デフォルト 60）

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local を自動ロードします。
- OS 環境変数 > .env.local > .env の優先順位。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

---

## 使い方（起動 / CLI）

主要なエントリポイントはモジュールとして実行できます。各スクリプトは package 内にあり、以下のように実行します。

- 環境設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  動作:
    - KABUSYS_ENV に応じて paper_trading 用の専用 DB を使用する（本番 DB と分離）
    - 起動時にプロセス優先度を high に設定
    - data/stop_requested.flag の存在で起動を中止または停止
    - 実行中は pid ファイル（data/execution.pid）を書き、停止時に削除する（実装に依存）

- 監視ループ起動（Monitoring）
  python -m kabusys.run_monitoring
  オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  動作:
    - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用
    - SystemMonitor, TradeMonitor, RiskMonitor 等を定期実行
    - 停止フラグ（data/stop_requested.flag）を検知してループ終了

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）

---

## 停止 / Kill Switch / フラグ

プロセス停止や外部からの強制停止はファイルフラグで行います：

- data/stop_requested.flag
  - run_execution / run_monitoring のループがこのファイルの存在を検知すると静かに停止します。
  - 管理者が手動で作成して停止を要求できます。

- data/kill.flag（Settings.kill_flag_path）
  - KillSwitch により自動生成される可能性があるファイル。
  - KillSwitch はリスク（ドローダウン超過、ポジション上限超過等）を検出したときに書き込み、ExecutionEngine に停止を促します。

- KILL_FLAG_CLEAR_ON_START=1 を設定している場合、ExecutionEngine 起動時に kill.flag が自動的にクリアされます（本番では 0 を推奨）。

---

## ログ・DB の扱い

- ログ: kabusys.utils.logging_setup.setup_logging を通じて統一設定されます。
  - stdout（StreamHandler）とファイル（logs/<app_name>.log）の二系統
  - 日次ローテーション（TimedRotatingFileHandler）、バックアップ 30 日
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみ

- DB:
  - DuckDB: 分析用（デフォルト data/kabusys.duckdb）
  - SQLite:
    - 監視/履歴用 monitoring.db（設定: SQLITE_PATH、デフォルト data/monitoring.db）
    - Paper Trading 用に分離された paper_trading.db（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）
  - monitoring_db.init_monitoring_db は必要テーブルを冪等に作成（マイグレーション処理も一部実装）

---

## ディレクトリ構成（主要ファイルと説明）

以下は src/kabusys の主要モジュール・ファイルと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__ 等）

- src/kabusys/config.py
  - 環境変数 / 設定の読み取りロジック（Settings クラス）
  - .env 自動ロード機能（プロジェクトルート検出）
  - 各種設定プロパティ（DB パス、KABUSYS_ENV、閾値等）

- src/kabusys/config_setup.py
  - .env を対話式で生成/更新するウィザード

- src/kabusys/validate_config.py
  - 起動前の設定検証 CLI（必須環境変数や config/*.yaml の有無チェック等）

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト
  - paper_trading 時は MockBrokerClient を使用、専用 SQLite に記録

- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL により間隔変更可能

- src/kabusys/utils/
  - logging_setup.py: ログ共通設定
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite への永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の評価・書き込み
  - monitoring_engine.py: 複数モニタの統合実行、アラート送出連携

- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
  - 注文管理・リスク管理・ブローカ抽象（実稼働用ブローカ or MockBroker）

- src/kabusys/portfolio/
  - portfolio_builder.py: 候補選定、重み付け（等金額 / スコア加重）
  - position_sizing.py: 株数算出、aggregate cap 処理、lot 単位丸め
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- src/kabusys/research/
  - factor_research.py: Momentum / Value / Volatility 等のファクター算出（DuckDB を使用）
  - feature_exploration.py: forward returns / IC / 統計サマリー等

- src/kabusys/ai/
  - news_nlp.py: raw_news を OpenAI に送って銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.py: ETF (1321) の MA200 とマクロニュースセンチメントを組み合わせて市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py: Paper Trading DB のログを集計して PASS/FAIL レポートを生成

---

## 開発者向けメモ・注意点

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストや一時的に自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を利用する機能は API キーが未設定だと例外を投げます（score_news / score_regime 等）。運用時は OPENAI_API_KEY を設定してください。
- run_monitoring は監視用 SQLite（Settings.sqlite_path）を使用します。監視ログは常に production に書き込む設計です（KABUSYS_ENV に依存しない）。
- run_execution は paper_trading の場合 DB を分離します。実運用での誤発注防止のため必ず KABUSYS_ENV を確認してください。
- ログディレクトリ作成が失敗した場合、ファイル出力は無効化されコンソールログのみになります。適切なパーミッションを設定してください。
- psutil によるプロセス優先度 / CPU affinity の変更は OS に依存します。権限不足で失敗しても警告を出して継続します。

---

## 付録：よく使うコマンドまとめ

- .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視ループ起動:
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

この README はリポジトリ内のソースコードのコメントおよび設計意図に基づいてまとめられています。詳細な挙動や追加オプションは各モジュール（特に execution/*、monitoring/*、ai/*、research/*）の docstring を参照してください。必要であれば README を英語版や運用手順（Runbook）に拡張できます。