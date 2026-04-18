# KabuSys

日本株向け自動売買システム KabuSys のリポジトリ（抜粋）。  
この README は、提供されたコードベースに基づく利用方法・セットアップ手順・構成の説明を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するモジュール群（発注エンジン、監視、ポートフォリオ構築、リサーチ、AI ニューススコアリング等）を含むコードベースです。コンポーネントは独立して起動可能で、設定は .env ファイルまたは環境変数で行います。監視・ロギングやペーパートレード用の分離など運用を考慮した設計になっています。

主な設計方針：
- 本番 / ペーパートレードを環境変数 `KABUSYS_ENV` で切替
- 設定は .env（.env.local）→ 環境変数の順で解決（自動読み込みあり、無効化可）
- ログはコンソール + 日次ローテートファイル（logs/）
- 監視は SQLite、分析は DuckDB を想定

---

## 機能一覧

- ExecutionEngine（発注エンジン）
  - 本番 / ペーパー発注の分離（paper_trading 時は MockBrokerClient を使用）
  - リスク管理（RiskManager）、注文管理、再整合（Reconciler）等を統合
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
  - TradeMonitor: 注文/約定ログの監視（滞留注文、異常約定検出等）
  - RiskMonitor: ドローダウン・ポジション上限チェック、Kill Switch 発動
  - MonitoringEngine: これらを束ねて定期ポーリング・アラート発行
- Portfolio（銘柄選定・配分・サイズ計算）
  - 候補選定、等金額/スコア加重・リスクベースの株数算定、セクターキャップ適用等
- Research（リサーチ / ファクター計算）
  - Momentum / Volatility / Value ファクター計算
  - Forward return、IC（Spearman）や統計サマリー
- AI（ニュース NLP / レジーム判定）
  - raw_news を OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores へ書き込み
  - マクロニュース + ETF MA200 による市場レジーム判定
- ユーティリティ
  - 設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール
  - ログ設定 / プロセス優先度設定ユーティリティ

---

## 要件（概略）

- Python 3.10+
- 主な依存パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合に任意）
- 標準ライブラリ: sqlite3, logging, threading, pathlib, datetime 等

依存は環境や配布方法に応じて requirements.txt を作成して下さい。例：
pip install duckdb psutil openai PyYAML

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン / 展開

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. 環境変数設定（.env）
   - 対話式で作成（推奨）
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルートに置く）
     主要なキー（例・デフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）

   - 自動ロードは既定で有効。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合は --strict を付ける

6. データ / ログディレクトリ
   - 実行時に自動作成されますが、事前に以下を作成しておくと権限関連で安全:
     - data/
     - logs/

---

## 使い方（主要スクリプト）

- 設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話式に生成/更新します。

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合: MockBrokerClient を使用し paper_sqlite_path（デフォルト data/paper_trading.db）に記録
    - PID ファイル: data/execution.pid（Settings.pid_file_path でオーバーライド可）
    - 停止は data/stop_requested.flag を作成するか Kill Switch が書く data/kill.flag を使う

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔秒を指定（デフォルト 60）
    - 監視用 DB（SQLite）は settings.sqlite_path（monitoring は環境にかかわらず本番 sqlite_path を使用）
    - 停止は data/stop_requested.flag を作成

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY 環境変数、または引数で API key を渡す
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- 監視ループやエンジンは Ctrl+C（KeyboardInterrupt）で停止可能
- stop フラグ / kill.flag により外部から安全に停止できます

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (default: development)
- DUCKDB_PATH: DuckDB ファイルパス (default: data/kabusys.duckdb)
- SQLITE_PATH: 監視用 SQLite (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
- OPENAI_API_KEY: OpenAI API Key（AI 機能で必須）
- PAPER_FILL_MODE: paper_trading のフィルモード (instant|partial|never|reject)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか (0/1)

補足:
- 自動で .env を読み込む仕組みがある。読み込み順: OS 環境 > .env.local > .env。
- 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 運用上の注意

- 本番環境 (KABUSYS_ENV=live) の場合は必須環境変数や LINE 通知設定、Kill Switch の設定などを慎重に確認してください。
- モニタリングは監視用 SQLite を使って永続化します。run_monitoring は monitoring 用の DB パス（Settings.sqlite_path）を使用します（環境に依らず本番 DB を利用する仕様）。
- ExecutionEngine は paper_trading 環境であれば paper_sqlite_path に完全分離して記録します。
- ログは logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリの作成に失敗した場合、コンソール出力のみになります。
- OpenAI API 呼び出しではレートリミット等に対する指数バックオフ実装がありますが、APIキーの漏洩や料金には注意してください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル群（提供コードに基づく）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       — （コード参照されるが省略）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信ロジック：LINE 等、省略）
    - monitoring_engine.py
  - execution/
    - execution_engine.py    — ExecutionEngine（起動/セッション制御）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
  - data/                    — 実行時生成想定（data/*.db, flags, pid など）
  - logs/                    — ログ出力先（実行時生成）

（上記は抜粋です。実際のリポジトリではさらにファイルやサブモジュールがあります）

---

## 開発メモ / よくある質問

- .env は決してリポジトリにコミットしないでください（config_setup はその旨を注意書きで明示）。
- SQLite / DuckDB のファイルは運用時の権限に注意してください（読み書きできないと起動に失敗する可能性があります）。
- run_monitoring のポーリング間隔を短くしすぎるとログ肥大や API 呼び出し過多を招きます。デフォルト 60 秒を推奨。
- OpenAI API を利用する機能は API コストが発生します。テストではモック（unittest.mock.patch）を使う設計になっています。

---

必要であれば、この README をベースに「systemd ユニット例」「docker-compose 設定」「requirements.txt」「example .env.example」などの追加ドキュメントも作成します。どれを優先して欲しいか教えてください。