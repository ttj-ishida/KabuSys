# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
このドキュメントはコードベースに含まれるモジュール群を基に、セットアップ手順・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。  
主に次の責務を持ちます：

- ブローカー（kabuステーション等）への発注・照合（Execution 層）
- 注文状態の永続化（SQLite）
- シグナルの読み出し・発注ロジック（DuckDB）
- 3段階のリスクガード（Gate1/2/3）
- 起動時のリコンシリエーション（再同期）と監視（Monitoring）
- .env を用いた設定管理と対話式セットアップウィザード

設計方針は「DB と API 呼び出しを分離」「クラッシュからの復旧（Reconciliation）」「発注安全性の優先」です。

---

## 機能一覧

- 環境設定ウィザード（.env の生成 / 更新）
  - python -m kabusys.config_setup
- 起動前の設定検証ツール（.env と config/*.yaml をチェック）
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱い
- 発注エンジン（ExecutionEngine）
  - シグナル読込 → Gate1/2（リスクチェック）→ 発注 → Push ドレイン
  - Paper trading（MockBrokerClient）対応
  - kill.flag による安全停止、PID ファイル管理
- ブローカークライアント
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabuステーション REST / WebSocket クライアント）
- 注文永続化（SQLite）
  - OrderRepository（orders テーブル管理、永続化）
  - OrderRecord（状態遷移ロジック）
- リスク管理（RiskManager）
  - Gate1: 余力・重複・ポジション上限
  - Gate2: レート制限・サーキットブレーカー
  - Gate3: ドローダウン監視（約定後）
- 起動時リコンシリエーション（Reconciler）：OrderSent の突合せ、ポジション差分ログ
- 監視ループ（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL で間隔指定（デフォルト 60秒）
- データ処理補助
  - マーケットカレンダー管理（next_trading_day 等）
  - RSS ニュース収集（安全対策を施した実装）

---

## 前提 / 必要環境

- Python 3.10 以上（型注記に「|」表記を使用）
- 標準ライブラリ：sqlite3, logging, threading 等
- 推奨外部パッケージ（機能に応じて）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（config/*.yaml のパース検証用、未インストール時は検証スキップ）
  - defusedxml（RSS パース用）

例（仮）:
pip install duckdb httpx websocket-client pyyaml defusedxml

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
   - python -m venv .venv
   - source .venv/bin/activate （Windows は .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   - または必要なパッケージを個別に pip install

3. .env を作成する（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env の既存値を読み込み、対話的に入力できます
   - ウィザードで生成した .env は決して Git にコミットしないでください

4. 設定検証を実行
   - python -m kabusys.validate_config
   - 警告も失敗扱いにするには --strict を付ける

5. （任意）DB 初期化は各起動スクリプトが必要に応じて行います
   - run_execution/run_monitoring 実行時に monitoring DB 初期化等が呼ばれます

---

## 使い方（主要コマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - オプション: --env-file で保存先を指定

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（本番・ペーパートレード）
  - python -m kabusys.run_execution
    - KABUSYS_ENV によってペーパートレード（MockBrokerClient）か本番が切替
    - paper_trading の場合は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
    - 実行中は PID ファイル、停止には data/stop_requested.flag を作成
    - 起動前に data/stop_requested.flag が存在する場合、起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動クリア）

- 監視ループ
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能
    - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依らず）

- 重要な環境変数（一部）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB デフォルト data/monitoring.db）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番での通知に使用）
  - KILL_FLAG_CLEAR_ON_START（0/1、本番での kill.flag 自動クリア）

---

## 動作モードについて

- development
  - ローカル開発向け。MockBrokerClient（発注せず）を使用することが想定されます。

- paper_trading
  - 発注ロジックを検証するためのペーパートレードモード。MockBrokerClient を用い、paper 用 SQLite に記録します。

- live
  - 実際のブローカーに発注する本番モード（注意: 本実装では Live broker client は未実装の箇所があります。必ず設定を確認してください）。
  - KABUSYS_ENV=live の場合は追加の安全チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START）に注意が必要です。

---

## 注意事項 / トラブルシュート

- .env は決してリポジトリにコミットしないでください。
- validate_config は PyYAML が無いと YAML 内容検証をスキップします（警告を出します）。
- DUCKDB_PATH / SQLITE_PATH の親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、事前に作成してパーミッションを確認してください。
- run_execution/run_monitoring は起動時に PID ファイルや stop flag を扱います。停止したい場合は data/stop_requested.flag を作成してください。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、config モジュールによる .env 自動ロードを無効化できます（テスト向け）。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル・モジュールと役割の一覧（本リポジトリの抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（settings = Settings()）
    - .env 自動ロード（プロジェクトルート判定あり）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI（必須環境変数・config/*.yaml 等）
  - run_execution.py
    - ExecutionEngine の起動スクリプト（PID / stop flag 管理）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - execution/
    - broker_api.py
      - BrokerAPIProtocol, データモデル（OrderRequest, Position, ...）、例外、ファクトリ
    - kabu_client.py
      - KabuStationClient（httpx + WebSocket 実装）
    - mock_client.py
      - MockBrokerClient（fill_mode で挙動を制御）
    - broker_factory.py
      - Settings に応じたブローカークライアント生成
    - execution_engine.py
      - ExecutionEngine（シグナル処理・push ドレイン・kill switch 等）
    - order_record.py
      - OrderRecord（状態遷移ロジック）
    - order_repository.py
      - SQLite による永続化層（orders テーブル DDL と CRUD）
    - order_manager.py
      - OrderManager（OrderRecord + OrderRepository を用いた外向き API）
    - reconciler.py
      - Reconciliation（OrderSent 照合、ポジション差分検出）
    - risk_manager.py
      - RiskManager（Gate1/2/3 実装）
  - data/
    - calendar_management.py
      - JPX カレンダー管理（is_trading_day / next_trading_day 等）
    - news_collector.py
      - RSS ニュース収集（セキュア実装）
  - monitoring/
    - monitoring_db.py (参照される)
    - system_monitor.py (参照される)
  - utils/
    - logging_setup.py (参照される)
    - process_priority.py (参照される)

（上記はリポジトリの一部抜粋です。実際のファイル構成はリポジトリのツリーをご確認ください）

---

## 開発者向け補足

- 注文の永続化は SQLite の orders テーブルで行い、同一 signal_id の active 注文を部分ユニークインデックスで保護しています。
- 発注フローはクラッシュ安全性を配慮した2相的な永続化を行っています（OrderSent を先に保存→API呼び出し→broker_order_id を保存→OrderAccepted に遷移等）。
- Reconciler は起動時に OrderSent の注文を照合し、必要に応じて状態を復元／ポジション差分をログ出力します。
- RiskManager はサーキットブレーカー、レート制限（トークンバケツ）、ポジション／利用率上限、ドローダウン監視を組み合わせて安全性を確保します。

---

もし README に追記したい具体的な項目（例: sample .env.example、requirements.txt、デプロイ手順、詳細な CLI オプション説明など）があれば教えてください。必要に応じて追記・整形します。