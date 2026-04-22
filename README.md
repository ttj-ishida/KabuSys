# KabuSys

日本株向け自動売買システムのコアライブラリ群です。  
このリポジトリには、発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ、ニュースNLP / レジーム判定などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存パッケージ
- セットアップ手順
- 実行方法（使い方）
- 主要環境変数（抜粋）
- 停止 / Kill スイッチ
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコンポーネント群です。主な目的は以下のとおりです。

- 発注（ExecutionEngine）
- 実行・注文監視（TradeMonitor 等）
- システム稼働性監視（SystemMonitor）
- リスク監視（ドローダウン・ポジション上限等）
- ポートフォリオ構築（候補選定・重み付け・単元丸め）
- 研究用ファクター計算（DuckDB を用いたファクター算出）
- ニュースの NLP（OpenAI を使った銘柄センチメント）
- 市場レジーム判定（MA とマクロ NLP を合成）
- Paper Trading（実際の発注と分離された SQLite に記録）
- 検証用ツール（Paper Trading レポート生成など）

設計方針として、DB（DuckDB/SQLite）を明示的に指定し、実行環境ごとに本番/ペーパーを分離することで安全に運用できるようになっています。

---

## 機能一覧（抜粋）

- Execution
  - ExecutionEngine（発注実行・セッション管理）
  - BrokerClientFactory（本番 or Mock ブローカーの切替）
  - OrderManager / OrderRepository / Reconciler / RiskManager
- Monitoring
  - SystemMonitor（CPU/Mem/Disk・データ鮮度・プロセス生存監視）
  - TradeMonitor（注文の滞留・約定異常等の検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（フラグファイルにより発注エンジン停止）
  - MonitoringEngine（上記を束ねてポーリング）
- Portfolio
  - 候補選定、等金額 / スコア重み、リスクベースの株数決定、セクター制限、レジーム乗数
- Research
  - ファクター計算（momentum / volatility / value 等）
  - 特徴量探索（forward returns / IC / summary）
- AI
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメント集計と ai_scores 書き込み
  - regime_detector: ma200 とマクロニュース NLP を合成して market_regime を書き込み
- Tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力
- 設定管理
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- ロギング
  - 統一的な logging 設定ユーティリティ（コンソール + 日次ローテートファイル）

---

## 前提条件 / 依存パッケージ（主要）

最低限必要なパッケージ（用途に応じて追加）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定検証で config/*.yaml のパースを行う場合）

簡易インストール例:
pip install duckdb psutil openai PyYAML

（実際のプロジェクトでは requirements.txt を用意することを推奨します）

---

## セットアップ手順

1. リポジトリを取得
   - git clone ... && cd <repo>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式）
   - python -m kabusys.config_setup
     - J-Quants / kabuAPI パスワード等の必須値を入力します。
     - .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

注意:
- 自動で .env を読み込む機能は kabusys.config で有効になっています。  
  自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 実行方法（使い方）

以下はワンラインで実行できるモジュール例です。プロジェクトルートで実行してください。

- ExecutionEngine （実際の発注を行うエンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path）
    - 起動時に data/stop_requested.flag が存在するとエンジンを起動しません。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を参照（環境に関わらず本番の monitoring DB を使用）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- .env 対話式ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- AI / Research / ライブラリ関数
  - ライブラリ関数は Python から import して利用します。
    例:
      from kabusys.ai.news_nlp import score_news
      from kabusys.ai.regime_detector import score_regime
      from kabusys.research import calc_momentum

各起動スクリプトは共通で setup_logging を使用し、プロセス優先度を "high" に設定してから起動します（可能な場合）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード
  - development / paper_trading / live
  - paper_trading のときは本番発注を行わず専用 DB に記録されます
- PAPER_FILL_MODE: paper_trading 時の約定モード
  - instant | partial | never | reject
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB のデフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパー用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: INFO 等
- LOG_DIR: ログ出力先（デフォルト logs/）
- PID_FILE_PATH: Execution PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- OPENAI_API_KEY: OpenAI API キー（ニュース / レジーム機能で使用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

env の初期化は config_setup.py で対話的に行うのが簡単です。

---

## 停止 / Kill スイッチ

- 永続的な停止要求（外部からスクリプトを止めたいとき）
  - stop_requested.flag: run_execution / run_monitoring のループはプロジェクトルート/data/stop_requested.flag を監視しており、存在するとループを抜けます。
  - kill.flag: KillSwitch によって書かれるフラグ。ExecutionEngine に停止を促すために使用されます（Settings.kill_flag_path）。

- KillSwitch の動作:
  - RiskMonitor の結果（ドローダウン閾値超過やポジション数オーバー）がトリガーされると kill.flag が書き込まれます。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動的に kill.flag をクリアします（本番では 0 推奨）。

---

## ログ

- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一されます。
- コンソール（stdout）出力 + 日次ローテートファイル（logs/<app_name>.log、30日保持）
- LOG_DIR 環境変数で変更可能。ディレクトリ作成に失敗した場合はコンソールのみで出力されます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主なモジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI）
    - regime_detector.py          — 市場レジーム判定（LLM + MA）
    - __init__.py
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, ...）
    - system_monitor.py
    - trade_monitor.py            — （存在：注文監視）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            — （アラート送信管理）
  - execution/
    - execution_engine.py         — ExecutionEngine（メインの発注ロジック）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...（その他）
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
  - data/                         — 実行時に用いるデータ / DB / フラグファイル（例: data/*.db, data/kill.flag）

---

## 追加メモ / 運用上の注意

- KABUSYS_ENV=live は本番モードです。環境変数・LINE 通知設定・kill flag の設定を十分に確認してから起動してください（validate_config で注意喚起があります）。
- Paper Trading は本番 DB と分離されます。paper_trading 実行時は PAPER_TRADING_SQLITE_PATH に記録されるため、本番データを汚すことはありません。
- OpenAI を利用する機能は API コストやレスポンスの安定性を考慮しており、一部はリトライやフェイルセーフ（失敗時はスコア 0.0 等）を備えていますが、運用時はレート制限等に注意してください。
- process_priority.set_process_priority は可能な限り優先度を上げますが、権限不足等で失敗した場合は警告ログが出ます（動作は継続します）。
- DuckDB / SQLite のファイルパスは Settings で管理されます。必要に応じて .env で指定してください。

---

この README はコードベースの概要説明を目的としています。各モジュールの詳細な API や設計文書（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクト内にある場合はそちらも参照してください。必要があれば README にコマンド例やトラブルシュートセクションを追加します。