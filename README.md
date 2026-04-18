# KabuSys

日本株自動売買システムの一部コードベース。戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ／AI モジュールなどを含みます。

この README はこのリポジトリ内の主要スクリプト・モジュールの概要、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は以下です。

- 発注実行（ExecutionEngine）：ブローカークライアント経由で注文を管理・送信
- 監視（Monitoring）：システム状態、注文状況、リスク（ドローダウン・ポジション上限）を監視し、必要に応じて停止フラグ（kill）を生成
- ポートフォリオ構築：候補選定、重み付け、ポジションサイズ決定、セクター制限などの純粋関数群
- リサーチ：ファクター計算、将来リターン計算、IC 計測など（DuckDB ベース）
- AI モジュール：ニュースの NLP スコアリング（OpenAI を利用）や市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、設定読み込み・ウィザード等
- ツール：Paper Trading の検証レポート生成など

設計上、DB（DuckDB / SQLite）を用いた分析・永続化、環境変数による設定管理、.env ウィザード／検証機能が含まれています。

---

## 機能一覧（抜粋）

- 設定管理
  - .env 自動読み込み（プロジェクトルートに基づく）
  - 対話式設定ウィザード：`python -m kabusys.config_setup`
  - 設定検証 CLI：`python -m kabusys.validate_config`
- 実行関連
  - ExecutionEngine 起動スクリプト：`python -m kabusys.run_execution`
    - `KABUSYS_ENV=paper_trading` のときは Mock ブローカーを使い、paper_trading専用 SQLite（`data/paper_trading.db`）に記録
  - 停止フラグ／PID 管理（`data/stop_requested.flag`, `data/execution.pid` 等）
- 監視関連
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリング
  - Monitoring 起動スクリプト：`python -m kabusys.run_monitoring`
  - KillSwitch（`data/kill.flag`）による ExecutionEngine の強制停止
  - ログ、監視テーブル（SQLite）への永続化
- ポートフォリオ
  - 候補選定（スコア順 etc.）
  - 等金額／スコア加重配分、リスクベース配分
  - セクターキャップ、レジーム乗数
  - 株数決定（単元株丸め、aggregate cap 等）
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman rank）計算、統計サマリー
- AI
  - ニュースセンチメント付与（OpenAI を利用、JSON Mode）
  - 市場レジーム判定（ETF + マクロニュース + LLM）
- ツール
  - Paper Trading 検証レポート生成スクリプト（`python -m kabusys.tools.paper_verification_report`）

---

## セットアップ手順

1. 前提
   - Python 3.10+
   - pip によるパッケージ管理
   - system での SQLite3（標準に含まれる）と psutil, duckdb, openai 等が必要

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存関係のインストール（プロジェクトの requirements.txt が無い場合、代表的なもの）
   - pip install duckdb psutil openai PyYAML

   ※ 実際のプロダクトでは別途 requirements.txt を提供する想定です。

4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - ウィザードはデフォルト / 既存の .env を読み取り、.env を生成します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他（必要に応じて）:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等

   サンプル（.env の一部）:
   ```
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_password_here
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   ```

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データ／ログ用ディレクトリの作成（通常はログユーティリティが自動作成しますが、明示的に）
   - mkdir -p data logs

---

## 使い方（実行例）

- ExecutionEngine 起動（本番/開発/ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - ペーパートレード時:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - この場合、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）が使用され、MockBrokerClient を利用する

- Monitoring（監視）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視プロセスは常に本番 sqlite_path を参照（設定に関係なく）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- 停止 / Kill
  - Execution や Monitoring はプロジェクト内 `data/stop_requested.flag` の存在を検知して安全停止します（run_execution/run_monitoring のループがチェック）。
  - KillSwitch（監視側）により `data/kill.flag` が書き込まれると ExecutionEngine に停止指示が送られます。
  - Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` にすると起動時に kill.flag を自動クリアします（本番では推奨しません）。

---

## 主要設定とデフォルトパス

- DuckDB: data/kabusys.duckdb
- SQLite（監視 DB）: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- PID / stop / kill フラグ:
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
- ログ:
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler 日次回転、30日保持）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一

---

## 開発者向けメモ

- Logging
  - setup_logging(app_name="execution" または "monitoring" など) を起動時に呼び出すことで、コンソール＋日次ローテートログを統一的に設定します。
- プロセス優先度
  - run_* スクリプトは起動時に set_process_priority("high") を呼び出します（psutil に依存、権限により失敗する場合は警告になる）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等実行でテーブルを作成し、既存 DB に対する軽微なマイグレーション（カラム追加）も行います。
- テスト／モック
  - AI 周りや外部 API 呼び出しは内部で小さなラッパー関数（_call_openai_api 等）を用いているため、unit test で patch して置き換えやすく設計されています。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要な Python モジュール・パッケージ構成の例です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — レジーム判定（ETF + LLM）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       — （存在する想定: 監視の注文関連ロジック）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （存在する想定: 通知送信ロジック）
  - execution/
    - execution_engine.py    — ExecutionEngine 実体（起動・セッション実行）
    - broker_factory.py      — BrokerClient の生成（環境に応じて Mock/実ブローカー選択）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時に生成される DB / フラグファイル等（例: data/*.db, data/*.flag）
  - logs/                    — ログ（自動作成）

※ 上記は現状の主要ファイルを抜粋したもので、細かいサブモジュールや補助スクリプトが含まれます。

---

## よくある質問（FAQ）

- Q: Paper Trading と本番 DB は分離されていますか？
  - A: はい。KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使い、本番監視 DB とは分離されます。

- Q: 監視（Monitoring）はどの DB を参照しますか？
  - A: Monitoring は説明どおり、環境に関係なく本番 sqlite_path（Settings.sqlite_path / data/monitoring.db デフォルト）を使用して監視ログを記録します。

- Q: 強制停止（Kill Switch）はどうやって動作しますか？
  - A: RiskMonitor などの判定結果から KillSwitch.evaluate() が発火すると、指定の kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine はこのフラグを検知して停止します。

---

この README はコードベースの要点をまとめたものです。詳細な API、内部仕様、戦略設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）が別途あれば併せて参照してください。問題点や補足したいドキュメントがあればお知らせください。