README
======

概要
----
KabuSys は日本株の自動売買を想定した小型のフレームワークです。  
主な目的は、シグナルに基づく発注処理（ExecutionEngine）、発注状態管理、再起動時のリコンシリエーション、およびシステム監視を提供することです。  
モジュール設計により、実運用（kabuステーション連携）と開発/テスト（Mock ブローカー）を切り替えて利用できます。

主な特徴
--------
- 環境設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 発注エンジン（ExecutionEngine）
  - シグナルを読み取り Gate1/Gate2（リスクチェック）を通した発注
  - WebSocket push（kabu push）ドレイン処理
  - PID / 停止フラグ / Kill Switch のサポート
- 注文管理
  - OrderRecord（状態遷移の純粋ロジック）
  - SQLite による永続化（OrderRepository）
  - OrderManager：発注・同期・キャンセルのワークフロー（クラッシュ安全性設計）
  - Reconciler：起動時の OrderSent レコード照合とポジション差分検出
- ブローカークライアント
  - MockBrokerClient（テスト用、fill_mode 制御可）
  - KabuStationClient（kabuステーション REST / WebSocket）
  - create_broker_api() ファクトリで切替
- リスク管理（RiskManager）
  - Gate1: 余力 / 重複 / ポジション上限
  - Gate2: レート制限（トークンバケツ）とサーキットブレーカー
  - Gate3: ドローダウン監視（キルスイッチ発動）
- 監視ループ（run_monitoring）
  - SQLite + DuckDB を利用した監視データの収集・記録
- データ関連ユーティリティ
  - カレンダー管理（JPX 営業日判定、next_trading_day 等）
  - ニュース収集（RSS を正規化して raw_news に保存）
- ユーティリティ
  - ロギング設定、プロセス優先度設定など

セットアップ手順
--------------
前提:
- Python 3.10 以上を推奨（型注釈で | 演算子を使用）
- SQLite は標準ライブラリに含まれます。DuckDB 等の追加パッケージはインストールが必要です。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存関係をインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な外部パッケージ（例）:
     - pip install duckdb httpx websocket-client defusedxml
     - PyYAML を入れると config/*.yaml のパース検証が有効になります（pip install pyyaml）

4. 環境変数を作成
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env をプロジェクトルートに作成
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う任意・デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - LOG_LEVEL — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（本番では設定推奨）

5. 設定を検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict
   - PyYAML があると config/*.yaml の中身もパースチェックされます。

使い方（実行例）
----------------
- 実行エンジン（注文処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に data/kill.flag があると、KILL_FLAG_CLEAR_ON_START が 1 のときのみクリアして起動し、それ以外は起動を拒否します。
  - エンジンは data/execution.pid（デフォルト）に PID を書きます。停止は data/stop_requested.flag を作成することで安全停止できます。

- 監視ループ
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可能。デフォルト 60 秒。
  - 監視は常に本番用 sqlite_path を使用します（設定に依らず同じ DB を使う設計）。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成／更新できます。

- 設定検証
  - python -m kabusys.validate_config [--strict]

プロセス制御 / フラグ
-------------------
- 停止フラグ（サービス停止依頼）
  - data/stop_requested.flag を作成するとループを検知して優雅に停止します。
- Kill Switch
  - data/kill.flag の存在は実行を拒否または即時停止のトリガーになります（設定に依存）。
  - KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると、起動時に既存の kill.flag を自動でクリアする挙動になります（本番では 0 を推奨）。
- PID ファイル
  - デフォルト: data/execution.pid（ExecutionEngine）
  - PID ファイルの保存先は環境変数 PID_FILE_PATH で変更可能。

主要な環境変数（抜粋）
---------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 推奨 / 任意
  - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL — DEBUG|INFO|...（デフォルト INFO）
  - KABU_API_BASE_URL — kabu station API ベース URL
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知用
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading の fill モード（instant|partial|never|reject）

ディレクトリ構成（抜粋）
---------------------
（リポジトリの src/kabusys 以下を抜粋して示します）

- src/kabusys/
  - __init__.py
  - config.py                 — .env 自動読み込み / Settings クラス
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine を起動するスクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - execution/
    - __init__.py
    - broker_api.py           — Broker API の Protocol / データモデル / ファクトリ
    - kabu_client.py          — kabuステーション REST / WebSocket クライアント
    - mock_client.py          — MockBrokerClient（テスト用）
    - broker_factory.py       — Settings に応じたクライアント生成
    - order_record.py         — 注文状態と状態遷移ロジック
    - order_repository.py     — SQLite 永続化層
    - order_manager.py        — 発注フロー（create/send/sync/cancel）
    - reconciler.py           — 再起動時リコンシリエーション
    - execution_engine.py     — 実行エンジン（シグナル処理 / push ドレイン）
    - risk_manager.py         — 3 段階リスクガード
  - monitoring/
    - monitoring_db.py        — 監視 DB 初期化 / ログ関数（参照）
    - system_monitor.py       — 監視ロジック（参照）
  - data/
    - calendar_management.py  — JPX カレンダー管理ユーティリティ
    - news_collector.py       — RSS ニュース収集
  - utils/
    - logging_setup.py        — ロギング初期化ユーティリティ
    - process_priority.py     — プロセス優先度設定ユーティリティ

補足と運用メモ
--------------
- 設計上、OrderManager はクラッシュ耐性を考慮して二相的な永続化（OrderSent 前保存、broker_order_id の先行保存 等）を行います。Reconciler が再起動時に不確定状態を回復します。
- デフォルトでは paper_trading / development 環境で MockBrokerClient が使われるため、kabuステーションをローカルに用意しなくとも発注フローのテストが可能です。
- config/*.yaml（system_config.yaml 等）は設定ファイル群です。validate_config は存在チェックと（PyYAML があれば）パースチェックを行います。欠落している場合は警告が出ます。
- ログ設定やプロセス優先度は utils 配下のユーティリティで制御します。

ライセンス
---------
リポジトリに明示のライセンスファイルが含まれていない場合は、利用前にプロジェクト管理者に確認してください。

問い合わせ / 開発者向けメモ
-----------------------
- 開発・テストを行う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます（ユニットテスト等で便利）。
- 追加のスクリプト（例: scripts/generate_config.py）により config/*.yaml を生成する想定の箇所があります。該当スクリプトが存在する場合はそちらを利用して初期ファイルを用意してください。

以上。必要であれば README に記載するサンプル .env や起動コマンドの具体例（systemd ユニット、docker-compose など）を追記します。どの形式で追記したいか教えてください。