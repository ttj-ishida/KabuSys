KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買を目的とした軽量なプラットフォームです。  
主に以下を提供します。

- 環境設定の対話式ウィザード（.env 作成）
- 起動前の設定検証コマンド（環境変数 / config/*.yaml）
- ExecutionEngine によるシグナル駆動の発注フロー（本番 / ペーパートレード対応）
- ブローカー抽象化（MockBrokerClient / KabuStationClient）
- リスクガード（Gate1〜Gate3）、サーキットブレーカー、レート制限
- 起動時リコンシリエーション（OrderSent の復旧）
- 監視プロセス（SystemMonitor）によるリソース監視とログ保存
- データ機能（市場カレンダー管理、ニュース収集、DuckDB を用いた集計）

注: このリポジトリは実装の一部を抜粋した形です。実運用では kabuステーション API や J-Quants API の設定、適切な運用手順の整備が必要です。

主な機能
---------
- config_setup: .env を対話式に生成・更新するウィザード
- validate_config: .env と config/*.yaml の存在・妥当性チェック（--strict オプションあり）
- run_execution: ExecutionEngine を起動しシグナルに基づく発注実行（paper_trading / development / live）
- run_monitoring: SystemMonitor のポーリングループを実行して監視データを記録
- Broker 抽象層: create_broker_api により Mock または実実装（KabuStationClient）を選択
- Order 管理: OrderRecord（状態遷移）、OrderRepository（SQLite 永続化）、OrderManager（発注フロー）
- RiskManager: Gate1（余力/重複/ポジション上限）、Gate2（レート制限/CB）、Gate3（ドローダウン）
- Data モジュール: 市場カレンダー管理（DuckDB）、ニュース収集（RSS）

セットアップ手順
----------------
前提
- Python 3.9+（typing の一部機能や型注釈に依存）
- SQLite は標準ライブラリで同梱
- DuckDB（分析用 DB）を使用する場合は duckdb パッケージが必要

推奨インストール手順（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（実プロジェクトでは requirements.txt を参照）
   - pip install duckdb httpx websocket-client defusedxml pyyaml
     - pyyaml は config/*.yaml の構文チェックに使われます（未インストール時はチェックをスキップ）
     - defusedxml は RSS パースの安全化に使用
   - （本番連携時）kabu station の利用には適切な HTTP サーバ・API が必要

3. データディレクトリ作成
   - mkdir -p data

必須環境変数
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）

代表的な任意 / 上書き可能な環境変数（デフォルト値を併記）
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- LOG_LEVEL — default: INFO
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN — default: (空)
- LINE_USER_ID — default: (空)
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒） default: 60
- PAPER_FILL_MODE — paper_trading の mock 動作: instant|partial|never|reject default: instant
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 sqlite path default: data/paper_trading.db
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視 / 制御用）

自動 .env ロードについて
- プロジェクトルート（.git または pyproject.toml を起点）を探索し、.env/.env.local を自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（CLI）
--------------
1) 初期設定ウィザード（.env を作成/更新）
   - python -m kabusys.config_setup
   - 対話式に必要なキーを入力します。Enter で既存値/デフォルトを利用可能。
   - 完了後は .env が保存されます（保存前に確認プロンプトあり）。

2) 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit 1 になります。
   - config/*.yaml の文法チェックには PyYAML が必要（未インストール時はスキップされる）。

3) ExecutionEngine を起動（本番/ペーパーを環境変数 KABUSYS_ENV で切り替え）
   - 簡易実行（ペーパートレードの例）
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 実行時は data/execution.pid（PID）、data/kill.flag（停止フラグ）等を使用します。
   - 起動前に validate_config を推奨。

4) Monitoring を起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）。

注意点・運用メモ
- 本番環境（KABUSYS_ENV=live）では LINE の設定や kill flag の確認など追加チェックが走ります。
- run_execution は起動時に Reconciler による復旧（OrderSent の突合）を行います。
- PID ファイル・停止フラグを使った外部制御をサポートしています。
- Paper trading は実ブローカーと分離された SQLite（data/paper_trading.db）に記録します。
- KabuStationClient 実装は HTTP + WebSocket（websocket-client）を用いて kabu ステーションと連携します（実運用では kabuステーション の稼働が必須）。

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 以下の主要モジュール／ファイルです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings 定義（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 環境設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py           — BrokerAPI の Protocol / データモデル / ファクトリ
    - broker_factory.py       — Settings に基づくブローカ生成
    - kabu_client.py          — kabu station 実装（HTTP/WebSocket）
    - mock_client.py          — テスト用 Mock ブローカー
    - order_record.py         — Order の状態マシン（純粋ロジック）
    - order_repository.py     — SQLite 永続化レイヤ
    - order_manager.py        — 発注フローの高レベル API
    - execution_engine.py     — 発注エンジンのメイン実装
    - reconciler.py           — 起動時のリコンシリエーション
    - risk_manager.py         — Gate1/2/3 を提供するリスク評価
  - data/
    - calendar_management.py  — 市場カレンダー管理（DuckDB）
    - news_collector.py       — RSS ニュース収集・正規化
    - jquants_client.py       — （参照される想定の J-Quants クライアント）
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite スキーマ初期化・ログ保存（参照あり）
    - system_monitor.py       — 実際の監視ロジック（参照あり）
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度設定ユーティリティ

サンプル .env（主要項目）
-------------------------
以下は config_setup が生成する .env に含まれる主要キー（コメント抜粋）です。

JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

開発・テストのヒント
-------------------
- MockBrokerClient を使えば kabuステーション が無くても発注フローのテストが可能です（PAPER_FILL_MODE を調整）。
- .env の自動読み込みはプロジェクトルート探索に基づきます。CI などで意図的に無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config は起動前チェックで有用です。--strict を CI に組み込むことで警告も取りこぼさず失敗にできます。
- DuckDB を使った集計やカレンダー機能はデータの正確さに依存します。jquants_client による市場カレンダー更新ジョブ(calendar_update_job) を定期実行することを推奨します。

ライセンス・注意
----------------
この README に記載した内容はリポジトリ内のコードから読み取れる振る舞いの説明です。実際の運用で金銭のやり取り・発注を行う場合は、十分なテスト・監査・安全対策（誤発注対策、外部認証管理、秘密情報の取り扱い）を施してください。KabuSys 自体のライセンス情報はリポジトリのトップレベル（LICENSE 等）を参照してください。

問い合わせ・貢献
----------------
バグ修正や改善提案がある場合は Pull Request を送るか Issue を立ててください。README に記載漏れや補足が必要であればお知らせください。