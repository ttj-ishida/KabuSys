# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買システムのコアライブラリ群です。  
モジュールはトレード実行、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などで構成されています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（コマンド／環境変数）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は次の要素で構成された自動売買プラットフォーム向けユーティリティ群です。

- ExecutionEngine：発注実行ロジック（本番 / ペーパートレード対応）
- Monitoring：システム安全性・注文・リスクの監視と Kill Switch（停止フラグ）機能
- Portfolio：候補選定・重み付け・ポジションサイズ算出・セクター制限
- Research：DuckDB を使ったファクター計算・特徴量探索
- AI：ニュース NLP（OpenAI を利用した銘柄別センチメントスコア）、市場レジーム判定
- Tools：ペーパートレード検証レポート生成など
- Utilities：ログ設定・プロセス優先度設定・環境設定読み込み等

設計方針の例：
- 本番 DB とペーパートレード DB を分離可能
- DuckDB を分析用に使用（prices_daily / raw_financials 等）
- 外部 API 呼び出し（OpenAI 等）は設定によって有効化
- ログは統一的に設定・ローテート

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレードモード切替（KABUSYS_ENV）
  - Broker クライアント工場（Mock と実クライアントの切替）
  - ExecutionEngine 実行ループ、PID ファイル管理、停止フラグ検知

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセスの監視、データ鮮度チェック
  - TradeMonitor：注文の滞留・約定異常検出（ログテーブル参照）
  - RiskMonitor：ドローダウン／保有上限監視、ダッシュボード更新
  - KillSwitch：重大リスク時に data/kill.flag を書き込み Execution を停止
  - MonitoringEngine：各種モニタを束ねポーリング実行

- Portfolio
  - シグナル候補選定 / スコア順ソート
  - 等重・スコア重み・リスクベースの配分
  - セクターキャップ適用、レジーム乗数

- Research
  - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI
  - ニュース記事を OpenAI (gpt-4o-mini) でスコアリングし ai_scores に保存
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定

- Tools
  - Paper Trading 検証レポート生成スクリプト（performance/uptime/latency など）

- Utilities
  - 統一ロギング（console + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話式ウィザード & 設定検証 CLI

---

## セットアップ手順（開発 / ローカル）

以下は一般的な手順です。環境に応じて適宜調整してください。

1. Python 環境作成
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)

2. 依存ライブラリインストール
   - 必要なパッケージ例:
     - duckdb, psutil, openai
   - 具体的な requirements.txt はプロジェクトに合わせて用意してください。
     - 例: pip install duckdb psutil openai

3. .env の作成
   - 初回は対話式ウィザードを利用すると簡単です:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（例）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - ペーパートレード用 DB は PAPER_TRADING_SQLITE_PATH で上書き可能（例: data/paper_trading.db）

4. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は指示に従って .env / config/*.yaml を修正してください

5. ログディレクトリ
   - デフォルトは logs/。必要に応じて環境変数 LOG_DIR を設定

---

## 使い方（起動・操作）

基本的にパッケージのモジュールを直接モジュール実行します。

- 実行エンジン（ExecutionEngine）起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV によって切替
  - コマンド:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます
    - 実行中に data/stop_requested.flag を作るとスレッドによりエンジン停止を要求します
    - 実行時にプロセス優先度を "high" に設定します
    - PID ファイル: data/execution.pid（設定で変更可）

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 説明:
    - Monitoring は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（KABUSYS_ENV に依存せず本番 sqlite_path を参照する点に注意）
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60）
    - 停止フラグ: data/stop_requested.flag を置くと監視ループを終了します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いになります

- .env ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を利用するか、環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI 関連
  - OpenAI API を利用する機能（ニュース NLP / レジーム判定）は環境変数 OPENAI_API_KEY または関数引数で API キーを渡す必要があります
  - score_news / score_regime 等の関数は DuckDB 接続と target_date を渡して実行する方式です

- ログ
  - setup_logging により logs/<app_name>.log に日次ローテートで出力されます

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: duckdb ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring 用、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）

---

## ディレクトリ構成（主要ファイルと説明）

以下は src/kabusys 以下の主要ファイル・ディレクトリです（抜粋）。

- kabusys/
  - __init__.py
    - パッケージ定義（__version__ 等）
  - config.py
    - 環境変数・.env 自動読み込み、Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前検証 CLI（必須環境変数・YAML 等のチェック）
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成
  - execution/
    - （ExecutionEngine、OrderManager、Reconciler、RiskManager 等の実装）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文ログ監視（滞留・異常）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — （通知管理。LINE 送信など）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・単元丸め・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し、バッチ/リトライ、バリデーション）
    - regime_detector.py — ETF MA200 + マクロニュースでレジーム判定
  - utils/
    - logging_setup.py — 共通ログ設定（console + 日次ローテート）
    - process_priority.py — プロセス優先度 / CPU affinity 設定

（注）実装ファイルの多くが DuckDB / SQLite を前提としています。prices_daily や raw_financials / raw_news 等のテーブルはデータ投入が必要です。

---

## 運用上の注意点

- データベース分離
  - run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番 sqlite を汚染しないようにしています。
  - しかし run_monitoring は「環境にかかわらず」Settings.sqlite_path（監視 DB）を利用します。監視 DB と Execution の DB を分けたい場合は .env を適切に設定してください。

- Kill Switch / Stop フラグ
  - KillSwitch は risk 条件（ドローダウン、ポジション数超過）を検出した場合に data/kill.flag を作成します。ExecutionEngine は kill.flag を検知して安全に停止します。
  - 手動で ExecutionEngine / Monitoring を停止するには data/stop_requested.flag を作成する運用も用意されています（run_* スクリプトが検知して終了します）。

- ログ & ローテーション
  - logs/<app_name>.log に日次ローテーションで 30 日分保持されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

- OpenAI API
  - AI 機能を有効にする場合は OPENAI_API_KEY を設定してください。API の失敗時はフォールバック動作（スコア 0.0、例外を上位に投げないなど）を行う設計になっていますが、キー未設定は例外になります（関数呼び出しによる）。

- 権限・優先度設定
  - プロセス優先度設定は psutil を使用します。権限不足で失敗する可能性があるため、ログで警告が出ますが起動自体は継続されます。

---

必要であれば、この README をベースにさらに「運用手順」「CI / デプロイ手順」「config/*.yaml の雛形」「DB スキーマの初期化方法（データ投入スクリプト）」などを追加できます。どの情報が必要か教えてください。