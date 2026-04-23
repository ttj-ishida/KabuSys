# KabuSys

日本株向け自動売買システム（KabuSys）の簡易ドキュメントです。  
このリポジトリは、シグナルに基づく発注エンジン、監視ループ、設定ウィザード／検証ツール、データ収集・カレンダー管理等を含みます。

> バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群から構成される自動売買システムです。

- 設定管理（.env / 環境変数）と設定ウィザード
- 設定検証 CLI（起動前に環境不備を検出）
- 発注エンジン（ExecutionEngine） — シグナル取得 → リスク検査 → 発注
- ブローカー API 抽象（実装: MockBrokerClient / KabuStationClient）
- 注文永続化（SQLite）と状態遷移ロジック（OrderRecord）
- リコンシリエーション（Reconciler）によるクラッシュ後復旧
- 監視プロセス（SystemMonitor からのポーリング）
- データ系ユーティリティ（DuckDB ベースのカレンダー管理、ニュース収集 等）

設計方針として、ビジネスロジックと永続化／API 層は明確に分離されており、テスト用のモッククライアントを用いて本番接続なしで検証可能です。

---

## 主な機能一覧

- .env 対話ウィザード（kabusys.config_setup）
  - .env の対話的作成・更新を支援
- 設定検証（kabusys.validate_config）
  - 必須環境変数チェック、config/*.yaml の存在/パース確認、運用環境チェック等
  - --strict モードで警告も失敗扱いにできる
- 発注エンジン（kabusys.run_execution / ExecutionEngine）
  - シグナル取得（DuckDB）→ Gate1/2（RiskManager）→ 発注（OrderManager）→ push ドレイン
  - Paper Trading（MockBrokerClient）と Live（将来対応）の分離
  - リコンシリエーション（起動時に OrderSent の不確定注文を同期）
- 注文管理
  - OrderRecord（状態遷移の検証）・OrderRepository（SQLite 永続化）
  - 安全な二相的永続化等、クラッシュ時の整合性を考慮したフロー
- 監視ループ（kabusys.run_monitoring）
  - SystemMonitor のポーリングループ（SQLite + DuckDB を使用）
- データ関連
  - カレンダー管理（jquants 連携、DuckDB の market_calendar）
  - ニュース収集（RSS、正規化、SSRF 対策 等）

---

## セットアップ手順

以下はローカルで動かすための最小手順例です（環境に応じて調整してください）。

1. リポジトリを取得
   - git clone ... / ダウンロード

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必須/推奨ライブラリ（実行機能に応じて必要）
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（config YAML のパース検証に必要）
   - 例:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

   > 注意: requirements.txt はプロジェクトに含める想定ですが、無い場合は上記を個別にインストールしてください。

4. .env の初期作成
   - 対話ウィザードを実行:
     - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークンや kabuAPI パスワード等を設定します。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. DB 初期化（Execution / Monitoring を動かす前に）
   - 実行スクリプトが起動時に必要テーブルを作成する処理を呼んでいますが、必要に応じて手動で SQLite / DuckDB ファイルの親ディレクトリを作成してください（デフォルト: data/）。

---

## 主要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — execution 環境 (development | paper_trading | live)。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知設定
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1、デフォルト 0）

Settings クラス（kabusys.config.Settings）はこれらをラップしており、プロパティ経由でアクセスできます。

---

## 使い方（実行例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗）:
    - python -m kabusys.validate_config --strict

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading または development の場合は MockBrokerClient を使用（安全）
    - live は現在 NotImplementedError（明示的に未実装）

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - export MONITOR_POLL_INTERVAL=30  # 例: 30秒

- 停止フラグ／PID
  - 停止を伝えるファイル: data/stop_requested.flag — 存在するとループが終了します
  - kill.flag によりエンジンは起動を拒否または kill_switch を発動します（設定に依存）
  - PID ファイル: data/execution.pid（デフォルト）等

---

## 重要な挙動・運用メモ

- ExecutionEngine の起動フローでは、起動時に Reconciler（設定時）で OrderSent の不確定注文をブローカーと同期し、ポジション差分を検出します。これによりクラッシュ復旧が容易になります。
- OrderManager の send_order はクラッシュ耐性を重視した永続化順序（OrderSent を先に保存 → ブローカー呼び出し → broker_order_id を保存 → OrderAccepted）を採用しています。
- RiskManager は Gate1（余力・重複・ポジション上限）/ Gate2（レート制限・サーキットブレーカー）/ Gate3（ドローダウン）を実装しています。
- MockBrokerClient は fill_mode オプションを持ち（instant/partial/never/reject）テスト用に約定シミュレーションが可能です。
- 本番運用時は KABUSYS_ENV=live の設定に注意。validate_config や config_setup は live を選択した場合に警告を出します（LINE 通知設定や Kill Switch 設定など）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / .env ロードと Settings クラス
- config_setup.py — .env 対話ウィザード CLI
- validate_config.py — 起動前の設定検証 CLI

- run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
- run_monitoring.py — Monitoring 起動スクリプト（エントリポイント）

- execution/
  - __init__.py — execution パッケージの公開 API
  - broker_api.py — BrokerAPIProtocol, データモデル, 例外, ファクトリ
  - broker_factory.py — Settings に基づくブローカークライアント生成
  - kabu_client.py — KabuStationClient（HTTP/WebSocket 実装）
  - mock_client.py — MockBrokerClient（テスト用）
  - order_record.py — OrderRecord データモデルと状態遷移
  - order_repository.py — SQLite を用いた永続化
  - order_manager.py — 外向け注文 API（create/send/sync/cancel）
  - execution_engine.py — ExecutionEngine（シグナル処理 / push ドレイン /セッション制御）
  - reconciler.py — 起動時リコンシリエーション
  - risk_manager.py — 3 段階リスクガード

- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB + J-Quants）
  - news_collector.py — RSS ニュース収集（正規化・SSRF 対策）

- monitoring/ (監視関連: DB 初期化・SystemMonitor 等) — run_monitoring が使用

（その他、utils や monitoring 周りのモジュールが含まれます）

---

## トラブルシューティング

- validate_config がエラーを返す
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の設定を確認
  - config/*.yaml が存在しない場合は警告が出る（scripts/generate_config.py 等の利用を想定）
  - PyYAML 未インストール時は YAML の内容検証をスキップ（警告）

- ExecutionEngine が kill.flag により起動拒否される
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアします（ただし本番では推奨されません）

- ブローカー接続エラー
  - paper_trading / development では MockBrokerClient を使用する設定を推奨（設定は BrokerClientFactory）
  - 実ブローカー接続（KabuStationClient）を使う場合は kabuステーション アプリの起動と API パスワード / base_url を確認

---

## 参考コマンド一覧

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行（ローカル / テスト）:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

---

必要に応じて、この README をプロジェクトの実状（requirements.txt の有無、本番運用手順、CI 設定等）に合わせて補完してください。