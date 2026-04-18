# KabuSys

日本株向け自動売買システムのコアライブラリ群。ポートフォリオ構築、ポジションサイズ計算、監視・リスク管理、Paper Trading 検証、LLM を使ったニュースセンチメント評価などを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存
- セットアップ手順
- 使い方（コマンド例）
- 環境変数 / .env の主な項目
- 停止 / Kill スイッチ
- ディレクトリ構成（主要ファイルと説明）

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム用に設計されたライブラリ群です。  
戦略のためのファクター計算・特徴量解析、ポートフォリオ構築・ポジションサイズ計算、実行エンジン（ExecutionEngine）連携、監視・リスク判定、Paper Trading 用の分離 DB および検証レポート、OpenAI を用いたニュース NLP（センチメント）などの機能を備えています。

設計方針の一部:
- DB（DuckDB / SQLite）を使ったデータ駆動設計
- 実行環境（本番 / paper_trading / development）を環境変数で切替
- Paper Trading は本番 DB と完全分離（別 SQLite）
- LLM 呼び出しはフェイルセーフ（失敗時はスキップ or 中立値）
- 自動ログ設定（コンソール + 日次ローテーションファイル）

---

## 主な機能

- portfolio:
  - 候補選定（スコア順）、等金額 / スコア加重配分
  - ポジションサイズ計算（risk_based / equal / score）、単元株丸め、aggregate cap
  - セクターキャップ適用、レジーム乗数
- research:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 上）
  - 将来リターン計算、IC（Spearman）評価、統計サマリ
- ai:
  - news_nlp: OpenAI（gpt-4o-mini 等）でニュースを銘柄ごとにセンチメント化し ai_scores に書き込み
  - regime_detector: ETF とマクロ記事 + LLM を組み合わせて日次の市場レジーム判定
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - MonitoringDB: SQLite を使った監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）
  - KillSwitch: 一定条件で data/kill.flag を書き、ExecutionEngine を停止
- 実行スクリプト:
  - run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用）
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト
- ユーティリティ:
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 設定検証 CLI（.env / config/*.yaml のチェック）
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 前提・依存

- Python 3.10+
  - 型注釈で | を使用しているため Python 3.10 以上を想定します
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証に必要だが必須ではない）
- 標準ライブラリ: sqlite3, logging, pathlib, datetime など

インストール例（仮）:
pip install duckdb psutil openai PyYAML

（実プロジェクトでは requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布アーカイブを展開
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. 対話式に環境変数を作成
   - python -m kabusys.config_setup
   - これによりプロジェクトルートに .env ファイルが生成されます（Git にコミットしないでください）
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります
6. 必要ディレクトリの作成（通常は自動で作成されます）
   - data/ （SQLite, pid, flag 等）
   - logs/（ログファイル）
7. OpenAI を使う機能を利用する場合:
   - 環境変数 OPENAI_API_KEY を設定する（あるいは score_news 等の関数にキーを渡す）

---

## 使い方（主要コマンド例）

- 実行環境初期設定（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / paper_trading に応じて .env の KABUSYS_ENV を設定）
  - python -m kabusys.run_execution
  - 特記事項: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に保存され本番 DB と分離されます。

- Monitoring 起動（ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で間隔秒を指定可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- ライブラリ呼び出し（Python API）
  - ポートフォリオ構築関数:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - 研究関数:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI スコアリング:
    from kabusys.ai import score_news  # DuckDB 接続と target_date を渡して呼ぶ

---

## 環境変数 / .env の主な項目

自動読み込み:
- プロジェクトルートに .env / .env.local があると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading の場合、run_execution は PAPER_TRADING_SQLITE_PATH を使用して DB を分離
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai.score_news / regime_detector 等）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログ出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定動作（instant | partial | never | reject）

例（.env の一部）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...

---

## 停止 / Kill スイッチ

- run_execution.py / run_monitoring.py はプロジェクトの data ディレクトリにあるフラグファイルを使って停止検出します:
  - data/stop_requested.flag: run_monitoring/run_execution の外部終了要求に使用（存在するとループを終了）
  - KillSwitch は監視結果に基づき data/kill.flag を書き込み、ExecutionEngine に停止シグナルを発行します
- ExecutionEngine 起動時の挙動:
  - KILL_FLAG_CLEAR_ON_START 環境変数が "1" の場合、起動時に kill.flag を自動クリア（本番では 0 を推奨）

---

## ログ

- logging_setup.setup_logging を用いて統一的に設定されます
  - コンソール出力 (stdout)
  - 日次ローテーションファイル: logs/<app_name>.log（30日分保持）
- LOG_DIR / LOG_LEVEL で挙動を制御可能

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと簡単な説明です:

- __init__.py
  - パッケージ初期化、バージョン情報
- config.py
  - 環境変数読み込み、Settings クラス（各種パス / フラグ /閾値等）
  - 自動でプロジェクトルートの .env, .env.local を読み込み
- config_setup.py
  - .env 作成用の対話式ウィザード
- validate_config.py
  - .env と config/*.yaml の簡易検証 CLI

- run_execution.py
  - ExecutionEngine を立ち上げるスクリプト（pid ファイル、paper_trading 用 DB 切替など）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔制御）

- utils/
  - logging_setup.py: ログ初期化ユーティリティ
  - process_priority.py: プロセス優先度 & CPU affinity 設定ユーティリティ

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算・スケーリング
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: momentum/volatility/value のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書込む
  - regime_detector.py: ETF MA + マクロ記事 + LLM による市場レジーム判定

- monitoring/
  - monitoring_db.py: SQLite テーブル初期化と永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: システム状態・データ鮮度監視
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - monitoring_engine.py: Monitor を束ねるエンジン
  - kill_switch.py: 条件により kill.flag を書き込む
  - alert_manager.py (参照されるが一覧に含まれる): 通知管理（LINE 等）

- execution/
  - （ExecutionEngine, OrderManager, BrokerClientFactory 等はこのディレクトリに存在）

- tools/
  - paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト

（上記はコードベースの主要部分を抜粋したものです）

---

## 補足 / 運用上の注意

- Paper Trading:
  - KABUSYS_ENV=paper_trading のとき run_execution は専用の PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と分離されます。
  - PAPER_FILL_MODE によりペーパートレードでの約定動作を制御できます（instant / partial / never / reject）。
- 監視:
  - run_monitoring は env に関係なく Settings.sqlite_path（監視 DB）を使います（監視ログは本番 DB を参照して一元管理される想定）。
- OpenAI:
  - API 呼び出しは失敗時にフォールバック（無視や中立スコア）するよう実装されていますが、API キーは必須です（score_news / score_regime を使う場合）。
- 権限:
  - process_priority.set_process_priority() は管理者権限が必要な場合があり、失敗時は警告が出てスキップされます。

---

この README はコードベースのエントリポイント・主要機能と基本的な運用手順をまとめたものです。実運用時は .env と config/*.yaml の内容を入念に確認し、validate_config を必ず実行してください。必要であれば追加のデプロイ手順（systemd ユニット、cron、コンテナ化など）を別途用意してください。