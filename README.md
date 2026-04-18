# KabuSys

日本株向けの自動売買システムのコードベース。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ファクター/研究用モジュール、ポートフォリオ構築ロジック、OpenAI を使ったニュース NLP 等のユーティリティが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / 依存ライブラリ
- セットアップ手順
- 実行方法（使い方）
- 主要環境変数
- ディレクトリ構成（概略）
- 補足（運用上の注意）

---

プロジェクト概要
- KabuSys は日本株の自動売買を想定したモジュール群です。  
  コア機能は発注エンジン（ExecutionEngine）・監視エンジン（MonitoringEngine）・リスク管理・ポートフォリオ構築・因子計算・ニュース NLP（LLM）などで構成されています。
- 設定は .env ファイル（もしくは環境変数）で行い、実運用（live）・ペーパートレード（paper_trading）・開発（development）を切り替え可能です。

主な機能一覧
- Execution（実行エンジン）
  - ブローカークライアント切り替え（paper_trading 時は MockBrokerClient を利用）
  - 発注管理、リスク管理、再整合（reconciler）など（各コンポーネントは execution 配下）
- Monitoring（監視）
  - システム資源（CPU/メモリ/ディスク）監視、データ鮮度チェック、プロセス生存確認
  - 注文ログ / リスクログ / ダッシュボードの SQLite 永続化（monitoring_db）
  - Kill Switch（条件による停止フラグ書き込み）
  - アラート管理（AlertManager 経由で通知）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等ウェイト／スコア加重配分、ポジションサイズ計算（単元丸め等）、セクター制限、レジーム乗数
- Research（研究・因子計算）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン・IC（Information Coefficient）・統計サマリ等
- AI（OpenAI）連携
  - ニュース記事のセンチメントスコア化（news_nlp）
  - マクロニュース + ETF MA200 を使った市場レジーム判定（regime_detector）
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools/paper_verification_report）

前提条件 / 依存ライブラリ
- Python 3.10+
- 必要な外部パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config ファイル検証時に任意）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

例: 最低限のインストール例
pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt があればそれを利用してください）

セットアップ手順
1. リポジトリをクローン / 取得
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb psutil openai pyyaml
4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式に入力後 .env に保存されます（.env を Git にコミットしないでください）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けると警告も FAIL 扱いになります
6. DB 初期化は起動時に自動で行われる（monitoring モジュールが SQLite のテーブルを作成します）
7. OpenAI を使う機能を使う場合は OPENAI_API_KEY を環境変数へ設定するか、実行時引数で渡す

実行方法（使い方）
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって実行モードが切り替わります:
    - development: 開発用（発注なし）
    - paper_trading: MockBrokerClient を利用し data/paper_trading.db に記録
    - live: 実際に発注を行う（注意して使用）
  - 起動前に data/stop_requested.flag や data/kill.flag の存在を確認してください。stop フラグがあると起動しません。
  - 実行時に PID ファイル（data/execution.pid など）を出力します

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）
  - 監視は監視用の SQLite DB（Settings.sqlite_path、デフォルト data/monitoring.db）を使用します（監視は本番 sqlite_path を参照）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可能（デフォルト data/paper_trading.db）

- 設定ウィザード / 検証
  - python -m kabusys.config_setup  （.env を対話式で生成/更新）
  - python -m kabusys.validate_config  （設定の静的検証）

主要な環境変数（抜粋）
- 必須（起動前に設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- データベース関連
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- ロギング / プロセス
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - PID_FILE_PATH: Execution PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効、デフォルト "0"）
- モニタ設定
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
  - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で使用

運用に関するファイル・フラグ
- data/stop_requested.flag: run_* スクリプトが存在確認して停止するためのフラグファイル
- data/kill.flag: KillSwitch が書き込む停止指示（ExecutionEngine 停止トリガー）
- data/execution.pid: ExecutionEngine の PID 管理用ファイル
- DB ファイル: data/monitoring.db（監視）, data/paper_trading.db（ペーパー）, data/kabusys.duckdb（研究／分析）

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・永続化 API
    - system_monitor.py      — システム・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - trade_monitor.py       — （注文監視）※実装参照
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — （アラート送信）※実装参照
  - execution/
    - execution_engine.py    — ExecutionEngine（起動 / セッション管理）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化（SQLite） 等
    - reconciler.py          — 注文再整合
    - risk_manager.py        — 発注前リスクチェック
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + LLM）
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / 統計
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

補足（運用上の注意）
- KABUSYS_ENV=live での起動は実際の発注を伴います。production では .env の中身・通知設定・kill flag の扱いを十分に確認してください。
- .env は機密情報（API トークン等）を含むため、決して VCS にコミットしないでください。
- OpenAI を利用する機能は API 使用料が発生します。API キーの管理に注意してください。
- run_monitoring/run_execution は stop flag（data/stop_requested.flag）や kill.flag の存在によって安全に停止/起動制御できる設計です。運用時はこれらフラグを利用してください。
- DuckDB のテーブルスキーマやデータ投入は別途データパイプライン（kabusys.data.pipeline 等）を利用して行います。研究用クエリは DuckDB 接続を期待します。

---

README はここまでです。必要であれば以下を追記できます:
- 各モジュールの API リファレンス（関数一覧・引数仕様）
- サンプル .env.example
- systemd / supervisor 用の起動ユニット例
- CI / テストの実行方法

どの追加情報が必要か教えてください。