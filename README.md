# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリは、戦略研究（リサーチ）、ポートフォリオ構築、発注・実行エンジン、監視・リスク管理、AI を使ったニュース解析等を含むモジュール構成になっています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とするモジュール群を提供します。

- データ取得／分析（DuckDB を用いたファクター算出）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ExecutionEngine（ブローカークライアント経由での発注管理、ペーパートレード分離）
- 監視（システム状況、注文ログ、リスク監視、Kill Switch）
- AI 支援（ニュース NLP による銘柄センチメントや市場レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、本番とペーパートレードは DB を分離し、LLM など外部 API 呼び出しはエラーハンドリングとリトライを備えて安全に扱います。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（KABUSYS_ENV=paper_trading で MockBroker）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔上書き可）
- 環境設定
  - config_setup.py — 対話式ウィザードで .env を作成 / 更新
  - validate_config.py — 環境変数と config/*.yaml の静的検証（--strict オプションあり）
- 監視・リスク管理
  - monitoring/… — SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch 等
  - monitoring_db — SQLite ベースのスキーマ定義・読み書きユーティリティ
- ポートフォリオ構築
  - portfolio/… — 候補選定・重み付け・ポジションサイズ計算・セクター制約など純粋関数
- 研究（Research）
  - research/… — ファクター算出（Momentum/Value/Volatility）、特徴量探索・IC 計算
- AI
  - ai/news_nlp.py — OpenAI を使ったニュースセンチメント集約と ai_scores への書込
  - ai/regime_detector.py — ETF MA とマクロニュースで日次レジーム判定
- ユーティリティ
  - utils/logging_setup.py — 統一ロギング設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py — プロセス優先度・CPU affinity 設定
- ツール
  - tools/paper_verification_report.py — ペーパートレード DB を解析して検証レポートを生成

---

## セットアップ手順

1. Python 環境を準備（推奨: Python 3.10+）
   - 仮想環境の作成例:
     - python -m venv .venv
     - source .venv/bin/activate (Unix)
     - .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール
   - 主な依存:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML（config の YAML 検証に使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動して .env を作成
   - 対話ウィザードで作成:
     - python -m kabusys.config_setup
   - 手動で作る場合は `.env.example` を参考に `.env` を作成してください（Git にコミットしないこと）。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラーとみなす場合:
     - python -m kabusys.validate_config --strict

5. 必要ディレクトリ確認
   - デフォルトでは以下のファイル/ディレクトリを使用します:
     - data/monitoring.db (SQLite)
     - data/paper_trading.db (PAPER_TRADING 用)
     - data/kabusys.duckdb (DuckDB)
     - logs/
   - 起動スクリプトは必要に応じてこれらを自動作成しますが、権限等を確認してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — LLM 機能使用時に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒, デフォルト 60）
- PAPER_FILL_MODE — ペーパートレード MockBroker の fill モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=クリア）

.env の自動読み込み: OS 環境 > .env.local > .env の順でロードされます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方

基本的な実行コマンド例:

- ExecutionEngine を起動（通常運用）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient が使われ、データは data/paper_trading.db に記録され本番 DB と分離されます。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- .env 対話生成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

運用上のポイント:

- ログは logs/<app_name>.log に日次ローテートで保存されます（デフォルト 30 日保持）。
- run_execution/run_monitoring は起動直後にプロセス優先度を高く設定しようとします（プラットフォーム依存で権限不足時は警告）。
- 停止は data/stop_requested.flag（実行スクリプトで参照）や Kill Switch（data/kill.flag）を利用する仕組みがあります。
  - KillSwitch は監視結果に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を自動クリアします（本番では 0 推奨）。

AI 機能（news_nlp / regime_detector）を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライやバックオフを備えていますが、API キー未設定時は例外が投げられます。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主な構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数／設定読み込みロジック
  - config_setup.py        — 対話式 .env ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py      (例: 注文滞留・約定異常検出)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      (通知送信ロジック)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/                  — 実行時に使用するデフォルトの DB/flag/pid 用ディレクトリ (data/monitoring.db など)

注: 上記はコードベースから抜粋した主要ファイルです。詳細は各モジュールの docstring を参照してください。

---

## 運用上の注意・ベストプラクティス

- 本番（KABUSYS_ENV=live）での起動前に必ず設定検証を行ってください（validate_config.py）。
- .env は機密情報（API トークン・パスワード）を含むため、絶対に VCS にコミットしないでください。
- ペーパートレードは paper_sqlite_path で本番 DB と物理的に分離されています。検証時はペーパートレードモードを活用してください。
- kill.flag / stop_requested.flag / *.pid による停止・制御を組み合わせる運用設計を推奨します。
- OpenAI 等の外部 API を使用する機能は API 利用料が発生します。API キーと使用上限を適切に管理してください。
- DB マイグレーションや既存 DB スキーマの拡張（例: monitoring_db のカラム追加）は init_monitoring_db で冪等に扱われますが、バックアップをとってから運用することを推奨します。

---

## 貢献・開発

- 新しい機能を追加する場合は、まず既存のモジュールの設計方針（docstring）を確認してください。特に研究・ポートフォリオ・実行ロジックは「DB 非依存 / 純粋関数」を意識するべき箇所があります。
- テストは各純粋関数（portfolio/*, research/*）を単体テストでカバーし、外部 API を呼ぶ箇所はモックしてテストしてください（news_nlp._call_openai_api などはパッチ可能に設計されています）。

---

README に書かれていない実装詳細や、個別のモジュールに関する質問があれば教えてください。必要に応じてコマンド例や .env のテンプレートを追加で提供します。