# KabuSys

日本株自動売買システムの一部実装です。  
本リポジトリは発注エンジン（Execution）、監視（Monitoring）、リサーチ／ファクター計算、ポートフォリオ構築、AI を使ったニュース評価などのユーティリティ群を含みます。

## 概要

KabuSys は日本株の自動売買を想定したコンポーネント群です。主な目的は以下です。

- ExecutionEngine：発注ロジックの実行（本番 / ペーパートレード対応）
- Monitoring：プロセス・システム状態・注文状態・リスク監視と Kill Switch
- Research：DuckDB を用いたファクター計算・特徴量分析
- Portfolio：銘柄選定・配分・ポジションサイズ計算
- AI：ニュースの NLP スコアリングやレジーム判定（OpenAI 使用）
- Tools：設定ウィザード・検証・ペーパートレード検証レポートなど

設計方針として、できる限り副作用を抑え、環境変数で挙動を制御し、ペーパートレード時には本番 DB と完全分離することを重視しています。

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による本番 / paper_trading 切替）
  - run_monitoring.py: SystemMonitor ポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可能）
- 設定管理
  - config_setup.py: .env の対話式ウィザードでの作成 / 更新
  - validate_config.py: 環境変数・config/*.yaml の起動前検証 CLI
- DB 初期化 / 永続化
  - monitoring_db.py: 監視用 SQLite テーブルの作成・CRUD ユーティリティ
- 監視・アラート
  - MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager（実装の一部）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重/スコア加重、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ（DuckDB）
  - momentum / volatility / value 等ファクター計算、将来リターン・IC 計算
- AI（OpenAI）
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に書き込み
  - regime_detector: ETF・マクロニュースを組み合わせた市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレードの検証レポート生成

## 必要条件（概略）

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config のパース検証を行う場合）
- （任意）J-Quants / kabuステーション の API 情報、OpenAI API キー、LINE トークン等

requirements.txt は含まれていないためプロジェクト用途に応じてインストールしてください。例:

pip install duckdb psutil openai pyyaml

## 環境変数（重要なもの）

必須（起動前に設定）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要なオプション / デフォルト
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード MockBroker の挙動（instant / partial / never / reject、デフォルト: instant）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

.env はルートに配置します。.env 作成は下記のウィザードを推奨します。

## セットアップ手順（例）

1. リポジトリをクローン / 展開
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - ※ 実際の requirements はプロジェクト方針に合わせて作成してください
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または .env.example を元に手動作成
5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
6. データディレクトリ（data/）やログディレクトリ（logs/）を作成（通常はスクリプトが作成しますが、権限問題の確認をする）
7. OpenAI を使う場合は OPENAI_API_KEY を環境変数に設定

## 使い方（起動・ツール）

- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 実行前に .env の KABUSYS_ENV を設定:
    - development: 発注なし（安全モード）
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
    - live: 本番 API にアクセスして実際に発注（注意して利用）
  - 起動時に data/execution.pid に PID を書きます。data/stop_requested.flag があると起動しません。
  - 終了は stop flag を書くか、プロセスに割り込み（Ctrl+C）を送ってください。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60 秒）
  - 監視は Settings.sqlite_path（本番 sqlite_path）を使用してログを永続化します（KABUSYS_ENV に依存せず本番 DB を使う設計）
  - 停止は data/stop_requested.flag を作成するか Ctrl+C

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を作成 / 更新します

- 設定検証
  - python -m kabusys.validate_config
  - 起動前に環境変数や config/*.yaml をチェックします

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能
  - OpenAI を使う処理（news_nlp.score_news, regime_detector.score_regime）は OPENAI_API_KEY が必要です
  - AI 呼び出しはネットワークエラーや 5xx をリトライする実装が含まれますが、API キーの制御とコストに注意してください

## 実装上の注意点 / 安全ガード

- ペーパートレード（KABUSYS_ENV=paper_trading）は本番 DB とは分離され、MockBroker を使用します（data/paper_trading.db）。本番 DB を上書きしないための設計です。
- run_monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を使用して監視ログを書き込みます（監視は本番状態の把握が目的なため）。
- KillSwitch（data/kill.flag）により ExecutionEngine を外部から停止できます。KILL_FLAG_CLEAR_ON_START の設定により自動クリアの有無を制御します（本番では自動クリアを無効化推奨）。
- ロギングは console（stdout）と logs/<app_name>.log（日次ローテート、30日保管）に出力されます。LOG_DIR / LOG_LEVEL で設定可能です。
- プロセス優先度（高）・CPU affinity の設定を起動時に試みますが、アクセス権限不足時は警告ログを出してスキップします。

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - config_setup.py — .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - data/  （モジュール参照: data 関連ユーティリティは別途）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_db.py
    - kill_switch.py
    - alert_manager.py (想定)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

ルートには data/ や logs/ ディレクトリが生成されます（必要に応じて手動で作成してください）。

## 開発 / デバッグに関するヒント

- .env の自動読み込みは、プロジェクトルート（.git か pyproject.toml の場所）を検出して行われます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 設定検証ツール（validate_config）をまず実行し、必須環境変数の未設定やパスの誤りを検出してください。
- DuckDB はリサーチ・AI の集計処理で使用します。prices_daily / raw_financials / raw_news などのテーブルが前提です。
- AI 機能は外部 API を使うため、ユニットテスト時は該当関数の外部呼び出しをモックしてください（コード内にモック用の注釈があります）。

## 参考コマンド一覧

- .env 作成ウィザード
  - python -m kabusys.config_setup
- 設定検証（警告を失敗扱いにするには --strict）
  - python -m kabusys.validate_config [--strict]
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper トレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア実行（例: news_nlp を直接呼び出すスクリプトを作る）
  - 必須: OPENAI_API_KEY 環境変数を設定

---

この README はコードベースの主要な使用法・設計上の注意点をまとめたものです。実運用時には各 config/*.yaml（存在する場合）や環境変数、監視・アラートの設定を慎重に確認してください。