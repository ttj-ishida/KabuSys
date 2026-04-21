# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・AI/リサーチ機能を含む自動売買システムのコア実装です。モジュールはできるだけ純粋関数・DB分離・フェイルセーフを重視して設計されています。

以下は本コードベースの README（日本語）です。

- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト）
- ディレクトリ構成（主要ファイルの説明）
- 重要な環境変数と運用メモ

---

## プロジェクト概要

KabuSys は日本株自動売買のためのコンポーネント群です。設計方針として：

- ポートフォリオ構築、ポジションサイジング、リスク調整は純粋関数で実装（副作用を最小化）。
- 実行エンジン（ExecutionEngine）と監視（MonitoringEngine）は明確に分離。
- Paper Trading（シミュレーション）と Live（本番）を環境変数で切り替え、DB も分離。
- AI（OpenAI）を用いたニュースセンチメントや市場レジーム判定をサポート（API キー必須）。
- DuckDB を分析用途に、SQLite を監視/トランザクションログ用途に利用。

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine を起動して発注・注文管理・リスク管理を行う（run_execution）。
  - 環境 `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper_trading 用 DB に記録して本番 DB と完全分離。

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングして状態を DB に記録、アラートや Kill Switch を評価（run_monitoring）。
  - 監視は環境にかかわらず本番の sqlite_path を参照（運用方針に基づく設計）。

- ポートフォリオ構築（portfolio モジュール）
  - 候補選定、重み計算（等配分・スコア配分）、ポジションサイジング（単元丸め・リスクベース）を提供。

- リサーチ（research モジュール）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）、将来リターン計算、IC計算、統計サマリ等。

- AI（ai モジュール）
  - ニュース記事からセンチメントを生成して ai_scores に書き込む（OpenAI，gpt-4o-mini を想定）。
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（regime_detector）。

- ユーティリティ
  - ロギングの統一セットアップ（コンソール + 日次ローテートファイル）。
  - プロセス優先度 / CPU affinity の設定ユーティリティ。
  - .env 対話作成ウィザード（config_setup）と設定検証 CLI（validate_config）。

- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）。

---

## セットアップ手順（開発 / 実行環境）

前提:
- Python 3.9 以上を想定（typing の union 表記などを使用）。
- SQLite は標準ライブラリで利用可。DuckDB は外部パッケージ。

推奨パッケージ（例）:
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（config 検証時に利用）

インストール例:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 必要パッケージをインストール:
  - pip install duckdb psutil openai PyYAML

（リポジトリに requirements.txt がない場合は上記を必要に応じてインストールしてください）

.env の準備:
1. 対話式ウィザードを実行して .env ファイルを作成:
   - python -m kabusys.config_setup
   - これにより `.env` が生成されます（Git 管理下にコミットしないでください）。
2. 設定を検証:
   - python -m kabusys.validate_config
   - 必須環境変数の未設定や config/*.yaml の欠落を検出します。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN（J-Quants API 用）
- KABU_API_PASSWORD（kabuステーション API パスワード）
- OPENAI_API_KEY（AI 機能を使う場合）

他の主要な環境変数やデフォルトは下の「重要な環境変数」を参照してください。

---

## 使い方（主要スクリプト）

1. 設定準備（一度）
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. 実行エンジン起動
   - python -m kabusys.run_execution
   - 説明:
     - 起動時にプロセス優先度を "high" に設定し、ExecutionEngine を起動します。
     - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。
     - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
     - 実行中に data/stop_requested.flag が作成されると停止します。
     - 実行中は data/execution.pid が使われます（pid_file）。

3. 監視ループ起動
   - python -m kabusys.run_monitoring
   - 説明:
     - SystemMonitor を初期化してポーリングループを開始します（デフォルト 60 秒）。
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書きできます（秒）。
     - 監視は常に settings.sqlite_path（本番 monitoring DB）を使用します（設計上の注意点）。
     - 停止は data/stop_requested.flag の生成で行います。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --db PATH を指定して別 DB を参照可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先。

5. AI / レジーム判定（ライブラリ関数として利用）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡してニューススコアを生成し ai_scores テーブルに保存します。
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - market_regime テーブルに当日のレジーム判定を保存します。
   - これらはライブラリ関数なので、スケジューラやバッチジョブから呼び出して使います。

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV
  - 実行環境: development | paper_trading | live
  - デフォルト: development

- JQUANTS_REFRESH_TOKEN
  - J-Quants API のリフレッシュトークン（必須）

- KABU_API_PASSWORD
  - kabuステーション API のパスワード（必須）

- DUCKDB_PATH
  - DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視 DB（monitoring.db）のパス（デフォルト: data/monitoring.db）
  - 監視プロセスは環境にかかわらずこの設定を使います（run_monitoring の設計）

- PAPER_TRADING_SQLITE_PATH
  - paper_trading モード時の SQLite（デフォルト: data/paper_trading.db）

- PAPER_FILL_MODE
  - Paper Trading の注文約定モード（instant | partial | never | reject）
  - デフォルト: instant

- LOG_LEVEL
  - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - デフォルト: INFO

- LOG_DIR
  - ログファイル保存ディレクトリ（デフォルト: logs/）

- OPENAI_API_KEY
  - OpenAI API キー（AI 機能を使う場合に必須）

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒、デフォルト 60）
  - 0 以下の値は無効としてデフォルトにフォールバックする

- KILL_FLAG_PATH
  - Kill Switch ファイルパス（デフォルト: data/kill.flag）
  - KillSwitch はリスク閾値超過時にこのファイルを書き込み、ExecutionEngine 側で検出して停止させる想定

- KILL_FLAG_CLEAR_ON_START
  - 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。production では 0 推奨）

---

## 運用メモ（ファイル・フラグ）

- data/stop_requested.flag
  - 管理者がこのファイルを作成すると run_execution / run_monitoring は検出して停止します（外部停止フラグ）。

- data/kill.flag
  - KillSwitch がリスク超過時に生成するフラグ。ExecutionEngine 側で読み検出して安全停止します。

- data/execution.pid
  - 実行エンジンの PID を格納するファイル（run_execution で使用）。

- logs/
  - ログはアプリケーション名ごとに日次ローテーションで保存（例: logs/execution.log, logs/monitoring.log）。

---

## ディレクトリ構成（抜粋・主要ファイル説明）

- src/kabusys/
  - __init__.py
    - パッケージ初期化、バージョン定義
  - config.py
    - 環境変数読み込み/Settings クラス
    - 自動でプロジェクトルートの .env/.env.local を読み込む（無効化可）
  - config_setup.py
    - .env を対話式に作成するウィザード
  - validate_config.py
    - 起動前チェック CLI（必須環境変数や config/*.yaml の検証）
  - run_execution.py
    - ExecutionEngine 起動スクリプト
    - paper_trading モードの DB 分離・MockBroker 対応
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL で間隔を変更可能
  - utils/
    - logging_setup.py : ロギング初期化（console + TimedRotatingFileHandler）
    - process_priority.py : プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py : SQLite スキーマ初期化と簡易永続化クラス（MonitoringDB）
    - system_monitor.py : システムリソース / データ鮮度監視
    - risk_monitor.py : ドローダウン / ポジション上限監視
    - kill_switch.py : kill.flag の評価・書き込み
    - monitoring_engine.py : 各 Monitor を束ねるエンジン
    - alert_manager.py, trade_monitor.py 等（アラートや注文監視ロジック）
  - execution/
    - execution_engine.py, order_manager.py, risk_manager.py, reconciler.py, broker_factory.py, order_repository.py
    - Execution の主要コンポーネント（発注、リスク、照合）
  - portfolio/
    - portfolio_builder.py : 候補選定・重み計算
    - position_sizing.py : 株数決定・資金配分ロジック
    - risk_adjustment.py : セクターキャップ・レジーム乗数
  - research/
    - factor_research.py : モメンタム・バリュー・ボラティリティ等のファクター計算（DuckDB）
    - feature_exploration.py : 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py : OpenAI を用いたニュースセンチメント（ai_scores 書き込み）
    - regime_detector.py : ETF MA とマクロニュースで市場レジーム判定
    - __init__.py : export（score_news など）
  - tools/
    - paper_verification_report.py : Paper Trading の検証レポート生成ツール

（上記はこの README 作成時点の主要ファイルです。実際のリポジトリではさらに細かいモジュールが存在します）

---

## 開発・デバッグのヒント

- ロギング
  - setup_logging(app_name="...") を各起動スクリプトで呼び出しており、logs/<app_name>.log に出力されます。
  - 環境変数 LOG_DIR でログディレクトリを変更できます。

- Process Priority
  - run_* スクリプトは起動時に set_process_priority("high") を呼びます。権限不足で失敗すると警告ログのみ出ます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、必要に応じて簡易マイグレーション（カラム追加）を行います。

- AI 呼び出しテスト
  - news_nlp._call_openai_api / regime_detector._call_openai_api などはテスト時にモック差し替えが想定されています（unittest.mock.patch）。

---

## ライセンス / 注意点

- この README はコードスニペットに基づいてまとめたものです。実運用に入れる前に必ず validate_config を実行し、config/*.yaml や .env の内容を確認してください。
- 本コードは実際に発注を行うロジックを含むため、live 環境での実行は十分な確認のうえ行ってください（KABUSYS_ENV=live は慎重に）。
- .env に機密情報を保存するため、絶対に Git にコミットしないでください。

---

必要であれば、README にサンプル .env のテンプレート（最小構成）や systemd / cron の起動例、Dockerfile / docker-compose の雛形も追加できます。どの情報を追加しますか？