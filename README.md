# KabuSys

日本株向け自動売買システムのコアライブラリと起動スクリプト群です。  
このリポジトリは発注エンジン（ExecutionEngine）、監視プロセス（SystemMonitor）、設定ウィザード／検証ツール、データ処理ユーティリティ等を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- シグナルを取り込み発注する ExecutionEngine（Signal Queue 方式）
- 発注のクラッシュ安全性やリコンシリエーション（再同期）
- 3段階のリスクガード（Gate1/2/3）
- Mock ブローカ（ペーパートレード／開発用）と実ブローカクライアント（kabu station）
- 監視（SystemMonitor）と監視 DB（SQLite）
- データ周りのユーティリティ（マーケットカレンダー、ニュース収集など）
- .env の対話式ウィザードおよび起動前設定検証ツール

設計方針の一例：
- 発注処理は DB による永続化（SQLite）と状態遷移（OrderRecord）でクラッシュ耐性を確保
- 本番／検証環境分離（paper_trading は専用 SQLite を使用）
- 外部 API 呼び出しのレート制御・サーキットブレーカーを内蔵

---

## 主な機能一覧

- 設定ウィザード（python -m kabusys.config_setup）で .env を対話式作成
- 起動前チェック（python -m kabusys.validate_config）で環境変数・config/*.yaml を検証
- ExecutionEngine（発注ループ、WebSocket push ドレイン、kill switch）
- Order 状態管理（OrderRecord の状態遷移検証）
- Order 永続化（SQLite を用いた OrderRepository）
- Broker クライアント層（MockBrokerClient / KabuStationClient）
- RiskManager（Gate1: シグナル、Gate2: 実行（レート／CB）、Gate3: ドローダウン）
- Reconciler（起動時の OrderSent 照合・ポジション差分検出）
- データユーティリティ：マーケットカレンダー管理、ニュース収集モジュール
- 監視プロセス（run_monitoring）用ループ・DB 初期化（monitoring 用 SQLite）

---

## 必要条件（概略）

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証で推奨）
- SQLite3（標準ライブラリに同梱）
- OS で許可されているファイル書き込み（data ディレクトリ等）

package 管理ファイルがない場合は手動でインストールしてください。例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし作業ディレクトリへ移動
2. 仮想環境を作成・有効化し依存をインストール（上記参照）
3. .env を作成（対話式）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードで J-Quants トークンや kabu API パスワード等を入力します。
   - .env は Git にコミットしないでください（README 内にも注意が書き出されます）。
4. 作成後、設定検証を実行
   ```bash
   python -m kabusys.validate_config
   # 警告も fail にしたい場合
   python -m kabusys.validate_config --strict
   ```
   - PyYAML が無い場合は YAML 内容の検証がスキップされ、警告が出ます。
5. data ディレクトリ等は起動時に自動作成されますが、手動で準備しておくことも可能です。
6. 実行用データベース（DuckDB / SQLite）はスクリプト内で必要に応じて初期化されます（init_monitoring_db / init_orders_db が呼ばれる）。

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 作成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 起動前設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` または `development` の場合は MockBrokerClient を使用します。
  - `live` は現状では NotImplemented（実ブローカは未実装）になっています。
  - 停止はプロセス外部から data/stop_requested.flag を作成することで検出されます。
  - PID ファイル: デフォルト `data/execution.pid`（設定で変更可）

- 監視ループ起動（SystemMonitor）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書きできます（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用します。
  - 停止検知は data/stop_requested.flag を見ることで行います。

- ライブラリとしての利用
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```
  - Settings クラス経由で各種設定（パス・環境名・閾値など）にアクセスできます。

---

## 主要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意／デフォルトあり:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

.env の自動ロード:
- 実行時に .env と .env.local をプロジェクトルート（.git または pyproject.toml がある位置）を基準に自動読み込みします。
- OSの環境変数は上書きされません（.env.local は override=True ですが protected によって OS 環境は保持されます）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 通常の停止方法 / フラグ

- 実行停止（外部）: プロセスに SIGINT/キーボード割り込みで停止します。
- 管理用フラグ:
  - data/stop_requested.flag — 実行中ループが検出して安全に終了します（run_execution, run_monitoring が参照）。
  - data/kill.flag（KILL フラグ） — ExecutionEngine は起動時に存在する場合、KILL_FLAG_CLEAR_ON_START によって自動クリア有無を判断して起動可否を決めます。実行中に検出した場合は kill_switch を発動して全 active 注文をキャンセルします。

---

## 注意点

- `KABUSYS_ENV=live` の場合は運用注意が多数あります（警告が出力される）。LINE 通知などの設定漏れは本番運用で重要です。
- Live broker client（kabu station を使う実装）は一部で未実装・注意表記があります（BrokerClientFactory で live を選んだ場合 NotImplementedError）。
- config/*.yaml の内容検証は PyYAML の有無に依存します。インストールされていない場合は YAML のパース検証がスキップされ、警告が出ます。
- .env は秘密情報を含むため決して Git にコミットしないでください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数/.env のロードロジック、Settings クラス
- config_setup.py — .env 対話式ウィザード CLI
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine を起動するエントリスクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

subpackages / 主要モジュール:
- execution/
  - broker_api.py — BrokerAPI の Protocol、データモデル、ファクトリ
  - kabu_client.py — kabu station 実クライアント（HTTP + WebSocket）
  - mock_client.py — MockBrokerClient（テスト／paper_trading 用）
  - broker_factory.py — Settings に基づくクライアント生成
  - order_record.py — 注文状態モデルと遷移ロジック
  - order_repository.py — SQLite 永続化層（orders テーブル）
  - order_manager.py — 外向き発注 API（Order 状態遷移 + Broker 呼び出し）
  - execution_engine.py — ExecutionEngine（シグナル処理 + WebSocket ドレイン）
  - reconciler.py — 起動時リコンシリエーション（OrderSent の突合等）
  - risk_manager.py — Gate1/2/3 を実装するリスク管理
- monitoring/
  - monitoring_db.py — 監視用 DB 初期化・ロギング（参照される）
  - system_monitor.py — システム監視ロジック（run_monitoring から利用）
- data/
  - calendar_management.py — マーケットカレンダーユーティリティ
  - news_collector.py — RSS ニュース収集と前処理
  - jquants_client.py — J-Quants API との取り回し（参照）
- utils/
  - logging_setup.py — ロギング初期化ユーティリティ
  - process_priority.py — プロセス優先度設定ユーティリティ

（上記は主要ファイルの一覧と役割。実際の tree はリポジトリで確認してください）

---

## 開発／テストに関するヒント

- ExecutionEngine の単体テストやローカル検証は `KABUSYS_ENV=development` / `paper_trading` として MockBrokerClient を利用するのが安全です。
- MockBrokerClient の fill_mode（instant / partial / never / reject）を用いて各種ケース（即時約定、部分約定、pending、拒否）をテストできます。
- Reconciler は再起動後の自動回復を担うため、order_repository の list_uncertain / list_active の挙動に注目してテストしてください。
- DuckDB を使うクエリはローカルファイル（デフォルト data/kabusys.duckdb）で高速にテストできます。

---

もし README の内容をさらに詳しく（例: API リファレンス、設定ファイルのテンプレート、CI 手順、実行例のログサンプル等）に拡張したい場合は、必要な項目を教えてください。