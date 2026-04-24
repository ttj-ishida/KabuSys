# KabuSys

日本株自動売買システム（ライブラリ＋実行スクリプト群）の README。  
このリポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュース NLP）などの主要コンポーネントで構成されています。

--- 

## プロジェクト概要
KabuSys は日本株自動売買のためのモジュール群です。主な目的は以下の通りです。

- シグナル生成 → ポートフォリオ構築 → 注文発行（ExecutionEngine）
- 発注・約定ログとシステム状態の永続化（SQLite / DuckDB）
- 実行プロセスの監視（MonitoringEngine）、Kill Switch による緊急停止
- Paper Trading（模擬発注）を本番 DB と分離して検証可能
- ニュースを LLM（OpenAI）でスコアリングしてファクターへ反映
- ファクター計算・リサーチ用ユーティリティ（DuckDB ベース）

設計方針の一例:
- 設定は .env / 環境変数で管理。Settings クラスを通して読み出す。
- DuckDB は時系列データ・リサーチ用、SQLite は監視・発注ログ用に使用。
- 本番・ペーパートレードの DB を分離（KABUSYS_ENV により切替）。

---

## 主な機能一覧
- Execution
  - ExecutionEngine を起動して注文処理を行う（run_execution.py）。
  - Paper Trading 時は MockBrokerClient を利用し、data/paper_trading.db に記録。
  - リスク管理（RiskManager）、OrderManager、Reconciler 等を含む。

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）。
  - システム稼働率、データ鮮度、滞留注文や約定異常、ドローダウン監視。
  - Kill Switch（data/kill.flag）を書き込んで ExecutionEngine を停止可能。

- Portfolio Construction
  - 候補選定・重み付け・ポジションサイジング（等金額、スコア加重、リスクベース）を純関数として提供。

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 参照）。
  - 将来リターンや IC 計算、統計サマリ。

- AI（ニュース）
  - raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメント（ai_scores）を生成。
  - レジーム判定（ETF + マクロニュースの LLM スコア合成）で市場レジーム（bull/neutral/bear）を算出。

- ユーティリティ
  - 設定ウィザード（config_setup.py）で .env を対話的に生成。
  - 設定検証 CLI（validate_config.py）で必須環境変数や config/*.yaml の存在チェック。
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）。

---

## セットアップ手順（ローカル開発向け）
以下は一般的なセットアップ例です。プロジェクトルートで実行してください。

1. Python と仮想環境（推奨）
   - Python 3.9+ を想定（一部ライブラリにより要バージョン確認）
   - 仮想環境作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必要最低限（例）:
     - pip install duckdb psutil openai PyYAML
   - openai はニュース NLP / regime_detector の実行時に必要
   - PyYAML は validate_config が config/*.yaml のパース検証を行う場合に必要

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成し、最低限以下を設定してください:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=... (AI 機能を使う場合)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - config_setup はデフォルト値や秘匿値マスク表示に対応しています。

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗と扱います。

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ と logs/ を使用します。スクリプトが自動で作成しますが、権限等で失敗する場合は手動作成してください。

注意:
- SQLite / DuckDB ファイルパスは Settings で環境変数から読み込まれます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まないようにできます（テスト用）。

---

## 使い方（主要スクリプト）
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 戻りコード: 0 = OK, 1 = FAIL（--strict で警告も FAIL）

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を扱います。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して DB を分離します。
    - data/stop_requested.flag が存在すると起動しない / 実行中に停止します。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - Process priority を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを書きます。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
    - data/stop_requested.flag を検知するとループを抜けます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db でデータベースパスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数も利用可）。

- AI / リサーチ関数（ライブラリとして利用）
  - Python から直接インポートして利用できます。例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - OpenAI API を使う関数は OPENAI_API_KEY を環境変数に設定するか、引数で API キーを渡してください。

ログ:
- ログは logs/ 配下に日次ローテーションで出力されます（例: logs/execution.log, logs/monitoring.log）。
- setup_logging() が全ての起動スクリプトで使用されています。

停止・緊急停止:
- ExecutionEngine を停止したい場合:
  - data/stop_requested.flag を作成すると run_execution/monitoring のループが検出して停止します（run_execution は起動時に既に存在すると起動しません）。
- Kill Switch:
  - monitoring の判定で致命的条件となった場合、data/kill.flag を書き込み ExecutionEngine を停止させられます。KillSwitch.clear() により起動時にクリア可能（設定で自動クリアの有無を制御）。

---

## 環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境関連
  - KABUSYS_ENV         : development | paper_trading | live（default: development）
  - LOG_LEVEL           : DEBUG | INFO | WARNING | ERROR | CRITICAL

- DB パス
  - DUCKDB_PATH         : data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH         : data/monitoring.db（監視用、本番 DB）
  - PAPER_TRADING_SQLITE_PATH : data/paper_trading.db（paper_trading 用）

- AI
  - OPENAI_API_KEY

- Monitoring
  - MONITOR_POLL_INTERVAL : ポーリング間隔（秒、default: 60）
  - PID_FILE_PATH         : data/execution.pid（実行エンジン PID ファイル）
  - KILL_FLAG_PATH        : data/kill.flag
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアする（"1" で有効）

- Paper Trading
  - PAPER_FILL_MODE : instant | partial | never | reject（デフォルト: instant）

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主なファイルと役割の一覧です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト

  - execution/               — 実行系（Engine, BrokerFactory, OrderManager 等） ※詳細は該当ディレクトリ
  - monitoring/
    - monitoring_db.py       — SQLite のスキーマ初期化・永続化層
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - system_monitor.py      — CPU / memory / disk / データ鮮度 / プロセス生存監視
    - trade_monitor.py       — 発注ログの監視（滞留注文、異常約定など）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み・判定
    - alert_manager.py       — （アラート送信を担う想定の管理クラス）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum/volatility/value 計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリング
    - regime_detector.py     — 市場レジーム判定（ETF + マクロ LLM）
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

- その他
  - data/                   — デフォルトで使用する DB / フラグ / PID の格納場所（実行時に使用）
  - logs/                   — ログ出力ディレクトリ（設定により変更可能）
  - config/                 — YAML 設定テンプレート（system_config.yaml 等）

---

## 開発・運用上の注意点
- データベースの扱い
  - Monitoring は常に sqlite_path（本番用）を参照します。Paper Trading は paper_sqlite_path を使用する点に注意。
- .env の取り扱い
  - .env は秘匿情報を含むため絶対に Git へコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- OpenAI API
  - AI 機能は API 利用料がかかります。API キー管理と呼び出し頻度に注意してください。
  - レート制限や 5xx など一時的エラーはリトライロジックが入っていますが、コスト面の管理は利用者責任です。
- 権限
  - process priority の設定や PID ファイルの書き込みは OS の権限に依存します。権限不足時は警告にフォールバックします。
- テスト
  - 設定や DB パスの検証は validate_config.py を活用してください。
  - AI 呼び出しはモック可能（テスト用に関数をパッチする設計になっています）。

---

## よく使うコマンドまとめ
- 仮想環境作成・有効化:
  - python -m venv .venv
  - source .venv/bin/activate

- 依存関係インストール:
  - pip install duckdb psutil openai PyYAML

- .env 作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はソースコードの主要な部分に基づいて作成しています。より詳細な設計や運用手順（デプロイ、監視設定のチューニング、Broker 実装の差し替え方法など）は別途ドキュメント（Design/Operation.md 等）を参照・整備してください。必要であれば README に追記する内容（例: Docker 化手順、CI 設定、サンプル .env.example）を教えてください。