# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ内 README。  
このドキュメントはコードベースの主要機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

> 注意: 本プロジェクトは実取引（kabuステーション等）を扱う設計を含みます。  
> 開発／検証時は必ず KABUSYS_ENV を `development` または `paper_trading` に設定し、実運用（live）は十分に注意して使用してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤（バックエンド）です。  
主な責務は以下の通りです。

- シグナルに基づく発注（ExecutionEngine）
- 発注状態管理（OrderRecord / OrderRepository / OrderManager）
- ブローカー API 抽象化（KabuStationClient / MockBrokerClient）
- リスク管理（3段階ガード: Gate1/2/3）
- リコンシリエーション（クラッシュ復旧）
- 監視（SystemMonitor, monitoring DB）
- データ処理（マーケットカレンダー、ニュース収集 等）
- 環境設定ウィザード・設定検証ツール

設計上、DB（SQLite / DuckDB）と外部 API へのアクセスを分離し、モッククライアントを使ってローカルでの検証やユニットテストを行えるようになっています。

---

## 主な機能一覧

- 設定関連
  - 対話式 .env 作成ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI (.env と config/*.yaml のチェック): python -m kabusys.validate_config
- 実行系
  - ExecutionEngine: シグナル読み取り→発注→push ドレイン（run_execution.py）
  - MockBrokerClient によるペーパートレード（PAPER_FILL_MODE による挙動変更）
  - Reconciler による起動時復旧（OrderSent の同期、ポジション差分検出）
- 発注・注文管理
  - OrderRecord（状態遷移の検証）
  - OrderRepository（SQLite 永続化）
  - OrderManager（作成・送信・同期・キャンセル）
- リスク管理
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューションレベル（レート制限／サーキットブレーカー）
  - Gate3: メトリクス（ドローダウン監視）
- 監視
  - SystemMonitor（run_monitoring.py によるポーリング）
  - 監視用 SQLite / DuckDB へのログ記録
- データ処理
  - カレンダー管理（next_trading_day 等）
  - ニュース収集（RSS -> raw_news 保存、SSRF 対策等）

---

## セットアップ手順

以下はローカルで開発・検証するための最小手順です。

1. Python 環境（推奨: 3.10+）を準備

2. 依存パッケージをインストール（例）:
   - 必要最小限:
     - duckdb
     - httpx
     - websocket-client
     - pyyaml (設定検証の YAML パース用)
     - defusedxml (RSS パーサ用)
   - インストール例:
     ```
     pip install duckdb httpx websocket-client pyyaml defusedxml
     ```

   プロジェクトに requirements.txt がある場合はそちらを使用してください。

3. プロジェクトルートに .env を作成
   - 対話式で作る:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（下の最小例参照）。

4. 設定を検証:
   ```
   python -m kabusys.validate_config
   ```
   - 警告も FAIL 扱いにする場合:
     ```
     python -m kabusys.validate_config --strict
     ```

5. DB ディレクトリ作成（必要なら）:
   ```
   mkdir -p data
   ```
   実行時に自動生成される箇所もありますが、手動で用意しておくと安全です。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABU_API_BASE_URL — kabu station の base URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用

その他:
- KILL_FLAG_CLEAR_ON_START — 起動時に既存 kill.flag を自動クリアする（1 にするとクリア）
- PAPER_FILL_MODE — paper_trading 用 Mock の約定モード（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

.env の自動読み込み:
- OS 環境変数 > .env.local > .env の優先度でロードされます。  
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

最小の .env（例）:
```
JQUANTS_REFRESH_TOKEN=your_value
KABU_API_PASSWORD=your_value
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

注意: .env を絶対にリポジトリへコミットしないでください（README 内にも警告コメントあり）。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（実運用/ペーパートレード）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` または `development` の場合、MockBrokerClient が使われます（本番ブローカーは未実装で NotImplementedError）。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（秒、デフォルト 60）。

運用時のフラグファイル:
- data/kill.flag — 実行中に kill.flag が存在すると kill_switch を起動（発注停止・キャンセル）
- data/stop_requested.flag — run_monitoring / run_execution のポーリングループを終了するための外部停止フラグ
- PID ファイル: config で指定された場所（デフォルト data/execution.pid）

ログ:
- setup_logging を通じてアプリ名（execution / monitoring）でログ出力されます。LOG_LEVEL 環境変数でレベルを指定してください。

Mock ブローカーの動作（PAPER_FILL_MODE）:
- instant: 発注即全量約定
- partial: 半量約定（手動で fill_order で残りを約定可能）
- never: 注文は pending（OrderSentPendingError）
- reject: 発注拒否（OrderRejectedError）

---

## 開発メモ / 動作の注意点

- ExecutionEngine のセッション制御は市場時間（例: signal_send_start, signal_send_end, market_close）に基づきます。テストでは _process_signals や _drain_push_queue を直接呼ぶことで制御できます。
- リコンシリエーション（Reconciler）は起動時に OrderSent 状態の注文をブローカーと突合して復旧処理を行います。これによりクラッシュ後の整合性を改善します。
- OrderRepository は SQLite を使い、orders テーブルには同一 signal_id の active 注文が同時に 1 件しか入らない UNIQUE 制約が設定されています（レース対策）。
- KabuStationClient（実ブローカー）は httpx / websocket-client を利用しています。実際の kabuステーション API を呼ぶためにはローカルで kabu station® アプリが動作している必要があります（通常ローカル HTTP サーバーを立てる）。
- YAML 設定ファイルの検証には PyYAML が必要です。未インストール時は検証をスキップします（validate_config が警告を出します）。
- news_collector 等は SSRF 対策や受信サイズ制限等セキュリティに配慮した実装です。外部 URL を扱う処理は注意して実行してください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要ファイル一覧（このリポジトリに含まれるファイルを基に整理）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定読み取りと Settings クラス
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py            — BrokerAPI Protocol / データモデル / ファクトリ
    - broker_factory.py        — Settings に基づくクライアント生成
    - kabu_client.py           — KabuStation REST/WebSocket クライアント
    - mock_client.py           — MockBrokerClient（テスト用）
    - order_record.py          — OrderRecord（状態遷移ロジック）
    - order_repository.py      — SQLite 永続化層（orders テーブル）
    - order_manager.py         — 発注・送信・同期・キャンセルの高レベル API
    - execution_engine.py      — ExecutionEngine（セッション制御、push/drain）
    - reconciler.py            — 再起動リコンシリエーション
    - risk_manager.py          — 3段階リスクガード
  - data/
    - calendar_management.py   — マーケットカレンダー管理（DuckDB）
    - news_collector.py        — RSS ニュース収集（defusedxml 等）
    - jquants_client.py        —（参照されるがここに含まれている想定）
  - monitoring/
    - monitoring_db.py         — 監視 DB 初期化 / ログ（参照あり）
    - system_monitor.py        — システム監視ロジック（参照あり）
  - utils/
    - logging_setup.py         — ロギング初期化ユーティリティ
    - process_priority.py      — プロセス優先度設定ユーティリティ

（注）実際のファイル一覧はリポジトリの内容によります。上はこの README 作成時点で読み取れる主要ソースをまとめたものです。

---

## 追加情報・トラブルシューティング

- PyYAML が無ければ validate_config は YAML 内容チェックをスキップしますが、config/*.yaml が破損していると本番で問題になります。可能であれば PyYAML をインストールして検証してください。
- 実運用（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確認し、KILL_FLAG_CLEAR_ON_START は 0 を推奨します。validate_config は live 環境時に追加チェックを行います。
- run_execution 実行時に既に data/stop_requested.flag が存在すると起動をスキップします。不要なら削除してください。
- DuckDB / SQLite のファイルパスは環境変数で上書きできます。ファイルの親ディレクトリが存在しない場合は起動時に自動生成される箇所もありますが、適切な権限があることを確認してください。
- 実ブローカー（KabuStationClient）を利用する場合、API パスワードやネットワーク設定等の正確な準備が必要です。本コードでは本番クライアントの完全動作に関する追加実装や環境依存要件を確認してください（KabuStation の起動など）。

---

必要であれば、README に追加したい内容（インストール済みライブラリ一覧、システム要件、運用手順書、データベース初期化手順、サンプル .env.example など）を指定してください。