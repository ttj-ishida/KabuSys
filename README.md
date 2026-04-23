# KabuSys

日本株向けの自動売買システム（ミニマル実装）。  
このリポジトリには、発注エンジン・リスクガード・監視ループ・設定ウィザード等の主要コンポーネントが含まれます。設計は「現場で安全に動かす」ことを重視しており、paper_trading（モック）モードを使った開発/テストが可能です。

---

## 概要

- 発注フローは Signal Queue を引いて発注する Pull 型（ExecutionEngine）。
- 発注のクラッシュ安全性（2 相永続化）や再起動時のリコンシリエーション機構を備えています。
- 3 段階のリスクガード（Gate1: シグナル単位、Gate2: レート制限/サーキットブレーカー、Gate3: ドローダウン監視）を提供。
- kabu ステーションの実 API を使うクライアント（KabuStationClient）と、テスト用の MockBrokerClient を両方サポート。
- 環境設定ウィザード(.env の生成)、設定検証 CLI、監視ループ、実行ループの起動スクリプトを同梱。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env の対話式生成・更新
- 設定検証ツール（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在や基本整合性チェック
  - --strict オプションで警告を FAIL 扱いに
- 実行エンジン（python -m kabusys.run_execution）
  - Signal 処理（発注）および WebSocket push ドレイン
  - Paper trading（MockBrokerClient）対応
  - PID / kill flag の管理、停止フラグ検出
- 監視ループ（python -m kabusys.run_monitoring）
  - SystemMonitor のポーリングループ
  - MONITOR_POLL_INTERVAL で間隔上書き可能
- ブローカークライアント層
  - KabuStationClient（実環境、httpx + websocket）
  - MockBrokerClient（テスト・開発用、fill_mode の切替可）
- 注文永続化／状態管理
  - SQLite に orders テーブルを保持（OrderRepository）
  - OrderRecord（状態遷移検証）
  - OrderManager（DB と broker を繋ぐ上位 API）
- リコンシリエーション（Reconciler）
  - 再起動時に OrderSent レコードとブローカー状態を突合
- データユーティリティ
  - マーケットカレンダー管理（DuckDB）
  - ニュース収集モジュール（RSS 収集と前処理）

---

## 必要条件

- Python 3.9+（typing | Path 等を利用）
- 推奨: 仮想環境（venv 等）
- 依存ライブラリ（例）
  - httpx, websocket-client, duckdb, defusedxml, PyYAML（YAML 検証を行う場合）
- OS 権限: プロセス優先度変更等で管理者権限が必要になることがあります（環境依存）。

（実際の requirements.txt はプロジェクトに含めている想定です。未定の場合は主要ライブラリを手動で pip install してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ※ YAML の内容検証を使う場合は PyYAML をインストールしてください:
     - pip install pyyaml
4. .env を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - あるいは .env.example をコピーして編集（存在する場合）
5. 設定検証（必須）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict
6. DB 初期化（必要箇所で自動作成されます）
   - SQLite / DuckDB の親ディレクトリが無ければ自動作成されますが、権限等を確認してください。

注意: 自動で .env をロードする仕組みがデフォルトで有効です（OS 環境 > .env.local > .env の順に読み込み）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

オプション（代表）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB (SQLite) のパス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

細かい既定値や検証ルールは kabusys.config.Settings および validate_config に実装されています。validate_config は PyYAML があれば config/*.yaml のパース検証も行います。

---

## 使い方（コマンド）

- 環境設定ウィザード（.env を対話的に作る）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告もエラー扱い）
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（通常は systemd / supervisor 等で起動）
  - python -m kabusys.run_execution
  - 動作モード: KABUSYS_ENV に従い paper_trading / development は MockBrokerClient を使用

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書きする:
    - export MONITOR_POLL_INTERVAL=30

- テスト／開発
  - MockBrokerClient を使ってユニットテストや統合テストを行えます（paper_trading モード）。

停止制御:
- 停止フラグファイル data/stop_requested.flag が存在すると監視・実行ループは停止します。
- kill.flag（デフォルト: data/kill.flag）は ExecutionEngine の kill_switch に関連する安全機構です。KILL_FLAG_CLEAR_ON_START 環境変数で起動時の自動クリアを制御します（本番では 0 推奨）。

---

## 実装ノート（重要な挙動）

- 発注の永続化は SQLite（orders テーブル）で行います。OrderManager は「OrderCreated → OrderSent の DB 永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新」の順で処理し、クラッシュ後の復旧に強く設計されています。
- Reconciler は起動時に OrderSent の注文をブローカーへ照合し、状態を復旧します。
- RiskManager は 3 層のガードを持ち、サーキットブレーカーやレート制限、ドローダウン検知を行います。
- KabuStationClient は HTTP API と WebSocket push をサポートし、トークンの自動再取得や 401 リトライ、429 レート制限判定を実装しています。
- MockBrokerClient は paper_trading や unit test 向けに fill_mode（instant/partial/never/reject）を切替可能です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数ロード / Settings（アプリ設定）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py — execution 層の公開インターフェース
    - broker_api.py — ブローカー API のデータモデル / Protocol / ファクトリ
    - broker_factory.py — Settings に基づくクライアント生成
    - kabu_client.py — KabuStationClient（実際の REST / WebSocket 実装）
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — OrderRecord（状態遷移ロジック）
    - order_repository.py — SQLite 永続化（orders テーブル）
    - order_manager.py — 発注フローの上位 API（DB と broker を結合）
    - execution_engine.py — ExecutionEngine（セッションロジック）
    - reconciler.py — 再起動時リコンシリエーション
    - risk_manager.py — 3段階リスクガード
    - ...（その他補助モジュール）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集
    - ...（jquants_client 等想定）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル初期化 / ログ関数（参照されている）
    - system_monitor.py — SystemMonitor 実装（参照されている）
  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

（上記はコードベース内の主要モジュールを抜粋した説明です）

---

## 開発・テストのヒント

- paper_trading / development 環境では MockBrokerClient を使用してネットワーク依存を排除できます（settings.paper_fill_mode で約定動作を制御）。
- 設定を変更したら、まず python -m kabusys.validate_config でチェックしてください。
- DB スキーマ作成関数（init_orders_db / init_monitoring_db）は起動時に呼ぶか、テストで明示的に呼び出してスキーマを用意してください。
- WebSocket push を使う場合、KabuStationClient.stream_push はブロッキングメソッドとして別スレッドで実行する設計です。

---

必要であれば README に次を追加できます:
- 具体的な .env のサンプル（秘匿値はマスク）
- requirements.txt の具体的な推奨バージョン
- systemd / supervisor 用のサービスユニット例
- テスト実行方法（pytest 等）

ご希望あれば上記追加情報を含めた拡張版 README を作成します。