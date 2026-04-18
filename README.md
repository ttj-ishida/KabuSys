# KabuSys

日本株向けの自動売買システムのライブラリ / 実行スクリプト群です。  
本 README はこのリポジトリ（src/kabusys 以下）の主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下のような機能を持つ自動売買基盤のコンポーネント群です。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制約）
- 実行層（ExecutionEngine） — ブローカークライアント経由での注文発行（本番 / ペーパートレード対応）
- 監視（Monitoring） — システム稼働状況、注文ログ、リスク監視、Kill Switch
- AI 補助（ニュース NLP / レジーム判定） — OpenAI を使ったセンチメント評価（任意）
- 管理用 CLI：環境設定ウィザード、設定検証、ペーパートレードの検証レポート生成

設計方針の一部：
- DuckDB と SQLite を用途に応じて使い分け（分析用 DuckDB、監視/発注ログは SQLite）
- ペーパートレード環境は本番 DB と分離（デフォルトで data/paper_trading.db）
- 外部 API 呼び出し（OpenAI など）は明示的な API キーを必要とし、失敗時はフェイルセーフ動作

---

## 主な機能一覧

- 実行 / 監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番 / paper_trading を切替）
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視データを記録
- 環境設定 / 検証
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env および config/*.yaml の事前検証ツール
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成
- ポートフォリオ構築
  - portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ
  - research: ファクター計算（Momentum/Value/Volatility）、特徴量探索、IC 計算など
- AI
  - ai.news_nlp: ニュース記事のセンチメント評価（OpenAI）
  - ai.regime_detector: ETF / マクロニュースを元に市場レジーム判定（OpenAI）
- ユーティリティ
  - utils.logging_setup: 統一ログ設定（コンソール＋日次ローテートファイル）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定（Windows / POSIX 対応）
- 監視永続化
  - monitoring.monitoring_db: SQLite へのテーブル作成 / 永続化 API
  - monitoring.*: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine

---

## セットアップ手順

以下は開発環境での標準的なセットアップ例です。

1. Python と仮想環境
   - Python 3.10 以上を推奨（リポジトリの要件に合わせて調整）
   - 仮想環境作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - 必要モジュールのインストール（例）:
     - pip install -r requirements.txt
     - もし requirements.txt がない場合は少なくとも以下をインストールしてください:
       - duckdb, psutil, openai, pyyaml（設定検証時に YAML 検証を行う場合）

3. リポジトリの .env 作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - 任意/重要な設定
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗と扱う:
     - python -m kabusys.validate_config --strict

5. ログディレクトリ作成
   - デフォルトは logs/
   - setup_logging は起動時に自動で作成を試みますが、書き込み権限を確認してください。

注意:
- ペーパートレードを行う場合は KABUSYS_ENV=paper_trading を設定すると、専用の paper DB に書き込みます（本番 DB と分離）。
- Kill Switch / stop フラグのファイルは data/kill.flag と data/stop_requested.flag（または data/execution.pid）で管理されます。

---

## 簡単な使い方（コマンド例）

- 環境ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中は data/execution.pid に PID を書きます（指定は Settings.pid_file_path）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 挙動:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視テーブルを初期化します
    - data/stop_requested.flag を検知するとループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（コードから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください。

注意点:
- 実行前に validate_config を実行して必須環境変数が設定されているか確認してください。
- 本番（KABUSYS_ENV=live）での実行は十分に設定・確認した上で行ってください（LINE 通知や Kill Switch 設定などを確認）。

---

## 主要な環境変数（抜粋 / デフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）

- データベース
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）

- ログ / デバッグ
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - LOG_DIR: logs/（デフォルト）

- AI
  - OPENAI_API_KEY: OpenAI API を使う場合に必須

- 監視・停止
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1、本番では 0 推奨）

---

## 停止 / Kill Switch の仕組み

- Kill Switch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを与えます（KillSwitch クラス）。
- run_execution.py / run_monitoring.py は data/stop_requested.flag（停止要求ファイル）を監視し、存在すれば安全にシャットダウンします。
- Settings で kill_flag_path や pid_file_path を変更できます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・サブパッケージの概要です。

- src/kabusys/
  - __init__.py (パッケージ情報)
  - config.py (環境変数・設定管理)
  - config_setup.py (対話式 .env ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor 起動スクリプト)
  - tools/
    - paper_verification_report.py (ペーパートレード検証レポート)
  - portfolio/
    - portfolio_builder.py (候補選定・重み付け)
    - position_sizing.py (株数決定・投資制約)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
  - research/
    - factor_research.py (モメンタム/バリュー/ボラティリティ等)
    - feature_exploration.py (将来リターン・IC・統計)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング - OpenAI)
    - regime_detector.py (市場レジーム判定 - OpenAI)
  - monitoring/
    - monitoring_db.py (SQLite テーブル初期化 + 永続化 API)
    - system_monitor.py (システム状態・データ鮮度監視)
    - trade_monitor.py (注文ログ監視)  ※実装ファイルが存在（コードベース参照）
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag の生成 / 制御)
    - alert_manager.py (LINE など通知管理) ※実装ファイルが存在（コードベース参照）
    - monitoring_engine.py (各 Monitor を束ねるエンジン)
  - utils/
    - logging_setup.py (ログ設定ユーティリティ)
    - process_priority.py (プロセス優先度 / CPU affinity)
  - data/（実行時に使用される想定ディレクトリ）
    - kill.flag, stop_requested.flag, execution.pid, monitoring.db 等（実行/運用で使用）

（注）上記はこのコードベースで確認できる主要モジュールの一覧です。細かい補助モジュールや追加ファイルがある場合があります。

---

## 開発者向けメモ / 実装上の注意

- データベース
  - DuckDB は分析用途（prices_daily / raw_financials / raw_news 等）に利用されます。research モジュールは DuckDB 接続を受け取り SQL を実行します。
  - 監視・注文ログは SQLite（monitoring.db / paper_trading.db）に保存します。monitoring_db.init_monitoring_db は冪等にテーブルを作成します。
- ログ
  - setup_logging() は stdout と日次ローテートのファイル出力を統一して設定します。logs/ ディレクトリの書き込み権限を確認してください。
- AI (OpenAI)
  - OpenAI を使う処理は API 失敗時にフォールバックやリトライ実装がありますが、API キーは必ず安全に管理してください。
  - AI 呼び出しのテストでは _call_openai_api をモックすることを推奨します（ユニットテスト用フックが各モジュールに用意されています）。
- ペーパートレード
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使って発注ログ等を専用 DB に記録します。本番 DB と分離されるため安全に検証できます。

---

## サポート / 拡張アイデア

- 個別銘柄毎の lot_size を stocks マスタで管理して position_sizing の柔軟性を向上
- AI モデルの切替やローカル LLM のサポート
- モニタリングの外部通知（Slack / PagerDuty）プラグイン拡張
- コンテナ化（Docker）と systemd / k8s での運用マニュアル

---

以上がこのコードベースの README です。必要であれば:
- インストール要件（requirements.txt）や CI 設定例
- systemd / Docker / k8s 向けのデプロイ手順
- 詳細な API リファレンス（各モジュール関数の docstring を元にしたドキュメント）
などを追記できます。どの項目を優先して追加しますか？