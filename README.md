# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ + 起動スクリプト群）。  
この README はコードベース（src/kabusys 以下）の主要コンポーネント、セットアップ、起動方法、ディレクトリ構成をまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。主な役割は以下のとおりです。

- 戦略研究モジュール（ファクター計算、特徴量探索）
- ポートフォリオ構成（候補選定・重み付け・株数算出）
- 実行エンジン（ExecutionEngine） — 発注ロジック・リスク管理・注文管理
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- ユーティリティ（設定管理、ログ設定、プロセス優先度設定、ツール）

設計方針の例:
- DuckDB を分析用 DB として利用、SQLite を監視/発注ログ用に利用
- Paper trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db）
- 起動スクリプトはプロセス優先度の設定やログ設定を一貫して行う
- LLM 呼び出し（OpenAI）は失敗時にフェイルセーフで継続する設計

---

## 機能一覧（主な機能）

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード: `python -m kabusys.config_setup`
  - 起動前検証 CLI: `python -m kabusys.validate_config`

- 実行（Execution）
  - 起動スクリプト: `python -m kabusys.run_execution`
  - Paper trading 時は MockBroker を使用し、paper DB に記録
  - RiskManager / OrderManager / Reconciler / ExecutionEngine を組み合わせて発注を実行

- 監視（Monitoring）
  - 起動スクリプト: `python -m kabusys.run_monitoring`
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存/データ鮮度を監視
  - RiskMonitor: ドローダウン／ポジション数の監視・アラート記録
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine を停止させる
  - Monitoring DB（SQLite）にログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）

- 研究・分析
  - ファクター計算: momentum / volatility / value 等（DuckDB 接続を受け取る）
  - 特徴量探索: forward returns, IC, 基本統計量

- AI（OpenAI）
  - news_nlp: ニュース記事のセンチメントを LLM で評価して ai_scores に格納
  - regime_detector: ETF（1321）MA とマクロニュースの LLM センチメントを合成し市場レジーム判定

- ツール
  - Paper Trading の検証レポート生成: `python -m kabusys.tools.paper_verification_report`

- ユーティリティ
  - ログ設定ユーティリティ（Stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env のパースと安全な読み込み

---

## 前提 / 依存関係

主に以下のパッケージが必要です（環境に応じて適切にインストールしてください）:

必須（最低限）:
- Python 3.8+
- duckdb
- psutil
- openai

推奨 / オプション:
- PyYAML（config/*.yaml の検証時に使用）
- sqlite3（標準ライブラリ）
- その他、実行環境で必要となるブローカークライアント等（実運用時）

例（pip）:
pip install duckdb psutil openai pyyaml

※ requirements.txt はこのリポジトリに含まれていない想定なので、環境に合わせて依存を整えてください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成してアクティベート（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なライブラリをインストール
   - pip install duckdb psutil openai pyyaml
4. .env の作成（推奨: 対話式ウィザードを利用）
   - python -m kabusys.config_setup
   - ウィザードは .env にキー/値を書き込みます（.env は絶対に Git にコミットしないでください）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗扱い（exit 1）
6. データディレクトリの準備
   - デフォルトでは data/ に SQLite / pid / フラグファイルを作成します。必要に応じ既存ディレクトリを調整してください。
7. OpenAI を使用する場合は環境変数 OPENAI_API_KEY を設定

環境変数の主なキー（主要なもののみ抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- OPENAI_API_KEY (AI 機能を使う場合)
- PAPER_FILL_MODE (instant | partial | never | reject) — Paper trading の約定モード
- KILL_FLAG_CLEAR_ON_START (0|1)

自動 .env ロード:
- プロジェクトルートに .env / .env.local がある場合、起動時に自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効にする: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（起動・主なコマンド）

主要なエントリポイント（モジュール実行）:

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（実取引 / Paper）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に書き込む（本番 DB と分離）
    - 起動時に data/execution.pid が作られ、停止は data/stop_requested.flag / data/kill.flag で行う（KillSwitch は別）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照（環境にかかわらず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 任意期間:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の上書き）

ログ:
- ログは stdout に出力されつつ、logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリが作成できない場合はファイル出力をスキップして stdout のみ）。

停止 / Kill:
- 実行中の Engine を外部から停止するには data/kill.flag（KillSwitch）や data/stop_requested.flag（スクリプト内部の停止フラグ）を利用します。KillSwitch はしきい値超過時に自動で kill.flag を書き込みます。

注意（Paper vs Live）:
- KABUSYS_ENV=paper_trading は本番 DB と完全分離（paper DB を使用）されます。live は実際に発注が行われるため十分な確認が必要です。

---

## ディレクトリ構成（src/kabusys）※抜粋

以下は主要ファイル／ディレクトリのツリー（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定ラッパ
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - execution/                — 発注関連（Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュースセンチメント取得（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py

データ・ログ・PID 等のデフォルトパス（Settings による）:
- data/monitoring.db        — SQLite 監視 DB（SQLITE_PATH）
- data/paper_trading.db    — Paper trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/execution.pid       — ExecutionEngine PID ファイル（PID_FILE_PATH）
- data/kill.flag           — Kill Switch フラグ（KILL_FLAG_PATH）
- logs/<app_name>.log      — ログ出力（ログディレクトリは LOG_DIR または default: logs/）

---

## 開発時のヒント / 注意点

- .env は絶対にリポジトリにコミットしないでください。
- validate_config は起動前に実行して欠落や明らかな設定ミスを検出してください。
- OpenAI を利用する機能は API キーの設定が必要です。失敗時はフォールバック動作を取るよう設計されていますが、意図どおりの結果を得るにはキーを設定してください。
- Monitoring は本番 sqlite_path を参照するため、監視用途で別 DB を使いたい場合は環境変数を調整してください。
- 実運用で live モードを使う場合は KILL_FLAG_CLEAR_ON_START 等の設定に注意してください（安全のためデフォルトは 0）。

---

必要であれば、README にサンプル .env テンプレートやより詳細な起動フローチャート、各モジュールの API 使用例（research/ai 関数の直接呼び出し例）を追記します。どの情報を追加したいか教えてください。