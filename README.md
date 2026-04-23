# KabuSys

日本株自動売買システムのコアライブラリ（開発中 / 部分的にモック実装あり）。

このリポジトリは発注エンジン、リスクガード、監視、データ収集（カレンダー・ニュース）などの主要コンポーネントを含み、ローカル開発・ペーパートレード・本番運用を想定した設計になっています。

---

## 概要

- 発注フローは Signal Queue をプルして OrderManager 経由でブローカーへ送信し、OrderRecord（状態遷移ロジック）と OrderRepository（SQLite 永続化）で管理します。
- リスク管理は 3 段階（Gate1: シグナル、Gate2: 実行、Gate3: メトリクス）で実装されています。
- 本番接続用の KabuStationClient（kabu ステーション REST API）と、テスト用の MockBrokerClient（ペーパートレード／開発用）が用意されています。
- DuckDB を分析・シグナル読み込み用に、SQLite を監視・注文履歴用に使用します。
- .env（環境変数）と config/*.yaml による設定管理、対話式の .env 作成ウィザード、起動前検証ツールを備えています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml のチェック）
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動スクリプト
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて MockBrokerClient を使用（paper_trading / development）
- 監視（SystemMonitor）ポーリングループ起動スクリプト
  - python -m kabusys.run_monitoring
- 発注ロジック
  - OrderRecord（状態遷移）、OrderRepository（SQLite 保存）、OrderManager（送信・同期・キャンセル）
- ブローカーAPI 層
  - BrokerAPIProtocol、KabuStationClient（httpx）、MockBrokerClient
- リスクマネジメント
  - Rate limit（トークンバケツ）、Circuit Breaker、ポジション / 利用率チェック、ドローダウン監視
- リコンシリエーション（起動時自動復旧）
- データモジュール
  - マーケットカレンダー管理（DuckDB + J-Quants 連携）
  - ニュース収集（RSS → raw_news）
- ユーティリティ（ログ設定、プロセス優先度制御 など）

---

## 前提 / 依存関係

- Python 3.10 以上（PEP 604 の | 型注釈を使用しているため）
- ライブラリ（代表例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml の内容チェックに使用。未インストールでも検証はスキップされる）
- 標準ライブラリ: sqlite3, threading, logging 等

インストール方法はプロジェクトに requirements.txt がある前提で：
```
python -m pip install -r requirements.txt
```
個別に開発環境へインストールする場合は上のパッケージを pip で追加してください。

---

## セットアップ手順

1. リポジトリをクローン / 配置
2. 仮想環境を作成して有効化（任意）
3. 依存パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードで作成するのが簡単です：
     ```
     python -m kabusys.config_setup
     ```
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他の主な環境変数（省略可／デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラートに必要
     - PAPER_FILL_MODE — ペーパートレードの埋まる挙動（instant | partial | never | reject）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

5. 起動前に検証
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```
   - PyYAML があれば config/*.yaml のパース検証を行います。無い場合は YAML 検証をスキップし警告を出します。

6. データベース初期化
   - Execution / Monitoring 起動時に自動的にテーブル作成（init_monitoring_db / init_orders_db 等）を呼び出す箇所があります。明示的に初期化したい場合はそれらの関数を呼んでください。

---

## 使い方（実行例）

- 設定ウィザード（.env の作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（発注）起動
  - 開発 / ペーパートレード:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 実行中に /data/stop_requested.flag を作成すると停止処理が動きます（stop フラグ）。
  - PID ファイル: data/execution.pid（デフォルト）

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- プログラム内で設定を参照
  ```py
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  duckdb_path = settings.duckdb_path
  ```

- Mock クライアントを使ったテスト
  - BrokerFactory 経由で MockBrokerClient が生成されます（KABUSYS_ENV=development/paper_trading）。
  - Mock の挙動は PAPER_FILL_MODE によって変化します（instant/partial/never/reject）。

---

## 運用上の注意

- KABUSYS_ENV=live の場合は本番用の設定（LINE通知や Kill Switch など）を慎重に確認してください。validate_config は live を検出すると警告を出します。
- kill.flag（settings.kill_flag_path）によって起動拒否や即時停止の制御を行います。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアしますが、本番では 0 を推奨します。
- OrderManager の発注フローはクラッシュ耐性を考慮して部分永続化（OrderSent の永続化、broker_order_id の先行保存）する設計になっています。Reconciler が起動時に不整合を修復します。
- config/*.yaml はプロジェクト設定用（存在しない場合は警告）。scripts/generate_config.py（リポジトリ内に存在するなら）でテンプレート生成可能としています。

---

## ディレクトリ構成 (簡易)

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み / Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py — Broker API のデータモデル・Protocol・例外・ファクトリ
    - kabu_client.py — KabuStationClient（実ブローカー用）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づくクライアント生成
    - order_record.py — Order の状態遷移ロジック
    - order_repository.py — SQLite 永続化レイヤ
    - order_manager.py — 発注フロー（create/send/sync/cancel）
    - execution_engine.py — セッション（シグナル処理 + push ドレイン）
    - reconciler.py — 起動時リコンシリエーション
    - risk_manager.py — Gate1/2/3 のリスクチェック
    - ...（他の execution 関連モジュール）
  - data/
    - calendar_management.py — マーケットカレンダー（J-Quants 連携）
    - news_collector.py — RSS ニュース収集
    - jquants_client.py — （外部ファイル、J-Quants API 用クライアント想定）
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化 / ログ記録（参照されている）
    - system_monitor.py — SystemMonitor（ポーリング処理）
  - utils/
    - logging_setup.py — ログ初期化ヘルパ
    - process_priority.py — プロセス優先度設定ヘルパ
  - scripts/（オプション）
    - generate_config.py — config/*.yaml を生成するヘルパ（validate_config の警告参照）

※ 実際のファイル構成はリポジトリのルートを参照してください。上記はこの README に含まれる主要モジュールの抜粋です。

---

## 開発メモ / 拡張ポイント

- Live ブローカークライアント（KabuStationClient） は既に実装されていますが、BrokerClientFactory は本番クライアントを未実装（例外）にしている箇所があります。実運用ではここを有効にしてください。
- YAML 構成ファイルのスキーマ検証を強化すると運用が楽になります（現在は PyYAML の safe_load によるパースチェックのみ）。
- テスト用に MockBrokerClient の挙動を活用し、ExecutionEngine / OrderManager の統合テストを書くと良いです。

---

必要であれば README にサンプル .env のテンプレートや簡単な diagrama（発注フロー図）、さらに詳細な API 使用例を追加できます。どの情報を補足しますか？