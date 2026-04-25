# KabuSys

日本株自動売買システムの一部（ミニマルな実装）。  
このリポジトリには、監視・実行・ポートフォリオ構築・リサーチ・AI 製品（ニュースセンチメント／レジーム判定）などのモジュール群が含まれています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する以下の主要コンポーネントを含むライブラリ／実行スクリプト群です。

- ExecutionEngine（発注実行、paper_trading モードでの MockBroker）
- Monitoring（システム健全性・注文状況・リスク監視）
- Portfolio construction（銘柄選定、重み付け、株数計算）
- Research（ファクター計算・特徴量探索）
- AI 製品（ニュースのセンチメントスコアリング、レジーム判定）
- ユーティリティ（設定管理・ログ設定・プロセス優先度設定 等）

設計方針の例：
- DB は duckdb（分析用）と sqlite（監視・注文ログ）に分離
- 設定は .env / 環境変数中心（自動ロード機能あり）
- 本番（live）とペーパートレード（paper_trading）を切替可能
- LLM（OpenAI）を利用した非同期的・フェイルセーフな処理

---

## 主な機能一覧

- 設定管理
  - .env の自動ロード（プロジェクトルートに .env/.env.local）
  - 対話式ウィザード: kabusys.config_setup (python -m kabusys.config_setup)
  - 設定検証 CLI: kabusys.validate_config

- 実行（Execution）
  - ExecutionEngine 起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し、paper_trading 用 SQLite に完全分離して記録

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring.py：ポーリングループで監視を実行（MONITOR_POLL_INTERVAL で間隔制御）
  - Kill Switch（data/kill.flag）により ExecutionEngine を停止可能
  - 監視ログ永続化：monitoring_db.init_monitoring_db により SQLite スキーマを初期化

- ポートフォリオ構築
  - 銘柄選定、等配分・スコア配分、ポジションサイズ計算、セクター制約適用

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC 計算、統計サマリ等

- AI（OpenAI 利用）
  - ニュース NLP による銘柄センチメント付与（kabusys.ai.news_nlp.score_news）
  - レジーム判定（kabusys.ai.regime_detector.score_regime）
  - 両モジュールは OpenAI API キー（OPENAI_API_KEY）が必要。API 呼び出しはリトライ・フェイルセーフ実装

- ツール
  - ペーパートレード検証レポート生成: kabusys.tools.paper_verification_report

---

## 必要な依存パッケージ（例）

実行に必要な主要パッケージ（最低限）：
- python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定検証時に YAML パースを行う場合）

※ requirements.txt は本コードベースに同梱されていませんが、上記を pip でインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリを取得し、Python 仮想環境を用意する
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. 環境変数設定 (.env)
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - 生成された `.env` をプロジェクトルートに置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 必須環境変数が揃っているか、DB パスの親ディレクトリの存在などをチェックします。
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリの準備（必要に応じて）
   - デフォルトのデータファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/（自動作成を試みますが、権限に注意）

---

## 主要環境変数（代表例とデフォルト）

- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live") — デフォルト "development"
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- DUCKDB_PATH: data/kabusys.duckdb（分析 DB）
- SQLITE_PATH: data/monitoring.db（監視 DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/...）、デフォルト "INFO"
- LOG_DIR: ログ保存先ディレクトリ（デフォルト "logs"）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか (0/1)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

特記事項:
- run_monitoring は Monitoring の DB 接続に「常に」settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依存しません）。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite を使用します（本番 DB と分離）。

---

## 実行方法（使い方）

各スクリプトはモジュールとして実行できます（python -m ...）。

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード:
    python -m kabusys.validate_config --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します

- 実行エンジン起動
  - python -m kabusys.run_execution
  - paper_trading モード（MockBroker・専用 DB）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能呼び出し（コードから）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - api_key を渡さない場合は OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...).cursor/connection）を渡して使用

---

## ログとプロセス制御

- ログ設定:
  - kabusys.utils.logging_setup.setup_logging を各スクリプトが呼び出します。
  - stdout（コンソール）出力と日次ローテーションファイル（logs/<app_name>.log）を設定します。
  - ログディレクトリが作成できない場合はコンソール出力のみになります。

- プロセス優先度:
  - set_process_priority("high") を実行時に呼び出し、可能な限り高優先度に設定します（psutil 必須）。

- 停止フラグ / Kill Switch:
  - data/stop_requested.flag: スクリプト内でポーリングループを終了させるための内部停止フラグとして利用
  - data/kill.flag: KillSwitch が書き込むファイルで ExecutionEngine に対する停止指令（Execution は起動時/実行中に存在をチェック）
  - data/execution.pid: ExecutionEngine の PID を書き出す想定（run_execution で使用）

---

## ディレクトリ構成（抜粋）

src/ 以下にパッケージが置かれています。主なファイルと役割:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — 監視ポーリングループ起動スクリプト
  - run_execution.py         — 実行エンジン起動スクリプト

  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化と DB 操作クラス
    - monitoring_engine.py   — 複数モニタのポーリング統括
    - system_monitor.py      — システム・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - trade_monitor.py       — （注文・約定の監視ロジック, 本コードは一部参照あり）
    - kill_switch.py         — Kill Switch（flag ファイル書き込み）
    - alert_manager.py       — （アラート通知管理：LINE 等、実装参照）

  - execution/
    - execution_engine.py    — ExecutionEngine（セッション管理）
    - broker_factory.py      — Broker クライアント生成（Mock / 実ブローカー）
    - order_manager.py
    - order_repository.py
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
    - news_nlp.py            — ニュースセンチメント付与（OpenAI 使用）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA）
    - __init__.py

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py

- data/ (実行時に作成されるファイル群)
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite, paper_trading 用)
  - kabusys.duckdb (DuckDB)
  - stop_requested.flag, kill.flag, execution.pid など

---

## 注意点・運用上のポイント

- 設定ファイル（.env）は機密情報を含むため決して Git にコミットしないでください（config_setup でもその旨を案内します）。
- run_monitoring は監視 DB にアクセスするため、監視対象インスタンス上で実行する必要があります。Monitoring は settings.sqlite_path を使うため環境に依らず本番監視 DB を参照します。
- KABUSYS_ENV=paper_trading を使えば発注はモックに切り替わり、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。本番 DB と明確に分離する設計です。
- OpenAI を使う機能は外部 API 依存であり、API 利用料・レート制限・機密性に注意してください。失敗時はフェイルセーフ（0.0 等でフォールバック）する実装になっていますが、ログは必ず確認してください。
- DB スキーマのマイグレーション処理（monitoring_db.init_monitoring_db）には既存列の存在チェックが含まれており、後方互換を考慮した safe な変更が施されています。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの現状（主要モジュール・設定・実行方法）を簡潔にまとめたものです。さらに詳しい設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）はプロジェクト内の追加ドキュメントを参照してください。