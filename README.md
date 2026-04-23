# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）。

このリポジトリはアルゴリズムの構成、実行エンジン、監視、研究用ユーティリティ、AI（ニュース NLP）連携などを含んでいます。

---

## プロジェクト概要

- 自動売買の ExecutionEngine（発注・リスク管理・注文管理・照合）を含む実行コンポーネント
- システム監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）による運用監視・自動停止制御
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算・セクター制限）
- 研究用モジュール（ファクター計算・特徴量探索・IC計算）
- AI 関連：ニュースを LLM（OpenAI）でスコア化してテーブルへ保存、レジーム判定
- 運用用 CLI：
  - 環境設定ウィザード（.env 作成）`config_setup`
  - 設定検証 `validate_config`
  - 起動スクリプト：`run_execution`, `run_monitoring`
  - 検証レポート生成ツール：`tools.paper_verification_report`

---

## 主な機能一覧

- Execution
  - ブローカークライアント抽象化（paper_trading では MockBroker を使用）
  - 注文管理・リスク管理（rate limit / circuit breaker / drawdown 等）
  - ExecutionEngine によるセッション実行と PID 管理
- Monitoring
  - システム資源（CPU / メモリ / ディスク）監視
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - 取引ログ監視（滞留注文、約定異常、遅延など）
  - リスクモニタ（ドローダウン、ポジション上限）→ kill.flag 出力で Execution を停止
  - ログ永続化（SQLite を使用）
- Portfolio
  - 候補選定、等重・スコア重み、リスクベース配分、単元株丸め、セクター上限適用、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC 計算、統計サマリー
- AI
  - ニュースを LLM（gpt-4o-mini 等）でセンチメント評価し ai_scores に書き込み
  - マクロニュース + ETF MA を使った市場レジーム判定
- 運用ツール
  - .env 対話ウィザード（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）
  - Paper Trading 検証レポート（`python -m kabusys.tools.paper_verification_report`）

---

## セットアップ手順（簡易）

1. リポジトリを取得
   - git clone ... またはパッケージ配布を参照

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必須（主なもの）:
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML（設定検証時に YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt が無い場合は上記パッケージを個別にインストールしてください。

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（下記「重要な環境変数」を参照）

   Settings モジュールは起動時にプロジェクトルートの `.env` と `.env.local` を自動で読み込みます（OS 環境変数を優先）。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 設定の検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit 1

6. データディレクトリ（必要に応じて）
   - デフォルトで `data/` に SQLite / DuckDB / PID / フラグが作成されます。存在しないときは自動作成される箇所もありますが、権限等に注意してください。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV : execution モード
  - development / paper_trading / live
  - paper_trading の場合、MockBroker を使用し DB を paper_trading.db に分離
- OPENAI_API_KEY : AI モジュール（news_nlp / regime_detector）で必要
- DUCKDB_PATH : デフォルト data/kabusys.duckdb
- SQLITE_PATH : 監視 DB（monitoring.db）デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH : paper_trading 用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE : paper_trading の約定モード（instant / partial / never / reject）
- LOG_LEVEL : デフォルト INFO
- PID_FILE_PATH : デフォルト data/execution.pid
- KILL_FLAG_PATH : デフォルト data/kill.flag
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）

例（.env の一部）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 実行方法（主要なスクリプト）

- 環境設定ウィザード（.env を作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（デフォルトは Settings に従う）
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 MockBroker と専用 DB を使用
  - 例（paper_trading）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 例（本番/ローカル）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 特徴:
    - 起動時にプロセス優先度を "high" に設定しようとします（プラットフォーム依存）
    - 起動時に `data/stop_requested.flag` が存在する場合はエンジン起動を行いません
    - 実行中に `data/stop_requested.flag` を作成するとエンジンは停止シグナルを受け取ります
    - Kill Switch 用の停止信号は `KILL_FLAG_PATH`（デフォルト data/kill.flag）

- Monitoring（ポーリング監視）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は Settings の sqlite_path を常に使用（環境に関わらず本番の monitoring DB を参照する点に注意）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

終了・停止
- `data/stop_requested.flag` を作成すると run_execution/run_monitoring のデーモンループが検知して終了します（グレースフルシャットダウン）。
- KillSwitch（ドローダウン等）による自動停止は `data/kill.flag` を書き込み、ExecutionEngine に停止を要求します。

ログ
- ログはデフォルト `logs/` ディレクトリに日次ローテート（30日保持）で保存されます。ログ設定は `kabusys.utils.logging_setup.setup_logging` で制御されます。

---

## 開発・デバッグのヒント

- Settings はプロジェクトルートの .env / .env.local を自動ロードします。テストで自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- YAML の構文チェックは PyYAML がインストールされている場合のみ行われます（validate_config 内）。
- AI 周りは OpenAI の API が必要です。API 呼び出しは堅牢化（リトライ/バックオフ/パース検証）されていますが、API キーは必須です。
- DuckDB 接続は分析/研究用途に最適化されています。prices_daily / raw_financials 等のテーブルを使用します。

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py          — .env 対話ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/                — 発注・リスク管理・エンジン等（詳細実装は別ファイル）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ・永続化層
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
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — レジーム判定（ETF MA + macro sentiment）
  - tools/
    - paper_verification_report.py
  - data/ (実行時に生成されることが想定)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite, paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - stop_requested.flag
    - kill.flag

---

## ライセンス・バージョン

- パッケージバージョン: __version__ = "0.1.0" （src/kabusys/__init__.py）

---

必要であれば、README に含めるサンプル .env テンプレートや systemd / Supervisor 用のサービス定義、docker-compose の例なども作成できます。どの形式が必要か教えてください。