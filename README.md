# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
この README はソースコード（src/kabusys 以下）を参照して、導入・起動・主要コンポーネントの使い方をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な目的は以下の通りです。

- 戦略（ファクター計算・ポートフォリオ構築）と注文実行 / リスク管理を分離した設計
- 監視（System / Trade / Risk）と Kill Switch による自動停止
- Paper Trading（仮想発注）と Live（実口座）を同一コードベースで切替可能
- ニュースの NLP（OpenAI）を活用したセンチメント評価や市場レジーム判定機能
- DuckDB / SQLite によるデータ分析・ログ保存

---

## 主な機能一覧

- 実行エンジン（ExecutionEngine）
  - ブローカークライアント抽象化（実口座 / モック）
  - 注文管理・リスク管理・再突合（reconciler）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、Executionプロセス監視
  - TradeMonitor: 発注ログの異常検出（滞留注文・約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件到達で `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringEngine: 上記モニタを束ねてポーリング実行
- ポートフォリオ構築（pure functions）
  - 候補選定、等ウェイト／スコア加重、単元株丸め、リスク調整（セクター制限・レジーム乗数）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等ファクターを DuckDB 上で計算
  - 将来リターン・IC 計算・統計サマリー
- AI（OpenAI）連携
  - ニュースの銘柄別センチメント推定（news_nlp）
  - マクロ＋ETF 指標を用いた市場レジーム判定（regime_detector）
- ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
- ログ管理
  - 標準化された logging 設定（コンソール + 日次ローテーションファイル）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨
- システムに sqlite3（標準ライブラリ）とファイルアクセス権があること

1. リポジトリをクローン / ワークディレクトリに移動
   - ソースは `src/kabusys` 配下に揃っています。

2. 仮想環境を作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   例（最低限）:
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - PyYAML を使いたい場合: pip install pyyaml

   （requirements.txt は本リポジトリに含まれていないため、実運用ではプロジェクト固有の requirements を用意してください。）

4. 環境変数の設定（.env）
   - 対話ウィザードで生成:
     - python -m kabusys.config_setup
     - 生成される `.env` はデフォルトでプロジェクトルートに作成されます。
   - 自動ロードの挙動:
     - 起動時に .env/.env.local の自動読み込みを行います（OS 環境変数が優先）。
     - テストなどで無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告を失敗扱いにする: python -m kabusys.validate_config --strict

6. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (Paper Trading専用 DB、デフォルト: data/paper_trading.db)
   - OPENAI_API_KEY (AI機能を使う場合に必要)
   - LOG_LEVEL (DEBUG/INFO/...)
   - PAPER_FILL_MODE (paper_trading 時の約定モード: instant/partial/never/reject)
   - MONITOR_POLL_INTERVAL（監視ポーリング間隔・秒、デフォルト 60）※ run_monitoring 用

   注意: `.env` は機密情報を含むため Git にコミットしないでください。

---

## 使い方（起動／主要コマンド）

- 実行エンジン（Execution）
  - 目的: 戦略が生成した発注を実際に処理するプロセス
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、paper-trading用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 起動時に `data/stop_requested.flag` が存在する場合は起動せず終了します。
    - プロセス優先度を "high" に設定します（権限により失敗する場合あり）。
    - PID ファイル: data/execution.pid（Settings.pid_file_path により変更可）

- 監視ループ（Monitoring）
  - 目的: System / Trade / Risk のポーリング、Kill Switch 判定、アラート送信
  - 起動:
    - python -m kabusys.run_monitoring
  - 挙動:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視データは本番 DB に記録）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 機能（プログラムから利用）
  - ニュースセンチメント:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - OpenAI API キーは OPENAI_API_KEY 環境変数、もしくは関数引数で指定します。

- 停止 / Kill Switch
  - 実行中プロセスを外部から止めたいとき:
    - 監視系の自動判定で `data/kill.flag` が書き込まれると ExecutionEngine は停止します。
    - 手動で停止フラグを立てる場合は `data/kill.flag` に理由文字列を書き込むか、`data/stop_requested.flag` を作成してください。
  - ExecutionEngine 側は起動時に `KILL_FLAG_CLEAR_ON_START` の設定を参照し、必要なら kill.flag をクリアする挙動を持ちます（本番では 0 を推奨）。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要なモジュールとファイルを示します（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みと Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (※存在する想定の補助モジュール)
  - execution/               — ExecutionEngine, order_manager, broker_factory 等
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のファイル群は src/kabusys 以下を参照してください。上は主要ファイルの抜粋です。）

---

## 運用上の注意点

- .env は機密情報を含むため Git にコミットしないでください（config_setup のヘッダにも記載）。
- KABUSYS_ENV による挙動差分:
  - development: 開発用（挙動の一部が抑制される想定）
  - paper_trading: 発注はモック（paper_trading 用 SQLite に記録）
  - live: 実口座に接続するため設定ミスは重大。validate_config で warnings を確認してください。
- Logging:
  - デフォルトで logs/ ディレクトリに日次ローテーションのログを出力します。権限やディスク空きによりファイル出力が失敗した場合はコンソールのみになります。
- DB:
  - DuckDB: 分析用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・発注ログ（デフォルト data/monitoring.db）、Paper Trading 用に分離された DB を使用する（data/paper_trading.db）。
- AI（OpenAI）:
  - API 使用にはコストが発生します。rate-limit や一時エラーへはリトライ実装があるものの、運用時はコストとリトライ方針を確認してください。
- 権限:
  - process priority 設定や CPU affinity の変更は権限により失敗することがあります。失敗時はログに警告が出て処理は継続します。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

README はここまでです。  
他に必要な項目（例: 詳細な設計ドキュメント、API レファレンス、運用手順書）や、実際の requirements.txt / systemd Unit ファイル例などが必要であれば作成します。どの情報が優先が教えてください。