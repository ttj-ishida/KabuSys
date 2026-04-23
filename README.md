# KabuSys

日本株向け自動売買システムのコードベース（読み取り用ドキュメント）。  
この README はプロジェクトの概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、kabuステーション等のブローカー API を用いた日本株自動売買のための実装群です。  
主な責務は以下の通りです。

- 環境変数 / 設定の読み込み・管理（.env 自動読み込み）
- 発注エンジン（ExecutionEngine）によるシグナルの処理と発注実行
- 発注の状態管理（OrderRecord / OrderRepository / OrderManager）
- ブローカークライアントの抽象化（実運用クライアントと Mock クライアント）
- リスク管理（3 段階のガード: Gate1/2/3）
- 再起動時のリコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor 用の polling ループ）
- データ周り：マーケットカレンダーやニュース収集などのユーティリティ

本リポジトリはライブラリ的に分割され、CLI スクリプト（パッケージとして実行可能）をいくつか備えています。

---

## 主な機能一覧

- 環境設定ウィザード（.env を対話式に生成 / 更新）
- 設定検証 CLI（.env と config/*.yaml の事前チェック）
- ExecutionEngine：signal → order のワークフロー（発注・同期・キャンセル・監視）
- OrderState を表す順序定義と状態遷移ロジック（OrderRecord）
- SQLite による注文永続化（OrderRepository）
- ブローカー API 抽象化（BrokerAPIProtocol）と Mock 実装（テスト用）
- リスク制御（余力チェック、ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視）
- リコンシリエーション機能（起動時に OrderSent の注文をブローカーと突合）
- 監視プロセス（SystemMonitor ポーリングループ）
- データユーティリティ（マーケットカレンダー、RSS ニュース収集 等）

---

## 必要条件（概要）

- Python 3.10 以上（型アノテーションや union 型 `|` を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config YAML のパース検証に任意）
- SQLite は標準ライブラリに含まれます。

（requirements.txt が用意されている場合はそちらを利用してください）

---

## セットアップ手順（開発 / ローカル実行）

1. リポジトリを取得
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   最低限（例）:
   ```
   pip install duckdb httpx websocket-client defusedxml
   ```
   PyYAML をインストールすると `python -m kabusys.validate_config` の YAML 検証が有効になります:
   ```
   pip install pyyaml
   ```

4. .env の作成
   対話式ウィザードで .env を生成できます:
   ```
   python -m kabusys.config_setup
   ```
   ウィザード実行後は `.env` がプロジェクトルートに保存されます（Git 管理対象外にしてください）。

5. 設定の検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いで exit(1) になります:
   ```
   python -m kabusys.validate_config --strict
   ```

---

## 主要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/設定項目:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL（kabu station のベース URL）
- LINE_CHANNEL_ACCESS_TOKEN（本番での通知）
- LINE_USER_ID（本番での通知）
- PAPER_FILL_MODE（paper_trading 用: instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1）

.env の優先読み込み順:
- OS 環境変数 > .env.local > .env

自動ロードはデフォルトで有効。テスト等で無効化するには:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

サンプル（.env の一部例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（.env と config/*.yaml チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動（SystemMonitor のポーリング）
  環境変数でポーリング間隔を調整できます（秒、デフォルト 60）:
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  監視は常に本番 sqlite_path（settings.sqlite_path）を使います。停止はプロジェクトルートの `data/stop_requested.flag` を作成してください。

- 実行エンジン起動（発注プロセス）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ data/paper_trading.db に分離して記録されます。
  - 停止は `data/stop_requested.flag` を作成してください。
  - PID ファイルは `data/execution.pid` に書き出されます（設定で変更可能）。

---

## 運用メモ / 注意点

- KABUSYS_ENV=live を利用する場合は、本番向け設定（LINE 通知など）を必ず確認してください。validate_config は live 時に追加の注意喚起を出します。
- kill.flag（デフォルト KILL_FLAG_PATH= data/kill.flag）を使った安全停止があり、起動時に残っている場合は設定に応じて起動を拒否します。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアします（本番では推奨しません）。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- PyYAML がインストールされていると config/*.yaml のパース検証が有効になります。存在しないファイルは警告になります（validate_config）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数の自動読み込みと Settings クラス（アプリケーション設定）
  - config_setup.py — .env を対話式に生成するウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py — execution モジュールのエクスポート
    - broker_api.py — BrokerAPIProtocol とデータモデル、ファクトリ
    - broker_factory.py — Settings に基づくブローカークライアント生成
    - kabu_client.py — kabuステーション REST API クライアント実装
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — OrderRecord（状態遷移モデル）
    - order_repository.py — SQLite 永続化層（orders テーブルの初期化関数あり）
    - order_manager.py — 発注フロー（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（シグナル処理、WS ドレイン、kill_switch 等）
    - risk_manager.py — リスクガード（Gate1/2/3）
    - reconciler.py — 起動時のリコンシリエーション
  - data/
    - calendar_management.py — マーケットカレンダー管理（J-Quants 連携想定）
    - news_collector.py — RSS からのニュース収集
    - ...（他データ関連ユーティリティ）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル初期化・ログ機能（参照される）
    - system_monitor.py — 実際の監視処理（ポーリングでのメトリクス収集等）
  - utils/
    - logging_setup.py — ロギング初期化ヘルパ
    - process_priority.py — プロセス優先度設定ユーティリティ

（実際のリポジトリにはさらに細分化されたモジュールや補助スクリプトが含まれます）

---

## 参考関数 / 初期化

- orders DB 初期化:
  - 関数: kabusys.execution.order_repository.init_orders_db(conn)
  - 監視 DB 初期化は起動スクリプト内で呼ばれる: init_monitoring_db(sqlite_conn)

必要に応じてスクリプトや小さなユーティリティを追加して DB 初期化を行ってください。

---

## 開発・拡張ポイント

- Live broker クライアントの実装（現在は Mock が動作対象、BrokerClientFactory は未実装のケースで NotImplementedError を投げます）
- YAML 設定ファイル（config/*.yaml）のスキーマ検証の強化
- モニタリング / アラートの拡充（LINE 送信など）
- テストの整備（ユニット・統合テスト）

---

この README はコード内のドキュメント文字列や CLI の挙動に基づいて作成しています。詳細な API 仕様や追加の設定は各モジュールの docstring を参照してください。必要であれば README を拡張してインストール手順やより具体的な運用例（systemd unit・Dockerfile 等）を追加できます。