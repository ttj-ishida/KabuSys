# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ＋起動スクリプト群）。  
この README はリポジトリ内の主要コンポーネントの概要、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群を提供します。主な機能は以下の通りです：

- 注文実行エンジン（ExecutionEngine）
- 監視（Monitoring）・アラート・Kill Switch
- ポートフォリオ構築（銘柄選定・重み計算・株数決定）
- リサーチ（ファクター計算、特徴量解析）
- AI（ニュースのNLPスコアリング、レジーム判定）による補助機能
- Paper Trading（ペーパートレード）向け分離DBサポート
- 各種ユーティリティ（ログ設定、プロセス優先度設定等）
- 運用支援ツール（設定ウィザード、設定検証、検証レポート生成）

設計方針として「本番データへの不要なアクセスを避ける」「ルックアヘッドバイアス防止」「フェイルセーフ」を重視しています。

---

## 機能一覧（抜粋）

- 起動スクリプト
  - run_execution.py — 実際の ExecutionEngine を起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py — SystemMonitor を定期ポーリングで実行
- 設定管理
  - config.py — 環境変数/.env 読み込み、Settings クラスを提供
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前チェック（必須環境変数・config yaml 等）
- 監視
  - monitoring/monitoring_db.py — SQLite ベースの永続化層（schema マイグレーション含む）
  - monitoring/system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager（通知関連）
- 注文・実行
  - execution/* — ブローカークライアント生成、OrderManager、ExecutionEngine、Reconciler、RiskManager 等（実行ロジック）
- ポートフォリオ
  - portfolio/* — 候補選定、重み計算、リスク調整、ポジションサイズ計算
- リサーチ
  - research/* — ファクター計算（momentum/value/volatility）、特徴量探索、IC 計算等（DuckDB を使用）
- AI
  - ai/news_nlp.py — OpenAI を使ったニュースセンチメント集約＆スコア保存（ai_scores）
  - ai/regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- ツール
  - tools/paper_verification_report.py — Paper Trading 検証レポート生成
- ユーティリティ
  - utils/logging_setup.py — 統一的なログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py — プラットフォームに依存しないプロセス優先度 / CPU affinity 設定

---

## 要件（主な依存ライブラリ）

推奨 Python バージョン: 3.9+（型注釈やライブラリ互換を想定）

主な依存パッケージ（例）:
- duckdb
- psutil
- openai
- （任意）PyYAML — validate_config で config/*.yaml の検証を行う場合

requirements.txt はリポジトリに無い可能性があるため、手動でインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows Powershell: .venv\Scripts\Activate.ps1)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 必要に応じて他パッケージも追加
4. ディレクトリ作成（最小限）
   - mkdir -p data logs
5. 環境変数設定
   - 対話式に .env を作る: python -m kabusys.config_setup
   - もしくは .env を手動作成（下記「重要な環境変数」を参照）
6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題があれば修正してください

---

## 重要な環境変数（主なもの）

（config_setup.py で扱うキーを抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API を使う機能（ai/news_nlp, ai/regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用専用 SQLite（default: data/paper_trading.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live
  - paper_trading のとき run_execution は MockBrokerClient を使い paperDB を使用
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL
- KILL_FLAG_CLEAR_ON_START — 本番での自動 kill.flag クリアを防ぐため通常は 0

自動 .env ロード:
- デフォルトでプロジェクトルートの .env（および .env.local）を自動読込します。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

その他ランタイム変数:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — MockBroker のフィルモード（instant/partial/never/reject）

---

## 使い方（主要コマンド例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

- ExecutionEngine 起動（実運用／ペーパートレード共通）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使用し、PAPER_TRADING_SQLITE_PATH を使用します

- Monitoring 起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でループ間隔を秒単位で上書き可（デフォルト 60）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または --db で DB ファイルを直接指定

- AI モジュール実行（例）
  - ai.news_nlp.score_news(conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)

（注）多くのモジュールはライブラリとして呼び出すことを想定しており、単体で直接実行する CLI がない場合があります。上記は主要なエントリポイント例です。

---

## ログ・データ・停止制御

- ログ
  - デフォルトで stdout に StreamHandler を出力し、logs/<app_name>.log に日次ローテーションで出力します。
  - ログディレクトリは LOG_DIR 環境変数で上書き可能。

- データベース
  - DuckDB: DUCKDB_PATH（分析用）
  - SQLite: SQLITE_PATH（監視用）、PAPER_TRADING_SQLITE_PATH（ペーパートレード専用）

- 停止制御 / Kill Switch
  - 実行中のエンジンは data/stop_requested.flag を検知して graceful に停止します（run_execution/run_monitoring 上でチェック）。
  - KillSwitch は監視結果により data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。Kill フラグは明示的にクリアする必要があります（Settings.kill_flag_clear_on_start=1 の場合は起動時に自動クリアされますが、本番では無効を推奨）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール構成（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装ファイルがある想定)
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/ (実行時に生成される想定)
  - logs/ (実行時に生成される想定)

（注）上記はサンプル抜粋です。実際のファイル数・構成はリポジトリ全体を参照してください。

---

## 開発者向けメモ

- データ参照と本番リスク
  - research/ や ai/ モジュールは原則として DB のデータを参照するのみで、発注 API にアクセスしない旨が設計に明記されています。
- DuckDB と SQLite の使い分け
  - 分析向け（時系列/ファクター）には DuckDB を使用。監視・発注ログ等の永続化は SQLite を使用（monitoring.db / paper_trading.db）。
- テスト
  - OpenAI 呼び出し部分はテスト容易性のため _call_openai_api を patch 可能にしてあります。
- ロギング
  - 全エントリポイントで utils.logging_setup.setup_logging を呼んで統一したログ出力を行ってください。
- マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB に対する簡単なマイグレーション（列追加）を含みます。

---

## よくある操作例

- デフォルト設定で監視だけ動かす（ローカル）
  - KABUSYS_ENV=development python -m kabusys.run_monitoring

- ペーパートレードでエンジンを動かす（Mock Broker）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Kill Switch 手動クリア（開発）
  - rm data/kill.flag

---

もし README に追加してほしい内容（例: 各 CLI の詳細なオプション、API ドキュメント、ユニットテストの実行方法、依存関係ファイルの追加など）があれば教えてください。必要に応じてサンプル .env テンプレートや systemd / supervisor 用の起動ユニット例も用意できます。