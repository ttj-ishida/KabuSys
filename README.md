# KabuSys

日本株向けの自動売買システム（KabuSys）のコードベース README（日本語）

概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。主な機能は以下の通りです。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を担う実行系
- 監視（Monitoring）: システム状態、注文状況、リスク（ドローダウン、ポジション上限等）の定期チェックとアラート／Kill Switch
- ポートフォリオ構築ロジック: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム調整などの関数群
- リサーチ機能: DuckDB を用いたファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- AI 支援: ニュースの NLP（OpenAI）によるセンチメント集計、マーケットレジーム判定
- ツール群: .env ウィザード、設定検証、paper trading 検証レポート生成 など
- ロギング／プロセス優先度設定などのユーティリティ

設計上の留意点として、look-ahead バイアスを避けるため日付参照を直接用いない実装（関数に target_date を渡す）や、本番/ペーパートレードの分離（専用 DB）などが行われています。

---

## 機能一覧（抜粋）

- 環境設定
  - 対話式 .env ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
- 実行 / 監視
  - 実行エンジン起動スクリプト: `kabusys.run_execution`
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、履歴は専用 DB（data/paper_trading.db）へ保存
  - 監視ループ起動スクリプト: `kabusys.run_monitoring`
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能
- 監視コンポーネント
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
  - SQLite（監視 DB）への永続化層（monitoring_db）
- ポートフォリオ構築
  - 候補選定、等金額・スコア重み化、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI（OpenAI）
  - ニュースセンチメント集計（gpt-4o-mini を想定）
  - マクロニュース + ETF MA200 による市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 必要要件（概略）

- Python 3.10 以上（typing の `|` などを使用）
- 主要依存ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証に任意）
- 標準ライブラリ：sqlite3, logging, threading, datetime, pathlib 等

（実際の requirements.txt がリポジトリにある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリを設定
   - 例: git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)

3. 依存ライブラリのインストール
   - pip install duckdb psutil openai
   - 必要に応じて PyYAML をインストール（設定 YAML の検証に用いる）
     - pip install pyyaml

4. 環境変数設定（.env の準備）
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに `.env` を作成（例は下記）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番相当のチェックを厳密に行う場合は --strict を指定

6. データディレクトリ・ログディレクトリの確認
   - デフォルト SQLite / DuckDB / ログディレクトリは `.env` の値またはデフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - LOG_DIR: logs/
   - ログは logs/<app_name>.log に日次ローテーションで出力されます

例: 最低限の .env（.env.example を参照して作成する想定）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

注意: .env は機密情報を含むため Git にコミットしないでください。

---

## 使い方（主要スクリプト）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密チェック: python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）へ処理を記録します
    - 起動時に data/stop_requested.flag が存在すると起動しません
    - data/execution.pid に PID を出す（Engine に渡す）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に（環境にかかわらず）本番 sqlite_path を参照して監視ログを書きます
  - data/stop_requested.flag を作成するとループを止めます

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を設定して使用
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime として利用可能

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境切替
  - KABUSYS_ENV: development | paper_trading | live
- DB / ログ
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper trading 用 DB)
  - LOG_DIR / LOG_LEVEL
- AI
  - OPENAI_API_KEY（AI 機能利用時）
- 監視 / 停止制御
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒）
  - KILL_FLAG_PATH（Kill Switch 用、Settings.kill_flag_path で管理）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。production は 0 推奨）

詳細は `src/kabusys/config.py` の Settings クラスを参照してください。

---

## 注意事項 / 運用に関するポイント

- KABUSYS_ENV=live（本番）では外部アラート（LINE）や Kill Switch 設定に注意してください。`validate_config` は live 時の追加警告を出します。
- Paper trading（ペーパートレード）は本番 DB と分離されます。環境変数 `PAPER_TRADING_SQLITE_PATH` を利用してください。
- .env の自動ロードはプロジェクトルートから行われます（.git または pyproject.toml を探索）。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- ログ: `kabusys.utils.logging_setup.setup_logging` により stdout と日次ローテーションファイル出力が設定されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- Kill Switch（監視側で条件が満たされた場合にファイルを書き、ExecutionEngine を停止させる）や stop flag（run_* スクリプトの停止制御）により、運用停止がファイルベースで行われる設計です。`data/kill.flag`, `data/stop_requested.flag`, `data/execution.pid` 等のファイル存在により挙動が変わります。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュール・ディレクトリの概観（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 用永続化層
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （存在するはずの）発注状態監視ロジック
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — （通知管理）
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化（SQLite）
    - reconciler.py          — 注文調整
    - risk_manager.py        — 実行時のリスク管理
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数決定・単元丸め・資金配分
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - data/                    — 実行時に使用するデータディレクトリ（logs/, db 等）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

（上記は抜粋です。詳細はソースツリーをご参照ください）

---

## よくある運用コマンド例

- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動（開発モード例）:
  - KABUSYS_ENV=development python -m kabusys.run_execution
- 監視ループ起動（ポーリング30秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 追加情報 / 開発メモ

- DuckDB は分析向けのインプロセス DB として利用しています。prices_daily / raw_financials / raw_news などのテーブルを DuckDB に持ち、研究コードは DuckDB 接続を受け取って処理します。
- monitoring の DB（SQLite）は監視・注文ログ用で、init_monitoring_db によりテーブルが冪等的に作成・マイグレーションされます。
- AI 部分は OpenAI の新しい SDK インタフェース（chat completions + JSON mode）を想定しています。実際の API のバージョン差分に注意してください。
- 本リポジトリは実発注を行う構成を含むため、live モード・API キー・パスワード等の取り扱いに十分注意してください。テストや検証は paper_trading モードで行うことを推奨します。

---

この README はコードベースの現状の主要な挙動を元に作成しています。細かな実装や追加モジュールはソースを参照してください。必要に応じて項目を追補・更新できます。